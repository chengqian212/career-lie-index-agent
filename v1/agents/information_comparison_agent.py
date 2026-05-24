"""
Agent 2：信息比对 Agent / Evidence Comparison Agent
从当前用户回答中抽取职业身份相关事实，识别异常表达，将当前事实与历史事实比对。
调用关系：调用 llm_client.py、prompts.py、utils/json_utils.py、memory/fact_table.py；被 graph.py 注册为节点。
输入：state["current_user_text"], state["round_id"], state["facts_table"], state["last_followup_question"], state["dialogue_history"]
输出：state["current_facts"], state["current_anomalies"], state["consistency_results"]
"""
import json
from v1.state_schema import DialogueState
from v1.llm_client import call_llm_json
from v1.prompts import INFORMATION_COMPARISON_AGENT_PROMPT
from v1.utils.json_utils import parse_json_response
from v1.utils.text_utils import format_facts_table_brief
from v1.memory.fact_table import generate_facts_summary


def information_comparison_agent_node(state: DialogueState) -> dict:
    """
    Agent 2：抽取当前事实、识别异常表达、比对历史事实，输出结构化分析结果。
    """
    # 格式化历史事实表，放入 Prompt
    facts_table = state.get("facts_table", [])
    facts_table_str = generate_facts_summary(facts_table) if facts_table else "（历史事实为空，这是第一轮）"

    prompt = INFORMATION_COMPARISON_AGENT_PROMPT.format(
        round_id=state["round_id"],
        followup_question=state.get("last_followup_question", ""),
        user_text=state["current_user_text"],
        facts_table=facts_table_str,
    )

    response_text = call_llm_json(prompt)
    parsed = parse_json_response(response_text)

    # 提取三个部分
    current_facts = parsed.get("current_facts", [])
    current_anomalies = parsed.get("current_anomalies", [])
    consistency_results = parsed.get("consistency_results", [])

    # 为每条事实添加 round_id
    for fact in current_facts:
        fact["round_id"] = state["round_id"]
        if "time_stage" not in fact:
            fact["time_stage"] = "当前"
        if "confidence" not in fact:
            fact["confidence"] = "medium"

    # 为每条异常添加 round_id
    for anomaly in current_anomalies:
        anomaly["round_id"] = state["round_id"]

    # 如果历史事实为空，确保 consistency_results 中所有当前事实标记为"新增事实"
    if not facts_table:
        consistency_results = []
        for i, fact in enumerate(current_facts):
            consistency_results.append({
                "history_fact_id": None,
                "current_fact_temp_id": f"current_{i}",
                "relation": "新增事实",
                "severity": "low",
                "explanation": "历史事实为空，标记为新增事实",
                "need_followup": False,
            })

    return {
        "current_facts": current_facts,
        "current_anomalies": current_anomalies,
        "consistency_results": consistency_results,
    }
