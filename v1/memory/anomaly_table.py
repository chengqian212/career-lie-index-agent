"""
异常表操作：提供查找未澄清异常、按 id 查找、标记已澄清等辅助函数。
调用关系：当前未被其他文件直接调用，预留供后续使用。
输入：anomalies_table 列表
输出：find_unresolved(), find_by_id(), mark_resolved()
"""


def find_unresolved(anomalies_table: list) -> list:
    """查找所有未澄清的异常"""
    return [a for a in anomalies_table if a.get("status") == "unresolved"]


def find_by_id(anomalies_table: list, anomaly_id: str) -> dict:
    """按 anomaly_id 查找异常"""
    for a in anomalies_table:
        if a.get("anomaly_id") == anomaly_id:
            return a
    return {}


def mark_resolved(anomalies_table: list, anomaly_id: str) -> list:
    """将指定异常标记为已澄清"""
    for a in anomalies_table:
        if a.get("anomaly_id") == anomaly_id:
            a["status"] = "resolved"
    return anomalies_table
