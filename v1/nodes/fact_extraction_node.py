"""
事实抽取节点：调用 LLM 从用户回答中抽取职业身份相关事实。
调用关系：调用 llm_client.py、prompts.py、utils/json_utils.py；被 graph.py 注册为节点。
输入：state["round_id"], state["current_user_text"]
输出：state["current_facts"]
"""
from state_schema import DialogueState
from llm_client import call_llm_json
from prompts import FACT_EXTRACTION_PROMPT
from utils.json_utils import parse_json_response


def fact_extraction_node(state: DialogueState) -> dict:
    """
    从当前用户回答中抽取职业身份相关事实。
    """
    prompt = FACT_EXTRACTION_PROMPT.format(
        round_id=state["round_id"],
        user_text=state["current_user_text"],
    )

    response_text = call_llm_json(prompt)
    parsed = parse_json_response(response_text)

    facts = parsed.get("facts", [])

    # 为每条事实添加 round_id，确保字段完整
    for fact in facts:
        fact["round_id"] = state["round_id"]

    return {"current_facts": facts}
