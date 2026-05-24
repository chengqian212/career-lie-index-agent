"""追问生成节点：根据分析结果生成自然的追问

v3 改进：
- 升级职责：选择追问焦点 + 生成追问问题
- 优先使用 routing_decision 中的 priority_issue 和 followup_strategy
- 当 routing_decision 没有有效信息时，按优先级自动选择追问方向
- 返回 next_action="generate_followup" 供 CLI 判断流程状态
"""

import json

from ..llm_client import get_llm
from ..prompts import FOLLOWUP_GENERATION_PROMPT
from ..state_schema import DialogueState
from ..utils.text_utils import (
    clean_llm_output,
    format_anomalies_table,
    format_dialogue_history,
)

# ============================================================
# 允许的追问策略集合
# ============================================================
ALLOWED_FOLLOWUP_STRATEGIES = {
    "daily_routine",
    "entry_experience",
    "work_style",
    "recent_memory",
    "light_clarification",
    "topic_shift_buffer",
}


def _normalize_strategy(strategy: str, has_risk: bool) -> str:
    """归一化追问策略

    如果策略不在允许集合中，根据是否有风险进行兜底：
    - 有风险 → light_clarification（温和澄清）
    - 无风险 → daily_routine（日常了解）
    """
    if strategy in ALLOWED_FOLLOWUP_STRATEGIES:
        return strategy
    return "light_clarification" if has_risk else "daily_routine"


# 低风险排除词：risk_explanation 包含这些文本时视为无风险
_LOW_RISK_PHRASES = [
    "暂无明显风险",
    "未发现明显风险",
    "本轮未发现明显风险",
    "当前轮次未发现明显风险信号",
    "暂无明显不一致",
]


def _is_active_anomaly(anomaly: dict) -> bool:
    """判断异常是否仍处于活跃状态（仍需关注）

    活跃条件（满足任一即可）：
    - status 为 unresolved 或 reinforced
    - followup_needed 为 True
    """
    if not isinstance(anomaly, dict):
        return False
    status = anomaly.get("status", "")
    if status in ("unresolved", "reinforced"):
        return True
    if anomaly.get("followup_needed", False):
        return True
    return False


def _has_risk_signal(state: DialogueState) -> bool:
    """判断当前是否存在风险信号"""
    anomalies_table = state.get("anomalies_table", [])
    risk_explanation = state.get("risk_explanation", [])
    current_anomalies = state.get("current_anomalies", [])
    lie_index = state.get("lie_index", 0)

    # 1. anomalies_table 中有活跃异常（unresolved / reinforced / followup_needed=True）
    if any(_is_active_anomaly(a) for a in anomalies_table):
        return True

    # 2. risk_explanation 不为空，且不包含低风险排除词
    if risk_explanation:
        risk_text = str(risk_explanation)
        if risk_text.strip() and not any(phrase in risk_text for phrase in _LOW_RISK_PHRASES):
            return True

    # 3. current_anomalies 不为空
    if current_anomalies:
        return True

    # 4. lie_index 明显大于低风险阈值
    if lie_index and lie_index > 30:
        return True

    return False


def _infer_priority_issue(state: DialogueState) -> tuple[str, str]:
    """推断追问焦点和策略

    当 routing_decision 没有给出有效信息时，按以下优先级推断：
    1. anomalies_table 里有未解决异常 → 围绕未解决异常温和追问
    2. risk_explanation 不为空 → 围绕风险解释温和了解
    3. current_facts 有内容 → 围绕当前事实轻量了解日常
    4. 默认 → 继续自然聊天
    """
    anomalies_table = state.get("anomalies_table", [])
    risk_explanation = state.get("risk_explanation", [])
    current_facts = state.get("current_facts", [])

    active = [a for a in anomalies_table if _is_active_anomaly(a)]
    if active:
        latest = active[-1]
        issue = latest.get("description") or "待澄清的异常点"
        return f"温和澄清：{issue}", "light_clarification"

    if risk_explanation:
        issue = str(risk_explanation[0])
        return f"温和了解：{issue}", "light_clarification"

    if current_facts:
        latest_fact = current_facts[-1]
        content = latest_fact.get("content", "")
        if content:
            return f"围绕事实轻量了解：{content}", "daily_routine"

    return "继续自然聊天", "daily_routine"


def _is_invalid_priority_issue(priority_issue: str) -> bool:
    """判断 priority_issue 是否无效"""
    if not priority_issue:
        return True

    invalid_values = {
        "",
        "无明显待澄清点",
        "无",
        "暂无",
        "无明显问题",
        "无明显风险",
        "继续",
    }

    return priority_issue.strip() in invalid_values


def followup_generation_node(state: DialogueState) -> dict:
    """追问生成节点

    职责：
    1. 根据 routing_decision / 风险信息 / 当前事实确定追问焦点
    2. 调用 LLM 生成一个自然追问
    3. 更新 followup_history
    4. 返回 next_action="generate_followup"
    """
    llm = get_llm()

    routing_decision = state.get("routing_decision", {})
    routing_reason = ""

    priority_issue = ""
    followup_strategy = ""

    if isinstance(routing_decision, dict):
        routing_reason = routing_decision.get("routing_reason", "")
        priority_issue = routing_decision.get("priority_issue", "")
        followup_strategy = routing_decision.get("followup_strategy", "")

    if _is_invalid_priority_issue(priority_issue):
        priority_issue, followup_strategy = _infer_priority_issue(state)

    if not followup_strategy:
        followup_strategy = "daily_routine"

    # 在调用 LLM 前统一校验策略，非法则兜底
    has_risk = _has_risk_signal(state)
    followup_strategy = _normalize_strategy(followup_strategy, has_risk)

    dimension_scores = state.get("dimension_scores", {})
    debate_result = state.get("debate_result")
    anomalies_text = format_anomalies_table(state.get("anomalies_table", []))
    dialogue_text = format_dialogue_history(state.get("dialogue_history", []))

    debate_text = ""
    if isinstance(debate_result, dict):
        debate_text = json.dumps(debate_result, ensure_ascii=False, indent=2)

    response = llm.invoke(
        FOLLOWUP_GENERATION_PROMPT.invoke({
            "priority_issue": priority_issue,
            "followup_strategy": followup_strategy,
            "routing_reason": routing_reason,
            "dimension_scores": dimension_scores,
            "debate_result": debate_text or "无",
            "anomalies_table": anomalies_text,
            "dialogue_history": dialogue_text,
        })
    )

    followup_question = clean_llm_output(response.content)

    if not followup_question:
        followup_question = "能再具体聊聊你的学习或项目经历吗？"

    followup_history = list(state.get("followup_history", []))
    followup_history.append({
        "round_id": state.get("round_id", 1),
        "question": followup_question,
        "priority_issue": priority_issue,
        "followup_strategy": followup_strategy,
    })

    return {
        "last_followup_question": followup_question,
        "followup_history": followup_history,
        "priority_issue": priority_issue,
        "followup_strategy": followup_strategy,
        "next_action": "generate_followup",
    }