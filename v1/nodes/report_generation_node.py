"""
报告生成节点：调用 LLM 根据全部状态生成最终谎言指数测评报告。
调用关系：调用 llm_client.py、prompts.py、utils/json_utils.py；被 graph.py 注册为节点。
输入：state["dialogue_history"], state["facts_table"], state["anomalies_table"], state["indicator_history"], state["lie_index"], state["risk_level"]
输出：state["final_report"]
"""
import json
from state_schema import DialogueState
from llm_client import call_llm_json
from prompts import REPORT_GENERATION_PROMPT
from utils.json_utils import parse_json_response


def report_generation_node(state: DialogueState) -> dict:
    """
    生成最终谎言指数测评报告。
    """
    prompt = REPORT_GENERATION_PROMPT.format(
        dialogue_history=json.dumps(state.get("dialogue_history", []), ensure_ascii=False, indent=2),
        facts_table=json.dumps(state.get("facts_table", []), ensure_ascii=False, indent=2),
        anomalies_table=json.dumps(state.get("anomalies_table", []), ensure_ascii=False, indent=2),
        indicator_history=json.dumps(state.get("indicator_history", []), ensure_ascii=False, indent=2),
        lie_index=state.get("lie_index", 0),
        risk_level=state.get("risk_level", "低"),
    )

    response_text = call_llm_json(prompt)
    report = parse_json_response(response_text)

    return {"final_report": report}
