## Phase 3-4: Agent reasoning + policy gating

- Built diagnose_opportunity() — first LLM call, grounded in a real evidence bundle from the database.
- Learned the difference between a soft guardrail (asking the LLM nicely in the prompt) and a hard guardrail (validating output in code afterward) — the LLM initially suggested "Free Shipping" and "Cart Recovery Email," which weren't in our approved action list, before we added the hard guardrail.
- Noticed the LLM used "$" instead of "₹" in its diagnosis text once — a reminder that constraining content (actions) doesn't automatically constrain formatting/details we didn't explicitly ask about.
- Built the policy engine (rules.py) as pure deterministic Python — no LLM — enforcing max discount %, and an order-value threshold requiring approval. Tested all three outcomes (APPROVED/BLOCKED/NEEDS_APPROVAL) directly.
- Built the audit trail (AuditLog table) and confirmed a full pipeline run (evidence -> diagnosis -> policy check -> saved audit record) is queryable end to end.

## Phase: Measuring Incremental Revenue (did the agent actually help, or would it have happened anyway?)

**What we were trying to prove:** if our agent sends a discount to a customer, did THAT actually cause them to buy — or would they have bought anyway? To find out, we split abandoned orders into two random groups:
- Treatment group = agent takes action on them
- Control group = agent does nothing, just used to compare against

**Mistakes we made and fixed (good lessons, not embarrassing ones):**

1. **Ran things in the wrong order.**
   We assigned customers to treatment/control groups AFTER already running the agent — so nobody was labeled "treatment" yet when the agent acted. Result: our numbers showed 0 treated customers.
   **Lesson:** always decide who's in which group BEFORE doing anything to them. Fixed by running steps in the correct order: seed data → assign groups → THEN run the agent → THEN measure results.

2. **Hit real limits from Razorpay (not a bug, just a real API being a real API).**
   While testing at scale (50 orders), Razorpay started rejecting requests: first for calling too fast ("Too many requests"), then for hitting a hard cap of 30 test payment links total. Our error-handling code (built earlier) caught both cleanly — nothing crashed.
   **Fix:** added a "dry run" mode — for large batch testing, we log what WOULD have happened without actually calling Razorpay every single time. Clearly labeled "DRY RUN" in our records, never pretending it was real.

3. **Accidentally counted the same customer's outcome more than once.**
   Our code randomly decides if a treated customer "converts" (buys). But we only saved that result when they DID convert — if they didn't, we left them unmarked, so running the check again gave them another random chance. This kept inflating our success rate every time we reran it (44% instead of the real ~23%).
   **Fix:** now every customer gets exactly ONE random roll, saved permanently — whether they converted or not — so re-running the check never re-rolls anyone.

**Final, correct result:**
- 34 real customers got a genuine agent-driven intervention
- 8 of them were simulated to convert (~23.5%)
- Control group (487 people, no action taken): 0% — because by design, nothing happens to them
- Estimated incremental revenue caused by the agent: ~₹20,457

**Honest note for the demo:** control staying at exactly 0% is a simplification — in real life, some customers would return and buy on their own even with no action. We're not claiming otherwise; it's a known limitation of this MVP version.



## Phase: LangGraph orchestration

- Converted our manually-scripted pipeline (diagnose -> policy check -> log -> execute) into a real LangGraph state graph, with each step as a node and one shared "state" object passed between them.
- The most important new thing: a CONDITIONAL edge after the policy gate. If an action is APPROVED, the graph moves to the execute node. If NEEDS_APPROVAL or BLOCKED, the graph ends right there - the execute node never runs at all. This makes "gated" a structural property of the graph itself, not just an if-check we have to trust.
- Learned that multi-line Python commands with nested quotes break easily when typed directly into PowerShell - safer to write a small real .py file for any test more than one line long.

## Phase: Direction B (conversational checkout) connected to Direction A

- Built a chat-style product recommender (grounded only in our real catalog, same guardrail pattern as before) plus a function to create a REAL order from that recommendation.
- Key design choice: an abandoned conversational order is saved using the exact same Order/OrderItem/CheckoutEvent tables as our synthetic data - so our existing LangGraph agent picks it up automatically, with zero new logic. Proved this live: a simulated abandoned chat-checkout flowed straight into diagnose -> policy gate -> execute.
- Noticed the LLM's diagnosis text mentioned "shipping cost" once, which wasn't in our actual evidence data - a reminder that guardrails on STRUCTURED fields (like action type) don't automatically fact-check every sentence of free-text reasoning.