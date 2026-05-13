"""事实抽取节点：从用户回答中抽取职业身份相关事实"""

from langchain_core.messages import HumanMessage, SystemMessage
from ..llm_client import get_llm
from ..prompts import FACT_EXTRACTION_SYSTEM
from ..utils.json_utils import safe_json_parse
from ..utils.text_utils import (
    format_dialogue_history,
    format_facts_table,
    clean_llm_output,
)
from ..memory.fact_table import add_facts
from ..state_schema import DialogueState


def fact_extraction_node(state: DialogueState) -> dict:
    """事实抽取节点

    从当前用户回答中抽取与职业身份相关的事实，
    并更新事实表。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典
    """
    llm = get_llm()

    dialogue_text = format_dialogue_history(state.get("dialogue_history", []))
    facts_text = format_facts_table(state.get("facts_table", []))

    prompt = FACT_EXTRACTION_SYSTEM.format(
        dialogue_history=dialogue_text,
        current_user_text=state.get("current_user_text", ""),
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请抽取事实"),
    ])

    raw_output = clean_llm_output(response.content)
    new_facts = safe_json_parse(raw_output, default=[])

    # 确保是列表
    if isinstance(new_facts, dict):
        new_facts = [new_facts]
    if not isinstance(new_facts, list):
        new_facts = []

    # 为每条事实补充 round_id
    round_id = state.get("round_id", 1)
    for fact in new_facts:
        if isinstance(fact, dict):
            fact.setdefault("round_id", round_id)

    # 更新事实表
    updated_facts_table = add_facts(
        state.get("facts_table", []),
        new_facts,
        round_id,
    )

    return {
        "current_facts": new_facts,
        "facts_table": updated_facts_table,
    }
