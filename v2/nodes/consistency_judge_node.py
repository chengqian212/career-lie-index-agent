"""一致性判断节点：比对当前新事实与已有事实表的一致性"""

from langchain_core.messages import HumanMessage, SystemMessage
from ..llm_client import get_llm
from ..prompts import CONSISTENCY_JUDGE_SYSTEM
from ..utils.json_utils import safe_json_parse
from ..utils.text_utils import format_facts_table, clean_llm_output
from ..state_schema import DialogueState


def consistency_judge_node(state: DialogueState) -> dict:
    """一致性判断节点

    比对当前轮次的新事实与已有事实表，检查是否存在不一致。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典
    """
    llm = get_llm()

    facts_text = format_facts_table(state.get("facts_table", []))
    current_facts = state.get("current_facts", [])

    # 格式化当前新事实
    current_facts_text = "\n".join(
        f"  - {f.get('content', '')} ({f.get('category', '')})"
        for f in current_facts
    ) if current_facts else "（当前轮次无新事实）"

    prompt = CONSISTENCY_JUDGE_SYSTEM.format(
        facts_table=facts_text,
        current_facts=current_facts_text,
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请判断一致性"),
    ])

    raw_output = clean_llm_output(response.content)
    consistency_results = safe_json_parse(raw_output, default=[])

    # 确保是列表
    if isinstance(consistency_results, dict):
        consistency_results = [consistency_results]
    if not isinstance(consistency_results, list):
        consistency_results = []

    # 追加到历史
    updated_history = list(state.get("consistency_results", []))
    updated_history.extend(consistency_results)

    return {
        "consistency_results": updated_history,
    }
