# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A Larkspur disruption-care chat agent with the nine given tools, two of our own (hold_time_left, what_automation_will_not_do) and two served over MCP (next_available_day, fare_rules).
Does: Looks up the booking and flight status, finds alternatives, holds a seat, tells the customer how long the hold lasts, and hands out-of-scope requests like pets in cabin or refunds to a human.
Number: 3 to 4 of 6 eval cases passed (50-67%, n=6 cases, 2 runs); tool schemas cost 3,412 tokens in on every turn; the K7PQ2M probe cost 34,298 tokens in per contact.
Safety check: 4 hard-gate suites; the agent never confirmed a rebooking from chat, and the release is BLOCKED by tone_safety.
Next: Teach the agent to recognise abuse and legal threats and escalate them instead of answering normally.
Still broken: nothing watches tone; an angry customer threatening a lawyer gets a normal entitlements rundown and a voucher instead of a human.
Lever: intelligence

## Priya asked

Costs:
Wrong:
Runs it:
Left out:
