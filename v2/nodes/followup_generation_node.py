"""追问生成节点：根据分析结果生成自然的追问"""

from langchain_core.messages import HumanMessage, SystemMessage
from ..llm_client import get_llm
from ..prompts import FOLLOWUP_GENERATION_SYSTEM
from ..utils.text_utils import format_dialogue_history, format_anomalies_table, clean_llm_output
from ..state_schema import DialogueState


def followup_generation_node(state: DialogueState) -> dict:
    """追问生成节点

    根据当前分析结果生成一个自然的追问。

    规则：
    1. 只生成一个问题
    2. 语气自然，像正常聊天中的好奇
    3. 不能使用"谎言""矛盾""审查""核验"等词
    4. 优先围绕 priority_issue 追问
    5. 如果有 debate_result，优先围绕 consensus 指出的澄清方向追问

    Args:
        state: 当前对话状态
    Returns:
        状态更新字典，包含 last_followup_question
    """
    llm = get_llm()

    # 从 agent_votes 中获取策略信息
    agent_votes = state.get("agent_votes", {})
    priority_issue = agent_votes.get("priority_issue", "职业身份相关细节")
    followup_strategy = agent_votes.get("followup_strategy", "general")

    dimension_scores = state.get("dimension_scores", {})
    debate_result = state.get("debate_result")
    anomalies_text = format_anomalies_table(state.get("anomalies_table", []))
    dialogue_text = format_dialogue_history(state.get("dialogue_history", []))

    # 格式化 debate_result
    import json
    debate_text = ""
    if isinstance(debate_result, dict):
        debate_text = json.dumps(debate_result, ensure_ascii=False, indent=2)

    prompt = FOLLOWUP_GENERATION_SYSTEM.format(
        priority_issue=priority_issue,
        followup_strategy=followup_strategy,
        dimension_scores=dimension_scores,
        debate_result=debate_text or "无",
        anomalies_table=anomalies_text,
        dialogue_history=dialogue_text,
    )

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="请生成追问"),
    ])

    followup_question = clean_llm_output(response.content)

    # 更新追问历史
    followup_history = list(state.get("followup_history", []))
    followup_history.append({
        "round_id": state.get("round_id", 1),
        "question": followup_question,
    })

    return {
        "last_followup_question": followup_question,
        "followup_history": followup_history,
    }
