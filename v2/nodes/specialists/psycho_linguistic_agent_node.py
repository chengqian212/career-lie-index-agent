"""心理语言学线索分析 Agent 节点"""

from langchain_core.messages import HumanMessage, SystemMessage
from ...llm_client import get_llm
from ...prompts import PSYCHO_LINGUISTIC_AGENT_SYSTEM
from ...utils.json_utils import safe_json_parse
from ...utils.text_utils import (
    format_dialogue_history,
    format_anomalies_table,
    clean_llm_output,
)
from ...state_schema import DialogueState


def psycho_linguistic_agent_node(state: DialogueState) -> dict:
    """心理语言学线索分析 Agent

    识别文本中的软性风险信号。
    心理语言学线索只是辅助信号，不能单独造成高风险结论。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 specialist_results
    """
    llm = get_llm()

    dialogue_text = format_dialogue_history(state.get("dialogue_history", []))
    anomalies_text = format_anomalies_table(state.get("anomalies_table", []))

    prompt = PSYCHO_LINGUISTIC_AGENT_SYSTEM.format(
        dialogue_history=dialogue_text,
        current_user_text=state.get("current_user_text", ""),
        anomalies_table=anomalies_text,
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请进行心理语言学线索分析"),
    ])

    raw_output = clean_llm_output(response.content)
    result = safe_json_parse(raw_output, default={
        "agent": "psycho_linguistic",
        "score": 0,
        "confidence": "low",
        "findings": [],
        "vote": "low_risk",
    })

    if isinstance(result, dict):
        result["agent"] = "psycho_linguistic"
    else:
        result = {
            "agent": "psycho_linguistic",
            "score": 0,
            "confidence": "low",
            "findings": [],
            "vote": "low_risk",
        }

    return {
        "specialist_results": [result],
    }
