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


if __name__ == "__main__":
    summary = abandoned_summary()
    print("Abandoned orders:", summary["abandoned_count"])
    print("Total lost value: ₹", summary["total_lost_value"])
    print("Breakdown by stage:", summary["stage_breakdown"])

    print("\nSample opportunity detail:")
    sample = get_abandoned_orders()[0]
    print(get_opportunity_details(sample.id))