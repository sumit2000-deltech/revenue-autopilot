from fastapi import APIRouter
from app.data.database import SessionLocal
from app.data import models
from app.agent.executor import approve_pending_action
from app.data.analytics import measure_incremental_lift
from app.agent.graph import build_graph
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
        .order_by(models.AuditLog.updated_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for e in entries:
        customer = db.query(models.Customer).filter_by(id=e.customer_id).first()
        result.append({
            "audit_id": e.id,
            "order_id": e.order_id,
            "customer_name": customer.name if customer else "Unknown",
            "selected_action": e.selected_action,
            "policy_decision": e.policy_decision,
            "policy_reason": e.policy_reason,
            "api_result": e.api_result,
            "payment_link_url": e.payment_link_url,
        })
    db.close()
    return result


@router.get("/api/lift")
def get_lift():
    return measure_incremental_lift()

@router.post("/api/process-new-opportunities")
def process_new_opportunities():
    """
    Finds abandoned orders that haven't been processed by the agent yet,
    and runs them through the full LangGraph pipeline.
    Used by the merchant dashboard's 'Check for New Opportunities' button.
    """
    db = SessionLocal()
    processed_order_ids = [row.order_id for row in db.query(models.AuditLog.order_id).all()]
    new_abandoned = (
        db.query(models.Order)
        .filter_by(status="abandoned")
        .filter(~models.Order.id.in_(processed_order_ids))
        .order_by(models.Order.id.desc())
        .limit(10)
        .all()
    )
    order_ids = [o.id for o in new_abandoned]
    db.close()

    graph = build_graph()
    results = []
    for order_id in order_ids:
        final_state = graph.invoke({"order_id": order_id})
        results.append({
            "order_id": order_id,
            "policy_decision": final_state.get("policy_decision"),
            "diagnosis": final_state.get("diagnosis"),
        })

    return {"processed_count": len(results), "results": results}

@router.post("/api/mark-abandoned/{order_id}")
def mark_abandoned(order_id: int):
    db = SessionLocal()
    order = db.query(models.Order).filter_by(id=order_id).first()
    if order and order.status == "pending":
        order.status = "abandoned"
        db.commit()
    db.close()
    return {"order_id": order_id, "status": "abandoned"}