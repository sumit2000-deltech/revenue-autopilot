import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)


def create_payment_link(amount_in_rupees: float, customer_name: str, customer_email: str, description: str):
    """
    Creates a Razorpay test-mode payment link.
    Amount must be sent in paise (smallest currency unit) — Razorpay's API
    always expects integer paise, not rupees, to avoid floating-point issues with money.
    """
    amount_in_paise = int(amount_in_rupees * 100)

    payment_link = client.payment_link.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "description": description,
        "customer": {
            "name": customer_name,
            "email": customer_email,
        },
        "notify": {
            "sms": False,
            "email": False,
        },
    })

    return payment_link


if __name__ == "__main__":
    result = create_payment_link(
        amount_in_rupees=499,
        customer_name="Test Customer",
        customer_email="test@example.com",
        description="Test payment link from Revenue Autopilot",
    )
    print("Payment link created:")
    print("ID:", result["id"])
    print("Status:", result["status"])
    print("URL:", result["short_url"])