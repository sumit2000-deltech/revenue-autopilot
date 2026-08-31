from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.data.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    signup_date = Column(DateTime, default=datetime.utcnow)
    total_past_orders = Column(Integer, default=0)
    total_past_spend = Column(Float, default=0.0)

    orders = relationship("Order", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=100)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending, completed, abandoned
    total_amount = Column(Float, default=0.0)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    price_at_purchase = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class CheckoutEvent(Base):
    __tablename__ = "checkout_events"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    stage_reached = Column(String, nullable=False)  # cart, checkout_started, payment_attempted, completed
    timestamp = Column(DateTime, default=datetime.utcnow)




class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    evidence = Column(String)          # JSON string of the evidence bundle
    diagnosis = Column(String)         # the LLM's diagnosis text
    candidate_actions = Column(String) # JSON string of all candidates considered
    selected_action = Column(String)   # which one was chosen

    policy_decision = Column(String)   # APPROVED / BLOCKED / NEEDS_APPROVAL
    policy_reason = Column(String)

    api_result = Column(String, nullable=True)  # filled in later, once Razorpay is wired up