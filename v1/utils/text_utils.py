"""
文本处理工具：提供文本截断、格式化等辅助函数。
调用关系：被 agents/information_comparison_agent.py 等引用。
输入：字符串 / 列表
输出：truncate_text(), format_facts_table_brief()
"""


def truncate_text(text: str, max_length: int = 500) -> str:
    """截断过长文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def format_facts_table_brief(facts_table: list) -> str:
    """将事实表格式化为简洁文本，用于放入 Prompt"""
    if not facts_table:
        return "（无）"
    lines = []
    for f in facts_table:
        fact_id = f.get("fact_id", "?")
        slot = f.get("slot", "?")
        value = f.get("value", "")
        evidence = f.get("evidence", "")
        round_id = f.get("round_id", "?")
        lines.append(f"  [{fact_id}] R{round_id} | {slot}: {value}（原文：{evidence}）")
    return "\n".join(lines)
