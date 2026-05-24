"""
Agent 1：追问对话 Agent / Follow-up Dialogue Agent
根据 Agent 3 的策略生成一个自然、温和、不像审问的追问问题。
调用关系：调用 llm_client.py、prompts.py、utils/json_utils.py；被 graph.py 注册为节点。
输入：state["dialogue_history"], state["facts_table"], state["anomalies_table"],
      state["priority_issue"], state["followup_strategy"], state["strategy_reason"],
      state["last_followup_question"]
输出：state["last_followup_question"], state["followup_history"]
"""
import json
from v1.state_schema import DialogueState
from v1.llm_client import call_llm_json
from v1.prompts import FOLLOWUP_DIALOGUE_AGENT_PROMPT
from v1.utils.json_utils import parse_json_response
from v1.memory.anomaly_table import find_unresolved


def followup_dialogue_agent_node(state: DialogueState) -> dict:
    """
    Agent 1：根据策略生成一个自然追问问题。
    """
    # 获取未澄清的异常
    anomalies_table = state.get("anomalies_table", [])
    unresolved = find_unresolved(anomalies_table)

    prompt = FOLLOWUP_DIALOGUE_AGENT_PROMPT.format(
        dialogue_history=json.dumps(state.get("dialogue_history", []), ensure_ascii=False, indent=2),
        priority_issue=state.get("priority_issue", ""),
        followup_strategy=state.get("followup_strategy", "normal_expansion"),
        strategy_reason=state.get("strategy_reason", ""),
        facts_table=json.dumps(state.get("facts_table", []), ensure_ascii=False, indent=2),
        anomalies_table=json.dumps(unresolved, ensure_ascii=False, indent=2) if unresolved else "（无未澄清异常）",
        last_followup_question=state.get("last_followup_question", ""),
    )

    response_text = call_llm_json(prompt)
    parsed = parse_json_response(response_text)

    question = parsed.get("question", "你能再多说说你工作上的事吗？")

    return {
        "last_followup_question": question,
        "followup_history": [question],
    }
