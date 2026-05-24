"""快速预分析节点：一次 LLM 调用同时完成事实抽取和表层异常检测

v3.2 合并：将 quick_fact_extraction_node 和 quick_signal_detection_node
合并为一个节点，减少一次 LLM 调用。
"""

import logging

from ..llm_client import get_llm
from ..prompts import QUICK_PREANALYSIS_PROMPT
from ..state_schema import DialogueState
from ..utils.json_utils import extract_json_from_text
from ..utils.text_utils import (
    format_dialogue_history,
    format_facts_table,
    format_anomalies_table,
    clean_llm_output,
)
from ..memory.anomaly_table import (
    update_anomalies_status,
    add_anomalies,
)

logger = logging.getLogger(__name__)


def _ensure_list(value) -> list:
    """确保输入是 list，不是则返回空列表"""
    return value if isinstance(value, list) else []


def _safe_float(value, default: float = 0.0) -> float:
    """安全转换为 float，失败时返回默认值"""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def quick_preanalysis_node(state: DialogueState) -> dict:
    """
    快速预分析节点（合并版）

    职责：一次 LLM 调用，同时完成"事实抽取"和"表层异常检测"。

    输入字段：
        - current_user_text: 当前用户回答
        - last_followup_question: 上一轮系统追问
        - dialogue_history: 对话历史
        - facts_table: 已有事实表
        - anomalies_table: 已有异常表
        - round_id: 当前轮次

    输出字段：
        - facts_table: 更新后的事实表
        - current_facts: 当前抽取的事实列表
        - has_new_fact: 是否有新事实
        - anomalies_table: 更新后的异常表
        - current_anomalies: 当前识别的异常列表
        - surface_risk_score: 表层风险分数（0-100）
        - quick_fact_summary: 事实摘要
        - quick_signal_summary: 异常摘要
    """
    current_user_text = state.get("current_user_text", "")
    last_followup_question = state.get("last_followup_question", "")
    dialogue_history = state.get("dialogue_history", [])
    facts_table = state.get("facts_table", [])
    anomalies_table = state.get("anomalies_table", [])
    round_id = state.get("round_id", 1)

    history_str = format_dialogue_history(dialogue_history)
    facts_str = format_facts_table(facts_table) if facts_table else "暂无事实记录"
    anomalies_str = format_anomalies_table(anomalies_table) if anomalies_table else "暂无异常记录"

    llm = get_llm()
    response = llm.invoke(
        QUICK_PREANALYSIS_PROMPT.invoke({
            "last_followup_question": last_followup_question,
            "dialogue_history": history_str,
            "current_user_text": current_user_text,
            "facts_table": facts_str,
            "anomalies_table": anomalies_str,
        })
    )

    raw_output = clean_llm_output(response.content)
    result = extract_json_from_text(raw_output)

    if not result:
        logger.warning(
            f"[快速预分析节点] 第一次 JSON 解析失败，尝试重新解析。"
            f"原始输出长度: {len(raw_output)} 字符，"
            f"原始输出预览: {raw_output[:200]}..."
        )

        cleaned_again = clean_llm_output(raw_output, aggressive=True)
        result = extract_json_from_text(cleaned_again)

        if not result:
            logger.error(
                f"[快速预分析节点] JSON 解析彻底失败。"
                f"已尝试两次解析，均无法提取有效 JSON。"
                f"原始输出: {raw_output}"
            )

            return {
                "facts_table": facts_table,
                "current_facts": [],
                "has_new_fact": False,
                "anomalies_table": anomalies_table,
                "current_anomalies": [],
                "surface_risk_score": 0.0,
                "quick_fact_summary": "",
                "quick_signal_summary": "",
                "parse_error": "json_parse_failed",
                "original_output_preview": raw_output[:200] + "..." if len(raw_output) > 200 else raw_output,
            }

        logger.info("[快速预分析节点] 第二次解析成功")

    if not isinstance(result, dict):
        logger.warning(
            f"[快速预分析节点] JSON 解析结果不是 dict，类型为 {type(result)}，返回默认值"
        )
        return {
            "facts_table": facts_table,
            "current_facts": [],
            "has_new_fact": False,
            "anomalies_table": anomalies_table,
            "current_anomalies": [],
            "surface_risk_score": 0.0,
            "quick_fact_summary": "",
            "quick_signal_summary": "",
            "parse_error": "json_not_dict",
        }

    raw_facts = _ensure_list(result.get("facts", []))
    anomaly_updates = _ensure_list(result.get("anomaly_updates", []))
    raw_anomalies = _ensure_list(result.get("anomalies", []))

    surface_risk_score = _safe_float(result.get("surface_risk_score", 0), 0.0)
    surface_risk_score = max(0.0, min(100.0, surface_risk_score))

    quick_fact_summary = result.get("quick_fact_summary", "")
    quick_signal_summary = result.get("quick_signal_summary", "")

    if not isinstance(quick_fact_summary, str):
        quick_fact_summary = str(quick_fact_summary)

    if not isinstance(quick_signal_summary, str):
        quick_signal_summary = str(quick_signal_summary)

    logger.info(
        f"[快速预分析节点] 预分析成功 - "
        f"抽取到 {len(raw_facts)} 条事实，"
        f"识别到 {len(raw_anomalies)} 个异常，"
        f"更新 {len(anomaly_updates)} 个旧异常，"
        f"surface_risk_score={surface_risk_score}"
    )

    VALID_SLOTS = [
        "occupation",
        "role",
        "work_content",
        "company",
        "time_stage",
        "experience",
        "other",
    ]

    normalized_current_facts = []

    for fact in raw_facts:
        if not isinstance(fact, dict):
            logger.warning(f"[快速预分析节点] 跳过非 dict fact: {fact}")
            continue

        content = fact.get("content") or fact.get("value") or ""
        evidence = fact.get("evidence") or fact.get("raw_text") or content
        slot = fact.get("slot", "other")

        if not isinstance(content, str):
            content = str(content)

        if not isinstance(evidence, str):
            evidence = str(evidence)

        if slot not in VALID_SLOTS:
            slot = "other"

        if not content.strip():
            continue

        normalized_fact = {
            "round_id": round_id,
            "slot": slot,
            "content": content.strip(),
            "evidence": evidence.strip(),
            "source": "quick_preanalysis",
        }
        normalized_current_facts.append(normalized_fact)

    has_new_fact = bool(normalized_current_facts)

    normalized_anomaly_updates = []

    for update in anomaly_updates:
        if not isinstance(update, dict):
            logger.warning(f"[快速预分析节点] 跳过非 dict anomaly_update: {update}")
            continue
        normalized_anomaly_updates.append(update)

    updated_anomalies_table = update_anomalies_status(
        anomalies_table=anomalies_table,
        updates=normalized_anomaly_updates,
        round_id=round_id,
    )

    normalized_current_anomalies = []

    for anomaly in raw_anomalies:
        if not isinstance(anomaly, dict):
            logger.warning(f"[快速预分析节点] 跳过非 dict anomaly: {anomaly}")
            continue

        evidence = anomaly.get("evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence]
        elif not isinstance(evidence, list):
            evidence = []

        evidence = [str(e) for e in evidence if e is not None]

        score = _safe_float(anomaly.get("score", 0), 0.0)
        score = max(0.0, min(100.0, score))

        related_facts = anomaly.get("related_facts", [])
        if not isinstance(related_facts, list):
            related_facts = []

        normalized_anomaly = {
            "type": str(anomaly.get("type", "未分类")),
            "description": str(anomaly.get("description", "")),
            "evidence": evidence,
            "score": score,
            "related_facts": related_facts,
        }

        if not normalized_anomaly["description"].strip() and not normalized_anomaly["evidence"]:
            continue

        normalized_current_anomalies.append(normalized_anomaly)

    updated_anomalies_table = add_anomalies(
        anomalies_table=updated_anomalies_table,
        new_anomalies=normalized_current_anomalies,
        round_id=round_id,
        source="quick_preanalysis",
    )

    updated_facts_table = list(facts_table)
    updated_facts_table.extend(normalized_current_facts)

    return {
        "facts_table": updated_facts_table,
        "current_facts": normalized_current_facts,
        "has_new_fact": has_new_fact,
        "anomalies_table": updated_anomalies_table,
        "current_anomalies": normalized_current_anomalies,
        "surface_risk_score": surface_risk_score,
        "quick_fact_summary": quick_fact_summary,
        "quick_signal_summary": quick_signal_summary,
    }