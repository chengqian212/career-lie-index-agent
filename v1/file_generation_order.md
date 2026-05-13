# 项目文件生成顺序

1. `config.py` — 保存 API 密钥、模型名、谎言指数权重、风险等级阈值等全局配置
2. `utils/env_utils.py` — 实现 disable_proxy()，清除代理环境变量
3. `llm_client.py` — 封装阿里云百炼 DeepSeek-V4-Pro 调用，支持纯文本和 JSON 两种返回
4. `state_schema.py` — 定义 DialogueState 全局状态，标注各字段的 reducer（覆盖或追加）
5. `prompts.py` — 保存 5 个节点的 Prompt 模板
6. `utils/json_utils.py` — 从 LLM 响应中解析 JSON，兼容代码块和裸 JSON
7. `nodes/fact_extraction_node.py` — 从用户回答中抽取职业身份相关事实
8. `nodes/anomaly_detection_node.py` — 识别当前回答中的异常表达
9. `nodes/consistency_judge_node.py` — 将当前事实与历史事实比对，判断一致性关系
10. `nodes/state_update_node.py` — 更新事实表、异常表、对话历史，计算谎言指数和风险等级
11. `nodes/followup_generation_node.py` — 生成下一轮自然追问
12. `nodes/report_generation_node.py` — 生成最终谎言指数测评报告
13. `graph.py` — 用 LangGraph 定义节点、边和路由逻辑，编译为可执行工作流
14. `run_cli.py` — 命令行多轮对话入口，启动时关闭代理，循环调用工作流
15. `utils/text_utils.py` — 提供文本截断等工具函数
16. `memory/fact_table.py` — 事实表查询操作（按 slot、按 id 查找）
17. `memory/anomaly_table.py` — 异常表操作（查找未澄清、标记已澄清）
