from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from app.data.analytics import get_opportunity_details
from app.agent.nodes import diagnose_opportunity
from app.policy.rules import evaluate_action
from app.audit.logger import record_decision
from app.agent.executor import execute_action


class AgentState(TypedDict):
    order_id: int
    evidence: Optional[dict]
    diagnosis: Optional[str]
    candidate_actions: Optional[list]
    chosen_action: Optional[str]
    policy_decision: Optional[str]
    policy_reason: Optional[str]
    audit_id: Optional[int]
    execution_result: Optional[dict]

def diagnose_node(state: AgentState) -> AgentState:
    evidence = get_opportunity_details(state["order_id"])
    state["evidence"] = evidence

    if not evidence:
        state["candidate_actions"] = []
        return state

    result = diagnose_opportunity(evidence)
    state["diagnosis"] = result["diagnosis"]
    state["candidate_actions"] = result["candidate_actions"]
    return state


def policy_gate_node(state: AgentState) -> AgentState:
    if not state["candidate_actions"]:
        state["policy_decision"] = "BLOCKED"
        state["policy_reason"] = "No valid candidate actions"
        return state

    chosen = state["candidate_actions"][0]
    proposed_discount = 5 if chosen["action"] == "discount" else 0

    result = evaluate_action(
        action=chosen["action"],
        order_value=state["evidence"]["order_value"],
        proposed_discount_percent=proposed_discount,
    )
    state["chosen_action"] = chosen["action"]
    state["policy_decision"] = result["decision"]
    state["policy_reason"] = result["reason"]
    return state


def audit_node(state: AgentState) -> AgentState:
    audit_id = record_decision(
        order_id=state["evidence"]["order_id"],
        customer_id=state["evidence"]["customer_id"],
        evidence=state["evidence"],
        diagnosis=state["diagnosis"],
        candidate_actions=state["candidate_actions"],
        selected_action=state["chosen_action"],
        policy_decision=state["policy_decision"],
        policy_reason=state["policy_reason"],
    )
    state["audit_id"] = audit_id
    return state


def execute_node(state: AgentState) -> AgentState:
    if state["policy_decision"] == "APPROVED":
        result = execute_action(state["audit_id"], dry_run=True)
        state["execution_result"] = result
    else:
        state["execution_result"] = {"status": "not_executed", "reason": state["policy_decision"]}
    return state


def should_execute(state: AgentState) -> str:
    """Conditional edge: only proceed to execution if APPROVED."""
    if state["policy_decision"] == "APPROVED":
        return "execute"
    return "end"
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("diagnose", diagnose_node)
    graph.add_node("policy_gate", policy_gate_node)
    graph.add_node("audit", audit_node)
    graph.add_node("execute", execute_node)

    graph.set_entry_point("diagnose")
    graph.add_edge("diagnose", "policy_gate")
    graph.add_edge("policy_gate", "audit")
    graph.add_conditional_edges("audit", should_execute, {"execute": "execute", "end": END})
    graph.add_edge("execute", END)

    return graph.compile()


if __name__ == "__main__":
    from app.data.analytics import get_abandoned_orders

    app_graph = build_graph()

    sample_order = get_abandoned_orders()[0]
    initial_state = {"order_id": sample_order.id}

    final_state = app_graph.invoke(initial_state)

    print("Final state after graph run:")
    for key, value in final_state.items():
        print(f"  {key}: {value}")