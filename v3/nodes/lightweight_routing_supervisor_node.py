"""轻量路由监督节点：决定是否调用专家 Agent 以及调用哪些 Agent"""

import logging

from langchain_core.messages import HumanMessage

from ..llm_client import get_llm
from ..prompts import LIGHTWEIGHT_ROUTING_SUPERVISOR_PROMPT
from ..state_schema import DialogueState
from ..utils.json_utils import extract_json_from_text
from ..utils.text_utils import format_facts_table, format_anomalies_table, clean_llm_output
from ..config import ENABLE_ON_DEMAND_SPECIALISTS
from ..memory.anomaly_table import count_unresolved

logger = logging.getLogger(__name__)


# ============================================================
# 新增常量
# ============================================================

VALID_SPECIALISTS = ["semantic", "logical", "domain", "psycho_linguistic"]
DEFAULT_CORE_SPECIALISTS = ["semantic", "logical"]

# ============================================================
# 允许的追问策略集合
# ============================================================
ALLOWED_FOLLOWUP_STRATEGIES = [
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


def normalize_followup_strategy(strategy: str, has_risk: bool) -> str:
    """归一化追问策略

    如果策略不在允许集合中，根据是否有风险进行兜底：
    - 有风险 → light_clarification（温和澄清）
    - 无风险 → daily_routine（日常了解）
    """
    if strategy in ALLOWED_FOLLOWUP_STRATEGIES:
        return strategy
    return "light_clarification" if has_risk else "daily_routine"


# ============================================================
# 新增辅助函数
# ============================================================
def should_skip_specialist(state):
    surface_risk_score = state.get("surface_risk_score", 0)
    current_anomalies = state.get("current_anomalies", [])
    anomalies_table = state.get("anomalies_table", [])
    current_facts = state.get("current_facts", [])
    facts_table = state.get("facts_table", [])
    has_new_fact = state.get("has_new_fact", False)
    round_id = state.get("round_id", 1)

    unresolved_count = count_unresolved(anomalies_table)

    if current_anomalies:
        return False

    if unresolved_count > 0:
        return False

    if surface_risk_score >= 40:
        return False

    if round_id <= 1:
        return True

    if not has_new_fact and surface_risk_score < 30:
        return True

    core_slots = {
        "occupation",
        "role",
        "company",
        "time_stage",
        "experience",
        "work_content",
    }

    has_core_new_fact = any(
        isinstance(f, dict) and f.get("slot") in core_slots
        for f in current_facts
    )

    if has_new_fact and not has_core_new_fact and surface_risk_score < 20:
        return True

    if has_new_fact and surface_risk_score == 0 and len(current_facts) <= 2:
        return True

    if len(facts_table) < 3 and surface_risk_score < 30:
        return True

    return False

def infer_default_specialists(state: DialogueState) -> list[str]:
    """推断默认的专家列表

    根据当前状态推断应该调用的专家：
    - 默认优先 semantic + logical（核心任务：多轮职业身份/经历一致性分析）
    - domain 和 psycho_linguistic 只在异常类型明显相关时补充

    Args:
        state: 对话状态

    Returns:
        推断的专家列表
    """
    current_anomalies = state.get("current_anomalies", [])
    has_new_fact = state.get("has_new_fact", False)
    facts_table = state.get("facts_table", [])
    surface_risk_score = state.get("surface_risk_score", 0)

    selected = []

    # 有新事实或多条事实，需要核心专家检查一致性
    if has_new_fact or len(facts_table) >= 2:
        selected.extend(["semantic", "logical"])

    # 提取异常类型关键词
    anomaly_types = [
        str(a.get("type", ""))
        for a in current_anomalies
        if isinstance(a, dict)
    ]
    anomaly_text = " ".join(anomaly_types)

    # 根据异常类型补充专家
    if any(k in anomaly_text for k in ["职业常识", "岗位职责", "domain", "responsibility", "industry"]):
        selected.append("domain")

    if any(k in anomaly_text for k in ["回避", "模糊", "过度解释", "答非所问", "细节缺失", "self_correction", "avoidance", "vague"]):
        selected.append("psycho_linguistic")

    # 高风险且没有选择任何专家，默认调用核心专家
    if surface_risk_score >= 50 and not selected:
        selected.extend(["semantic", "logical"])

    # 最终兜底：如果仍然为空，使用默认核心专家
    if not selected:
        selected.extend(DEFAULT_CORE_SPECIALISTS)

    # 去重并保持顺序
    return list(dict.fromkeys(selected))


def invoke_router_with_retry(llm, prompt_input: dict, max_retries: int = 2):
    """带重试的路由 LLM 调用

    最多调用 max_retries + 1 次 LLM：
    - 第 1 次正常调用
    - 后续重试时追加 HumanMessage 要求输出合法 JSON
    每次调用后尝试两次 JSON 解析（普通清理 + 激进清理）。
    全部失败返回 None。
    """
    for attempt in range(max_retries + 1):
        prompt_value = LIGHTWEIGHT_ROUTING_SUPERVISOR_PROMPT.invoke(prompt_input)
        messages = prompt_value.to_messages()

        if attempt > 0:
            messages.append(
                HumanMessage(content=(
                    "你上一次输出不是合法 JSON，无法解析。"
                    "请重新输出，只输出一个标准 JSON 对象。"
                    "不要 Markdown，不要解释，不要代码块。"
                    "必须包含字段：need_specialist, selected_specialists, "
                    "routing_reason, priority_issue, followup_strategy。"
                    "followup_strategy 只能是 daily_routine、entry_experience、"
                    "work_style、recent_memory、light_clarification、topic_shift_buffer、"
                    "experience_probe、knowledge_probe、tool_workflow_probe、scenario_judgment_probe 之一。"
                ))
            )

        response = llm.invoke(messages)
        raw_output = clean_llm_output(response.content)

        result = extract_json_from_text(raw_output)
        if isinstance(result, dict):
            if attempt > 0:
                logger.info(f"[路由监督节点] 第 {attempt + 1} 次调用 LLM 后解析成功")
            return result

        cleaned_again = clean_llm_output(raw_output, aggressive=True)
        result = extract_json_from_text(cleaned_again)
        if isinstance(result, dict):
            if attempt > 0:
                logger.info(f"[路由监督节点] 第 {attempt + 1} 次调用 LLM 后激进清理解析成功")
            return result

        logger.warning(
            f"[路由监督节点] 第 {attempt + 1} 次 JSON 解析失败"
            f"（输出长度: {len(raw_output)} 字符，预览: {raw_output[:200]}...）"
        )

    return None


def lightweight_routing_supervisor_node(state: DialogueState) -> dict:
    """轻量路由监督节点

    根据第一层轻量预分析结果，决定调用第二层 Specialist Agent哪些 Agent
    
    新路由逻辑：
    - Python 规则决定本轮是否允许跳过专家
    - LLM 只决定如果不能跳过专家，具体调用哪些专家
    - LLM 选择失败则默认 semantic + logical
    """
    # 如果未启用按需专家，默认调用全部
    if not ENABLE_ON_DEMAND_SPECIALISTS:
        return {
            "routing_decision": {
                "need_specialist": True,
                "selected_specialists": ["semantic", "logical", "domain", "psycho_linguistic"],
                "routing_reason": "未启用按需专家模式，默认调用全部专家",
                "priority_issue": "完整分析",
                "followup_strategy": "light_clarification",
                "router_mode": "all_specialists",
            },
            "selected_specialists": ["semantic", "logical", "domain", "psycho_linguistic"],
            "need_specialist": True,
            "priority_issue": "完整分析",
            "followup_strategy": "light_clarification",
        }

    # 提取输入
    current_user_text = state.get("current_user_text", "")
    current_facts = state.get("current_facts", [])
    current_anomalies = state.get("current_anomalies", [])
    facts_table = state.get("facts_table", [])
    anomalies_table = state.get("anomalies_table", [])
    surface_risk_score = state.get("surface_risk_score", 0)

    # ============================================================
    # 规则跳过判断（优先级最高，不调用 LLM）
    # ============================================================
    if should_skip_specialist(state):
        routing_decision = {
            "need_specialist": False,
            "selected_specialists": [],
            "routing_reason": "规则判定为极低风险：无新事实、无当前异常、无未解决异常，跳过专家分析",
            "priority_issue": "无明显待澄清点",
            "followup_strategy": "daily_routine",
            "router_mode": "rule_skip",
        }
        
        logger.info(
            f"[路由监督节点] 规则跳过专家 - "
            f"surface_risk_score={surface_risk_score}, "
            f"has_new_fact={state.get('has_new_fact', False)}, "
            f"current_anomalies={len(state.get('current_anomalies', []))}, "
            f"unresolved_count={count_unresolved(anomalies_table)}"
        )
        
        return {
            "routing_decision": routing_decision,
            "selected_specialists": [],
            "need_specialist": False,
            "priority_issue": routing_decision["priority_issue"],
            "followup_strategy": routing_decision["followup_strategy"],
        }

    # ============================================================
    # 格式化数据并调用 LLM
    # ============================================================
    # 格式化事实表
    facts_str = format_facts_table(facts_table) if facts_table else "暂无事实记录"
    
    # 格式化当前事实
    current_facts_str = "\n".join([
        f"- {f.get('content', '')}（类型:{f.get('slot', '')}）"
        for f in current_facts
    ]) if current_facts else "本轮无新事实"
    
    # 格式化当前异常
    current_anomalies_str = "\n".join([
        f"- {a.get('type', '')}: {a.get('description', '')}（分数:{a.get('score', 0)}）"
        for a in current_anomalies
    ]) if current_anomalies else "本轮无新异常"
    
    # 格式化异常表
    anomalies_str = format_anomalies_table(anomalies_table) if anomalies_table else "暂无异常记录"

    # 调用 LLM（带重试：最多 3 次调用，每次调用后 2 次解析尝试）
    llm = get_llm()
    prompt_input = {
        "current_user_text": current_user_text,
        "current_facts": current_facts_str,
        "current_anomalies": current_anomalies_str,
        "facts_table": facts_str,
        "anomalies_table": anomalies_str,
        "surface_risk_score": surface_risk_score,
    }

    result = invoke_router_with_retry(llm, prompt_input, max_retries=2)

    # 全部重试均失败，走兜底逻辑
    if not result:
        logger.error(
            "[路由监督节点] LLM 调用 3 次均无法解析出有效 JSON，进入兜底"
        )

        if should_skip_specialist(state):
            fallback_decision = {
                "need_specialist": False,
                "selected_specialists": [],
                "routing_reason": "[解析错误兜底] 规则判定为极低风险，跳过专家分析",
                "priority_issue": "无明显待澄清点",
                "followup_strategy": "daily_routine",
                "parse_error": "json_parse_failed",
                "fallback_used": True,
                "router_mode": "rule_skip_after_parse_error",
            }
            logger.info(
                "[路由监督节点] 使用低风险兜底决策（重试耗尽，但满足跳过条件）"
            )
        else:
            fallback_selected = infer_default_specialists(state)
            fallback_decision = {
                "need_specialist": True,
                "selected_specialists": fallback_selected,
                "routing_reason": "[解析错误兜底] 不满足跳过条件，调用默认核心专家",
                "priority_issue": "需要进一步澄清当前事实或异常",
                "followup_strategy": "light_clarification",
                "parse_error": "json_parse_failed",
                "fallback_used": True,
                "router_mode": "rule_force_after_parse_error",
            }
            logger.info(
                "[路由监督节点] 使用默认专家兜底决策（重试耗尽，不满足跳过条件）"
            )

        return {
            "routing_decision": fallback_decision,
            "selected_specialists": fallback_decision["selected_specialists"],
            "need_specialist": fallback_decision["need_specialist"],
            "priority_issue": fallback_decision["priority_issue"],
            "followup_strategy": fallback_decision["followup_strategy"],
            "parse_error": fallback_decision["parse_error"],
        }

    # ============================================================
    # 提取 LLM 结果（修改：忽略 LLM 的 need_specialist）
    # ============================================================
    # 忽略 LLM 返回的 need_specialist，规则已经判定不能跳过
    need_specialist = True
    selected_specialists = result.get("selected_specialists", [])
    routing_reason = result.get("routing_reason", "")
    priority_issue = result.get("priority_issue", "")
    followup_strategy = result.get("followup_strategy", "")

    # 校验 followup_strategy 合法性，非法则兜底
    has_risk = bool(
        current_anomalies
        or any(
            isinstance(a, dict)
            and (
                a.get("status") in ("unresolved", "reinforced")
                or a.get("followup_needed") is True
            )
            for a in anomalies_table
        )
        or surface_risk_score >= 40
    )
    followup_strategy = normalize_followup_strategy(followup_strategy, has_risk)

    logger.info(
        f"[路由监督节点] LLM 决策成功解析 - "
        f"selected_specialists={selected_specialists}, "
        f"priority_issue={priority_issue}, "
        f"reason={routing_reason}"
    )

    # 验证 selected_specialists
    selected_specialists = [s for s in selected_specialists if s in VALID_SPECIALISTS]

    # ============================================================
    # 修改：LLM 选择为空时的兜底规则
    # ============================================================
    if not selected_specialists:
        logger.info(
            f"[路由监督节点] LLM 未选择专家，使用默认推断"
        )
        selected_specialists = infer_default_specialists(state)

    # ============================================================
    # 返回结果（保持原有格式）
    # ============================================================
    return {
        "routing_decision": {
            "need_specialist": need_specialist,
            "selected_specialists": selected_specialists,
            "routing_reason": routing_reason,
            "priority_issue": priority_issue,
            "followup_strategy": followup_strategy,
            "router_mode": "rule_force_llm_select",
        },
        "selected_specialists": selected_specialists,
        "need_specialist": need_specialist,
        "priority_issue": priority_issue,
        "followup_strategy": followup_strategy,
    }
