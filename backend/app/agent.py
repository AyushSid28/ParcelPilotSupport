from __future__ import annotations

import json
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
- What needs attention → get_ops_pulse
Do not call get_order, get_account, or search_documents for those questions.

Never put in the user-visible reply: PDF filenames, Sources, reason_codes, proposal UUIDs, or raw JSON.

Actions:
- Investigate / status / "have we breached SLA" is a question. Answer it. Do not propose_escalation or propose_task until they clearly say escalate, open a ticket, or go ahead.
- "Can I cancel?" is not a cancel request.
- Yes after you offered return-to-origin → propose_task for RTO, then wait for the confirm card.

Copy:
- 2–4 sentences. No tables.
- CONTRACT_WAIVES_FEE: still BOOKED; agreement waives the SOP ₹250-after-30-minutes fee.
- PICKED_UP: cannot cancel; offer RTO.
- P1 SLA breach: state that it is late and ask if they want it escalated. Do not claim you already flagged it.
- Customers: never mention TKT-450/451 unless they asked about that ticket.
- Off-topic: one line that you only do ParcelPilot support. No forums.
"""


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
    work = [{"role": "system", "content": SYSTEM.format(audience=audience)}, *_for_model(messages)]
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
                work.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    }
                )
            continue

        text = msg.content or ""
        yield {"event": "final", "data": {"text": text}}
        return

    yield {"event": "final", "data": {"text": "I hit the tool-step limit. Please confirm a narrower question or escalate."}}
