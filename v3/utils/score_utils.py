"""分数工具模块：谎言指数计算与风险等级判定"""

from .. import config
from typing import Dict, Optional, List


def compute_unresolved_followup_score(unresolved_count: int) -> float:
    """计算未澄清异常分数

    Args:
        unresolved_count: 未澄清异常数量
    Returns:
        0-100 分数
    """
    return min(100.0, unresolved_count * config.UNRESOLVED_FOLLOWUP_PER_SCORE)


def calculate_lightweight_risk_score(
    surface_risk_score: float,
    unresolved_count: int,
    current_anomalies: List[Dict]
) -> float:
    """v3 改进：轻量风险分数计算（删除 severity，只使用 score）
    
    当没有调用 Specialist Agent 时，根据第一层结果计算低成本谎言指数
    
    公式：lie_index = surface_risk_score + unresolved_count * 10 + avg_anomaly_score * 0.2
    
    Args:
        surface_risk_score: 表层风险分数（0-100）
        unresolved_count: 未解决异常数量
        current_anomalies: 当前轮次异常列表
    Returns:
        0-100 的谎言指数
    """
    # 基础分数
    base_score = float(surface_risk_score or 0)
    
    # 未解决异常加分
    anomaly_penalty = min(30.0, unresolved_count * 10.0)
    
    # 当前轮次异常分数加分（使用 score，不再使用 severity）
    anomaly_score_bonus = 0.0
    if current_anomalies:
        scores = [
            float(a.get("score", 0) or 0)
            for a in current_anomalies
            if isinstance(a, dict)
        ]
        if scores:
            avg_anomaly_score = sum(scores) / len(scores)
            anomaly_score_bonus = min(20.0, avg_anomaly_score * 0.2)
    
    # 计算总分
    lie_index = base_score + anomaly_penalty + anomaly_score_bonus
    
    # 限制在 0-100 范围
    return round(max(0.0, min(100.0, lie_index)), 1)


def compute_lie_index(
    dimension_scores: Dict[str, float],
    unresolved_count: int,
    debate_adjustment: Optional[Dict[str, float]] = None,
    called_specialists: Optional[List[str]] = None,
) -> float:
    """计算综合谎言指数

    v3 改进：支持按需专家调用，只对实际调用的维度归一化计算
    
    公式：
    lie_index = Σ(weight_i * score_i) / Σ(weight_i)  # 只对实际调用的维度
    
    如果有 debate_adjustment，先调整各维度分数再计算。

    Args:
        dimension_scores: 各维度分数 {"semantic": 65, "logical": 50, ...}
        unresolved_count: 未澄清异常数量
        debate_adjustment: Debate 调整 {"semantic": 5, "logical": -5, ...}
        called_specialists: v3 新增，实际调用的专家列表
    Returns:
        0-100 的谎言指数
    """
    # 深拷贝避免修改原始数据
    scores = dict(dimension_scores)

    # 应用 Debate 调整
    if debate_adjustment:
        for key, delta in debate_adjustment.items():
            if key in scores:
                scores[key] = max(0.0, min(100.0, scores[key] + delta))

    # 计算未澄清异常分数
    unresolved_score = compute_unresolved_followup_score(unresolved_count)

    # v3: 如果提供了 called_specialists，只对实际调用的维度加权
    if called_specialists is not None:
        # 权重映射
        weight_map = {
            "semantic": config.WEIGHT_SEMANTIC,
            "logical": config.WEIGHT_LOGICAL,
            "domain": config.WEIGHT_DOMAIN,
            "psycho_linguistic": config.WEIGHT_PSYCHO_LINGUISTIC,
        }
        
        # 只计算实际调用的维度
        active_weights = {}
        active_scores = {}
        
        for specialist in called_specialists:
            if specialist in weight_map and specialist in scores:
                active_weights[specialist] = weight_map[specialist]
                active_scores[specialist] = scores[specialist]
        
        # 如果没有调用任何专家，返回未澄清异常分数
        if not active_weights:
            return round(unresolved_score, 1)
        
        # 计算总权重和加权分数
        total_weight = sum(active_weights.values())
        weighted_sum = sum(active_weights[k] * active_scores[k] for k in active_weights)
        
        # 加入未澄清异常权重
        total_weight += config.WEIGHT_UNRESOLVED_FOLLOWUP
        weighted_sum += config.WEIGHT_UNRESOLVED_FOLLOWUP * unresolved_score
        
        # 归一化计算
        lie_index = weighted_sum / total_weight if total_weight > 0 else 0.0
    else:
        # v2 原始逻辑：固定权重计算
        lie_index = (
            config.WEIGHT_SEMANTIC * scores.get("semantic", 0)
            + config.WEIGHT_LOGICAL * scores.get("logical", 0)
            + config.WEIGHT_DOMAIN * scores.get("domain", 0)
            + config.WEIGHT_PSYCHO_LINGUISTIC * scores.get("psycho_linguistic", 0)
            + config.WEIGHT_UNRESOLVED_FOLLOWUP * unresolved_score
        )

    return round(max(0.0, min(100.0, lie_index)), 1)


def determine_risk_level(lie_index: float) -> str:
    """根据谎言指数判定风险等级

    0-30：低
    31-60：中
    61-100：高

    Args:
        lie_index: 谎言指数 0-100
    Returns:
        风险等级字符串
    """
    if lie_index <= config.RISK_LOW_THRESHOLD:
        return "低"
    elif lie_index <= config.RISK_HIGH_THRESHOLD:
        return "中"
    else:
        return "高"


def compute_dimension_scores_debate_adjusted(
    dimension_scores: Dict[str, float],
    debate_adjustment: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """返回经 Debate 调整后的维度分数

    Args:
        dimension_scores: 原始维度分数
        debate_adjustment: Debate 调整量
    Returns:
        调整后的维度分数
    """
    scores = dict(dimension_scores)
    if debate_adjustment:
        for key, delta in debate_adjustment.items():
            if key in scores:
                scores[key] = round(max(0.0, min(100.0, scores[key] + delta)), 1)
    return scores
