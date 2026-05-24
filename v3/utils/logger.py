"""详细日志模块：记录每轮分析的所有节点执行结果"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from typing import get_type_hints


class DetailedLogger:
    """详细日志记录器
    
    记录每轮对话中每个节点的执行过程和结果，
    包括输入、输出、耗时等信息。
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """初始化日志记录器
        
        Args:
            log_dir: 日志存储目录，默认为 v3/outputs/logs
        """
        if log_dir is None:
            # 默认日志目录
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(base_dir, "outputs", "logs")
        
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # 当前会话的日志数据
        self.session_data = {
            "session_start_time": datetime.now().isoformat(),
            "rounds": [],
        }
        
        # 当前轮次的日志
        self.current_round: Optional[Dict] = None
        self.current_round_id: int = 0
    
    def start_round(self, round_id: int, user_input: str):
        """开始新轮次的日志记录
        
        Args:
            round_id: 轮次编号
            user_input: 用户输入文本
        """
        self.current_round_id = round_id
        self.current_round = {
            "round_id": round_id,
            "start_time": datetime.now().isoformat(),
            "user_input": user_input,
            "nodes": [],
            "end_time": None,
            "total_elapsed_seconds": 0,
        }
    
    def log_node(
        self,
        node_name: str,
        input_state: Dict,
        output_updates: Dict,
        elapsed_seconds: float,
        error: Optional[str] = None,
    ):
        """记录节点执行信息
        
        Args:
            node_name: 节点名称
            input_state: 节点输入状态（选择性记录关键字段）
            output_updates: 节点输出更新
            elapsed_seconds: 执行耗时（秒）
            error: 错误信息（如果有）
        """
        if self.current_round is None:
            return
        
        # 只记录关键字段，避免日志过大
        input_snapshot = self._snapshot_state(input_state)
        output_snapshot = self._snapshot_state(output_updates)
        
        node_log = {
            "node_name": node_name,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "input": input_snapshot,
            "output": output_snapshot,
            "success": error is None,
        }
        
        if error:
            node_log["error"] = error
        
        self.current_round["nodes"].append(node_log)
    
    def end_round(self):
        """结束当前轮次的日志记录"""
        if self.current_round is None:
            return
        
        self.current_round["end_time"] = datetime.now().isoformat()
        
        # 计算总耗时
        start = datetime.fromisoformat(self.current_round["start_time"])
        end = datetime.fromisoformat(self.current_round["end_time"])
        self.current_round["total_elapsed_seconds"] = round(
            (end - start).total_seconds(), 3
        )
        
        # 添加到会话数据
        self.session_data["rounds"].append(self.current_round)
        self.current_round = None
    
    def finalize_session(self, final_state: Dict):
        """完成会话日志记录
        
        Args:
            final_state: 最终的对话状态
        """
        self.session_data["session_end_time"] = datetime.now().isoformat()
        self.session_data["final_state_snapshot"] = self._snapshot_state(final_state)
        
        # 保存日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"session_{timestamp}.json"
        log_filepath = os.path.join(self.log_dir, log_filename)
        
        with open(log_filepath, "w", encoding="utf-8") as f:
            json.dump(self.session_data, f, ensure_ascii=False, indent=2)
        
        # 生成可读的 Markdown 报告
        self._generate_markdown_report(log_filepath)
        
        return log_filepath
    
    def _snapshot_state(self, state: Dict) -> Dict:
        """创建状态快照，只保留关键字段
        
        Args:
            state: 完整的状态字典
        Returns:
            精简的状态快照
        """
        # 定义需要记录的字段
        tracked_fields = [
            # 基础字段
            "round_id",
            "max_rounds",
            "current_user_text",
            "last_followup_question",
            "next_action",
            
            # 核心结果字段
            "lie_index",
            "risk_explanation",
            "dimension_scores",
            
            # v3 路由字段
            "selected_specialists",
            "called_specialists",
            "need_specialist",
            "priority_issue",
            "followup_strategy",
            
            # 摘要字段
            "quick_fact_summary",
            "quick_signal_summary",
            "surface_risk_score",
            "has_new_fact",
            
            # 特殊处理：对话历史（只记录最近几条）
            "dialogue_history",
            
            # 特殊处理：专家结果
            "specialist_results",
            
            # 特殊处理：表数据
            "facts_table",
            "anomalies_table",
            "anomalies",
            
            # 辩论相关
            "debate_needed",
            "debate_result",
        ]
        
        snapshot = {}
        
        for field in tracked_fields:
            if field not in state:
                continue
                
            value = state[field]
            
            # 特殊处理对话历史
            if field == "dialogue_history":
                if isinstance(value, list):
                    # 只记录最近 5 条
                    snapshot[field] = value[-5:] if len(value) > 5 else value
                    snapshot[f"{field}_count"] = len(value)
                else:
                    snapshot[field] = value
                continue
            
            # 特殊处理专家结果
            if field == "specialist_results":
                if isinstance(value, list):
                    snapshot[field] = value
                    snapshot[f"{field}_count"] = len(value)
                else:
                    snapshot[field] = value
                continue
            
            # 特殊处理表数据（只记录数量）
            if field in ("facts_table", "anomalies_table", "anomalies"):
                if isinstance(value, list):
                    snapshot[f"{field}_count"] = len(value)
                    # 记录最近几条作为示例
                    if len(value) > 0:
                        snapshot[f"{field}_recent"] = value[-3:] if len(value) > 3 else value
                else:
                    snapshot[field] = value
                continue
            
            # 普通字段直接记录
            snapshot[field] = value
        
        return snapshot
    
    def _generate_markdown_report(self, json_log_path: str):
        """生成可读的 Markdown 报告
        
        Args:
            json_log_path: JSON 日志文件路径
        """
        # 替换扩展名
        md_path = json_log_path[:-5] + ".md" if json_log_path.endswith(".json") else json_log_path + ".md"
        
        lines = []
        lines.append("# 📊 会话详细日志报告")
        lines.append("")
        lines.append(f"**会话开始时间**: {self.session_data['session_start_time']}")
        lines.append(f"**会话结束时间**: {self.session_data.get('session_end_time', '进行中')}")
        lines.append(f"**总轮次数**: {len(self.session_data['rounds'])}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 逐轮记录
        for round_data in self.session_data["rounds"]:
            lines.append(f"## 🔄 轮次 {round_data['round_id']}")
            lines.append("")
            lines.append(f"**用户输入**: `{round_data['user_input']}`")
            lines.append(f"**开始时间**: {round_data['start_time']}")
            lines.append(f"**结束时间**: {round_data['end_time']}")
            lines.append(f"**总耗时**: {round_data['total_elapsed_seconds']} 秒")
            lines.append("")
            
            # 记录每个节点
            for node in round_data["nodes"]:
                lines.append(f"### 🔹 节点: {node['node_name']}")
                lines.append("")
                lines.append(f"- **耗时**: {node['elapsed_seconds']} 秒")
                lines.append(f"- **状态**: {'✅ 成功' if node['success'] else '❌ 失败'}")
                
                if node.get("error"):
                    lines.append(f"- **错误**: {node['error']}")
                
                # 记录关键输出
                if node["output"]:
                    lines.append("")
                    lines.append("**关键输出**:")
                    lines.append("")
                    lines.append("```")
                    lines.append(self._format_output(node["output"]))
                    lines.append("```")
                
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # 最终状态摘要
        if "final_state_snapshot" in self.session_data:
            lines.append("## 📋 最终状态摘要")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(
                self.session_data["final_state_snapshot"],
                ensure_ascii=False,
                indent=2
            ))
            lines.append("```")
            lines.append("")
        
        # 写入文件
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    
    def _format_output(self, output: Dict) -> str:
        """格式化输出为可读文本
        
        Args:
            output: 输出字典
        Returns:
            格式化的字符串
        """
        lines = []
        
        # 优先显示关键字段
        priority_fields = [
            ("lie_index", "谎言指数"),
            ("dimension_scores", "维度分数"),
            ("called_specialists", "调用专家"),
            ("selected_specialists", "选中专家"),
            ("need_specialist", "需要专家"),
            ("debate_needed", "需要辩论"),
            ("last_followup_question", "追问问题"),
            ("next_action", "下一步动作"),
            ("followup_strategy", "追问策略"),
            ("priority_issue", "优先问题"),
            ("quick_fact_summary", "事实摘要"),
            ("quick_signal_summary", "信号摘要"),
            ("surface_risk_score", "表面风险分"),
            ("has_new_fact", "是否有新事实"),
            ("risk_explanation", "风险解释"),
        ]
        
        for field, name in priority_fields:
            if field in output:
                value = output[field]
                lines.append(f"{name}: {value}")
        
        # 显示专家结果
        if "specialist_results" in output:
            lines.append("")
            lines.append("专家分析结果:")
            for result in output["specialist_results"]:
                if isinstance(result, dict):
                    agent = result.get("agent", "unknown")
                    score = result.get("score", 0)
                    lines.append(f"  - [{agent}] 分数: {score}")
        
        # 显示辩论结果
        if "debate_result" in output:
            debate = output["debate_result"]
            if isinstance(debate, dict):
                lines.append("")
                lines.append("辩论结果:")
                lines.append(f"  - 触发原因: {debate.get('debate_trigger', '')}")
                lines.append(f"  - 主要分歧: {debate.get('main_disagreement', '')}")
                lines.append(f"  - 共识: {debate.get('consensus', '')}")
        
        return "\n".join(lines)


# 全局日志实例
_logger_instance: Optional[DetailedLogger] = None


def get_logger() -> DetailedLogger:
    """获取全局日志实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = DetailedLogger()
    return _logger_instance


def reset_logger():
    """重置全局日志实例（用于新会话）"""
    global _logger_instance
    _logger_instance = None