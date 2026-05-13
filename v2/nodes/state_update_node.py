"""状态更新节点：汇总本轮信息并更新指示器历史"""

from ..state_schema import DialogueState
from ..memory.anomaly_table import count_unresolved


def state_update_node(state: DialogueState) -> dict:
    """状态更新节点

    汇总本轮抽取的事实、检测的异常、一致性判断结果，
    更新指示器历史。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典
    """
    round_id = state.get("round_id", 1)
    current_facts = state.get("current_facts", [])
    current_anomalies = state.get("current_anomalies", [])
    consistency_results = state.get("consistency_results", [])

    # 构建本轮指示器
    indicator = {
        "round_id": round_id,
        "fact_count": len(current_facts),
        "anomaly_count": len(current_anomalies),
        "unresolved_count": count_unresolved(state.get("anomalies_table", [])),
        "consistency_issues": sum(
            1 for r in consistency_results
            if isinstance(r, dict) and r.get("relation") in ("潜在不匹配", "明确矛盾", "无法判断")
        ),
    }

    # 更新指示器历史
    updated_indicator_history = list(state.get("indicator_history", []))
    updated_indicator_history.append(indicator)

    return {
        "indicator_history": updated_indicator_history,
    }
