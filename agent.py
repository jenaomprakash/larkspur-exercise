"""Larkspur disruption agent. This is the file you build.

It runs right now, and it is wrong in four places. The trace shows each one
before the code does, so read the trace first:

    python3 run.py K7PQ2M --trace

Where you edit:   grep -n '✏' agent.py   (six marks, one per place)
Steps and gates:  https://anthropicpartnerbasecamp.bts.com/
"""
from __future__ import annotations
from typing import Any, Dict, List
from support import (MODEL, SYSTEM_PROMPT, call_local, execute_tool, mcp_client,
                     new_session, next_available_day, record_tool_result,
                     runtime_preamble)

MAX_TOOL_CALLS = 8  # Larkspur's own build capped the loop here; then a human takes over.

TONE_ADDENDUM = (                        # ✏️ Build 4, step 4.1, intelligence goal
    "\n\nWhen a customer is abusive, insulting, or threatens legal action: stay calm "
    "and respectful. Acknowledge their frustration once, in one sentence, and say you "
    "are bringing in a person. Call escalate_to_human with the reason and a short "
    "summary. Do not give an entitlements rundown, do not issue vouchers, do not offer "
    "a refund pathway, and do not promise any outcome. This applies only to abuse or "
    "legal threats; a customer who is merely upset or asks for a refund is handled by "
    "the normal rules."
)
EXTRA_TOOLS: List[Dict[str, Any]] = [   # ✏️ Build 2, step 2.1: schemas for the tools you add
    {
        "name": "what_automation_will_not_do",
        "description": (
            "Check Handbook section 7, the list of requests this chat is not allowed to "
            "handle itself (for example refunds, cancelling a trip for money back, "
            "rebooking on another airline, groups of 10 or more, unaccompanied minors, "
            "pets in cabin, medical requests, baggage tracing). Call it as soon as the "
            "customer asks for something you are not sure the chat may do, before "
            "promising or attempting it. It does not hand anyone over: it returns the "
            "Handbook's own wording on what people handle and what the chat may still "
            "do, so you can explain it. If a handover is then needed, use "
            "escalate_to_human."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                    "description": (
                        "What the customer is asking for, in a few plain words, "
                        "e.g. 'cancel the whole trip and get a refund'."
                    ),
                },
            },
            "required": ["request"],
        },
    },
    {
        "name": "hold_time_left",
        "description": (
            "Tell the customer how long they have before a seat we are holding for "
            "them is released. Call it when the customer asks how much time is left "
            "on a hold. Needs the hold_id returned by hold_seat earlier in this "
            "conversation; if no seat has been held yet, call hold_seat first. "
            "Read-only: it changes nothing and does not extend the hold. Quote only "
            "the minutes it returns; if it says expired or unknown_hold, say so and "
            "offer to hold the seat again."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hold_id": {
                    "type": "string",
                    "description": "The hold_id returned by hold_seat, e.g. HOLD-1A2B3C",
                },
            },
            "required": ["hold_id"],
        },
    },
]


def hold_time_left(hold_id: str) -> Dict[str, Any]:
    """How long until a held seat is released, read from the mock backend's
    holds against the same fixture clock every other tool uses."""
    from support import mock_backend
    hold = mock_backend._holds.get(hold_id)
    if hold is None:
        return {"status": "error", "reason": "unknown_hold", "hold_id": hold_id}
    seconds = (hold["expires_at"] - mock_backend.FIXTURE_CLOCK).total_seconds()
    if seconds <= 0:
        return {"status": "expired", "hold_id": hold_id, "minutes_left": 0}
    return {
        "status": "active",
        "hold_id": hold_id,
        "option_id": hold["option_id"],
        "minutes_left": int(seconds // 60),
        "seconds_left": int(seconds),
    }


def what_automation_will_not_do(request: str) -> Dict[str, Any]:
    """Answer only from Handbook section 7 in fare_rules_excerpt.md; never invent."""
    from pathlib import Path
    path = Path(__file__).resolve().parent / "data" / "americas" / "fare_rules_excerpt.md"
    text = path.read_text(encoding="utf-8")
    marker = "### 7. What chat automation will not do"
    if marker not in text:
        return {"error": "Section 7 was not found in the Handbook file."}
    section = text.split(marker, 1)[1].split("\n### ", 1)[0].strip()
    people_part = section.split(" are handled by people.", 1)[0]
    handled_by_people = [i.strip().removeprefix("and ").strip()
                         for i in people_part.replace(", and ", ", ").split(",") if i.strip()]
    words = [w for w in request.lower().replace("-", " ").split() if len(w) > 3]
    matches = [item for item in handled_by_people
               if any(w.rstrip("s") in item.lower() for w in words)]
    return {
        "request": request,
        "source": "Larkspur Handbook v14.3, section 7",
        "matched_items_handled_by_people": matches,
        "match_note": ("No item in section 7 matched this request; the Handbook does not "
                       "say it is restricted.") if not matches else "",
        "section_7_text": section,
    }


LOCAL_TOOLS: Dict[str, Any] = {          # ✏️ Build 2, step 2.1: the functions behind them
    "what_automation_will_not_do": what_automation_will_not_do,
    "hold_time_left": hold_time_left,
}


def text_of(response) -> str:
    """Given. The last non-empty text block, never content[0]."""
    texts = [b.text for b in response.content if getattr(b, "type", None) == "text" and b.text]
    return texts[-1] if texts else ""


def tool_results(response) -> List[Dict[str, Any]]:
    """Given. Runs every tool_use block and packages the results the way the
    API expects them back. A tool can live in three places: the MCP server,
    LOCAL_TOOLS, or support/tools.py."""
    # three branches, no try/except in this file: mcp_client.call_remote() and
    # support.call_local() answer with an error dict instead of raising, and both
    # record what came back on the trace
    results = []
    for block in response.content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if block.name in mcp_client.tool_names:
            output = mcp_client.call_remote(block.name, block.input)
        elif block.name in LOCAL_TOOLS:
            output = call_local(LOCAL_TOOLS[block.name], block.name, block.input)
        else:
            output = execute_tool(block.name, block.input)
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(output),
        })
    return results


def run_agent(pnr: str, last_name: str, message: str) -> str:            # ✏️ Build 1, step 1.2
    """Run the tool loop until Claude stops asking for tools. Return its final text."""
    client, tracer = new_session()
    tools = tool_list()
    messages = [
        {"role": "user", "content": f"PNR {pnr}, last name {last_name}. {message}"},
    ]

    response = client.messages.create(
        model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
        thinking={"type": "adaptive"}, tools=tools, messages=messages,
    )

    answer = ""
    turns = 1
    while response.stop_reason == "tool_use" and turns < MAX_TOOL_CALLS:
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results(response)})
        answer = text_of(response)
        response = client.messages.create(
            model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
            thinking={"type": "adaptive"}, tools=tools, messages=messages,
        )
        turns += 1

    return text_of(response)


def tool_list() -> List[Dict[str, Any]]:                   # ✏️ Build 2, step 2.2
    """Given. Exactly what Claude is offered on every turn; run.py --show-tools
    prints this list."""
    return build_tools() + EXTRA_TOOLS + mcp_client.tools()


# ──────────────────────────────────────────────────────────────────────────────
# Below this line: what Claude is told about each tool. Step 1.3.
# The functions these describe are written and correct, in support/tools.py.
# ──────────────────────────────────────────────────────────────────────────────
def build_tools() -> List[Dict[str, Any]]:                 # ✏️ Build 1, step 1.3
    """Anthropic-shaped schemas: name, description, input_schema. What Claude is
    told about each of the nine tools, and all it is ever told."""
    return [
        {
            "name": "lookup_booking",
            "description": (
                "Retrieve a Larkspur reservation from Altura by confirmation code (PNR) "
                "and the passenger's last name. Both are required to prevent a lookup on "
                "a guessed PNR. Returns fare family, loyalty tier, the segment that needs "
                "attention, and any group/partner/minor/SSR flags relevant to scope."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "last_name": {"type": "string"}},
                "required": ["pnr", "last_name"],
            },
        },
        {
            "name": "get_flight_status",
            "description": (
                "Look up a Larkspur or Larkspur Link flight's current OpsFeed status for "
                "one local date: status, delay minutes, and cause. Use this before telling "
                "a customer anything about a flight's timing; never state it from memory."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "flight_no": {"type": "string"},
                    "date": {"type": "string", "description": "The flight's local departure date, formatted YYYY-MM-DD (e.g. 2025-05-08). Take it from the booking."},
                },
                "required": ["flight_no", "date"],
            },
        },
        {
            "name": "search_alternatives",
            "description": (
                "Find alternative Larkspur flights for a customer whose flight is cancelled "
                "or significantly delayed. Call it only after lookup_booking and "
                "get_flight_status show the disruption, and before offering or holding any "
                "seat. Returns candidate flights with times and seat availability; never "
                "invent options it did not return."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string", "description": "The 6-character booking reference from lookup_booking."}},
                "required": ["pnr"],
            },
        },
        {
            "name": "check_policy",
            "description": (
                "Resolve what Larkspur owes this customer for the disruption: rebooking "
                "waiver, refund path, meal/hotel/ground care, goodwill eligibility and cap, "
                "and any escalation triggers. cause_code, delay_minutes and status describe "
                "what get_flight_status told you; fare_family, loyalty_tier and whether this "
                "is overnight are looked up from the booking, not asked of you. Every "
                "response carries a policy_row_id. Cite it if you reference this decision "
                "again. When you refuse or limit something the customer asked for, give "
                "only the reason the result itself states (its cause_class or policy "
                "reason), in the result's own words. Always state the policy_row_id and "
                "the result's cause_class in plain words (for example that the delay is "
                "classed as outside Larkspur's control) as the reason for every refusal. "
                "If an item says only eligible: false, say Larkspur policy row "
                "<policy_row_id> does not cover it, together with that cause_class. "
                "Never explain why in any other words (not the time of day, not where the "
                "customer will be), and never add a reason of your own."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"},
                    "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]},
                    "delay_minutes": {"type": "integer"},
                    "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                    "wait_minutes_for_alternative": {"type": "integer"},
                    "chosen_option_id": {"type": "string"},
                },
                "required": ["pnr", "cause_code", "delay_minutes", "status"],
            },
        },
        {
            "name": "hold_seat",
            "description": "Place a 15-minute hold on one alternative. Reversible. It simply expires.",
            "input_schema": {
                "type": "object",
                "properties": {"option_id": {"type": "string"}, "pnr": {"type": "string"}},
                "required": ["option_id", "pnr"],
            },
        },
        {
            "name": "confirm_rebooking",
            "description": (
                "Finalize a held seat. Irreversible. Requires a confirmation_token that "
                "only the customer's own Confirm-click can produce. You cannot supply it "
                "yourself, and 'the customer said yes' in chat does not substitute for it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"hold_id": {"type": "string"}, "confirmation_token": {"type": "string"}},
                "required": ["hold_id", "confirmation_token"],
            },
        },
        {
            "name": "issue_voucher",
            "description": (
                "Issue a meal, ground, hotel, or goodwill voucher. Auto-approves within the "
                "policy's threshold for that type; above it, returns a pending status for a "
                "human. It does not fail. Always pass the policy_row_id that made it eligible."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "voucher_type": {"type": "string", "enum": ["meal", "ground", "hotel", "goodwill"]},
                    "amount_usd": {"type": "number"},
                    "pnr": {"type": "string"},
                    "policy_row_id": {"type": "string"},
                },
                "required": ["voucher_type", "amount_usd", "pnr", "policy_row_id"],
            },
        },
        {
            "name": "escalate_to_human",
            "description": (
                "Hand this conversation to a human, with your reasoning attached. Use for "
                "groups, partner segments, unaccompanied minors, refunds, or anything else "
                "out of scope. This is the correct outcome for those cases, not a failure."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"}, "reason": {"type": "string"},
                    "summary_for_human": {"type": "string"}, "queue": {"type": "string"},
                },
                "required": ["pnr", "reason", "summary_for_human"],
            },
        },
        {
            "name": "send_confirmation",
            "description": "Send the customer a written confirmation of what was just done. Benign.",
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "message": {"type": "string"}},
                "required": ["pnr", "message"],
            },
        },
    ]
