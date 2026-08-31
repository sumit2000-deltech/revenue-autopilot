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


if __name__ == "__main__":
    summary = abandoned_summary()
    print("Abandoned orders:", summary["abandoned_count"])
    print("Total lost value: ₹", summary["total_lost_value"])
    print("Breakdown by stage:", summary["stage_breakdown"])