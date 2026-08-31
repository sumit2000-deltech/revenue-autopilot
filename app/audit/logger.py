import json
from app.data.database import SessionLocal
from app.data import models


def record_decision(order_id, customer_id, evidence, diagnosis, candidate_actions,
                     selected_action, policy_decision, policy_reason, api_result=None):
    db = SessionLocal()

    entry = models.AuditLog(
        order_id=order_id,
        customer_id=customer_id,
        evidence=json.dumps(evidence),
        diagnosis=diagnosis,
        candidate_actions=json.dumps(candidate_actions),
        selected_action=selected_action,
        policy_decision=policy_decision,
        policy_reason=policy_reason,
        api_result=api_result,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    db.close()

    return entry.id