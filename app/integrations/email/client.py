import os
import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_API_URL = "https://api.resend.com/emails"


def send_discount_email(customer_email: str, customer_name: str, product_name: str,
                         order_value: float, payment_link: str) -> dict:
    """
    Sends a discount/order notification email via Resend's HTTPS API.
    Works on Render's free tier since it's HTTPS, not SMTP (which is blocked).
    """
    if not RESEND_API_KEY:
        return {"success": False, "error": "RESEND_API_KEY not configured"}

    payload = {
        "from": "Revenue Autopilot <onboarding@resend.dev>",
        "to": [customer_email],
        "subject": f"Complete your order — {product_name}",
        "html": f"""
            <h2>Hi {customer_name},</h2>
            <p>We noticed you didn't finish checking out for <strong>{product_name}</strong> (₹{order_value}).</p>
            <p>Here's a link to complete your purchase:</p>
            <p><a href="{payment_link}" style="background:#2563eb;color:white;padding:10px 20px;text-decoration:none;border-radius:6px;">Complete Payment</a></p>
            <p style="color:#666;font-size:12px;">This is a test-mode transaction from Revenue Autopilot, a Razorpay AI Buildathon project.</p>
        """,
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=10)
        if response.status_code in (200, 201):
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = send_discount_email(
        customer_email="anugya2001@gmail.com",
        customer_name="Test Customer",
        product_name="Studio Headphones Lite",
        order_value=2999.0,
        payment_link="https://rzp.io/rzp/example",
    )
    print(result)