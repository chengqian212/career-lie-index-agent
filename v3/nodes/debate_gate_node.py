"""Debate 门控节点：判断是否需要触发 Debate"""

from ..state_schema import DialogueState
from .. import config


def debate_gate_node(state: DialogueState) -> dict:
    """Debate 门控节点

    v3 改进：只在已经调用至少 2 个 Specialist Agent 时才考虑触发 Debate
    
    根据以下条件判断是否需要触发 Debate：
    0. v3 新增：called_specialists 数量 < 2，则 debate_needed = False
    1. 任一 Specialist Agent 的 score >= 75
    2. Specialist Agent 分数最大差值 >= 40
    3. Semantic / Logical / Domain 中任一输出 high_risk，而另一个输出 low_risk
    4. consistency_results 中存在"潜在不匹配"或"无法判断"
    5. 任一关键 Agent confidence 为 low 且存在 unresolved anomaly

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 debate_needed
    """
    specialist_results = state.get("specialist_results", [])
    called_specialists = state.get("called_specialists", [])

    # v3 新增：如果调用专家数量 < 2，不触发 Debate
    if len(called_specialists) < config.MIN_SPECIALISTS_FOR_DEBATE:
        return {
            "debate_needed": False,
        }

    # 提取各 Agent 分数
    scores = {}
    for result in specialist_results:
        if isinstance(result, dict):
            agent = result.get("agent", "")
            scores[agent] = result.get("score", 0)

    debate_needed = False

    # 条件 1：任一 Specialist Agent 的 score >= 75
    for agent, score in scores.items():
        if score >= config.DEBATE_SCORE_THRESHOLD:
            debate_needed = True
            break

    # 条件 2：Specialist Agent 分数最大差值 >= 40
    if len(scores) >= 2:
        score_values = list(scores.values())
        max_diff = max(score_values) - min(score_values)
        if max_diff >= config.DEBATE_SCORE_DIFF_THRESHOLD:
            debate_needed = True

    # 条件 3：Semantic / Logical / Domain 中任一分数 >= 60，而另一个分数 < 30
    key_agents = ["semantic", "logical", "domain"]
    key_scores = [scores.get(a, 0) for a in key_agents if a in scores]
    if any(s >= 60 for s in key_scores) and any(s < 30 for s in key_scores):
        debate_needed = True

    # 条件 4：consistency_results 中存在"潜在不匹配"或"无法判断"
    consistency_results = state.get("consistency_results", [])
    for result in consistency_results:
        if isinstance(result, dict):
            relation = result.get("relation", "")
            if relation in ("潜在不匹配", "无法判断"):
                debate_needed = True
                break

    # 条件 5：任一关键 Agent 分数 < 30 且存在 unresolved anomaly
    anomalies_table = state.get("anomalies_table", [])
    unresolved_count = sum(
        1 for a in anomalies_table
        if isinstance(a, dict) and a.get("status") == "unresolved"
    )
    if unresolved_count > 0:
        for agent in key_agents:
            if scores.get(agent, 0) < 30:
                debate_needed = True
                break

    return {
        "debate_needed": debate_needed,
    }
