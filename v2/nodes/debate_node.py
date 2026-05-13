"""Debate 节点：结构化争议汇总"""

import json
from langchain_core.messages import HumanMessage, SystemMessage
from ..llm_client import get_llm
from ..prompts import DEBATE_SYSTEM
from ..utils.json_utils import safe_json_parse
from ..utils.text_utils import (
    format_facts_table,
    format_anomalies_table,
    clean_llm_output,
)
from ..state_schema import DialogueState


def debate_node(state: DialogueState) -> dict:
    """Debate 节点

    当存在明显分歧时，进行结构化争议汇总。
    只做结构化争议总结，不做自由长篇辩论。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 debate_result
    """
    llm = get_llm()

    specialist_results = state.get("specialist_results", [])
    consistency_results = state.get("consistency_results", [])
    anomalies_text = format_anomalies_table(state.get("anomalies_table", []))
    facts_text = format_facts_table(state.get("facts_table", []))

    # 格式化 specialist_results
    specialist_text = "\n".join(
        f"  [{r.get('agent', '?')}] 分数: {r.get('score', 0)}, "
        f"置信度: {r.get('confidence', '?')}, 投票: {r.get('vote', '?')}\n"
        f"    发现: {json.dumps(r.get('findings', []), ensure_ascii=False)}"
        for r in specialist_results
        if isinstance(r, dict)
    )

    # 格式化 consistency_results
    consistency_text = "\n".join(
        f"  - {r.get('fact_a', '')} vs {r.get('fact_b', '')} → {r.get('relation', '')}: {r.get('explanation', '')}"
        for r in consistency_results
        if isinstance(r, dict)
    ) if consistency_results else "（暂无一致性判断结果）"

    prompt = DEBATE_SYSTEM.format(
        specialist_results=specialist_text,
        consistency_results=consistency_text,
        anomalies_table=anomalies_text,
        facts_table=facts_text,
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请进行争议讨论"),
    ])

    raw_output = clean_llm_output(response.content)
    result = safe_json_parse(raw_output, default={
        "debate_trigger": "unknown",
        "main_disagreement": "",
        "skeptic_view": "",
        "explainer_view": "",
        "consensus": "",
        "recommended_followup_focus": "",
        "debate_adjustment": {
            "semantic": 0,
            "logical": 0,
            "domain": 0,
            "psycho_linguistic": 0,
        },
    })

    if not isinstance(result, dict):
        result = {
            "debate_trigger": "unknown",
            "main_disagreement": "",
            "skeptic_view": "",
            "explainer_view": "",
            "consensus": "",
            "recommended_followup_focus": "",
            "debate_adjustment": {
                "semantic": 0,
                "logical": 0,
                "domain": 0,
                "psycho_linguistic": 0,
            },
        }

    return {
        "debate_result": result,
    }
