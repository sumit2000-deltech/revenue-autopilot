from app.data.database import SessionLocal
from app.data import models
from app.data.analytics import get_abandoned_orders, get_opportunity_details
from app.agent.nodes import diagnose_opportunity
from app.policy.rules import evaluate_action
from app.audit.logger import record_decision
from app.agent.executor import execute_action

# Find any abandoned order and manually override the customer's email
# to YOUR real email, just for this test
db = SessionLocal()
sample_order = get_abandoned_orders()[0]
customer = db.query(models.Customer).filter_by(id=sample_order.customer_id).first()
customer.email = "anugya2001@gmail.com"  # <-- put your actual email here
db.commit()
db.close()

evidence = get_opportunity_details(sample_order.id)
diagnosis_result = diagnose_opportunity(evidence)
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

print("Policy decision:", policy_result["decision"])

if policy_result["decision"] == "APPROVED":
    result = execute_action(audit_id, dry_run=False)
    print("Execution result:", result)
else:
    print("Order needs approval — approving it now to test that path...")
    from app.agent.executor import approve_pending_action
    result = approve_pending_action(audit_id, dry_run=False)
    print("Execution result (via approval):", result)