"""异常检测节点：识别用户对话中可能存在问题的表达"""

from langchain_core.messages import HumanMessage, SystemMessage
from ..llm_client import get_llm
from ..prompts import ANOMALY_DETECTION_SYSTEM
from ..utils.json_utils import safe_json_parse
from ..utils.text_utils import (
    format_dialogue_history,
    format_facts_table,
    clean_llm_output,
)
from ..memory.anomaly_table import add_anomalies
from ..state_schema import DialogueState


def anomaly_detection_node(state: DialogueState) -> dict:
    """异常检测节点

    从用户回答中识别可能存在问题的表达，
    并更新异常表。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典
    """
    llm = get_llm()

    dialogue_text = format_dialogue_history(state.get("dialogue_history", []))
    facts_text = format_facts_table(state.get("facts_table", []))

    prompt = ANOMALY_DETECTION_SYSTEM.format(
        dialogue_history=dialogue_text,
        current_user_text=state.get("current_user_text", ""),
        facts_table=facts_text,
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请识别异常"),
    ])

    raw_output = clean_llm_output(response.content)
    new_anomalies = safe_json_parse(raw_output, default=[])

    # 确保是列表
    if isinstance(new_anomalies, dict):
        new_anomalies = [new_anomalies]
    if not isinstance(new_anomalies, list):
        new_anomalies = []

    # 为每条异常补充 round_id
    round_id = state.get("round_id", 1)
    for anomaly in new_anomalies:
        if isinstance(anomaly, dict):
            anomaly.setdefault("round_id", round_id)

    # 更新异常表
    updated_anomalies_table = add_anomalies(
        state.get("anomalies_table", []),
        new_anomalies,
        round_id,
    )

    return {
        "current_anomalies": new_anomalies,
        "anomalies_table": updated_anomalies_table,
    }
