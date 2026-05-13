"""
事实表操作：提供按 slot、按 fact_id 查询事实的辅助函数。
调用关系：当前未被其他文件直接调用，预留供后续使用。
输入：facts_table 列表
输出：find_facts_by_slot(), find_fact_by_id()
"""


def find_facts_by_slot(facts_table: list, slot: str) -> list:
    """按 slot 查找事实"""
    return [f for f in facts_table if f.get("slot") == slot]


def find_fact_by_id(facts_table: list, fact_id: str) -> dict:
    """按 fact_id 查找事实"""
    for f in facts_table:
        if f.get("fact_id") == fact_id:
            return f
    return {}
