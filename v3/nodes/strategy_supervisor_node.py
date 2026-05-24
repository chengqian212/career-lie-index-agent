"""策略决策节点：决定下一步是追问还是生成最终报告"""

import json
import logging

from ..llm_client import get_llm
from ..prompts import STRATEGY_SUPERVISOR_PROMPT
from ..utils.json_utils import safe_json_parse_with_retry
from ..utils.text_utils import format_anomalies_table, clean_llm_output
from ..state_schema import DialogueState
from .. import config

logger = logging.getLogger(__name__)


def strategy_supervisor_node(state: DialogueState) -> dict:
    """策略决策节点

    v3 改进：
    - 不负责决定调用哪些专家（由 lightweight_routing_supervisor 决定）
    - 只负责：是否继续追问、是否生成最终报告、当前优先追问点、追问语气和方向
    - 新增输入：routing_decision, called_specialists, dimension_scores, risk_explanation, debate_result

    路由规则：
    - 如果 round_id >= max_rounds → final_report
    - 否则如果 lie_index >= 30 或存在 unresolved anomaly → generate_followup
    - 否则 → generate_followup（默认继续追问）

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 next_action, priority_issue, followup_strategy
    """
    lie_index = state.get("lie_index", 0)
    dimension_scores = state.get("dimension_scores", {})
    specialist_results = state.get("specialist_results", [])
    debate_result = state.get("debate_result")
    anomalies_table = state.get("anomalies_table", [])
    round_id = state.get("round_id", 1)
    max_rounds = state.get("max_rounds", config.MAX_ROUNDS)

    # v3 新增输入
    routing_decision = state.get("routing_decision", {})
    called_specialists = state.get("called_specialists", [])

    # 先用规则快速判断是否应该直接生成最终报告
    if round_id >= max_rounds:
        # 已达最大轮次，生成最终报告
        next_action = "final_report"
    else:
        # 未达最大轮次，继续追问
        next_action = "generate_followup"

    # 准备 Supervisor 的输入
    anomalies_text = format_anomalies_table(anomalies_table)

    # 格式化 specialist_results
    specialist_text = "\n".join(
        f"  [{r.get('agent', '?')}] 分数: {r.get('score', 0)}"
        for r in specialist_results
        if isinstance(r, dict)
    )

    debate_text = ""
    if isinstance(debate_result, dict):
        debate_text = json.dumps(debate_result, ensure_ascii=False, indent=2)

    # v3: 格式化路由决策
    routing_text = json.dumps(routing_decision, ensure_ascii=False, indent=2) if routing_decision else "无路由决策"

    # v3: 格式化实际调用专家
    called_text = ", ".join(called_specialists) if called_specialists else "无"

    # 调用 LLM 获取策略建议（使用 ChatPromptTemplate 的 invoke 方法）
    llm = get_llm()
    response = llm.invoke(
        STRATEGY_SUPERVISOR_PROMPT.invoke({
            "lie_index": lie_index,
            "dimension_scores": dimension_scores,
            "specialist_results": specialist_text,
            "debate_result": debate_text or "无",
            "anomalies_table": anomalies_text,
            "round_id": round_id,
            "max_rounds": max_rounds,
            "routing_decision": routing_text,
            "called_specialists": called_text,
        })
    )

    raw_output = clean_llm_output(response.content)
    result = safe_json_parse_with_retry(
        raw_output,
        default={},
        node_name="策略决策节点"
    )

    if not isinstance(result, dict):
        result = {}

    # 用规则覆盖 next_action（LLM 只提供追问策略，不决定是否结束）
    result["next_action"] = next_action

    logger.info(
        f"[策略决策节点] 决策完成 - next_action={result.get('next_action')}, priority_issue={result.get('priority_issue')}"
    )

    return {
        "next_action": result.get("next_action", next_action),
        "priority_issue": result.get("priority_issue", "继续了解职业细节"),
        "followup_strategy": result.get("followup_strategy", "clarification"),
    }