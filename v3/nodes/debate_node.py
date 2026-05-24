"""Debate 节点：结构化争议汇总"""

import json
import logging

from ..llm_client import get_llm
from ..prompts import DEBATE_PROMPT
from ..utils.json_utils import safe_json_parse_with_retry
from ..utils.text_utils import (
    format_facts_table,
    format_anomalies_table,
    clean_llm_output,
)
from ..state_schema import DialogueState

logger = logging.getLogger(__name__)


def debate_node(state: DialogueState) -> dict:
    """Debate 节点

    当存在明显分歧时，进行结构化争议汇总。
    只做结构化争议总结，不做自由长篇辩论。

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 debate_result
    """
    llm = get_llm()

    specialist_results = state.get("specialist_results", [])
    anomalies_text = format_anomalies_table(state.get("anomalies_table", []))
    facts_text = format_facts_table(state.get("facts_table", []))

    # 格式化 specialist_results
    specialist_text = "\n".join(
        f"  [{r.get('agent', '?')}] 分数: {r.get('score', 0)}\n"
        f"    发现: {json.dumps(r.get('findings', []), ensure_ascii=False)}"
        for r in specialist_results
        if isinstance(r, dict)
    )

    # 调用 LLM（使用 ChatPromptTemplate 的 invoke 方法）
    response = llm.invoke(
        DEBATE_PROMPT.invoke({
            "specialist_results": specialist_text,
            "anomalies_table": anomalies_text,
            "facts_table": facts_text,
        })
    )

    raw_output = clean_llm_output(response.content)
    result = safe_json_parse_with_retry(
        raw_output,
        default={
            "debate_trigger": "unknown",
            "main_disagreement": "",
            "skeptic_view": "",
            "explainer_view": "",
            "consensus": "",
            "recommended_followup_focus": "",
            "debate_adjustment": {
                "semantic": 0,
                "logical": 0,
                "domain": 0,
                "psycho_linguistic": 0,
            },
        },
        node_name="争议汇总节点"
    )

    if not isinstance(result, dict):
        result = {
            "debate_trigger": "unknown",
            "main_disagreement": "",
            "skeptic_view": "",
            "explainer_view": "",
            "consensus": "",
            "recommended_followup_focus": "",
            "debate_adjustment": {
                "semantic": 0,
                "logical": 0,
                "domain": 0,
                "psycho_linguistic": 0,
            },
        }
    
    logger.info(
        f"[争议汇总节点] 汇总完成 - trigger={result.get('debate_trigger')}, consensus={result.get('consensus', '')}"
    )

    return {
        "debate_result": result,
    }