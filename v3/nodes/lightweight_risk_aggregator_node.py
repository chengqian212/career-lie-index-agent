"""轻量风险聚合节点：当没有调用 Specialist Agent 时，根据第一层结果计算低成本谎言指数"""

from ..state_schema import DialogueState
from ..utils.score_utils import calculate_lightweight_risk_score
from ..memory.anomaly_table import get_active_anomalies, count_unresolved


def lightweight_risk_aggregator_node(state: DialogueState) -> dict:
    """轻量风险聚合节点

    当没有调用 Specialist Agent 时，根据第一层结果计算一个低成本谎言指数
    """
    surface_risk_score = state.get("surface_risk_score", 0)
    current_anomalies = state.get("current_anomalies", [])
    anomalies_table = state.get("anomalies_table", [])

    # v3: 使用 get_active_anomalies 获取仍需关注的异常
    active_anomalies = get_active_anomalies(anomalies_table)
    unresolved_count = len(active_anomalies)

    # 使用轻量风险计算函数
    lie_index = calculate_lightweight_risk_score(
        surface_risk_score=surface_risk_score,
        unresolved_count=unresolved_count,
        current_anomalies=current_anomalies
    )

    # 构造维度分数（轻量模式只有表层维度）
    dimension_scores = {
        "lightweight_surface": surface_risk_score,
        "unresolved_anomalies": min(100, unresolved_count * 20)
    }

    # 构造风险解释
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
        "risk_explanation": risk_explanation
    }
