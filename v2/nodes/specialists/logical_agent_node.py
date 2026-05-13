"""逻辑与时间线分析 Agent 节点"""

from langchain_core.messages import HumanMessage, SystemMessage
from ...llm_client import get_llm
from ...prompts import LOGICAL_AGENT_SYSTEM
from ...utils.json_utils import safe_json_parse
from ...utils.text_utils import (
    format_dialogue_history,
    format_facts_table,
    clean_llm_output,
)
from ...state_schema import DialogueState


def logical_agent_node(state: DialogueState) -> dict:
    """逻辑与时间线分析 Agent

    判断职业叙述中的时间、因果、职业路径是否自洽。

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

    consistency_results = state.get("consistency_results", [])
    consistency_text = "\n".join(
        f"  - {r.get('fact_a', '')} vs {r.get('fact_b', '')} → {r.get('relation', '')}: {r.get('explanation', '')}"
        for r in consistency_results
    ) if consistency_results else "（暂无一致性判断结果）"

    prompt = LOGICAL_AGENT_SYSTEM.format(
        dialogue_history=dialogue_text,
        facts_table=facts_text,
        current_facts=current_facts_text,
        consistency_results=consistency_text,
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请进行逻辑与时间线分析"),
    ])

    raw_output = clean_llm_output(response.content)
    result = safe_json_parse(raw_output, default={
        "agent": "logical",
        "score": 0,
        "confidence": "low",
        "findings": [],
        "vote": "low_risk",
    })

    if isinstance(result, dict):
        result["agent"] = "logical"
    else:
        result = {
            "agent": "logical",
            "score": 0,
            "confidence": "low",
            "findings": [],
            "vote": "low_risk",
        }

    return {
        "specialist_results": [result],
    }
