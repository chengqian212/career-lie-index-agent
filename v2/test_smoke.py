"""端到端冒烟测试脚本"""
import os
import sys

# 关闭代理
for key in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
    os.environ.pop(key, None)

# 设置编码
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from career_lie_index_agent.config import disable_proxy
from career_lie_index_agent.graph import build_graph

disable_proxy()

graph = build_graph()
state = {
    "round_id": 1,
    "max_rounds": 2,
    "current_user_text": "我现在在投行，最近主要做新能源IPO",
    "dialogue_history": [
        {"role": "assistant", "content": "你平时是做什么方向的工作呀？"},
        {"role": "user", "content": "我现在在投行，最近主要做新能源IPO"},
    ],
    "current_facts": [],
    "facts_table": [],
    "current_anomalies": [],
    "indicator_history": [],
    "consistency_results": [],
    "anomalies_table": [],
    "last_followup_question": "",
    "followup_history": [],
    "specialist_results": [],
    "dimension_scores": {},
    "agent_votes": {},
    "debate_needed": False,
    "debate_result": None,
    "lie_index": 0.0,
    "risk_level": "低",
    "risk_explanation": [],
    "next_action": "",
    "final_report": None,
}

print("Running single round test...")
result = graph.invoke(state)

print("\n" + "=" * 60)
print(f"lie_index: {result.get('lie_index', 0)} / 100")
print(f"risk_level: {result.get('risk_level', '?')}")
print(f"dimension_scores: {result.get('dimension_scores', {})}")
print(f"debate_needed: {result.get('debate_needed', False)}")
print(f"risk_explanation: {result.get('risk_explanation', [])}")
print(f"followup: {result.get('last_followup_question', '')}")
print("=" * 60)
print("Single round test PASSED!")
