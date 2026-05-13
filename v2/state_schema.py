"""状态定义模块：定义 LangGraph State 的 TypedDict"""

from typing import TypedDict, List, Dict, Optional, Annotated
import operator


class DialogueState(TypedDict):
    """多 Agent 谎言指数测评系统的全局状态"""

    # ---- 基础对话状态 ----
    round_id: int
    max_rounds: int
    current_user_text: str
    dialogue_history: List[Dict]

    # ---- 第一版已有字段 ----
    current_facts: List[Dict]
    facts_table: List[Dict]
    current_anomalies: List[Dict]
    indicator_history: List[Dict]
    consistency_results: List[Dict]
    anomalies_table: List[Dict]
    last_followup_question: str
    followup_history: List[Dict]

    # ---- 第二版新增字段 ----
    specialist_results: Annotated[List[Dict], operator.add]  # reducer 合并并行结果
    dimension_scores: Dict[str, float]
    agent_votes: Dict[str, Dict]
    debate_needed: bool
    debate_result: Optional[Dict]

    # ---- 谎言指数相关 ----
    lie_index: float
    risk_level: str
    risk_explanation: List[str]

    # ---- 路由 ----
    next_action: str
    final_report: Optional[Dict]
