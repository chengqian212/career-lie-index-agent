"""
异常表达识别节点：调用 LLM 识别用户回答中的 5 类异常表达（细节缺失、回避、答非所问、模糊、过度解释）。
调用关系：调用 llm_client.py、prompts.py、utils/json_utils.py；被 graph.py 注册为节点。
输入：state["current_user_text"], state["last_followup_question"]
输出：state["current_anomalies"]
"""
from state_schema import DialogueState
from llm_client import call_llm_json
from prompts import ANOMALY_DETECTION_PROMPT
from utils.json_utils import parse_json_response


def anomaly_detection_node(state: DialogueState) -> dict:
    """
    识别当前回答中的异常表达。
    """
    prompt = ANOMALY_DETECTION_PROMPT.format(
        followup_question=state.get("last_followup_question", ""),
        user_text=state["current_user_text"],
    )

    response_text = call_llm_json(prompt)
    parsed = parse_json_response(response_text)

    anomalies = parsed.get("anomalies", [])

    return {"current_anomalies": anomalies}
