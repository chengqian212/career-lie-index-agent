"""分数工具模块：谎言指数计算与风险等级判定"""

from .. import config
from typing import Dict, Optional


def compute_unresolved_followup_score(unresolved_count: int) -> float:
    """计算未澄清异常分数

    Args:
        unresolved_count: 未澄清异常数量
    Returns:
        0-100 分数
    """
    return min(100.0, unresolved_count * config.UNRESOLVED_FOLLOWUP_PER_SCORE)


def compute_lie_index(
    dimension_scores: Dict[str, float],
    unresolved_count: int,
    debate_adjustment: Optional[Dict[str, float]] = None,
) -> float:
    """计算综合谎言指数

    公式：
    lie_index = 0.30 * semantic + 0.25 * logical + 0.20 * domain
              + 0.15 * psycho_linguistic + 0.10 * unresolved_followup

    如果有 debate_adjustment，先调整各维度分数再计算。

    Args:
        dimension_scores: 各维度分数 {"semantic": 65, "logical": 50, ...}
        unresolved_count: 未澄清异常数量
        debate_adjustment: Debate 调整 {"semantic": 5, "logical": -5, ...}
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

    # 加权计算
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
