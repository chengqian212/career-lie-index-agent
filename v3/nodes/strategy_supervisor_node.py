"""策略决策节点：决定下一步是追问还是生成最终报告

v3.3 改进：
- 恢复动态判断，由 Python 硬规则根据最大轮次、异常状态、信息充分度、追问次数决定 next_action
- 仅当需要继续追问时，调用 LLM 提供 priority_issue 和 followup_strategy
- 停止追问的 5 类条件：
  1. 达到最大轮次
  2. 没有活跃疑点，且核心事实已经足够
  3. 疑点已经被澄清（所有异常 resolved）
  4. 同一个疑点追问多次仍未澄清（followup_count >= 2）
  5. 疑点已经被强化且风险分数很高
"""

import json
import logging

from langchain_core.messages import HumanMessage

from ..llm_client import get_llm
from ..prompts import STRATEGY_SUPERVISOR_PROMPT
from ..utils.json_utils import extract_json_from_text
from ..utils.text_utils import format_anomalies_table, clean_llm_output
from ..state_schema import DialogueState
from .. import config

logger = logging.getLogger(__name__)


# ============================================================
# 辅助函数（v3.3 新增）
# ============================================================

def _is_active_anomaly(anomaly: dict) -> bool:
    """判断异常是否仍处于活跃状态（需要被考虑）

    活跃条件：
    - stop_followup 不为 True
    - status 为 unresolved 或 reinforced
    - 或者 followup_needed 为 True
    """
    if not isinstance(anomaly, dict):
        return False
    if anomaly.get("stop_followup") is True:
        return False
    status = anomaly.get("status", "")
    if status in ("unresolved", "reinforced"):
        return True
    if anomaly.get("followup_needed") is True:
        return True
    return False


def _has_enough_core_facts(facts_table: list[dict]) -> bool:
    slots = set()
    for fact in facts_table:
        if not isinstance(fact, dict):
            continue
        slot = fact.get("slot") or fact.get("category", "")
        if slot:
            slots.add(slot)

    has_identity = bool(slots & {"occupation", "role"})
    has_content = bool(slots & {"work_content", "experience"})
    has_time_or_project = bool(slots & {"time_stage", "company"})

    return has_identity and has_content and has_time_or_project


def _has_exhausted_anomaly(anomalies_table: list[dict], max_followup_per_anomaly: int = 2) -> bool:
    """检查是否有异常追问次数达到上限"""
    for anomaly in anomalies_table:
        if not isinstance(anomaly, dict):
            continue
        if anomaly.get("status") in ("unresolved", "reinforced"):
            followup_count = int(anomaly.get("followup_count", 0) or 0)
            if followup_count >= max_followup_per_anomaly:
                return True
    return False


def _has_confirmed_high_risk_anomaly(anomalies_table: list[dict]) -> bool:
    """检查是否存在已被强化且分数很高的异常（坐实风险）"""
    for anomaly in anomalies_table:
        if not isinstance(anomaly, dict):
            continue
        status = anomaly.get("status", "")
        score = float(anomaly.get("score", 0) or 0)
        if status == "reinforced" and score >= 75:
            return True
    return False


# ============================================================
# 主节点函数
# ============================================================

def strategy_supervisor_node(state: DialogueState) -> dict:
    """策略决策节点

    v3.3 职责：
    1. 根据异常状态、信息充分度、追问次数硬决策是否结束
    2. 如果继续追问，调用 LLM 获取 priority_issue 和 followup_strategy
    3. 如果结束，直接返回 next_action = "final_report"

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 next_action, priority_issue, followup_strategy, stop_reason
    """
    round_id = state.get("round_id", 1)
    max_rounds = state.get("max_rounds", config.MAX_ROUNDS)
    min_rounds_before_early_stop = 6
    can_early_stop = round_id >= min_rounds_before_early_stop
    facts_table = state.get("facts_table", [])
    anomalies_table = state.get("anomalies_table", [])
    lie_index = state.get("lie_index", 0)
    risk_explanation = state.get("risk_explanation", [])

    # ---- 收集活跃异常 ----
    active_anomalies = [a for a in anomalies_table if _is_active_anomaly(a)]

    # ---- 判断各类结束条件 ----
    all_anomalies_resolved = (
        bool(anomalies_table)
        and all(
            isinstance(a, dict) and a.get("status") == "resolved"
            for a in anomalies_table
        )
    )
    has_enough_facts = _has_enough_core_facts(facts_table)
    has_exhausted = _has_exhausted_anomaly(anomalies_table, max_followup_per_anomaly=2)
    has_confirmed_high_risk = _has_confirmed_high_risk_anomaly(anomalies_table)

    # ---- 决策 ----
    stop_reason = "need_more_information_or_clarification"  # 默认继续
    next_action = "generate_followup"

    if round_id >= max_rounds:
        next_action = "final_report"
        stop_reason = "max_rounds"
    elif can_early_stop and all_anomalies_resolved and has_enough_facts:
        next_action = "final_report"
        stop_reason = "anomaly_resolved"
    elif can_early_stop and has_exhausted:
        next_action = "final_report"
        stop_reason = "followup_exhausted"
    elif can_early_stop and has_confirmed_high_risk:
        next_action = "final_report"
        stop_reason = "anomaly_confirmed"
    elif can_early_stop and not active_anomalies and has_enough_facts:
        next_action = "final_report"
        stop_reason = "enough_information_no_active_anomaly"
    else:
        # 还需要继续追问
        next_action = "generate_followup"
        stop_reason = "need_more_information_or_clarification"

    # 如果需要结束，直接返回
    if next_action == "final_report":
        return {
            "next_action": "final_report",
            "priority_issue": "",
            "followup_strategy": "",
            "stop_reason": stop_reason,
        }

    # ---- 继续追问时，调用 LLM 获取策略建议 ----
    anomalies_text = format_anomalies_table(anomalies_table)

    # 格式化其他输入
    dimension_scores = state.get("dimension_scores", {})
    specialist_results = state.get("specialist_results", [])
    debate_result = state.get("debate_result")

    specialist_text = "\n".join(
        f"  [{r.get('agent', '?')}] 分数: {r.get('score', 0)}"
        for r in specialist_results
        if isinstance(r, dict)
    )

    debate_text = ""
    if isinstance(debate_result, dict):
        debate_text = json.dumps(debate_result, ensure_ascii=False, indent=2)

    routing_decision = state.get("routing_decision", {})
    called_specialists = state.get("called_specialists", [])

    # 调用 LLM（使用 ChatPromptTemplate 的 invoke 方法）
    llm = get_llm()
    response = llm.invoke(
        STRATEGY_SUPERVISOR_PROMPT.invoke({
            "lie_index": lie_index,
            "dimension_scores": dimension_scores,
            "specialist_results": specialist_text,
            "debate_result": debate_text or "无",
            "anomalies_table": anomalies_text,
            "round_id": round_id,
            "max_rounds": max_rounds,
            "routing_decision": json.dumps(routing_decision, ensure_ascii=False, indent=2) if routing_decision else "无",
            "called_specialists": ", ".join(called_specialists) if called_specialists else "无",
        })
    )

    raw_output = clean_llm_output(response.content)
    result = extract_json_from_text(raw_output)

    priority_issue = ""
    followup_strategy = "daily_routine"
    target_anomaly_id = ""

    if isinstance(result, dict):
        priority_issue = result.get("priority_issue", "")
        followup_strategy = result.get("followup_strategy", "daily_routine")
        target_anomaly_id = result.get("target_anomaly_id", "")

    # 校验 followup_strategy 合法性
    ALLOWED_STRATEGIES = [
        "daily_routine",
        "entry_experience",
        "work_style",
        "recent_memory",
        "light_clarification",
        "topic_shift_buffer",
        "experience_probe",
        "knowledge_probe",
        "tool_workflow_probe",
        "scenario_judgment_probe",
    ]
    if followup_strategy not in ALLOWED_STRATEGIES:
        followup_strategy = "daily_routine"

    return {
        "next_action": "generate_followup",
        "priority_issue": priority_issue,
        "followup_strategy": followup_strategy,
        "stop_reason": stop_reason,
        "target_anomaly_id": target_anomaly_id,  # 可选，用于后续追问计数
    }
