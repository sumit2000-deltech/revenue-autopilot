


import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-20b"

# The ONLY actions our system is allowed to take — locked from our brief
APPROVED_ACTIONS = ["reminder", "discount", "cross_sell"]


def diagnose_opportunity(evidence: dict) -> dict:
    """
    Takes an evidence bundle and returns a diagnosis + candidate actions,
    constrained to our approved action types only.
    """
    prompt = f"""You are analyzing a single abandoned checkout for an online audio-accessories merchant.

Evidence (this is the ONLY information you may use — do not invent any numbers or facts):
{json.dumps(evidence, indent=2)}

You may ONLY choose actions from this exact list: {APPROVED_ACTIONS}
Do not suggest any action outside this list.

Based ONLY on this evidence, respond with a JSON object in this exact shape:
{{
  "diagnosis": "one or two sentences on why this customer likely abandoned, grounded in the evidence",
  "candidate_actions": [
    {{"action": "one of {APPROVED_ACTIONS}", "reasoning": "why this could work, grounded in evidence"}},
    {{"action": "one of {APPROVED_ACTIONS}", "reasoning": "..."}}
  ]
}}

Return ONLY valid JSON, no other text."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    raw = response.choices[0].message.content
    result = json.loads(raw)

    # HARD GUARDRAIL: validate every action is actually in our approved list,
    # regardless of what the prompt asked for. Never trust the LLM's word alone.
    valid_actions = []
    for candidate in result.get("candidate_actions", []):
        if candidate.get("action") in APPROVED_ACTIONS:
            valid_actions.append(candidate)
        else:
            print(f"[GUARDRAIL] Rejected out-of-scope action: {candidate.get('action')}")

    result["candidate_actions"] = valid_actions
    return result


if __name__ == "__main__":
    from app.data.analytics import get_abandoned_orders, get_opportunity_details
    from app.policy.rules import evaluate_action
    from app.audit.logger import record_decision

    sample_order = get_abandoned_orders()[0]
    evidence = get_opportunity_details(sample_order.id)

    result = diagnose_opportunity(evidence)
    print("LLM diagnosis (after guardrail):")
    print(json.dumps(result, indent=2))

    if result["candidate_actions"]:
        chosen = result["candidate_actions"][0]  # simplest choice logic for now: take the first
        proposed_discount = 5 if chosen["action"] == "discount" else 0

        policy_result = evaluate_action(
            action=chosen["action"],
            order_value=evidence["order_value"],
            proposed_discount_percent=proposed_discount,
        )
        print("\nPolicy check result:")
        print(policy_result)

        audit_id = record_decision(
            order_id=evidence["order_id"],
            customer_id=evidence["customer_id"],
            evidence=evidence,
            diagnosis=result["diagnosis"],
            candidate_actions=result["candidate_actions"],
            selected_action=chosen["action"],
            policy_decision=policy_result["decision"],
            policy_reason=policy_result["reason"],
        )
        print(f"\nAudit entry saved with id: {audit_id}")
    else:
        print("\nNo valid candidate actions after guardrail — nothing to log.")