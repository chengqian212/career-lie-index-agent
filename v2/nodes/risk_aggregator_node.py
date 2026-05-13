"""风险聚合节点：根据各维度分数计算谎言指数"""

from ..state_schema import DialogueState
from ..utils.score_utils import (
    compute_lie_index,
    determine_risk_level,
    compute_dimension_scores_debate_adjusted,
)
from ..memory.anomaly_table import count_unresolved


def risk_aggregator_node(state: DialogueState) -> dict:
    """风险聚合节点

    根据 4 个 Specialist Agent 的分数、Debate 结果、未澄清异常数量，
    计算谎言指数。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 lie_index, risk_level, dimension_scores, risk_explanation
    """
    specialist_results = state.get("specialist_results", [])

    # 提取各维度分数
    dimension_scores = {
        "semantic": 0.0,
        "logical": 0.0,
        "domain": 0.0,
        "psycho_linguistic": 0.0,
    }

    for result in specialist_results:
        if isinstance(result, dict):
            agent = result.get("agent", "")
            score = float(result.get("score", 0))
            if agent in dimension_scores:
                dimension_scores[agent] = score

    # 获取 Debate 调整
    debate_result = state.get("debate_result")
    debate_adjustment = None
    if isinstance(debate_result, dict):
        debate_adjustment = debate_result.get("debate_adjustment")

    # 计算未澄清异常数
    unresolved_count = count_unresolved(state.get("anomalies_table", []))

    # 计算谎言指数
    lie_index = compute_lie_index(
        dimension_scores=dimension_scores,
        unresolved_count=unresolved_count,
        debate_adjustment=debate_adjustment,
    )

    # 判定风险等级
    risk_level = determine_risk_level(lie_index)

    # 生成风险解释
    risk_explanation = []

    # 经 Debate 调整后的维度分数
    adjusted_scores = compute_dimension_scores_debate_adjusted(
        dimension_scores, debate_adjustment
    )

    if adjusted_scores.get("semantic", 0) >= 50:
        risk_explanation.append("职业内容表述存在潜在不一致")
    if adjusted_scores.get("logical", 0) >= 50:
        risk_explanation.append("时间线或逻辑存在待澄清点")
    if adjusted_scores.get("domain", 0) >= 50:
        risk_explanation.append("职业描述与常识存在偏差")
    if adjusted_scores.get("psycho_linguistic", 0) >= 50:
        risk_explanation.append("表达方式存在软性风险信号")
    if unresolved_count > 0:
        risk_explanation.append(f"仍有 {unresolved_count} 个待澄清异常")

    if not risk_explanation:
        risk_explanation.append("暂无明显不一致")

    return {
        "lie_index": lie_index,
        "risk_level": risk_level,
        "dimension_scores": adjusted_scores,
        "risk_explanation": risk_explanation,
    }
