# Revenue Autopilot

**An agentic revenue-growth system for Razorpay merchants — built for the Razorpay AI Buildathon, Track 1: AI Growth & Agentic Commerce.**

🔗 **Live demo:** https://revenue-autopilot.onrender.com
*(Free-tier hosting — may take 30-60 seconds to wake up on first load.)*

---

## What It Solves

Merchants lose revenue in ways that are invisible or hard to act on: abandoned checkouts, missed cross-sells, hesitant high-intent customers who never convert. Existing tools either just *report* this ("sales dropped 12%") or blindly automate it (spam every customer with a discount) — neither is trustworthy for real money decisions.

**Revenue Autopilot** is an AI agent that:
1. Detects a specific revenue-loss moment (an abandoned checkout)
2. Diagnoses the likely cause, grounded only in real customer/order data
3. Proposes the best intervention (reminder, discount, or cross-sell)
4. Checks that decision against hard-coded merchant limits (bounded + gated)
5. Executes it via real Razorpay test-mode APIs
6. Measures whether the intervention **actually caused** additional revenue — not just correlated with it — using a control/treatment comparison

The core differentiator: we don't just report that revenue went up. We estimate the revenue *the agent itself caused*, distinct from revenue that would have happened anyway.

---

## Architecture

![Revenue Autopilot Architecture](./docs/architecture.svg)

A second entry point — **conversational checkout** (Direction B: agent-to-agent/AI-buyer commerce) — lets a customer describe what they want in natural language, get a recommendation from the real product catalog, and attempt checkout. If that checkout is abandoned, it flows into the **exact same agent loop** above, with zero additional logic — proving both track directions are one connected system, not two demos glued together.

---

## Trust Boundary Matrix

Every component in this system has a clearly scoped, limited authority — no single part (especially the LLM) can act alone on money.

| Component | Role | Execution Authority |
|---|---|---|
| **LLM (diagnosis agent)** | Diagnoses the opportunity, proposes candidate actions | **None.** Can only choose from a fixed, code-enforced list of approved actions (`reminder`, `discount`, `cross_sell`) — any other suggestion is rejected before it's ever used. |
| **Policy Engine** | Decides if/how an action executes | **Absolute.** Deterministic Python, no LLM involved. Enforces max discount %, order-value approval thresholds. Every decision returns a human-readable reason. |
| **Audit Trail** | Persistent record of every decision | **Read-only, permanent.** Every diagnosis, policy decision, and outcome is logged — including actions that were blocked or held for approval. |
| **Executor** | Physically calls Razorpay | **Gated.** Only runs if the Policy Engine marked an action `APPROVED`. Retries safely on failure, never creates duplicate payment actions. |
| **Merchant (human)** | Approves higher-value actions | **Override authority.** Any action above the auto-approve threshold is held until a human explicitly approves it via the dashboard. |

---

## Guardrails

Two layers, deliberately kept separate:

- **Soft guardrail (prompt-level):** the LLM is explicitly instructed to choose only from `reminder`, `discount`, `cross_sell`, and to never invent numbers or facts beyond the evidence it's given.
- **Hard guardrail (code-level):** after every LLM response, the chosen action is validated in Python against the same approved list. Anything outside it is rejected and logged — the LLM's compliance is never assumed, only the code's enforcement is trusted. This caught real out-of-scope suggestions ("Free Shipping," "Cart Recovery Email") during development.

The same discipline applies to money: numbers used in policy checks (discount %, order value, thresholds) always come from the database or hard-coded merchant policy — never from LLM output.

---

## How We Know It's Not Hallucinating

- **Structured output only:** the LLM is required to return JSON in a fixed shape, not free text — this alone rules out most silent drift.
- **Every diagnosis is grounded in a specific, database-sourced evidence bundle** (customer history, order value, cart contents, checkout stage) passed directly into the prompt — the LLM is instructed to reason only from this, never outside it.
- **Post-hoc validation, not trust:** every returned action is checked in code against the approved action list before it can proceed to the policy gate. Invalid actions are rejected and logged, never silently used.
- **Money math is never LLM-generated:** discount amounts, policy thresholds, and incremental revenue calculations are all deterministic Python — the LLM never computes or states a financial figure that gets acted on directly.
- **Known gap, stated honestly:** free-text reasoning (the `diagnosis` field) is not fact-checked line-by-line — during testing we caught one instance where the model mentioned "shipping cost," a detail not present in the evidence. This shows our guardrails constrain *actions*, not every sentence of *explanation* — a real limitation worth continued work, not hidden.

---

## Tech Stack

- **Backend:** Python, FastAPI
- **Agent orchestration:** LangGraph (explicit `StateGraph`)
- **LLM:** Groq (`openai/gpt-oss-20b`)
- **Database:** SQLite (SQLAlchemy ORM)
- **Payments:** Razorpay Python SDK, test mode
- **Frontend:** Plain HTML/JS dashboard (no framework)
- **Deployment:** Render (free tier)

Deliberately not used: Redis, a vector DB/RAG, fine-tuning, a frontend framework — none were needed for this scope, and adding them would have been unjustified complexity.

---

## What Broke, and How We Got Out

Real issues hit during development, kept honest rather than polished away:

- **Razorpay test-mode has a hard cap of 30 payment links per business account** (undocumented until we hit it during batch testing). Fixed by adding a `dry_run` mode — batch/demo runs simulate execution and log it as clearly labeled "DRY RUN," never disguised as real.
- **Groq's per-minute token rate limit** was exceeded during a 50-order batch run. Our existing retry/failure-handling logic caught every failure cleanly (no crash), and we added a longer backoff specifically for rate-limit errors.
- **A duplicate route definition** silently caused `dry_run=true` requests to hit the old, unguarded code path — no error was raised, it just silently made real API calls. Found by checking terminal logs for unexpected Razorpay retries, not by any crash. Fixed by removing the duplicate and verifying only one route definition existed.
- **A double-simulation bug** in our incremental-revenue measurement: unconverted orders weren't marked as "already simulated," so re-running the simulation re-rolled them, inflating the apparent conversion rate (44% vs. the honest ~23.5%). Fixed by giving every order exactly one permanent, non-reversible simulated outcome.

Full details of each issue, and the reasoning behind every design decision, are in [`LEARNING.md`](./LEARNING.md).

---

## Known Limitations (stated honestly)

- Customer response to interventions (discount/reminder recovery) is a **modeling assumption**, not observed real behavior — clearly labeled as such in code and data (`SIMULATED_RECOVERY_RATES`).
- The control group's conversion rate is fixed at 0% by design (nothing acts on them) — a real production experiment would also model organic return behavior in the control group.
- SQLite on Render's free tier is not persistent across redeploys — the live demo's data is re-seeded via a protected admin endpoint, not meant to survive indefinitely.

---

## Running Locally

```bash
git clone https://github.com/sumit2000-deltech/revenue-autopilot.git
cd revenue-autopilot
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`) with:






Seed the database and run the agent pipeline:
```bash
python -c "from app.data.database import Base, engine; from app.data import models; Base.metadata.create_all(bind=engine)"
python -m app.data.seed
python -c "from app.data.analytics import assign_experiment_groups; assign_experiment_groups()"
python -m app.agent.batch_runner
python -c "from app.data.analytics import simulate_treatment_outcomes; simulate_treatment_outcomes()"
```

Start the app:
```bash
uvicorn app.main:app --reload
```
Visit `http://127.0.0.1:8000`.

---

<!-- persistence test -->