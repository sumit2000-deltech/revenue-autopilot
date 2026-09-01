from app.agent.customer_agent import recommend_product, create_conversational_order
from app.agent.graph import build_graph

# Force a recommendation and create the order
rec = recommend_product("I want a cheap neckband under 1000 rupees")
print("Recommendation:", rec)

order_result = create_conversational_order(
    customer_name="Test Abandoner",
    customer_email="test.abandoner@example.com",
    recommended_product_id=rec["recommended_product_id"],
)
print("Order result:", order_result)

if order_result["status"] == "abandoned":
    print("\nOrder was abandoned! Running it through our Revenue Autopilot agent...")
    app_graph = build_graph()
    final_state = app_graph.invoke({"order_id": order_result["order_id"]})
    for k, v in final_state.items():
        print(f"  {k}: {v}")
else:
    print("\nOrder completed immediately this time — run this script again to try for an abandoned outcome.")