"""
状态更新节点：更新事实表、异常表、对话历史，计算谎言指数和风险等级。纯 Python 逻辑，不调用 LLM。
调用关系：调用 config.py 读取权重配置；被 graph.py 注册为节点。
输入：state["current_user_text"], state["current_facts"], state["current_anomalies"], state["consistency_results"], state["facts_table"], state["anomalies_table"], state["lie_index"]
输出：state["dialogue_history"], state["indicator_history"], state["facts_table"], state["anomalies_table"], state["lie_index"], state["risk_level"]
"""
from state_schema import DialogueState
from config import LIE_INDEX_WEIGHTS, LIE_INDEX_MAX, RISK_LEVELS


def _generate_fact_id(facts_table: list) -> str:
    """生成唯一 fact_id"""
    existing_ids = {f["fact_id"] for f in facts_table if "fact_id" in f}
    idx = len(facts_table) + 1
    fact_id = f"f{idx:03d}"
    while fact_id in existing_ids:
        idx += 1
        fact_id = f"f{idx:03d}"
    return fact_id


def _generate_anomaly_id(anomalies_table: list) -> str:
    """生成唯一 anomaly_id"""
    existing_ids = {a["anomaly_id"] for a in anomalies_table if "anomaly_id" in a}
    idx = len(anomalies_table) + 1
    anomaly_id = f"a{idx:03d}"
    while anomaly_id in existing_ids:
        idx += 1
        anomaly_id = f"a{idx:03d}"
    return anomaly_id


def _compute_lie_index(
    consistency_results: list,
    current_anomalies: list,
    anomalies_table: list,
) -> int:
    """根据一致性结果和异常表达计算谎言指数（累计）"""
    score = 0

    # 一致性判断贡献
    for result in consistency_results:
        relation = result.get("relation", "")
        weight = LIE_INDEX_WEIGHTS.get(relation, 0)
        score += weight

    # 当前轮异常表达贡献
    for anomaly in current_anomalies:
        indicator = anomaly.get("indicator", "")
        weight = LIE_INDEX_WEIGHTS.get(indicator, 0)
        score += weight

    return min(score, LIE_INDEX_MAX)


def _compute_risk_level(lie_index: int) -> str:
    """根据谎言指数计算风险等级"""
    for level, (low, high) in RISK_LEVELS.items():
        if low <= lie_index <= high:
            return level
    return "高"


def state_update_node(state: DialogueState) -> dict:
    """
    更新全局状态：事实表、异常表、对话历史、谎言指数、风险等级。

    Append 字段（dialogue_history, indicator_history, followup_history）只返回新增项。
    Overwrite 字段（facts_table, anomalies_table, lie_index, risk_level）返回完整值。
    """
    # --- 1. 对话历史：只返回新增项 ---
    new_dialogue = [{
        "role": "user",
        "content": state["current_user_text"],
    }]

    # --- 2. 事实表：返回完整列表 ---
    facts_table = list(state.get("facts_table", []))
    current_facts = state.get("current_facts", [])
    consistency_results = state.get("consistency_results", [])

    for i, fact in enumerate(current_facts):
        fact["fact_id"] = _generate_fact_id(facts_table)
        if "time_stage" not in fact:
            fact["time_stage"] = "当前"
        if "confidence" not in fact:
            fact["confidence"] = "medium"
        facts_table.append(fact)

    # --- 3. 异常表达历史：只返回新增项 ---
    current_anomalies = state.get("current_anomalies", [])
    for anomaly in current_anomalies:
        anomaly["round_id"] = state["round_id"]

    # --- 4. 异常表：返回完整列表 ---
    anomalies_table = list(state.get("anomalies_table", []))
    for result in consistency_results:
        relation = result.get("relation", "")
        if relation in ("潜在不匹配", "明显冲突"):
            anomaly_id = _generate_anomaly_id(anomalies_table)
            history_fact_id = result.get("history_fact_id")
            current_fact_id = result.get("current_fact_id")
            related_ids = []
            if history_fact_id:
                related_ids.append(history_fact_id)
            if current_fact_id:
                related_ids.append(current_fact_id)
            anomalies_table.append({
                "anomaly_id": anomaly_id,
                "round_id": state["round_id"],
                "type": f"职业内容{relation}",
                "related_fact_ids": related_ids,
                "description": result.get("explanation", ""),
                "severity": result.get("severity", "medium"),
                "status": "unresolved",
                "evidence": [],
            })

    # --- 5. 计算谎言指数（在已有基础上累加本轮增量） ---
    existing_lie_index = state.get("lie_index", 0)
    delta = _compute_lie_index(consistency_results, current_anomalies, anomalies_table)
    lie_index = min(existing_lie_index + delta, LIE_INDEX_MAX)

    # --- 6. 计算风险等级 ---
    risk_level = _compute_risk_level(lie_index)

    return {
        # Append 字段：只返回新增项
        "dialogue_history": new_dialogue,
        "indicator_history": current_anomalies,
        # Overwrite 字段：返回完整值
        "facts_table": facts_table,
        "anomalies_table": anomalies_table,
        "lie_index": lie_index,
        "risk_level": risk_level,
    }
