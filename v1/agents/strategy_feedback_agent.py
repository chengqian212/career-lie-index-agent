"""
Agent 3：策略反馈 Agent / Strategy Feedback Agent
根据 Agent 2 的事实比对结果和异常结果，决定下一轮追问重点与追问策略。
调用关系：调用 llm_client.py、prompts.py、utils/json_utils.py、memory/anomaly_table.py；被 graph.py 注册为节点。
输入：state["round_id"], state["max_rounds"], state["lie_index"], state["risk_level"],
      state["consistency_results"], state["current_anomalies"], state["anomalies_table"], state["dialogue_history"]
输出：state["priority_issue"], state["followup_strategy"], state["strategy_reason"], state["next_action"]
"""
import json
from v1.state_schema import DialogueState
from v1.llm_client import call_llm_json
from v1.prompts import STRATEGY_FEEDBACK_AGENT_PROMPT
from v1.utils.json_utils import parse_json_response
from v1.memory.anomaly_table import find_unresolved


def strategy_feedback_agent_node(state: DialogueState) -> dict:
    """
    Agent 3：根据异常表和比对结果选择下一轮追问重点与追问策略。
    """
    # 获取未澄清的异常
    anomalies_table = state.get("anomalies_table", [])
    unresolved = find_unresolved(anomalies_table)

    prompt = STRATEGY_FEEDBACK_AGENT_PROMPT.format(
        round_id=state["round_id"],
        max_rounds=state["max_rounds"],
        lie_index=state.get("lie_index", 0),
        risk_level=state.get("risk_level", "低"),
        consistency_results=json.dumps(state.get("consistency_results", []), ensure_ascii=False, indent=2),
        current_anomalies=json.dumps(state.get("current_anomalies", []), ensure_ascii=False, indent=2),
        anomalies_table=json.dumps(unresolved, ensure_ascii=False, indent=2) if unresolved else "（无未澄清异常）",
    )

    response_text = call_llm_json(prompt)
    parsed = parse_json_response(response_text)

    priority_issue = parsed.get("priority_issue", "")
    followup_strategy = parsed.get("followup_strategy", "normal_expansion")
    strategy_reason = parsed.get("strategy_reason", "")
    next_action = parsed.get("next_action", "generate_followup")

    # 强制路由规则：轮次达到上限必须生成最终报告
    if state["round_id"] >= state["max_rounds"]:
        next_action = "final_report"

    return {
        "priority_issue": priority_issue,
        "followup_strategy": followup_strategy,
        "strategy_reason": strategy_reason,
        "next_action": next_action,
    }
