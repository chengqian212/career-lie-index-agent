"""
命令行多轮对话 Demo：启动时关闭代理，循环接收用户输入并调用 LangGraph 工作流，输出追问和最终报告。
调用关系：调用 config.py 关闭代理和读取轮数；调用 graph.py 构建工作流。
输入：用户键盘输入
输出：终端打印（追问、谎言指数、风险等级、追问策略、最终报告）
"""
import json
import os
import sys
import time
from datetime import datetime
from typing import Any

# Windows 终端 UTF-8 编码
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v1.config import MAX_ROUNDS, RISK_LEVELS
from v1.utils.env_utils import disable_proxy
from v1.graph import build_graph
from v1.state_schema import DialogueState


def create_initial_state() -> dict[str, Any]:
    """创建初始状态"""
    return {
        "round_id": 1,
        "max_rounds": MAX_ROUNDS,
        "current_user_text": "",
        "dialogue_history": [],
        "current_facts": [],
        "current_anomalies": [],
        "consistency_results": [],
        "facts_table": [],
        "anomalies_table": [],
        "indicator_history": [],
        "priority_issue": "",
        "followup_strategy": "",
        "strategy_reason": "",
        "next_action": "generate_followup",
        "last_followup_question": "你平时是做什么工作的呀？",
        "followup_history": [],
        "lie_index": 0,
        "risk_level": "低",
        "final_report": None,
    }


def print_round_summary(state: dict, elapsed: float = 0.0) -> None:
    """打印每轮分析摘要

    Args:
        state: 当前状态
        elapsed: 本轮系统思考耗时（秒）
    """
    lie_index = state.get("lie_index", 0)
    risk_level = state.get("risk_level", "低")
    followup = state.get("last_followup_question", "")
    followup_strategy = state.get("followup_strategy", "")
    strategy_reason = state.get("strategy_reason", "")

    print("\n" + "=" * 60)
    print(f"📊 当前谎言指数：{lie_index} / 100（风险等级：{risk_level}）")
    print("-" * 60)
    if followup_strategy:
        print(f"🎯 追问策略：{followup_strategy}")
    if strategy_reason:
        print(f"💡 策略理由：{strategy_reason}")
    print("-" * 60)
    if followup:
        print(f"❓ 系统追问：{followup}")
    if elapsed > 0:
        print(f"⏱️  系统思考耗时：{elapsed:.2f} 秒")
    print("=" * 60)


def print_final_report(state: dict) -> None:
    """打印最终报告

    Args:
        state: 当前状态
    """
    final_report = state.get("final_report")
    if not final_report:
        print("\n❌ 未生成最终报告")
        return

    print("\n" + "=" * 60)
    print("📋 最终测评报告")
    print("=" * 60)
    print(json.dumps(final_report, ensure_ascii=False, indent=2))
    print("=" * 60)

    # 保存报告到文件
    save_report(final_report)


def save_report(report: dict) -> None:
    """保存报告到文件

    Args:
        report: 报告字典
    """
    reports_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "outputs",
        "reports",
    )
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.json"
    filepath = os.path.join(reports_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n💾 报告已保存至：{filepath}")


def main():
    # 关闭代理
    disable_proxy()

    print("=" * 60)
    print("  🤖 职业身份谎言指数测评系统（三 Agent 版）")
    print(f"   最大对话轮次：{MAX_ROUNDS}")
    print("   输入 'quit' 或 'exit' 退出")
    print("=" * 60)
    print()

    # 构建工作流
    app = build_graph()
    state: dict[str, Any] = create_initial_state()

    # 开场问题
    opening_question = state["last_followup_question"]
    print(f"系统：{opening_question}")

    # 多轮对话
    while state["round_id"] <= state["max_rounds"]:
        user_input = input("\n你：").strip()
        if not user_input:
            print("（输入为空，请重新输入）")
            continue
        if user_input.lower() in ("exit", "quit", "退出"):
            print("\n已退出对话。")
            break

        # 更新当前输入
        state["current_user_text"] = user_input
        # 清空本轮临时字段
        state["current_facts"] = []
        state["current_anomalies"] = []
        state["consistency_results"] = []

        print(f"\n--- 第 {state['round_id']} 轮 ---")

        # 运行工作流
        print("⏳ 系统思考中...")
        t_start = time.time()
        result = app.invoke(state)  # type: ignore[arg-type]
        t_end = time.time()
        elapsed = t_end - t_start

        # 更新状态
        state.update(result)

        # 显示本轮信息
        print(f"\n[抽取事实] {json.dumps(state.get('current_facts', []), ensure_ascii=False)}")
        print(f"[异常表达] {json.dumps(state.get('current_anomalies', []), ensure_ascii=False)}")
        print(f"[一致性判断] {json.dumps(state.get('consistency_results', []), ensure_ascii=False)}")
        print(f"[谎言指数] {state.get('lie_index', 0)} / 100")
        print(f"[风险等级] {state.get('risk_level', '低')}")
        print(f"[追问策略] {state.get('followup_strategy', '')}")
        print(f"[策略理由] {state.get('strategy_reason', '')}")
        print(f"⏱️  系统思考耗时：{elapsed:.2f} 秒")

        # 判断是否结束
        next_action = state.get("next_action", "")
        if next_action == "final_report":
            break

        # 显示追问
        question = state.get("last_followup_question", "")
        if question:
            print(f"\n系统：{question}")

        # 进入下一轮
        state["round_id"] += 1

    # 输出最终报告
    print_final_report(state)

    print(f"\n最终谎言指数：{state.get('lie_index', 0)} / 100")
    print(f"最终风险等级：{state.get('risk_level', '低')}")
    print("\n👋 感谢使用！")


if __name__ == "__main__":
    main()
