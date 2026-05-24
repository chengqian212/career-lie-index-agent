"""风险聚合节点：根据各维度分数计算谎言指数

v3 改进：
- 先处理专家 anomaly_updates
- 再写入专家 new_anomalies
- 再计算 unresolved_count
- 最后计算 lie_index

v3.3 改进：
- 合并 lightweight_risk_aggregator 的轻量评分逻辑
- 在没有调用专家时，使用 surface_risk_score、unresolved_count、current_anomalies 综合评分
"""

from typing import Optional

from ..state_schema import DialogueState
from ..utils.score_utils import (
    compute_lie_index,
    compute_dimension_scores_debate_adjusted,
    calculate_lightweight_risk_score,
)
from ..memory.anomaly_table import (
    count_unresolved,
    apply_specialist_anomaly_updates,
    add_specialist_results_as_anomalies,
)


def risk_aggregator_node(state: DialogueState) -> dict:
    """风险聚合节点

    v3.3 改进：
    - 合并轻量评分逻辑，跳过专家时不再只用 unresolved_count * 20
    - 引入 surface_risk_score 和 current_anomalies 信息

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 lie_index, dimension_scores, risk_explanation, anomalies_table
    """
    round_id = state.get("round_id", 1)
    anomalies_table = state.get("anomalies_table", [])
    specialist_results = state.get("specialist_results", [])
    called_specialists = state.get("called_specialists", [])

    # v3: 先处理专家 anomaly_updates
    updated_anomalies_table = apply_specialist_anomaly_updates(
        anomalies_table=anomalies_table,
        specialist_results=specialist_results,
        round_id=round_id,
    )

    # v3: 再写入专家 new_anomalies
    updated_anomalies_table = add_specialist_results_as_anomalies(
        anomalies_table=updated_anomalies_table,
        specialist_results=specialist_results,
        round_id=round_id,
    )

    # v3: 计算 unresolved_count（基于更新后的 anomalies_table）
    unresolved_count = count_unresolved(updated_anomalies_table)

    # ============================================================
    # 情况一：没有调用任何专家
    # ============================================================
    if not called_specialists:
        surface_risk_score = state.get("surface_risk_score", 0)
        current_anomalies = state.get("current_anomalies", [])

        lie_index = calculate_lightweight_risk_score(
            surface_risk_score=surface_risk_score,
            unresolved_count=unresolved_count,
            current_anomalies=current_anomalies,
        )

        dimension_scores = {
            "lightweight_surface": surface_risk_score,
            "unresolved_anomalies": min(100, unresolved_count * 20),
        }

        risk_explanation = []

        if surface_risk_score >= 30:
            risk_explanation.append(f"当前回答存在一定表层风险信号（{surface_risk_score}分）")

        if unresolved_count > 0:
            risk_explanation.append(f"存在{unresolved_count}个未澄清的异常信号")

        if current_anomalies:
            anomaly_types = [a.get("type", "未知") for a in current_anomalies]
            risk_explanation.append(f"本轮识别到异常类型：{', '.join(set(anomaly_types))}")

        if not risk_explanation:
            risk_explanation.append("当前轮次未发现明显风险信号")

        return {
            "lie_index": lie_index,
            "dimension_scores": dimension_scores,
            "risk_explanation": risk_explanation,
            "anomalies_table": updated_anomalies_table,
        }

    # ============================================================
    # 情况二：有专家分析结果
    # ============================================================

    # v3: 动态初始化维度分数，只对实际调用的专家设置初始值
    dimension_scores = {}

    # 从 specialist_results 提取分数
    for result in specialist_results:
        if isinstance(result, dict):
            agent = result.get("agent", "")
            score = float(result.get("score", 0))
            if agent in called_specialists:
                dimension_scores[agent] = score

    # 对于调用了但没有返回结果的专家，设置默认分数
    for specialist in called_specialists:
        if specialist not in dimension_scores:
            dimension_scores[specialist] = 0.0

    # 获取 Debate 调整
    debate_result = state.get("debate_result")
    debate_adjustment = None
    if isinstance(debate_result, dict):
        debate_adjustment = debate_result.get("debate_adjustment")

    # v3: 计算谎言指数，传入实际调用的专家列表
    lie_index = compute_lie_index(
        dimension_scores=dimension_scores,
        unresolved_count=unresolved_count,
        debate_adjustment=debate_adjustment,
        called_specialists=called_specialists,
    )

    # 生成风险解释
    risk_explanation = []

    # 经 Debate 调整后的维度分数
    adjusted_scores = compute_dimension_scores_debate_adjusted(
        dimension_scores, debate_adjustment
    )

    # v3: 只对实际调用的专家生成解释
    if "semantic" in adjusted_scores and adjusted_scores["semantic"] >= 50:
        risk_explanation.append("职业内容表述存在潜在不一致")
    if "logical" in adjusted_scores and adjusted_scores["logical"] >= 50:
        risk_explanation.append("时间线或逻辑存在待澄清点")
    if "domain" in adjusted_scores and adjusted_scores["domain"] >= 50:
        risk_explanation.append("职业描述与常识存在偏差")
    if "psycho_linguistic" in adjusted_scores and adjusted_scores["psycho_linguistic"] >= 50:
        risk_explanation.append("表达方式存在软性风险信号")
    
    if unresolved_count > 0:
        risk_explanation.append(f"仍有 {unresolved_count} 个待澄清异常")

    if not risk_explanation:
        risk_explanation.append("暂无明显不一致")

    # v3: 在维度分数中标记本轮未调用的专家
    full_dimension_scores: dict[str, Optional[float]] = {
        "semantic": None,
        "logical": None,
        "domain": None,
        "psycho_linguistic": None,
    }
    for specialist in called_specialists:
        if specialist in adjusted_scores:
            full_dimension_scores[specialist] = adjusted_scores[specialist]

    # 只返回非 None 的维度分数
    return {
        "lie_index": lie_index,
        "dimension_scores": {k: v for k, v in full_dimension_scores.items() if v is not None},
        "risk_explanation": risk_explanation,
        "anomalies_table": updated_anomalies_table,  # v3: 返回更新后的 anomalies_table
    }
