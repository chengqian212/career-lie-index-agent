"""职业常识分析 Agent 节点"""

from langchain_core.messages import HumanMessage, SystemMessage
from ...llm_client import get_llm
from ...prompts import DOMAIN_AGENT_SYSTEM
from ...utils.json_utils import safe_json_parse
from ...utils.text_utils import (
    format_dialogue_history,
    format_facts_table,
    clean_llm_output,
)
from ...state_schema import DialogueState


def domain_agent_node(state: DialogueState) -> dict:
    """职业常识分析 Agent

    判断用户对职业内容的描述是否符合基本职业常识。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 specialist_results
    """
    llm = get_llm()

    dialogue_text = format_dialogue_history(state.get("dialogue_history", []))
    facts_text = format_facts_table(state.get("facts_table", []))
    current_facts = state.get("current_facts", [])

    current_facts_text = "\n".join(
        f"  - {f.get('content', '')} ({f.get('category', '')})"
        for f in current_facts
    ) if current_facts else "（当前轮次无新事实）"

    prompt = DOMAIN_AGENT_SYSTEM.format(
        dialogue_history=dialogue_text,
        facts_table=facts_text,
        current_facts=current_facts_text,
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请进行职业常识分析"),
    ])

    raw_output = clean_llm_output(response.content)
    result = safe_json_parse(raw_output, default={
        "agent": "domain",
        "score": 0,
        "confidence": "low",
        "findings": [],
        "vote": "low_risk",
    })

    if isinstance(result, dict):
        result["agent"] = "domain"
    else:
        result = {
            "agent": "domain",
            "score": 0,
            "confidence": "low",
            "findings": [],
            "vote": "low_risk",
        }

    return {
        "specialist_results": [result],
    }
