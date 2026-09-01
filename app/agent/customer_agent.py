import os
import json
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
from groq import Groq
from app.data.database import SessionLocal
from app.data import models

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-20b"

# Modeling assumption for demo purposes — NOT real customer behavior.
CHECKOUT_COMPLETION_RATE = 0.55  # 55% of conversational checkouts assumed to complete immediately


def get_full_catalog():
    db = SessionLocal()
    products = db.query(models.Product).all()
    catalog = [
        {"id": p.id, "name": p.name, "category": p.category, "price": p.price}
        for p in products
    ]
    db.close()
    return catalog


def recommend_product(customer_request: str) -> dict:
    """
    Takes a natural-language customer request and recommends ONE product
    from our real catalog — never an invented product.
    """
    catalog = get_full_catalog()

    prompt = f"""A customer is shopping at an audio-accessories store and said:
"{customer_request}"

Here is the ONLY real product catalog available — you may recommend ONLY from this list, nothing else:
{json.dumps(catalog, indent=2)}

Respond with a JSON object in this exact shape:
{{
  "recommended_product_id": <id from the catalog, or null if nothing fits>,
  "reasoning": "why this product fits the customer's request, or why nothing fits"
}}

Return ONLY valid JSON, no other text."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    result = json.loads(response.choices[0].message.content)

    # Hard guardrail: verify the recommended product actually exists in our catalog
    valid_ids = [p["id"] for p in catalog]
    if result["recommended_product_id"] not in valid_ids:
        return {"recommended_product_id": None, "reasoning": "No matching product found in catalog"}

    return result


def create_conversational_order(customer_name: str, customer_email: str, recommended_product_id: int) -> dict:
    """
    Creates a real order from a conversational recommendation.
    Simulates whether the customer completes payment immediately.
    If not completed, this becomes a genuine abandoned order our
    existing Revenue Autopilot agent can detect and act on.
    """
    db = SessionLocal()

    product = db.query(models.Product).filter_by(id=recommended_product_id).first()
    if not product:
        db.close()
        return {"status": "error", "reason": "Product not found"}

    customer = db.query(models.Customer).filter_by(email=customer_email).first()
    if not customer:
        customer = models.Customer(name=customer_name, email=customer_email)
        db.add(customer)
        db.commit()
        db.refresh(customer)

    order = models.Order(
        customer_id=customer.id,
        created_at=datetime.now(timezone.utc),
        status="pending",
        total_amount=product.price,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    db.add(models.OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        price_at_purchase=product.price,
    ))

    completed_now = random.random() < CHECKOUT_COMPLETION_RATE

    if completed_now:
        order.status = "completed"
        stage = "completed"
        customer.total_past_orders += 1
        customer.total_past_spend += product.price
    else:
        order.status = "abandoned"
        stage = "checkout_started"

    db.add(models.CheckoutEvent(
        customer_id=customer.id,
        order_id=order.id,
        stage_reached=stage,
        timestamp=datetime.now(timezone.utc),
    ))

    db.commit()
    result = {
        "order_id": order.id,
        "customer_id": customer.id,
        "product": product.name,
        "amount": product.price,
        "status": order.status,
    }
    db.close()
    return result


if __name__ == "__main__":
    rec = recommend_product("I need headphones under 3000 rupees with good battery life")
    print("Recommendation:")
    print(json.dumps(rec, indent=2))

    if rec["recommended_product_id"]:
        order_result = create_conversational_order(
            customer_name="Demo Customer",
            customer_email="demo.customer@example.com",
            recommended_product_id=rec["recommended_product_id"],
        )
        print("\nOrder created from conversation:")
        print(order_result)