"""
LangGraph 工作流定义：注册 6 个节点、串行边和条件路由，编译为可执行图。
调用关系：调用 state_schema.py 定义状态类型；导入 6 个节点函数；被 run_cli.py 调用 build_graph()。
输入：6 个节点函数
输出：build_graph() → CompiledStateGraph
"""
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from state_schema import DialogueState
from nodes.fact_extraction_node import fact_extraction_node
from nodes.anomaly_detection_node import anomaly_detection_node
from nodes.consistency_judge_node import consistency_judge_node
from nodes.state_update_node import state_update_node
from nodes.followup_generation_node import followup_generation_node
from nodes.report_generation_node import report_generation_node


def route_node(state: DialogueState) -> str:
    """
    路由节点：决定下一步是追问还是生成报告。
    """
    if state["round_id"] >= state["max_rounds"]:
        return "report_generation"
    return "followup_generation"


def build_graph() -> CompiledStateGraph:
    """构建 LangGraph 工作流"""
    graph = StateGraph(DialogueState)

    # 添加节点
    graph.add_node("fact_extraction", fact_extraction_node)
    graph.add_node("anomaly_detection", anomaly_detection_node)
    graph.add_node("consistency_judge", consistency_judge_node)
    graph.add_node("state_update", state_update_node)
    graph.add_node("followup_generation", followup_generation_node)
    graph.add_node("report_generation", report_generation_node)

    # 设置入口
    graph.set_entry_point("fact_extraction")

    # 串行边
    graph.add_edge("fact_extraction", "anomaly_detection")
    graph.add_edge("anomaly_detection", "consistency_judge")
    graph.add_edge("consistency_judge", "state_update")

    # 路由：state_update 之后根据条件分支
    graph.add_conditional_edges(
        "state_update",
        route_node,
        {
            "followup_generation": "followup_generation",
            "report_generation": "report_generation",
        },
    )

    # 终止
    graph.add_edge("followup_generation", END)
    graph.add_edge("report_generation", END)

    return graph.compile()
