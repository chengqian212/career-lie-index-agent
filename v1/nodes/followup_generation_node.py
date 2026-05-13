"""
追问生成节点：调用 LLM 根据对话历史和异常信息生成一个自然追问问题。
调用关系：调用 llm_client.py、prompts.py；被 graph.py 注册为节点。
输入：state["dialogue_history"], state["facts_table"], state["anomalies_table"], state["current_anomalies"], state["consistency_results"]
输出：state["last_followup_question"], state["followup_history"]
"""
import json
from state_schema import DialogueState
from llm_client import call_llm
from prompts import FOLLOWUP_GENERATION_PROMPT


def followup_generation_node(state: DialogueState) -> dict:
    """
    生成下一轮自然追问。
    """
    prompt = FOLLOWUP_GENERATION_PROMPT.format(
        dialogue_history=json.dumps(state.get("dialogue_history", []), ensure_ascii=False, indent=2),
        facts_table=json.dumps(state.get("facts_table", []), ensure_ascii=False, indent=2),
        anomalies_table=json.dumps(state.get("anomalies_table", []), ensure_ascii=False, indent=2),
        current_anomalies=json.dumps(state.get("current_anomalies", []), ensure_ascii=False, indent=2),
        consistency_results=json.dumps(state.get("consistency_results", []), ensure_ascii=False, indent=2),
    )

    question = call_llm(prompt).strip()

    return {
        "last_followup_question": question,
        "followup_history": [question],
    }
