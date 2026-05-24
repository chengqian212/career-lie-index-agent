"""LangGraph 图定义：编排多 Agent 工作流

该模块定义了一个基于 LangGraph 的多 Agent 工作流，用于分析对话内容、识别风险信号、
并生成相应的策略和报告。工作流包含轻量级预分析、专家分析、辩论机制、风险聚合和策略生成等阶段。

v3 改进：绕过 strategy_supervisor，聚合器后直接根据 round_id 条件路由到追问或报告。
v3.3 改进：删除 lightweight_risk_aggregator，统一使用 risk_aggregator；
        恢复 strategy_supervisor，由其根据异常状态/信息充分度/追问次数等决定追问或报告。
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from .state_schema import DialogueState

# 导入日志包装器
from .utils.node_wrapper import wrap_node

# 轻量预分析节点
from .nodes.quick_preanalysis_node import quick_preanalysis_node
from .nodes.lightweight_routing_supervisor_node import lightweight_routing_supervisor_node
# v3.3: 不再使用 lightweight_risk_aggregator_node
# from .nodes.lightweight_risk_aggregator_node import lightweight_risk_aggregator_node

# Specialist Agent
from .nodes.specialists.semantic_agent_node import semantic_agent_node
from .nodes.specialists.logical_agent_node import logical_agent_node
from .nodes.specialists.domain_agent_node import domain_agent_node
from .nodes.specialists.psycho_linguistic_agent_node import psycho_linguistic_agent_node

# Debate 和聚合
from .nodes.debate_gate_node import debate_gate_node
from .nodes.debate_node import debate_node
from .nodes.risk_aggregator_node import risk_aggregator_node

# 策略和输出
from .nodes.strategy_supervisor_node import strategy_supervisor_node  # v3.3 恢复
from .nodes.followup_generation_node import followup_generation_node
from .nodes.report_generation_node import report_generation_node

# 用日志包装器包装所有节点函数
quick_preanalysis_node = wrap_node(quick_preanalysis_node)
lightweight_routing_supervisor_node = wrap_node(lightweight_routing_supervisor_node)
# lightweight_risk_aggregator_node = wrap_node(lightweight_risk_aggregator_node)  # 不再需要
semantic_agent_node = wrap_node(semantic_agent_node)
logical_agent_node = wrap_node(logical_agent_node)
domain_agent_node = wrap_node(domain_agent_node)
psycho_linguistic_agent_node = wrap_node(psycho_linguistic_agent_node)
debate_gate_node = wrap_node(debate_gate_node)
debate_node = wrap_node(debate_node)
risk_aggregator_node = wrap_node(risk_aggregator_node)
strategy_supervisor_node = wrap_node(strategy_supervisor_node)
followup_generation_node = wrap_node(followup_generation_node)
report_generation_node = wrap_node(report_generation_node)


def route_specialists(state: DialogueState) -> list[Send]:
    """根据路由决策条件启动 Specialist Agent
    
    Args:
        state: 当前对话状态，包含 selected_specialists 字段
        
    Returns:
        Send 对象列表，每个 Send 对象指定要调用的专家节点和传递的状态
        
    说明:
        - 从状态中获取 selected_specialists 列表
        - 根据映射关系将专家名称转换为节点名称
        - 为每个选中的专家创建一个 Send 对象
    """
    selected = state.get("selected_specialists", [])
    if not selected:
        return []
    
    # 专家名称到节点名称的映射
    mapping = {
        "semantic": "semantic_agent",
        "logical": "logical_agent",
        "domain": "domain_agent",
        "psycho_linguistic": "psycho_linguistic_agent",
    }
    
    # 为每个选中的专家创建并发任务
    return [Send(mapping[s], state) for s in selected if s in mapping]


def route_after_routing_supervisor(state: DialogueState) -> list[Send]:
    """路由监督后的条件分支：调用专家或跳转到风险聚合

    v3.3 修改：跳过专家时直接进入 risk_aggregator，不再使用 lightweight_risk_aggregator
    
    Args:
        state: 当前对话状态
        
    Returns:
        Send 对象列表，指定下一个要执行的节点
        
    说明:
        - 如果不需要专家分析或没有选中专家，直接跳转到 risk_aggregator
        - 否则，根据选中的专家列表并行启动相应的专家节点
    """
    if not state.get("need_specialist", False) or not state.get("selected_specialists", []):
        return [Send("risk_aggregator", state)]
    
    return route_specialists(state)


def route_after_debate_gate(state: DialogueState) -> str:
    """Debate 门控路由（目前暂时绕过辩论，直接进入风险聚合）
    
    v3.3 改进：暂时无效化辩论节点，所有情况直接进入 risk_aggregator
    
    Args:
        state: 当前对话状态
        
    Returns:
        下一个节点的名称
        
    说明:
        - 当前始终返回 "risk_aggregator"
        - 若要恢复辩论，可取消注释原始逻辑
    """
    # 暂时绕过辩论
    return "risk_aggregator"

    # 原始逻辑（保留以便恢复）
    # return "debate" if state.get("debate_needed", False) else "risk_aggregator"


def route_after_strategy_supervisor(state: DialogueState) -> str:
    """策略监督后的路由：根据 next_action 决定追问还是生成报告
    
    v3.3 新增：替代原来的 route_after_aggregator，由 strategy_supervisor 决策

    Args:
        state: 当前对话状态，包含 next_action 字段

    Returns:
        下一个节点的名称
    """
    next_action = state.get("next_action", "generate_followup")
    if next_action == "final_report":
        return "report_generation"
    return "followup_generation"


def build_graph() -> CompiledStateGraph:
    """构建 v3.3 LangGraph 工作流图
    
    Returns:
        编译完成的状态图对象，可用于执行工作流
        
    v3.3 改进：
        - 删除 lightweight_risk_aggregator，所有情况统一进入 risk_aggregator
        - 恢复 strategy_supervisor，由其根据异常、事实充分度等条件决定追问/报告
        
    工作流结构:
        1. 快速预分析节点一次 LLM 调用完成事实抽取和异常检测
        2. 路由监督器决定是否需要专家分析
        3. 根据决策并行启动指定的专家代理或直接进入 risk_aggregator
        4. 专家分析结果通过辩论门控，决定是否需要辩论（目前绕过辩论）
        5. 风险聚合器汇总所有分析结果（先处理异常更新，再写入新异常）
        6. strategy_supervisor 根据状态决定继续追问还是生成报告
        7. 输出结果并结束
    
    流程图:
        START → quick_preanalysis → lightweight_routing_supervisor
              → 条件 fan-out specialists 或 risk_aggregator
              →（若调用专家）debate_gate → risk_aggregator
              → risk_aggregator → strategy_supervisor
              → 根据 strategy_supervisor 路由 → followup_generation 或 report_generation
              → END
    """
    builder = StateGraph(DialogueState)

    #     ==================== 注册节点 ====================
    
    # 轻量预分析节点
    builder.add_node("quick_preanalysis", quick_preanalysis_node)                   # 快速预分析（事实+异常）
    builder.add_node("lightweight_routing_supervisor", lightweight_routing_supervisor_node)  # 轻量级路由决策
    # v3.3 删除 lightweight_risk_aggregator 节点
    
    # 专家分析节点
    builder.add_node("semantic_agent", semantic_agent_node)                         # 语义分析专家
    builder.add_node("logical_agent", logical_agent_node)                           # 逻辑分析专家
    builder.add_node("domain_agent", domain_agent_node)                             # 领域知识专家
    builder.add_node("psycho_linguistic_agent", psycho_linguistic_agent_node)       # 心理语言学专家
    
    # 辩论和聚合节点（辩论节点仍保留注册，但当前路由会绕过辩论）
    builder.add_node("debate_gate", debate_gate_node)                               # 辩论门控
    builder.add_node("debate", debate_node)                                         # 专家辩论（当前无效）
    builder.add_node("risk_aggregator", risk_aggregator_node)                       # 风险聚合器
    
    # 策略和输出节点
    builder.add_node("strategy_supervisor", strategy_supervisor_node)               # v3.3 恢复策略监督
    builder.add_node("followup_generation", followup_generation_node)               # 生成跟进问题
    builder.add_node("report_generation", report_generation_node)                   # 生成最终报告

    # ==================== 构建边（定义流程） ====================
    
    # v3.2 改为单节点流程：一次 LLM 调用完成事实抽取和异常检测
    builder.add_edge(START, "quick_preanalysis")
    builder.add_edge("quick_preanalysis", "lightweight_routing_supervisor")
    
    # 路由监督器根据条件分支：跳过专家直接到 risk_aggregator，或启动专家
    builder.add_conditional_edges("lightweight_routing_supervisor", route_after_routing_supervisor)

    # 所有专家分析完成后，汇聚到辩论门控
    for agent in ("semantic_agent", "logical_agent", "domain_agent", "psycho_linguistic_agent"):
        builder.add_edge(agent, "debate_gate")

    # 辩论门控：目前绕过辩论，直接到风险聚合器
    builder.add_conditional_edges(
        "debate_gate", route_after_debate_gate,
        {"debate": "debate", "risk_aggregator": "risk_aggregator"},
    )
    
    # 辩论结束后汇聚到风险聚合器（当前不会被触发，但保留以备后续启用）
    builder.add_edge("debate", "risk_aggregator")
    
    # v3.3 添加：risk_aggregator 后进入 strategy_supervisor
    builder.add_edge("risk_aggregator", "strategy_supervisor")
    
    # v3.3：strategy_supervisor 根据决策路由到追问或报告
    builder.add_conditional_edges(
        "strategy_supervisor",
        route_after_strategy_supervisor,
        {
            "followup_generation": "followup_generation",
            "report_generation": "report_generation",
        },
    )
    
    # 输出节点完成后结束工作流
    builder.add_edge("followup_generation", END)
    builder.add_edge("report_generation", END)

    # 编译并返回完整的工作流图
    return builder.compile()
