from fastapi import APIRouter
from app.data.database import SessionLocal
from app.data import models
from app.agent.executor import approve_pending_action
from app.data.analytics import measure_incremental_lift

router = APIRouter()


@router.get("/api/pending-approvals")
def get_pending_approvals():
    db = SessionLocal()
    entries = db.query(models.AuditLog).filter_by(policy_decision="NEEDS_APPROVAL").all()
    result = [
        {
            "audit_id": e.id,
            "customer_id": e.customer_id,
            "selected_action": e.selected_action,
            "policy_reason": e.policy_reason,
            "diagnosis": e.diagnosis,
        }
        for e in entries
    ]
    db.close()
    return result


@router.post("/api/approve/{audit_id}")
def approve_action(audit_id: int, dry_run: bool = True):
    result = approve_pending_action(audit_id, dry_run=dry_run)
    return result


@router.get("/api/audit-trail")
def get_audit_trail():
    db = SessionLocal()
    entries = (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.id.desc())
        .limit(20)
        .all()
    )
    result = [
        {
            "audit_id": e.id,
            "selected_action": e.selected_action,
            "policy_decision": e.policy_decision,
            "policy_reason": e.policy_reason,
            "api_result": e.api_result,
            "payment_link_url": e.payment_link_url,
        }
        for e in entries
    ]
    db.close()
    return result


@router.get("/api/lift")
def get_lift():
    return measure_incremental_lift()