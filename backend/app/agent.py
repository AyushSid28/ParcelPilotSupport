from __future__ import annotations

import json
import re
from collections.abc import Iterator

from openai import OpenAI

from app.config import settings
from app.models import Actor
from app.tools import SCHEMAS, run

SYSTEM = """You are a ParcelPilot support agent. Short chat. No research-report voice.

Clock: 2026-08-16 11:00 Asia/Kolkata. Currency INR.

{audience}

Tools:
- Cancel/fee → only assess_cancellation(order_id)
- Credit → only assess_failed_pickup_credit(order_id)
- Ticket status/SLA → only classify_severity_and_sla(ticket_id)
- Order / shipment status (ORD-*) → get_order(order_id). Staff may look up any order. If pickup is late or still BOOKED with carrier_fault, you may also call assess_failed_pickup_credit.
- What needs attention → get_ops_pulse
Do not call search_documents for those questions. Never say you don't have the order or to check the dashboard unless get_order returned not_found.

Never put in the user-visible reply: PDF filenames, Sources, reason_codes, proposal UUIDs, or raw JSON.

Actions:
- Investigate / status / "have we breached SLA" is a question. Answer it. Do not propose_escalation or propose_task until they clearly say escalate, open a ticket, or go ahead.
- "Can I cancel?" is not a cancel request.
- "Please cancel" / "go ahead and cancel" / apply the credit / RTO yes → call propose_task (title like "Cancel ORD-1001, no fee"). Then wait. Never say the order is cancelled or the credit is applied until they hit Confirm.
- Yes after you offered return-to-origin → propose_task for RTO, then wait for the confirm card.
- Billing contact / how-to that is not in current SOP or product docs → this is still ParcelPilot support. Call propose_escalation (P3) so a human can handle it. Do not invent steps. Do not say you only handle shipments.
- Exposed API key / credentials → ParcelPilot P1. Tell them to rotate the key and not paste secrets in chat. Call propose_escalation. Do not dump key material.

Copy:
- 2–4 sentences. No tables.
- Read fee_inr from the last assess_cancellation result. SOP_CANCELLATION_FEE / fee 250 = cannot cancel for free; charge ₹250. CONTRACT_WAIVES_FEE or WITHIN_FREE_WINDOW / fee 0 = no charge. "without a fee?" is a question, not an instruction to waive.
- CONTRACT_WAIVES_FEE: still BOOKED; agreement waives the SOP ₹250-after-30-minutes fee.
- PICKED_UP: cannot cancel; offer RTO.
- P1 SLA breach: state that it is late and ask if they want it escalated. Do not claim you already flagged it.
- Customers: never mention TKT-450/451 unless they asked about that ticket.
- Order not_found for this account: say you cannot find that order on this account. Do not quote cancel/credit SOP for a missing order.
- Known issues: bulk CSV limit is 5000 rows (KI-208). Splitting around 3000 is a workaround, not the product limit. Do not say the limit is 3k.
- Off-topic (unrelated forums, recipes, etc.): one line that you only do ParcelPilot support. No forums.
- After a proposal tool returns: say you prepared the cancel/credit/escalation and they should Confirm. Never claim it already happened.
- Plain sentences only. No markdown, no **stars**, no bullet hyphens.
"""


def _tool_hint(name: str, result: dict) -> str | None:
    if result.get("error"):
        return "The record is not visible to this caller. Do not invent policy for another account."
    if name == "assess_cancellation":
        return (
            f"Use these fields exactly: allowed={result.get('allowed')} fee_inr={result.get('fee_inr')} "
            f"reason_codes={result.get('reason_codes')} next_step={result.get('next_step')}. "
            "fee_inr 250 means a ₹250 fee applies. fee_inr 0 means no fee. "
            "STATUS_PICKED_UP / STATUS_DELIVERED: cannot cancel."
        )
    if name == "assess_failed_pickup_credit":
        return (
            f"Use these fields exactly: eligible={result.get('eligible')} amount_inr={result.get('amount_inr')} "
            f"reason_codes={result.get('reason_codes')}. Quote that credit amount; do not use SOP min(500, 10%)."
        )
    if name == "get_order":
        return (
            f"Use this record: status={result.get('status')} account_id={result.get('account_id')} "
            f"carrier_fault={result.get('carrier_fault')} pickup_actual_at={result.get('pickup_actual_at')}. "
            "State the status. Do not tell the user to check a dashboard."
        )
    if name == "classify_severity_and_sla":
        return (
            f"Use these fields exactly: severity={result.get('severity')} breached={result.get('breached')} "
            f"elapsed_minutes={result.get('elapsed_minutes')} target_minutes={result.get('target_minutes')}."
        )
    if name == "get_ops_pulse":
        return (
            "Summarize the issues list. Bulk CSV is KI-208 (5,000-row product limit); ~3,000 is a split workaround, not the limit."
        )
    return None


def _plain_reply(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = text.replace("`", "")
    return text.strip()


def _for_model(messages: list[dict]) -> list[dict]:
    """Drop UI-only fields. Groq/OpenAI reject unknown keys like `sources`."""
    out = []
    for raw in messages:
        role = raw.get("role")
        if role not in {"user", "assistant", "system", "tool"}:
            continue
        item = {"role": role, "content": raw.get("content") or ""}
        if raw.get("tool_calls"):
            item["tool_calls"] = raw["tool_calls"]
        if raw.get("tool_call_id"):
            item["tool_call_id"] = raw["tool_call_id"]
        out.append(item)
    return out


def _last_user_text(messages: list[dict]) -> str:
    for raw in reversed(messages):
        if raw.get("role") == "user":
            return raw.get("content") or ""
    return ""


def _mentioned_ids(text: str) -> tuple[list[str], list[str]]:
    orders = [m.upper() for m in re.findall(r"ORD-\d+", text, re.I)]
    tickets = [m.upper() for m in re.findall(r"TKT-\d+", text, re.I)]
    return list(dict.fromkeys(orders)), list(dict.fromkeys(tickets))


def _preload(text: str, actor: Actor, conn) -> tuple[list[dict], list[dict]]:
    """Look up IDs in the latest message so the model cannot skip tools."""
    events: list[dict] = []
    loaded: list[dict] = []
    orders, tickets = _mentioned_ids(text)
    low = text.lower()
    for order_id in orders:
        if "cancel" in low:
            name, args = "assess_cancellation", {"order_id": order_id}
        elif "credit" in low:
            name, args = "assess_failed_pickup_credit", {"order_id": order_id}
        else:
            name, args = "get_order", {"order_id": order_id}
        events.append({"event": "tool_start", "data": {"name": name, "args": args}})
        result = run(name, args, actor, conn)
        events.append({"event": "tool_end", "data": {"name": name, "result": result}})
        loaded.append({"tool": name, "result": result})
        if name == "get_order" and not result.get("error") and result.get("status") == "BOOKED" and result.get("carrier_fault"):
            extra = {"order_id": order_id}
            events.append({"event": "tool_start", "data": {"name": "assess_failed_pickup_credit", "args": extra}})
            credit = run("assess_failed_pickup_credit", extra, actor, conn)
            events.append({"event": "tool_end", "data": {"name": "assess_failed_pickup_credit", "result": credit}})
            loaded.append({"tool": "assess_failed_pickup_credit", "result": credit})
    for ticket_id in tickets:
        args = {"ticket_id": ticket_id}
        events.append({"event": "tool_start", "data": {"name": "classify_severity_and_sla", "args": args}})
        result = run("classify_severity_and_sla", args, actor, conn)
        events.append({"event": "tool_end", "data": {"name": "classify_severity_and_sla", "result": result}})
        loaded.append({"tool": "classify_severity_and_sla", "result": result})
    return events, loaded


def _client() -> OpenAI:
    kwargs = {"api_key": settings.llm_key}
    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    return OpenAI(**kwargs)


def iter_chat(messages: list[dict], actor: Actor, conn) -> Iterator[dict]:
    if not settings.llm_key:
        yield {"event": "error", "data": {"message": "Set GROQ_API_KEY or OPENAI_API_KEY in .env"}}
        return

    audience = (
        "The user is ParcelPilot staff. Talk like a colleague. Do not promise to 'keep the customer updated' unless they asked you to message the customer."
        if actor.is_staff
        else "The user is a customer. Do not mention internal PDFs or old ticket numbers."
    )
    client = _client()
    system = SYSTEM.format(audience=audience)
    events, loaded = _preload(_last_user_text(messages), actor, conn)
    for ev in events:
        yield ev
    if loaded:
        system += (
            "\n\nAuthoritative records for this turn (ignore any earlier claim that you lacked these details; "
            "never tell the user to check a dashboard):\n"
            + json.dumps(loaded)
        )
    work = [{"role": "system", "content": system}, *_for_model(messages)]
    for _ in range(8):
        try:
            resp = client.chat.completions.create(
                model=settings.llm_model,
                messages=work,
                tools=SCHEMAS,
            )
        except Exception:
            yield {
                "event": "error",
                "data": {"message": "I couldn't complete that just now. Please send your last message again."},
            }
            return
        choice = resp.choices[0]
        msg = choice.message
        if msg.tool_calls:
            work.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                yield {"event": "tool_start", "data": {"name": tc.function.name, "args": args}}
                result = run(tc.function.name, args, actor, conn)
                yield {"event": "tool_end", "data": {"name": tc.function.name, "result": result}}
                if result.get("needs_confirmation"):
                    yield {"event": "proposal", "data": result}
                payload = dict(result)
                hint = _tool_hint(tc.function.name, result)
                if hint:
                    payload["agent_must"] = hint
                work.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(payload),
                    }
                )
            continue

        text = _plain_reply(msg.content or "")
        yield {"event": "final", "data": {"text": text}}
        return

    yield {"event": "final", "data": {"text": "I hit the tool-step limit. Please confirm a narrower question or escalate."}}
