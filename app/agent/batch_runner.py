import time
from app.data.database import SessionLocal
from app.data import models
from app.data.analytics import get_opportunity_details
from app.agent.nodes import diagnose_opportunity
from app.policy.rules import evaluate_action
from app.audit.logger import record_decision
from app.agent.executor import execute_action


def run_pipeline_on_treatment_group(limit: int = 50):
    """
    Runs the full diagnose -> policy -> execute pipeline on the first
    `limit` treatment-group abandoned orders that haven't been processed yet.
    Uses dry_run=True for execution to avoid Razorpay test-mode quota limits
    when running at scale.
    """
    db = SessionLocal()
    treatment_orders = (
        db.query(models.Order)
        .filter_by(status="abandoned", experiment_group="treatment")
        .limit(limit)
        .all()
    )
    order_ids = [o.id for o in treatment_orders]
    db.close()

    results = {"executed": 0, "needs_approval_skipped": 0, "blocked": 0, "skipped": 0, "errors": 0}

    for order_id in order_ids:
        try:
            evidence = get_opportunity_details(order_id)
            if not evidence:
                results["skipped"] += 1
                continue

            diagnosis_result = diagnose_opportunity(evidence)
            if not diagnosis_result["candidate_actions"]:
                results["skipped"] += 1
                continue

            chosen = diagnosis_result["candidate_actions"][0]
            proposed_discount = 5 if chosen["action"] == "discount" else 0

            policy_result = evaluate_action(
                action=chosen["action"],
                order_value=evidence["order_value"],
                proposed_discount_percent=proposed_discount,
            )

            audit_id = record_decision(
                order_id=evidence["order_id"],
                customer_id=evidence["customer_id"],
                evidence=evidence,
                diagnosis=diagnosis_result["diagnosis"],
                candidate_actions=diagnosis_result["candidate_actions"],
                selected_action=chosen["action"],
                policy_decision=policy_result["decision"],
                policy_reason=policy_result["reason"],
            )

            if policy_result["decision"] == "APPROVED":
                exec_result = execute_action(audit_id, dry_run=True)
                if exec_result["status"] == "dry_run_executed":
                    results["executed"] += 1
                else:
                    results["errors"] += 1

            elif policy_result["decision"] == "NEEDS_APPROVAL":
                # Real approval flow already proven separately (Jared Miller test earlier).
                # Skipping in batch mode to keep this run simple and quota-safe.
                results["needs_approval_skipped"] += 1

            else:  # BLOCKED
                results["blocked"] += 1

            time.sleep(2)  # avoid hammering the LLM API too fast

        except Exception as e:
            print(f"[ERROR] Order {order_id} failed: {e}")
            results["errors"] += 1

    return results


if __name__ == "__main__":
    print("Running pipeline on first 50 treatment-group orders...")
    summary = run_pipeline_on_treatment_group(limit=50)
    print("\nBatch run complete:")
    print(summary)