from app.data.database import SessionLocal
from app.data import models
from app.integrations.razorpay.client import create_payment_link


def execute_action(audit_id: int):
    """
    Executes the action tied to an audit entry — ONLY if policy_decision is APPROVED.
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
        discounted_amount = order.total_amount * 0.95  # 5% discount, matches our earlier test
        description = f"5% discount on your cart - Revenue Autopilot"
    else:
        discounted_amount = order.total_amount
        description = f"Reminder: complete your purchase - Revenue Autopilot"

    link = create_payment_link(
        amount_in_rupees=discounted_amount,
        customer_name=customer.name,
        customer_email=customer.email,
        description=description,
    )

    entry.api_result = f"Payment link created: {link['short_url']} (status: {link['status']})"
    db.commit()
    db.close()

    return {"status": "executed", "payment_link": link["short_url"]}


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
    # Test both paths using real audit entries from our earlier pipeline run
    db = SessionLocal()
    approved_entry = db.query(models.AuditLog).filter_by(policy_decision="APPROVED").first()
    pending_entry = db.query(models.AuditLog).filter_by(policy_decision="NEEDS_APPROVAL").first()
    db.close()

    if approved_entry:
        print("Executing an already-APPROVED entry:")
        print(execute_action(approved_entry.id))
    else:
        print("No APPROVED entry found yet to test with.")

    if pending_entry:
        print("\nApproving a NEEDS_APPROVAL entry, then executing:")
        print(approve_pending_action(pending_entry.id))
    else:
        print("No NEEDS_APPROVAL entry found yet to test with.")