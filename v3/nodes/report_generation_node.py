"""最终报告生成节点：生成简洁的测评报告"""

import json
from ..llm_client import get_llm
from ..prompts import FINAL_REPORT_PROMPT
from ..utils.text_utils import format_dialogue_history, format_anomalies_table, clean_llm_output
from ..state_schema import DialogueState
from ..memory.anomaly_table import get_unresolved_anomalies


def report_generation_node(state: DialogueState) -> dict:
    """最终报告生成节点

    生成一份简洁的测评报告，包含：
    1. 总体结果
    2. 关键依据
    3. 待澄清点

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 final_report
    """
    llm = get_llm()

    lie_index = state.get("lie_index", 0)
    dimension_scores = state.get("dimension_scores", {})
    specialist_results = state.get("specialist_results", [])
    debate_result = state.get("debate_result")
    anomalies_table = state.get("anomalies_table", [])

    # 格式化各维度分数
    dimension_text = "\n".join(
        f"  - {name}: {score}"
        for name, score in dimension_scores.items()
    )

    # 格式化各 Specialist Agent 主要发现
    specialist_text = "\n".join(
        f"  [{r.get('agent', '?')}] 分数: {r.get('score', 0)}\n"
        f"    发现: {json.dumps(r.get('findings', []), ensure_ascii=False)}"
        for r in specialist_results
        if isinstance(r, dict)
    )

    # 格式化 Debate 结果
    debate_text = ""
    if isinstance(debate_result, dict):
        debate_text = json.dumps(debate_result, ensure_ascii=False, indent=2)

    # 格式化待澄清问题
    unresolved = get_unresolved_anomalies(anomalies_table)
    unresolved_text = "\n".join(
        f"  - {a.get('description', '')} (类型: {a.get('type', '')})"
        for a in unresolved
    ) if unresolved else "暂无明显待澄清点"

    # 调用 LLM（使用 ChatPromptTemplate 的 invoke 方法）
    response = llm.invoke(
        FINAL_REPORT_PROMPT.invoke({
            "lie_index": lie_index,
            "dimension_scores": dimension_text,
            "specialist_results": specialist_text,
            "debate_result": debate_text or "未触发 Debate",
            "unresolved_anomalies": unresolved_text,
        })
    )

    report_text = clean_llm_output(response.content)

    final_report = {
        "lie_index": lie_index,
        "dimension_scores": dimension_scores,
        "report_text": report_text,
    }

    return {
        "final_report": final_report,
        "next_action": "final_report",  # v3: 标记流程已结束
    }