"""
LangGraph 工作流定义：注册 3 个 Agent 节点 + 2 个普通节点 + 条件路由，编译为可执行图。
调用关系：调用 state_schema.py 定义状态类型；导入 3 个 Agent 节点和 2 个普通节点函数；被 run_cli.py 调用 build_graph()。
输入：5 个节点函数
输出：build_graph() → CompiledStateGraph
"""
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from v1.state_schema import DialogueState
from v1.agents.information_comparison_agent import information_comparison_agent_node
from v1.agents.strategy_feedback_agent import strategy_feedback_agent_node
from v1.agents.followup_dialogue_agent import followup_dialogue_agent_node
from v1.nodes.state_update_node import state_update_node
from v1.nodes.report_generation_node import report_generation_node
def route_next(state: DialogueState) -> str:
    """
    路由函数：根据 Agent 3 输出的 next_action 决定下一步。
    - generate_followup → Agent 1 追问
    - final_report → 报告生成
    """
    next_action = state.get("next_action", "generate_followup")
    if next_action == "final_report":
        return "report_generation"
    return "followup_dialogue_agent"


def build_graph() -> CompiledStateGraph:
    """构建 LangGraph 三 Agent 工作流"""
    graph = StateGraph(DialogueState)

    # 添加节点
    graph.add_node("information_comparison_agent", information_comparison_agent_node)
    graph.add_node("state_update", state_update_node)
    graph.add_node("strategy_feedback_agent", strategy_feedback_agent_node)
    graph.add_node("followup_dialogue_agent", followup_dialogue_agent_node)
    graph.add_node("report_generation", report_generation_node)

    # 设置入口
    graph.add_edge(START, "information_comparison_agent")

    # 串行边：Agent 2 → 状态更新 → Agent 3
    graph.add_edge("information_comparison_agent", "state_update")
    graph.add_edge("state_update", "strategy_feedback_agent")

    # 条件路由：Agent 3 之后根据 next_action 分支
    graph.add_conditional_edges(
        "strategy_feedback_agent",
        route_next,
        {
            "followup_dialogue_agent": "followup_dialogue_agent",
            "report_generation": "report_generation",
        },
    )

    # 终止
    graph.add_edge("followup_dialogue_agent", END)
    graph.add_edge("report_generation", END)

    return graph.compile()

