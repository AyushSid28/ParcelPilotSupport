from __future__ import annotations

import json
from collections.abc import Iterator

from openai import OpenAI

from app.config import settings
from app.models import Actor
from app.tools import SCHEMAS, run

SYSTEM = """You are a ParcelPilot support agent. Write like a human on chat, not a research brief.

Clock: 2026-08-16 11:00 Asia/Kolkata. Currency INR.

For cancel / fee / credit questions call ONE tool: assess_cancellation or assess_failed_pickup_credit with the order id. That tool already loads the order, account, and contract. Do not call get_order, get_account, or search_documents.

For tickets call classify_severity_and_sla or get_ticket. For "what needs attention" call get_ops_pulse.

Rules:
- 2–4 short sentences. No markdown tables. No reason_codes. No PDF filenames.
- If CONTRACT_WAIVES_FEE: SOP would charge ₹250 after 30 minutes of booking; the signed agreement waives the fee for any BOOKED shipment before pickup.
- If STATUS_PICKED_UP: cannot cancel; they can ask for return-to-origin.
- If a conflict ticket (e.g. TKT-450) is in the tool output, mention the old answer was wrong, once.
- Do not invent procedures. Billing-contact change is not in the pack — escalate.
- Do not promise a credit if the tool says uncertain.
- Never use deprecated policy v2.
- "Can I cancel?" is not a request to cancel. Only propose_* if they ask you to actually do it.
- If they reply yes / go ahead after you offered return-to-origin, call propose_task titled for return-to-origin on that order id, then wait for the confirm card.
- If a tool returns not_found for a customer, say it is not on this account.
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

    client = _client()
    work = [{"role": "system", "content": SYSTEM}, *_for_model(messages)]
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
