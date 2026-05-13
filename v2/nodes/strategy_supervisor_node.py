"""策略决策节点：决定下一步是追问还是生成最终报告"""

from langchain_core.messages import HumanMessage, SystemMessage
from ..llm_client import get_llm
from ..prompts import STRATEGY_SUPERVISOR_SYSTEM
from ..utils.json_utils import safe_json_parse
from ..utils.text_utils import format_anomalies_table, clean_llm_output
from ..state_schema import DialogueState
from .. import config


def strategy_supervisor_node(state: DialogueState) -> dict:
    """策略决策节点

    Supervisor 不重新抽取事实，不重新判断所有矛盾，只做策略决策。

    路由规则：
    - 如果 round_id >= max_rounds → final_report
    - 否则如果 lie_index >= 30 或存在 unresolved anomaly → generate_followup
    - 否则 → generate_followup（默认继续追问）

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 next_action
    """
    lie_index = state.get("lie_index", 0)
    risk_level = state.get("risk_level", "低")
    dimension_scores = state.get("dimension_scores", {})
    specialist_results = state.get("specialist_results", [])
    debate_result = state.get("debate_result")
    anomalies_table = state.get("anomalies_table", [])
    round_id = state.get("round_id", 1)
    max_rounds = state.get("max_rounds", config.MAX_ROUNDS)

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
    import json
    specialist_text = "\n".join(
        f"  [{r.get('agent', '?')}] 分数: {r.get('score', 0)}, 投票: {r.get('vote', '?')}"
        for r in specialist_results
        if isinstance(r, dict)
    )

    debate_text = ""
    if isinstance(debate_result, dict):
        debate_text = json.dumps(debate_result, ensure_ascii=False, indent=2)

    # 调用 LLM 获取策略建议（即使规则已经判断了，也让 LLM 提供追问策略）
    prompt = STRATEGY_SUPERVISOR_SYSTEM.format(
        lie_index=lie_index,
        risk_level=risk_level,
        dimension_scores=dimension_scores,
        specialist_results=specialist_text,
        debate_result=debate_text or "无",
        anomalies_table=anomalies_text,
        round_id=round_id,
        max_rounds=max_rounds,
    )

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请做出策略决策"),
    ])

    raw_output = clean_llm_output(response.content)
    result = safe_json_parse(raw_output, default={})

    if not isinstance(result, dict):
        result = {}

    # 用规则覆盖 next_action（LLM 只提供追问策略，不决定是否结束）
    result["next_action"] = next_action

    return {
        "next_action": result.get("next_action", next_action),
        "agent_votes": result,  # 存储完整的策略决策结果
    }
