"""
事实一致性判断节点：将当前抽取的事实与历史事实表比对，判断二者关系（新增/补充/一致/不匹配/冲突/无法判断）。
调用关系：调用 llm_client.py、prompts.py、utils/json_utils.py；被 graph.py 注册为节点。
输入：state["current_facts"], state["facts_table"]
输出：state["consistency_results"]
"""
import json
from state_schema import DialogueState
from llm_client import call_llm_json
from prompts import CONSISTENCY_JUDGE_PROMPT
from utils.json_utils import parse_json_response


def consistency_judge_node(state: DialogueState) -> dict:
    """
    将当前事实与历史事实进行比对，判断一致性关系。
    """
    current_facts = state.get("current_facts", [])
    facts_table = state.get("facts_table", [])

    # 如果没有历史事实，全部记为新增事实
    if not facts_table:
        results = []
        for i, fact in enumerate(current_facts):
            results.append({
                "history_fact_id": None,
                "current_fact_id": f"current_{i}",
                "relation": "新增事实",
                "severity": "low",
                "explanation": "历史事实为空，标记为新增事实",
                "need_followup": False,
            })
        return {"consistency_results": results}

    prompt = CONSISTENCY_JUDGE_PROMPT.format(
        current_facts=json.dumps(current_facts, ensure_ascii=False, indent=2),
        facts_table=json.dumps(facts_table, ensure_ascii=False, indent=2),
    )

    response_text = call_llm_json(prompt)
    parsed = parse_json_response(response_text)

    results = parsed.get("results", [])

    return {"consistency_results": results}
