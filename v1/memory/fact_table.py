"""
事实表操作：提供按 slot、按 fact_id 查询事实的辅助函数，以及生成事实摘要。
调用关系：被 agents/information_comparison_agent.py、nodes/state_update_node.py 引用。
输入：facts_table 列表
输出：find_facts_by_slot(), find_fact_by_id(), generate_facts_summary()
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


def generate_facts_summary(facts_table: list) -> str:
    """生成事实表的文本摘要，用于放入 Prompt"""
    if not facts_table:
        return "（历史事实为空）"
    lines = []
    for f in facts_table:
        fact_id = f.get("fact_id", "?")
        slot = f.get("slot", "?")
        value = f.get("value", "")
        evidence = f.get("evidence", "")
        time_stage = f.get("time_stage", "")
        round_id = f.get("round_id", "?")
        lines.append(
            f"  [{fact_id}] R{round_id} | slot={slot} | value={value} | "
            f"time_stage={time_stage} | evidence=\"{evidence}\""
        )
    return "\n".join(lines)
