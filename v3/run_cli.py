"""CLI 入口：命令行交互式多 Agent 谎言指数测评系统

该模块实现了 v3 版本的 CLI 交互入口，主要特性包括：
- 命令行交互式对话界面
- 轻量预分析 + 条件路由 + 按需专家调用
- 实时显示分析过程和结果
- 支持中文输出（Windows UTF-8 编码）

v3.3 改进：
- 支持显示 stop_reason
"""

import json
import os
import sys
import time
from datetime import datetime

# Windows 终端 UTF-8 编码设置
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")  # 设置代码页为 UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

# 确保项目根目录在 sys.path 中，便于导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v3.config import (
    disable_proxy,
    MAX_ROUNDS,
)
from v3.graph import build_graph
from v3.state_schema import DialogueState
from v3.utils.logger import get_logger, reset_logger


def create_initial_state(max_rounds: int = MAX_ROUNDS) -> dict:
    """创建初始状态

    v3 改进：新增 v3 相关字段初始化，包括路由决策、专家选择等字段

    Args:
        max_rounds: 最大对话轮次，默认使用配置文件中的 MAX_ROUNDS

    Returns:
        初始状态字典，包含所有必需的状态字段
    """
    return {
        # 基础轮次控制
        "round_id": 0,                  # 当前轮次 ID
        "max_rounds": max_rounds,       # 最大轮次限制
        
        # 对话相关
        "current_user_text": "",        # 当前用户输入文本
        "dialogue_history": [],         # 完整对话历史
        
        # 事实提取与异常检测
        "current_facts": [],            # 当前提取的事实
        "facts_table": [],              # 事实表格（结构化）
        "current_anomalies": [],        # 当前检测到的异常
        "indicator_history": [],        # 异常指示器历史
        "consistency_results": [],      # 一致性检查结果
        "anomalies_table": [],          # 异常表格（结构化）
        
        # 追问机制
        "last_followup_question": "",   # 最近一次追问问题
        "followup_history": [],         # 追问历史
        
        # 专家分析结果
        "specialist_results": [],       # 各专家的分析结果
        "dimension_scores": {},         # 各维度得分
        "debate_needed": False,         # 是否需要辩论
        "debate_result": None,          # 辩论结果
        
        # 最终评估
        "lie_index": 0.0,               # 谎言指数（0-100）
        "risk_explanation": [],         # 风险解释列表
        "next_action": "",              # 下一步动作（路由决策）
        "final_report": None,           # 最终报告
        
        # v3 新增字段：轻量预分析相关
        "quick_fact_summary": "",       # 快速事实摘要
        "quick_signal_summary": "",     # 快速信号摘要
        "surface_risk_score": 0.0,      # 表层风险分数
        "has_new_fact": False,          # 是否有新的事实
        
        # v3 新增字段：路由决策相关
        "routing_decision": {},         # 路由决策详情
        "selected_specialists": [],     # 选中的专家列表
        "need_specialist": False,       # 是否需要调用专家
        "priority_issue": "",           # 优先关注的问题
        "followup_strategy": "",        # 追问策略
        "called_specialists": [],       # 实际调用的专家列表
    }


def print_round_summary(state: dict, elapsed: float = 0.0) -> None:
    """打印每轮分析摘要

    v3.3 改进：显示 stop_reason

    Args:
        state: 当前对话状态字典
        elapsed: 本轮系统思考耗时（秒），用于性能监控
    """
    # 获取基础信息
    round_id = state.get("round_id", 0)
    lie_index = state.get("lie_index", 0)
    dimension_scores = state.get("dimension_scores", {})
    debate_needed = state.get("debate_needed", False)
    risk_explanation = state.get("risk_explanation", [])
    followup = state.get("last_followup_question", "")
    
    # v3 新增字段
    called_specialists = state.get("called_specialists", [])
    need_specialist = state.get("need_specialist", False)
    routing_reason = state.get("routing_decision", {}).get("routing_reason", "")
    stop_reason = state.get("stop_reason", "")         # v3.3 新增

    print("\n" + "=" * 60)
    print(f"📊 当前轮次：{round_id} / {MAX_ROUNDS}")
    
    # v3: 显示本轮调用的专家
    if called_specialists:
        specialist_names = {
            "semantic": "语义分析",
            "logical": "逻辑分析",
            "domain": "职业常识",
            "psycho_linguistic": "心理语言",
        }
        called_names = [str(specialist_names.get(s) or s) for s in called_specialists]
        print(f"🤖 本轮调用专家：{', '.join(called_names)}")
    else:
        print(f"🤖 本轮调用专家：无，使用轻量预分析结果")
    
    print("-" * 60)
    print(f"📈 当前谎言指数：{lie_index} / 100")
    
    print("-" * 60)

    # 显示各维度分数
    if dimension_scores:
        print("📊 各维度分数：")
        score_names = {
            "semantic": "语义一致性",
            "logical": "逻辑时间线",
            "domain": "职业常识",
            "psycho_linguistic": "心理语言",
            "lightweight_surface": "表层风险",
            "unresolved_anomalies": "未澄清异常",
        }
        for key, score in dimension_scores.items():
            name = score_names.get(key) or key
            print(f"   {name}：{score}")

    print("-" * 60)
    print(f"💬 是否触发 Debate：{'是' if debate_needed else '否'}")

    # v3: 显示路由原因
    if routing_reason:
        print(f"🔍 路由原因：{routing_reason}")

    # v3.3: 显示停止/继续原因
    if stop_reason:
        reason_explanations = {
            "max_rounds": "已达最大轮次",
            "enough_information_no_active_anomaly": "信息充分且无活跃疑点",
            "anomaly_resolved": "疑点已被澄清",
            "followup_exhausted": "疑点追问次数已达上限",
            "anomaly_confirmed": "疑点已基本坐实",
            "need_more_information_or_clarification": "仍需继续追问",
        }
        reason_text = reason_explanations.get(stop_reason, stop_reason)
        print(f"🛑 决策原因：{reason_text}")

    # 显示风险原因
    if risk_explanation:
        print("⚠️  主要原因：")
        for exp in risk_explanation:
            print(f"   - {exp}")

    print("-" * 60)
    
    # 显示追问和耗时
    if followup:
        print(f"❓ 系统追问：{followup}")
    if elapsed > 0:
        print(f"⏱️  系统思考耗时：{elapsed:.2f} 秒")
    print("=" * 60)


def print_final_report(state: dict) -> None:
    """打印最终报告

    Args:
        state: 当前对话状态字典，需包含 final_report 字段
    """
    final_report = state.get("final_report")
    if not final_report:
        print("\n❌ 未生成最终报告")
        return

    print("\n" + "=" * 60)
    print("📋 最终测评报告")
    print("=" * 60)
    print(final_report.get("report_text", ""))
    print("=" * 60)

    # 保存报告到文件
    save_report(final_report)


def save_report(report: dict) -> None:
    """保存报告到文件

    将最终报告以 JSON 格式保存到 outputs/reports/ 目录下，
    文件名包含时间戳以便区分不同会话的报告

    Args:
        report: 报告字典，需包含 report_text 等字段
    """
    # 创建报告输出目录
    reports_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "outputs",
        "reports",
    )
    os.makedirs(reports_dir, exist_ok=True)

    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.json"
    filepath = os.path.join(reports_dir, filename)

    # 写入 JSON 文件
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n💾 报告已保存至：{filepath}")


def print_detailed_node_log(logger, round_id: int) -> None:
    """打印本轮每个节点的详细执行日志

    在终端中清晰展示每个节点的输入/输出/耗时/状态，
    方便用户了解系统内部每一步的分析过程。

    v3.3 新增：显示 stop_reason

    Args:
        logger: DetailedLogger 实例
        round_id: 当前轮次编号
    """
    # 优先从已归档的 session_data 中查找（end_round 后数据在这里）
    nodes = []
    for r in logger.session_data.get("rounds", []):
        if r.get("round_id") == round_id:
            nodes = r.get("nodes", [])
            break

    # 如果还没归档，从 current_round 中获取
    if not nodes and logger.current_round and logger.current_round.get("round_id") == round_id:
        nodes = logger.current_round.get("nodes", [])

    if not nodes:
        return

    # 节点名称映射（英文名 → 中文名）
    node_name_map = {
        "quick_preanalysis_node": "快速预分析",
        "lightweight_routing_supervisor_node": "轻量路由监督",
        "lightweight_risk_aggregator_node": "轻量风险聚合",
        "semantic_agent_node": "语义一致性分析",
        "logical_agent_node": "逻辑时间线分析",
        "domain_agent_node": "职业常识分析",
        "psycho_linguistic_agent_node": "心理语言学分析",
        "debate_gate_node": "辩论门控",
        "debate_node": "专家辩论",
        "risk_aggregator_node": "风险聚合",
        "strategy_supervisor_node": "策略监督",
        "followup_generation_node": "追问生成",
        "report_generation_node": "报告生成",
    }

    print("\n" + "┌" + "─" * 58 + "┐")
    print(f"│ 📝 轮次 {round_id} 详细节点执行日志{' ' * (58 - 17 - len(str(round_id)))}│")
    print("├" + "─" * 58 + "┤")

    for i, node in enumerate(nodes):
        name = node["node_name"]
        cn_name = str(node_name_map.get(name) or name)
        elapsed = node["elapsed_seconds"]
        success = node["success"]
        status_icon = "✅" if success else "❌"
        output = node.get("output", {})

        # 节点标题行
        print(f"│ {status_icon} [{i+1}] {cn_name} ({name})")
        print(f"│     耗时: {elapsed:.3f}s")

        if node.get("error"):
            print(f"│     ❗ 错误: {node['error']}")

        # ---- 格式化输出关键信息 ----
        # 路由监督相关
        if "need_specialist" in output:
            print(f"│     需要专家: {'是' if output['need_specialist'] else '否'}")

        # 快速预分析相关
        if "quick_fact_summary" in output and output["quick_fact_summary"]:
            summary = output["quick_fact_summary"]
            if len(summary) > 80:
                summary = summary[:77] + "..."
            print(f"│     事实摘要: {summary}")
        if "quick_signal_summary" in output and output["quick_signal_summary"]:
            summary = output["quick_signal_summary"]
            if len(summary) > 80:
                summary = summary[:77] + "..."
            print(f"│     信号摘要: {summary}")
        if "surface_risk_score" in output:
            print(f"│     表面风险分: {output['surface_risk_score']}")

        # 专家分析结果
        if "specialist_results" in output:
            results = output.get("specialist_results", [])
            for r in results:
                if isinstance(r, dict):
                    agent = r.get("agent", "?")
                    score = r.get("score", 0)
                    cn_agent = str({"semantic": "语义", "logical": "逻辑", "domain": "领域", "psycho_linguistic": "心理语言"}.get(agent) or agent)
                    print(f"│     [{cn_agent}] 分数:{score}")
                    # 显示关键发现
                    findings = r.get("findings", [])
                    if isinstance(findings, list):
                        for f in findings[:3]:  # 最多显示3条
                            if isinstance(f, dict):
                                desc = f.get("description", f.get("finding", str(f)))
                                if len(desc) > 60:
                                    desc = desc[:57] + "..."
                                print(f"│       → {desc}")
                            elif isinstance(f, str):
                                if len(f) > 60:
                                    f = f[:57] + "..."
                                print(f"│       → {f}")

        # 调用专家记录
        if "called_specialists" in output:
            called = output.get("called_specialists", [])
            if called:
                spec_names = {"semantic": "语义", "logical": "逻辑", "domain": "领域", "psycho_linguistic": "心理语言"}
                names = [str(spec_names.get(s) or s) for s in called]
                print(f"│     已调用专家: {', '.join(names)}")

        # 辩论相关
        if "debate_needed" in output:
            print(f"│     触发辩论: {'是' if output['debate_needed'] else '否'}")
        if "debate_result" in output and output["debate_result"]:
            debate = output["debate_result"]
            if isinstance(debate, dict):
                if debate.get("main_disagreement"):
                    dis = debate["main_disagreement"]
                    if len(dis) > 60:
                        dis = dis[:57] + "..."
                    print(f"│     主要分歧: {dis}")
                if debate.get("consensus"):
                    con = debate["consensus"]
                    if len(con) > 60:
                        con = con[:57] + "..."
                    print(f"│     共识: {con}")
                adj = debate.get("debate_adjustment", {})
                if adj:
                    parts = []
                    for k, v in adj.items():
                        if v != 0:
                            cn = str({"semantic": "语义", "logical": "逻辑", "domain": "领域", "psycho_linguistic": "心理语言"}.get(k) or k)
                            parts.append(f"{cn}:{'+' if v > 0 else ''}{v}")
                    if parts:
                        print(f"│     分数调整: {', '.join(parts)}")

        # 风险聚合相关
        if "lie_index" in output:
            print(f"│     谎言指数: {output['lie_index']}")
        if "dimension_scores" in output and output["dimension_scores"]:
            scores = output["dimension_scores"]
            score_names = {"semantic": "语义", "logical": "逻辑", "domain": "领域", "psycho_linguistic": "心理语言"}
            parts = []
            for k, v in scores.items():
                if v is not None:
                    parts.append(f"{str(score_names.get(k) or k)}:{v}")
            if parts:
                print(f"│     维度分数: {', '.join(parts)}")
        if "risk_explanation" in output and output["risk_explanation"]:
            for exp in output["risk_explanation"][:3]:
                if len(exp) > 55:
                    exp = exp[:52] + "..."
                print(f"│     ⚠ {exp}")

        # 策略监督相关
        if "stop_reason" in output:
            reason_text = output["stop_reason"]
            reason_explanations = {
                "max_rounds": "已达最大轮次",
                "enough_information_no_active_anomaly": "信息充分且无活跃疑点",
                "anomaly_resolved": "疑点已被澄清",
                "followup_exhausted": "疑点追问次数已达上限",
                "anomaly_confirmed": "疑点已基本坐实",
                "need_more_information_or_clarification": "仍需继续追问",
            }
            reason_display = reason_explanations.get(reason_text, reason_text)
            print(f"│     决策原因: {reason_display}")

        if "next_action" in output:
            action_map = {"final_report": "生成报告", "generate_followup": "继续追问"}
            print(f"│     下一步: {str(action_map.get(output['next_action']) or output['next_action'])}")

        # 追问生成相关
        if "last_followup_question" in output and output["last_followup_question"]:
            q = output["last_followup_question"]
            if len(q) > 55:
                q = q[:52] + "..."
            print(f"│     追问: {q}")

        # 报告生成相关
        if "final_report" in output and output["final_report"]:
            report = output["final_report"]
            if isinstance(report, dict):
                text = report.get("report_text", "")
                if text and len(text) > 55:
                    text = text[:52] + "..."
                if text:
                    print(f"│     报告: {text}")

        # 节点之间的分隔
        if i < len(nodes) - 1:
            print("│")

    print("└" + "─" * 58 + "┘")


def run_cli():
    """主 CLI 交互循环

    实现与用户的交互对话：
    1. 初始化系统状态和图结构
    2. 系统提出开场问题
    3. 循环接收用户输入并调用图进行分析
    4. 显示每轮分析结果
    5. 达到最大轮次或检测到完成信号时生成最终报告
    6. 每轮结束后保存详细日志（JSON + Markdown）
    """
    # 关闭代理（避免网络请求失败）
    disable_proxy()

    # 初始化日志记录器
    reset_logger()
    logger = get_logger()

    # 打印欢迎信息
    print("🤖 多 Agent 谎言指数测评系统 v3.3")
    print(f"   最大对话轮次：{MAX_ROUNDS}")
    print("   输入 'quit' 退出，输入 'skip' 跳过当前轮次")
    print("   v3.3 特性：智能状态驱动决策，信息够了就停")
    print("   📝 详细日志将在每轮结束后自动保存")
    print()

    # 构建工作流图
    graph = build_graph()

    # 初始化对话状态
    state = create_initial_state()

    # 第一轮系统开场白
    opening_question = "你平时是做什么方向的工作呀？"
    print(f"系统：{opening_question}")
    state["last_followup_question"] = opening_question
    state["dialogue_history"].append({
        "role": "assistant",
        "content": opening_question,
    })

    # 主循环：逐轮处理用户输入
    for round_num in range(1, MAX_ROUNDS + 1):
        state["round_id"] = round_num
        # 每轮清空专家结果和调用记录
        state["specialist_results"] = []
        state["called_specialists"] = []

        # 获取用户输入
        user_input = input("\n用户：").strip()

        # 处理退出命令
        if user_input.lower() == "quit":
            print("退出系统。")
            break

        # 处理跳过命令或空输入
        if user_input.lower() == "skip" or not user_input:
            print("（跳过本轮）")
            continue

        # 更新状态：保存用户输入
        state["current_user_text"] = user_input
        state["dialogue_history"].append({
            "role": "user",
            "content": user_input,
        })

        # 开始本轮日志记录
        logger.start_round(round_num, user_input)

        # 运行工作流图进行分析
        try:
            print("⏳ 系统思考中...")
            t_start = time.time()
            result = graph.invoke(state)  # 调用图进行状态转换
            t_end = time.time()
            elapsed = t_end - t_start

            # 更新状态（保留完整结果）
            state.update(result)

            # 结束本轮日志记录
            logger.end_round()

            # 打印本轮分析摘要
            print_round_summary(state, elapsed)

            # 打印本轮详细节点日志
            print_detailed_node_log(logger, round_num)

            # 将追问加入对话历史（如果是普通追问而非最终报告）
            followup = state.get("last_followup_question", "")
            if followup and state.get("next_action") != "final_report":
                state["dialogue_history"].append({
                    "role": "assistant",
                    "content": followup,
                })

            # 检查是否已生成最终报告
            if state.get("next_action") == "final_report":
                print_final_report(state)
                break

        except Exception as e:
            # 即使出错也结束本轮日志
            logger.end_round()
            print(f"\n❌ 运行出错：{e}")
            import traceback
            traceback.print_exc()
            continue

    else:
        # 达到最大轮次但最后一轮走的是 followup，需额外生成报告
        print("\n🔄 已达到最大轮次，正在生成最终报告...")
        state["round_id"] = MAX_ROUNDS
        state["specialist_results"] = []
        state["called_specialists"] = []
        state["next_action"] = "final_report"

        logger.start_round(MAX_ROUNDS + 1, "（自动生成最终报告）")

        try:
            t_start = time.time()
            result = graph.invoke(state)
            t_end = time.time()
            elapsed = t_end - t_start
            state.update(result)

            logger.end_round()

            print(f"⏱️  报告生成耗时：{elapsed:.2f} 秒")
            print_final_report(state)
        except Exception as e:
            logger.end_round()
            print(f"\n❌ 生成报告出错：{e}")
            import traceback
            traceback.print_exc()

    # 保存会话日志
    try:
        log_path = logger.finalize_session(state)
        print(f"\n📝 详细日志已保存至：{log_path}")
        md_path = log_path[:-5] + ".md" if log_path.endswith(".json") else log_path + ".md"
        print(f"📄 可读报告已保存至：{md_path}")
    except Exception as e:
        print(f"\n⚠️  日志保存失败：{e}")

    # 程序结束提示
    print("\n👋 感谢使用！")


if __name__ == "__main__":
    # 作为脚本直接运行时执行 CLI
    run_cli()
