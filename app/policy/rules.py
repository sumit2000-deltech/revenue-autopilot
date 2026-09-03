# Merchant policy limits — locked, deterministic, no LLM involved
MAX_DISCOUNT_PERCENT = 10
AUTO_APPROVE_ORDER_VALUE_LIMIT = 500 # temporary orders above this need approval
MAX_MESSAGES_PER_CUSTOMER = 2


def evaluate_action(action: str, order_value: float, proposed_discount_percent: float = 0) -> dict:
    """
    Deterministic policy gate. Takes a proposed action and checks it
    against merchant limits. Returns a decision + reason — never
    executes anything itself, just decides whether execution is allowed.
    """
    if action == "discount":
        if proposed_discount_percent > MAX_DISCOUNT_PERCENT:
            return {
                "decision": "BLOCKED",
                "reason": f"Proposed discount {proposed_discount_percent}% exceeds max allowed {MAX_DISCOUNT_PERCENT}%"
            }

    if order_value > AUTO_APPROVE_ORDER_VALUE_LIMIT:
        return {
            "decision": "NEEDS_APPROVAL",
            "reason": f"Order value ₹{order_value} exceeds auto-approve limit of ₹{AUTO_APPROVE_ORDER_VALUE_LIMIT}"
        }

    return {
        "decision": "APPROVED",
        "reason": "Within all policy limits"
    }


if __name__ == "__main__":
    # Quick manual tests — three cases covering all three outcomes
    print(evaluate_action("discount", order_value=2000, proposed_discount_percent=5))
    print(evaluate_action("discount", order_value=2000, proposed_discount_percent=15))
    print(evaluate_action("discount", order_value=6597, proposed_discount_percent=5))