from app.data.database import SessionLocal
from app.data import models
from app.integrations.razorpay.client import create_payment_link


def execute_action(audit_id: int, simulate_failure: bool = False):
    """
    Executes the action tied to an audit entry — ONLY if policy_decision is APPROVED.
    Handles Razorpay failures safely: no duplicate action, failure recorded in audit trail.
    """
    db = SessionLocal()
    entry = db.query(models.AuditLog).filter_by(id=audit_id).first()

    if not entry:
        db.close()
        return {"status": "error", "reason": "Audit entry not found"}

    if entry.policy_decision != "APPROVED":
        db.close()
        return {"status": "blocked", "reason": f"Cannot execute — policy decision was {entry.policy_decision}, not APPROVED"}

    order = db.query(models.Order).filter_by(id=entry.order_id).first()
    customer = db.query(models.Customer).filter_by(id=entry.customer_id).first()

    if entry.selected_action == "discount":
        discounted_amount = order.total_amount * 0.95
        description = "5% discount on your cart - Revenue Autopilot"
    else:
        discounted_amount = order.total_amount
        description = "Reminder: complete your purchase - Revenue Autopilot"

    result = create_payment_link(
        amount_in_rupees=discounted_amount,
        customer_name=customer.name,
        customer_email=customer.email,
        description=description,
        simulate_failure=simulate_failure,
    )

    if result["success"]:
        entry.api_result = f"Payment link created: {result['data']['short_url']} (status: {result['data']['status']})"
        db.commit()
        db.close()
        return {"status": "executed", "payment_link": result["data"]["short_url"]}
    else:
        # Failure handled safely: no duplicate action, clearly logged, no crash
        entry.api_result = f"FAILED after {result['attempts']} attempts: {result['error']}"
        db.commit()
        db.close()
        return {"status": "failed", "reason": result["error"]}


def approve_pending_action(audit_id: int):
    """
    Simulates a merchant approving a NEEDS_APPROVAL action.
    After approval, immediately attempts execution.
    """
    db = SessionLocal()
    entry = db.query(models.AuditLog).filter_by(id=audit_id).first()

    if not entry or entry.policy_decision != "NEEDS_APPROVAL":
        db.close()
        return {"status": "error", "reason": "No pending approval found for this audit id"}

    entry.approved_by_merchant = "approved"
    entry.policy_decision = "APPROVED"  # now cleared for execution
    db.commit()
    db.close()

    return execute_action(audit_id)

if __name__ == "__main__":
    db = SessionLocal()
    approved_entry = db.query(models.AuditLog).filter_by(policy_decision="APPROVED").first()
    db.close()

    if approved_entry:
        print("Executing an already-APPROVED entry normally:")
        print(execute_action(approved_entry.id))

        print("\nSimulating a failure on the SAME entry (should not double-log or crash):")
        print(execute_action(approved_entry.id, simulate_failure=True))
    else:
        print("No APPROVED entry found yet to test with.")