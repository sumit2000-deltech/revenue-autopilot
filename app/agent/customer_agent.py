import os
import json
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
from groq import Groq
from app.data.database import SessionLocal
from app.data import models
from app.integrations.razorpay.client import create_payment_link

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-20b"


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

    valid_ids = [p["id"] for p in catalog]
    if result["recommended_product_id"] not in valid_ids:
        return {"recommended_product_id": None, "reasoning": "No matching product found in catalog"}

    return result


def create_conversational_order(customer_name: str, customer_email: str, recommended_product_id: int, dry_run: bool = False) -> dict:
    """
    Creates a real order from a conversational recommendation.
    If dry_run=True, skips the real Razorpay call and returns a placeholder
    link instead — used for safe rehearsal without spending quota.
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

    db.add(models.CheckoutEvent(
        customer_id=customer.id,
        order_id=order.id,
        stage_reached="checkout_started",
        timestamp=datetime.now(timezone.utc),
    ))
    db.commit()

    result = {
        "order_id": order.id,
        "customer_id": customer.id,
        "product": product.name,
        "amount": product.price,
        "status": "pending",
    }

    if dry_run:
        result["payment_link"] = "https://rzp.io/rzp/DRY-RUN-EXAMPLE"
        db.close()
        return result

    link_result = create_payment_link(
        amount_in_rupees=product.price,
        customer_name=customer_name,
        customer_email=customer_email,
        description=f"{product.name} - Audio Accessories Store",
    )

    if link_result["success"]:
        result["payment_link"] = link_result["data"]["short_url"]
    else:
        result["payment_error"] = link_result["error"]

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
            dry_run=True,
        )
        print("\nOrder created from conversation (dry run):")
        print(order_result)