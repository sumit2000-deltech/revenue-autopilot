import random
from app.data.database import SessionLocal
from app.data import models


def get_abandoned_orders():
    db = SessionLocal()
    orders = db.query(models.Order).filter_by(status="abandoned").all()
    db.close()
    return orders


def abandoned_summary():
    db = SessionLocal()
    abandoned = db.query(models.Order).filter_by(status="abandoned").all()

    total_lost_value = sum(o.total_amount for o in abandoned)
    count = len(abandoned)

    stage_breakdown = {}
    for order in abandoned:
        event = (
            db.query(models.CheckoutEvent)
            .filter_by(order_id=order.id)
            .first()
        )
        stage = event.stage_reached if event else "unknown"
        stage_breakdown[stage] = stage_breakdown.get(stage, 0) + 1

    db.close()
    return {
        "abandoned_count": count,
        "total_lost_value": total_lost_value,
        "stage_breakdown": stage_breakdown,
    }


def get_opportunity_details(order_id: int):
    db = SessionLocal()
    order = db.query(models.Order).filter_by(id=order_id).first()
    if not order or order.status != "abandoned":
        db.close()
        return None

    customer = order.customer
    event = db.query(models.CheckoutEvent).filter_by(order_id=order.id).first()
    items = db.query(models.OrderItem).filter_by(order_id=order.id).all()

    product_names = []
    for item in items:
        product_names.append(item.product.name)

    details = {
        "order_id": order.id,
        "customer_id": customer.id,
        "customer_name": customer.name,
        "is_returning_customer": customer.total_past_orders > 0,
        "past_orders": customer.total_past_orders,
        "past_spend": customer.total_past_spend,
        "stage_reached": event.stage_reached if event else "unknown",
        "products_in_cart": product_names,
        "order_value": order.total_amount,
    }

    db.close()
    return details


def assign_experiment_groups():
    """
    Randomly assigns every abandoned order to 'treatment' or 'control',
    50/50, ONLY if not already assigned. Real experiments assign once,
    before any action is taken — never after seeing the outcome.
    """
    db = SessionLocal()
    abandoned = db.query(models.Order).filter_by(status="abandoned").all()

    assigned_count = 0
    for order in abandoned:
        if order.experiment_group is None:
            order.experiment_group = random.choice(["treatment", "control"])
            assigned_count += 1

    db.commit()
    db.close()
    return assigned_count

# Modeling assumption for demo purposes — NOT real customer behavior.
# These recovery rates represent an assumed uplift from each intervention type.
SIMULATED_RECOVERY_RATES = {
    "discount": 0.30,   # 30% of discount-treated customers assumed to convert
    "reminder": 0.15,   # 15% of reminder-treated customers assumed to convert
}


def simulate_treatment_outcomes():
    """
    For treatment-group orders that received a real logged intervention,
    simulate whether they converted, using SIMULATED_RECOVERY_RATES.
    This is a modeling assumption, not observed real customer behavior —
    must be stated as such in any demo or report.
    """
    db = SessionLocal()

    treatment_orders = (
        db.query(models.Order)
        .filter_by(status="abandoned", experiment_group="treatment")
        .all()
    )

    simulated_conversions = 0
    for order in treatment_orders:
        audit_entry = (
            db.query(models.AuditLog)
            .filter_by(order_id=order.id)
            .filter(models.AuditLog.api_result.isnot(None))
            .first()
        )
        if not audit_entry:
            continue  # no real intervention was executed for this order — skip

        recovery_rate = SIMULATED_RECOVERY_RATES.get(audit_entry.selected_action, 0)
        if random.random() < recovery_rate:
            order.status = "completed_via_intervention"
            simulated_conversions += 1

    db.commit()
    db.close()
    return simulated_conversions


if __name__ == "__main__":
    summary = abandoned_summary()
    print("Abandoned orders:", summary["abandoned_count"])
    print("Total lost value: ₹", summary["total_lost_value"])
    print("Breakdown by stage:", summary["stage_breakdown"])

    print("\nSample opportunity detail:")
    sample = get_abandoned_orders()[0]
    print(get_opportunity_details(sample.id))

    print("\nAssigning experiment groups...")
    count = assign_experiment_groups()
    print(f"Assigned {count} orders to treatment/control groups")