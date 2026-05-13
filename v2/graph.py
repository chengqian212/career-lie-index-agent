"""LangGraph 图定义：编排多 Agent 工作流"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from .state_schema import DialogueState
from .nodes.fact_extraction_node import fact_extraction_node
from .nodes.anomaly_detection_node import anomaly_detection_node
from .nodes.consistency_judge_node import consistency_judge_node
from .nodes.state_update_node import state_update_node
from .nodes.specialists.semantic_agent_node import semantic_agent_node
from .nodes.specialists.logical_agent_node import logical_agent_node
from .nodes.specialists.domain_agent_node import domain_agent_node
from .nodes.specialists.psycho_linguistic_agent_node import psycho_linguistic_agent_node
from .nodes.debate_gate_node import debate_gate_node
from .nodes.debate_node import debate_node
from .nodes.risk_aggregator_node import risk_aggregator_node
from .nodes.strategy_supervisor_node import strategy_supervisor_node
from .nodes.followup_generation_node import followup_generation_node
from .nodes.report_generation_node import report_generation_node


def fanout_specialists(state: DialogueState) -> list[Send]:
    """并行启动 4 个 Specialist Agent

    Args:
        state: 当前状态
    Returns:
        Send 列表，每个 Send 指向一个 specialist 节点
    """
    return [
        Send("semantic_agent", state),
        Send("logical_agent", state),
        Send("domain_agent", state),
        Send("psycho_linguistic_agent", state),
    ]


def route_after_debate_gate(state: DialogueState) -> str:
    """Debate 门控路由：判断是否需要进入 Debate

    Args:
        state: 当前状态
    Returns:
        "debate" 或 "aggregate"
    """
    if state.get("debate_needed", False):
        return "debate"
    return "aggregate"


def route_after_supervisor(state: DialogueState) -> str:
    """Supervisor 路由：决定下一步是追问还是生成报告

    Args:
        state: 当前状态
    Returns:
        "followup_generation" 或 "report_generation"
    """
    next_action = state.get("next_action", "generate_followup")
    if next_action == "final_report":
        return "report_generation"
    return "followup_generation"


def build_graph() -> CompiledStateGraph:
    """构建并返回 LangGraph 工作流图

    流程：
    START → fact_extraction → anomaly_detection → consistency_judge → state_update
    → fanout_specialists (并行 4 个 Agent)
    → debate_gate → debate 或 risk_aggregator
    → strategy_supervisor → followup_generation 或 report_generation → END

    Returns:
        编译后的 LangGraph 图
    """
    builder = StateGraph(DialogueState)

    # ---- 注册所有节点 ----
    builder.add_node("fact_extraction", fact_extraction_node)
    builder.add_node("anomaly_detection", anomaly_detection_node)
    builder.add_node("consistency_judge", consistency_judge_node)
    builder.add_node("state_update", state_update_node)

    # 4 个 Specialist Agent
    builder.add_node("semantic_agent", semantic_agent_node)
    builder.add_node("logical_agent", logical_agent_node)
    builder.add_node("domain_agent", domain_agent_node)
    builder.add_node("psycho_linguistic_agent", psycho_linguistic_agent_node)

    # Debate 和聚合
    builder.add_node("debate_gate", debate_gate_node)
    builder.add_node("debate", debate_node)
    builder.add_node("risk_aggregator", risk_aggregator_node)

    # 策略和输出
    builder.add_node("strategy_supervisor", strategy_supervisor_node)
    builder.add_node("followup_generation", followup_generation_node)
    builder.add_node("report_generation", report_generation_node)

    # ---- 构建边 ----

    # 第一版基础顺序流
    builder.add_edge(START, "fact_extraction")
    builder.add_edge("fact_extraction", "anomaly_detection")
    builder.add_edge("anomaly_detection", "consistency_judge")
    builder.add_edge("consistency_judge", "state_update")

    # state_update → 并行 fan-out 到 4 个 specialist
    builder.add_conditional_edges("state_update", fanout_specialists)

    # 4 个 specialist 汇聚到 debate_gate
    builder.add_edge("semantic_agent", "debate_gate")
    builder.add_edge("logical_agent", "debate_gate")
    builder.add_edge("domain_agent", "debate_gate")
    builder.add_edge("psycho_linguistic_agent", "debate_gate")

    # debate_gate 条件路由
    builder.add_conditional_edges(
        "debate_gate",
        route_after_debate_gate,
        {
            "debate": "debate",
            "aggregate": "risk_aggregator",
        },
    )

    # debate → risk_aggregator
    builder.add_edge("debate", "risk_aggregator")

    # risk_aggregator → strategy_supervisor
    builder.add_edge("risk_aggregator", "strategy_supervisor")

    # strategy_supervisor 条件路由
    builder.add_conditional_edges(
        "strategy_supervisor",
        route_after_supervisor,
        {
            "followup_generation": "followup_generation",
            "report_generation": "report_generation",
        },
    )

    # 两个终点
    builder.add_edge("followup_generation", END)
    builder.add_edge("report_generation", END)

    return builder.compile()
