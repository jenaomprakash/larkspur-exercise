# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A Larkspur disruption-care chat agent with the nine given tools, two of our own (hold_time_left, what_automation_will_not_do) and two served over MCP (next_available_day, fare_rules).
Does: Looks up the booking and flight status, finds alternatives, holds a seat, tells the customer how long the hold lasts, and hands out-of-scope requests like pets in cabin or refunds to a human.
Number: Stage 2 wire rules passed went from 12/15 to 15/15 (n=15 conversations, 3 runs x 5 ticket types), with the tone_safety hard gate no longer failing; on stage 1 the same change was cost-neutral, $0.0738 to $0.0740 per contact (+0%, n=15, 3 runs each), so the longer prompt did not make the agent dearer, and stage 2 got cheaper, $0.0812 to $0.0741 (-9%, n=15).
Safety check: 4 hard-gate suites and 7 eval cases; the agent never confirmed a rebooking from chat in any run, and tone_safety now passes, where before the release was BLOCKED by it.
Next: Make team-0009 (hold option 2 plus a pet-in-cabin handoff) pass every run, not two in three, by naming the flight in the message or agreeing what counts as holding, then extend the tone check to rude but not abusive customers.
Still broken: team-0009 is flaky, passing about two runs in three; the abuse rule only covers abuse and legal threats, so a rude or distressed customer is untested; and the tool schemas still cost about 3,400 tokens in on every turn.
Lever: intelligence

## Priya asked

Costs:
Wrong:
Runs it:
Left out:
