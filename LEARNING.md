## Phase 3-4: Agent reasoning + policy gating

- Built diagnose_opportunity() — first LLM call, grounded in a real evidence bundle from the database.
- Learned the difference between a soft guardrail (asking the LLM nicely in the prompt) and a hard guardrail (validating output in code afterward) — the LLM initially suggested "Free Shipping" and "Cart Recovery Email," which weren't in our approved action list, before we added the hard guardrail.
- Noticed the LLM used "$" instead of "₹" in its diagnosis text once — a reminder that constraining content (actions) doesn't automatically constrain formatting/details we didn't explicitly ask about.
- Built the policy engine (rules.py) as pure deterministic Python — no LLM — enforcing max discount %, and an order-value threshold requiring approval. Tested all three outcomes (APPROVED/BLOCKED/NEEDS_APPROVAL) directly.
- Built the audit trail (AuditLog table) and confirmed a full pipeline run (evidence -> diagnosis -> policy check -> saved audit record) is queryable end to end.