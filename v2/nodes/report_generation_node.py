"""最终报告生成节点：生成完整的谎言指数测评报告"""

from langchain_core.messages import HumanMessage, SystemMessage
from ..llm_client import get_llm
from ..prompts import FINAL_REPORT_SYSTEM
from ..utils.text_utils import format_dialogue_history, format_anomalies_table, clean_llm_output
from ..state_schema import DialogueState
from ..memory.anomaly_table import get_unresolved_anomalies


def report_generation_node(state: DialogueState) -> dict:
    """最终报告生成节点

    生成一份完整的谎言指数测评报告，包含：
    1. 总体评估
    2. 谎言指数解读
    3. 各维度分析摘要
    4. 关键风险证据
    5. 待澄清线索
    6. 后续建议

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 final_report
    """
    llm = get_llm()

    lie_index = state.get("lie_index", 0)
    risk_level = state.get("risk_level", "低")
    dimension_scores = state.get("dimension_scores", {})
    specialist_results = state.get("specialist_results", [])
    debate_result = state.get("debate_result")
    anomalies_table = state.get("anomalies_table", [])
    dialogue_text = format_dialogue_history(state.get("dialogue_history", []))

    # 格式化各维度分数
    dimension_text = "\n".join(
        f"  - {name}: {score}"
        for name, score in dimension_scores.items()
    )

    # 格式化各 Specialist Agent 主要发现
    import json
    specialist_text = "\n".join(
        f"  [{r.get('agent', '?')}] 分数: {r.get('score', 0)}, 投票: {r.get('vote', '?')}\n"
        f"    发现: {json.dumps(r.get('findings', []), ensure_ascii=False)}"
        for r in specialist_results
        if isinstance(r, dict)
    )

    # 格式化 Debate 结果
    debate_text = ""
    if isinstance(debate_result, dict):
        debate_text = json.dumps(debate_result, ensure_ascii=False, indent=2)

    # 格式化关键证据
    key_evidence = []
    for result in specialist_results:
        if isinstance(result, dict):
            for finding in result.get("findings", []):
                if isinstance(finding, dict):
                    for ev in finding.get("evidence", []):
                        if ev not in key_evidence:
                            key_evidence.append(ev)
    key_evidence_text = "\n".join(f"  - {ev}" for ev in key_evidence) if key_evidence else "暂无"

    # 格式化待澄清问题
    unresolved = get_unresolved_anomalies(anomalies_table)
    unresolved_text = "\n".join(
        f"  - {a.get('description', '')} (类型: {a.get('type', '')})"
        for a in unresolved
    ) if unresolved else "所有异常已澄清"

    prompt = FINAL_REPORT_SYSTEM.format(
        lie_index=lie_index,
        risk_level=risk_level,
        dimension_scores=dimension_text,
        specialist_results=specialist_text,
        debate_result=debate_text or "未触发 Debate",
        key_evidence=key_evidence_text,
        unresolved_anomalies=unresolved_text,
        dialogue_history=dialogue_text,
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请生成最终测评报告"),
    ])

    report_text = clean_llm_output(response.content)

    final_report = {
        "lie_index": lie_index,
        "risk_level": risk_level,
        "dimension_scores": dimension_scores,
        "report_text": report_text,
    }

    return {
        "final_report": final_report,
    }
