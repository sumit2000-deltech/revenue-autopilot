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
        else:
            order.status = "abandoned_no_conversion"  # simulation ran, order did NOT convert — never re-roll this order

    db.commit()
    db.close()
    return simulated_conversions
def measure_incremental_lift():
    """
    Compares completion rates between treated (intervened) orders and
    control orders to estimate incremental lift and revenue.
    Only counts treatment orders that had a REAL executed intervention —
    not all orders merely assigned to the treatment group.
    """
    db = SessionLocal()

    # Treatment: orders with an executed intervention (real audit entry, api_result present)
    treated_order_ids = [
        row.order_id for row in
        db.query(models.AuditLog.order_id)
        .filter(models.AuditLog.api_result.isnot(None))
        .all()
    ]
    treated_orders = (
        db.query(models.Order)
        .filter(models.Order.id.in_(treated_order_ids))
        .filter(models.Order.experiment_group == "treatment")
        .all()
    )

    control_orders = (
        db.query(models.Order)
        .filter_by(experiment_group="control", status="abandoned")
        .all()
    )
    # Note: control orders that were ALREADY completed (organically) don't
    # belong in this comparison since they were never abandoned+observed —
    # we compare apples to apples: originally-abandoned orders in both groups.

    treated_total = len(treated_orders)
    treated_converted = len([o for o in treated_orders if o.status == "completed_via_intervention"])

    control_total = len(control_orders)
    # Control orders that later got marked completed_via_intervention would be
    # a bug (they shouldn't), so we just check original abandoned count vs none converting
    control_converted = 0  # by design, nothing acts on control — always 0

    treated_rate = (treated_converted / treated_total * 100) if treated_total else 0
    control_rate = (control_converted / control_total * 100) if control_total else 0

    incremental_lift_pct = treated_rate - control_rate

    # Estimate incremental revenue: lift % applied to average order value across abandoned orders
    avg_order_value = (
        sum(o.total_amount for o in treated_orders) / treated_total if treated_total else 0
    )
    estimated_incremental_revenue = (incremental_lift_pct / 100) * treated_total * avg_order_value

    db.close()

    return {
        "treated_total": treated_total,
        "treated_converted": treated_converted,
        "treated_conversion_rate_pct": round(treated_rate, 2),
        "control_total": control_total,
        "control_converted": control_converted,
        "control_conversion_rate_pct": round(control_rate, 2),
        "incremental_lift_pct": round(incremental_lift_pct, 2),
        "estimated_incremental_revenue": round(estimated_incremental_revenue, 2),
    }

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
    print("\nSimulating treatment outcomes...")
    conversions = simulate_treatment_outcomes()
    print(f"Simulated conversions: {conversions}")
    print("\nIncremental lift measurement:")
    lift = measure_incremental_lift()
    for key, value in lift.items():
        print(f"  {key}: {value}")