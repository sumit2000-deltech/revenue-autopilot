import os
import time
import razorpay
from dotenv import load_dotenv

load_dotenv()

client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)


def create_payment_link(amount_in_rupees: float, customer_name: str, customer_email: str,
                         description: str, simulate_failure: bool = False, max_retries: int = 2):
    """
    Creates a Razorpay test-mode payment link, with safe retry handling.
    simulate_failure: for testing our failure path deliberately (sends an invalid amount).
    """
    amount_in_paise = int(amount_in_rupees * 100)

    if simulate_failure:
        amount_in_paise = -100  # deliberately invalid — Razorpay will reject this

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            payment_link = client.payment_link.create({
                "amount": amount_in_paise,
                "currency": "INR",
                "description": description,
                "customer": {
                    "name": customer_name,
                    "email": customer_email,
                },
                "notify": {"sms": False, "email": False},
            })
            return {"success": True, "data": payment_link, "attempts": attempt}

        except Exception as e:
            last_error = str(e)
            print(f"[RETRY] Attempt {attempt} failed: {last_error}")
            if attempt < max_retries:
                time.sleep(1)  # brief pause before retrying

    # All retries exhausted — fail safely, no duplicate action created
    return {"success": False, "error": last_error, "attempts": max_retries}


if __name__ == "__main__":
    print("Normal call:")
    print(create_payment_link(499, "Test Customer", "test@example.com", "Normal test"))

    print("\nSimulated failure:")
    print(create_payment_link(499, "Test Customer", "test@example.com", "Failure test", simulate_failure=True))