"""异常表模块：管理对话中发现的异常记录"""

from typing import List, Dict, Optional


def init_anomaly_table() -> List[Dict]:
    """初始化空异常表

    Returns:
        空异常表
    """
    return []


def add_anomalies(
    anomalies_table: List[Dict],
    new_anomalies: List[Dict],
    round_id: int,
) -> List[Dict]:
    """向异常表中添加新异常

    每条异常格式：
    {
        "round_id": int,
        "type": str,           # 如 "语义不匹配", "时间线冲突", "回避" 等
        "description": str,
        "evidence": List[str],  # 引用原文
        "status": str,          # "unresolved" | "resolved" | "clarified"
        "related_facts": List[int],  # 关联事实索引
    }

    Args:
        anomalies_table: 当前异常表
        new_anomalies: 新发现的异常列表
        round_id: 当前轮次
    Returns:
        更新后的异常表
    """
    updated = list(anomalies_table)
    for anomaly in new_anomalies:
        entry = {
            "round_id": anomaly.get("round_id", round_id),
            "type": anomaly.get("type", "未分类"),
            "description": anomaly.get("description", ""),
            "evidence": anomaly.get("evidence", []),
            "status": anomaly.get("status", "unresolved"),
            "related_facts": anomaly.get("related_facts", []),
        }
        updated.append(entry)
    return updated


def resolve_anomaly(
    anomalies_table: List[Dict],
    index: int,
    status: str = "resolved",
) -> List[Dict]:
    """标记指定异常为已解决

    Args:
        anomalies_table: 异常表
        index: 异常索引
        status: 新状态
    Returns:
        更新后的异常表
    """
    updated = list(anomalies_table)
    if 0 <= index < len(updated):
        updated[index] = dict(updated[index])
        updated[index]["status"] = status
    return updated


def get_unresolved_anomalies(anomalies_table: List[Dict]) -> List[Dict]:
    """获取所有未解决的异常

    Args:
        anomalies_table: 异常表
    Returns:
        未解决的异常列表
    """
    return [a for a in anomalies_table if a.get("status") == "unresolved"]


def count_unresolved(anomalies_table: List[Dict]) -> int:
    """统计未解决的异常数量

    Args:
        anomalies_table: 异常表
    Returns:
        未解决异常数量
    """
    return len(get_unresolved_anomalies(anomalies_table))


def get_anomalies_by_type(anomalies_table: List[Dict], anomaly_type: str) -> List[Dict]:
    """获取指定类型的异常

    Args:
        anomalies_table: 异常表
        anomaly_type: 异常类型
    Returns:
        该类型的异常列表
    """
    return [a for a in anomalies_table if a.get("type") == anomaly_type]
