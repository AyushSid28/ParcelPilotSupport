from __future__ import annotations

import json
from collections.abc import Iterator

from openai import OpenAI

from app.config import settings
from app.models import Actor
from app.tools import SCHEMAS, run

SYSTEM = """You are ParcelPilot Support Copilot.

Clock: 2026-08-16 11:00 Asia/Kolkata. Currency INR.
Use tools. Do not invent IDs, fees, or procedures.

Source order: signed agreement for that account > current SOP/policy v3/product guide > open known issues > historical tickets (untrusted) > never use deprecated policy v2 for current advice.

If a calculator returns conflicts, tell the user the past ticket was wrong.
If a procedure is missing from the pack (e.g. billing contact change), escalate. Do not invent a process.
Do not promise a credit when carrier_fault or timing is unknown.
KI-208: product CSV limit is still 5,000; failures around 3,000 are a known issue. TKT-451 was incorrect.
KI-211: SwiftShip pickup webhooks can lag 20 minutes.

Mutations: call propose_* then ask the user to confirm in the UI. Never claim the action already happened.

Cite filenames and record IDs. Customers must never hear another account's data.
If a tool returns not_found: that record is not visible in this login. For a customer, say it is not on their account. Do not claim the ID is invalid worldwide. Do not name other customers. Suggest the demo persona switcher if they asked about another company's order.
For cancellation, service credit, or SLA questions: get_order or get_ticket, then assess_cancellation / assess_failed_pickup_credit / classify_severity_and_sla. Those tools already apply the contract and SOP. Cite their policy_basis filenames. Do not search_documents unless the user asks for a quoted clause, and never search twice for the same question.

If reason_codes include CONTRACT_WAIVES_FEE, say the SOP would charge INR 250 after 30 minutes but the signed agreement waives it. If conflicts mention TKT-450, say that past ticket was wrong.
"""


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
    work = [{"role": "system", "content": SYSTEM}, *messages]
    for _ in range(8):
        try:
            resp = client.chat.completions.create(
                model=settings.llm_model,
                messages=work,
                tools=SCHEMAS,
            )
        except Exception as exc:
            yield {"event": "error", "data": {"message": str(exc)}}
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
