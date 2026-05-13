"""语义一致性分析 Agent 节点"""

from langchain_core.messages import HumanMessage, SystemMessage
from ...llm_client import get_llm
from ...prompts import SEMANTIC_AGENT_SYSTEM
from ...utils.json_utils import safe_json_parse
from ...utils.text_utils import (
    format_dialogue_history,
    format_facts_table,
    clean_llm_output,
)
from ...state_schema import DialogueState


def semantic_agent_node(state: DialogueState) -> dict:
    """语义一致性分析 Agent

    判断用户职业身份、岗位、工作内容等表述在语义上是否一致。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 specialist_results
    """
    llm = get_llm()

    dialogue_text = format_dialogue_history(state.get("dialogue_history", []))
    facts_text = format_facts_table(state.get("facts_table", []))
    current_facts = state.get("current_facts", [])

    # 格式化当前新事实
    current_facts_text = "\n".join(
        f"  - {f.get('content', '')} ({f.get('category', '')})"
        for f in current_facts
    ) if current_facts else "（当前轮次无新事实）"

    # 格式化一致性判断结果
    consistency_results = state.get("consistency_results", [])
    consistency_text = "\n".join(
        f"  - {r.get('fact_a', '')} vs {r.get('fact_b', '')} → {r.get('relation', '')}: {r.get('explanation', '')}"
        for r in consistency_results
    ) if consistency_results else "（暂无一致性判断结果）"

    prompt = SEMANTIC_AGENT_SYSTEM.format(
        dialogue_history=dialogue_text,
        facts_table=facts_text,
        current_facts=current_facts_text,
        consistency_results=consistency_text,
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请进行语义一致性分析"),
    ])

    raw_output = clean_llm_output(response.content)
    result = safe_json_parse(raw_output, default={
        "agent": "semantic",
        "score": 0,
        "confidence": "low",
        "findings": [],
        "vote": "low_risk",
    })

    # 确保 agent 字段正确
    if isinstance(result, dict):
        result["agent"] = "semantic"
    else:
        result = {
            "agent": "semantic",
            "score": 0,
            "confidence": "low",
            "findings": [],
            "vote": "low_risk",
        }

    return {
        "specialist_results": [result],
    }
