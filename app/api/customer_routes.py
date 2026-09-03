from fastapi import APIRouter
from pydantic import BaseModel
from app.agent.customer_agent import recommend_product, create_conversational_order

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class CheckoutRequest(BaseModel):
    customer_name: str
    customer_email: str
    product_id: int
    dry_run: bool = True


@router.post("/api/customer/recommend")
def customer_recommend(req: ChatRequest):
    return recommend_product(req.message)


@router.post("/api/customer/checkout")
def customer_checkout(req: CheckoutRequest):
    return create_conversational_order(
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        recommended_product_id=req.product_id,
        dry_run=req.dry_run,
    )