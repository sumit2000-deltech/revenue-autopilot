import random
from datetime import datetime, timedelta

from faker import Faker
from app.data.database import SessionLocal, Base, engine
from app.data import models

fake = Faker()

# Our fixed product catalog — a narrow audio-accessories store
PRODUCTS = [
    ("Wireless Earbuds Pro", "earbuds", 2499),
    ("Bass Boost Earbuds", "earbuds", 1499),
    ("Over-Ear Headphones X1", "headphones", 3999),
    ("Studio Headphones Lite", "headphones", 2999),
    ("Bluetooth Neckband", "neckband", 999),
    ("Earbuds Carry Case", "accessory", 399),
    ("Headphone Stand", "accessory", 599),
    ("Wireless Charging Dock", "accessory", 1299),
]

STAGES = ["cart", "checkout_started", "payment_attempted", "completed"]


def seed():
   def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear existing data first — safe to re-run on a persistent database
    db.query(models.CheckoutEvent).delete()
    db.query(models.OrderItem).delete()
    db.query(models.AuditLog).delete()
    db.query(models.Order).delete()
    db.query(models.Customer).delete()
    db.query(models.Product).delete()
    db.commit()

    # 1. Create products
    product_objs = []
    for name, category, price in PRODUCTS:
        p = models.Product(name=name, category=category, price=price)
        db.add(p)
        product_objs.append(p)
    db.commit()

    # 2. Create customers
    customers = []
    for _ in range(1000):
        c = models.Customer(
            name=fake.name(),
            email=fake.unique.email(),
            signup_date=fake.date_time_between(start_date="-1y", end_date="-1d"),
        )
        db.add(c)
        customers.append(c)
    db.commit()

    # 3. Create orders + checkout events per customer
    for customer in customers:
        num_orders = random.randint(1, 4)
        for _ in range(num_orders):
            outcome = random.choices(
                ["completed", "abandoned"], weights=[0.6, 0.4]
            )[0]

            order = models.Order(
                customer_id=customer.id,
                status="pending",
                created_at=fake.date_time_between(start_date="-90d", end_date="now"),
                source="synthetic",
            )
            db.add(order)
            db.commit()  # so order.id is available

            chosen_products = random.sample(product_objs, k=random.randint(1, 2))
            total = 0
            for prod in chosen_products:
                qty = random.randint(1, 2)
                db.add(models.OrderItem(
                    order_id=order.id,
                    product_id=prod.id,
                    quantity=qty,
                    price_at_purchase=prod.price,
                ))
                total += prod.price * qty

            order.total_amount = total

            if outcome == "completed":
                order.status = "completed"
                reached_stage = "completed"
                customer.total_past_orders += 1
                customer.total_past_spend += total
            else:
                order.status = "abandoned"
                reached_stage = random.choice(["cart", "checkout_started", "payment_attempted"])

            db.add(models.CheckoutEvent(
                customer_id=customer.id,
                order_id=order.id,
                stage_reached=reached_stage,
                timestamp=order.created_at,
            ))

            db.commit()

    db.close()
    print("Seeding complete.")


if __name__ == "__main__":
    seed()