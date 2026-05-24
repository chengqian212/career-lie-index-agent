# v3 代码完成顺序与功能说明

## 第1层：项目配置与基础设施

| 序号 | 文件 | 功能 |
|:---:|------|------|
| 1 | `__init__.py` | 声明 v3 为 Python 包 |
| 2 | `.env` | 存放 API Key 等环境变量，不入库 |
| 3 | `config.py` | 读取环境变量，提供全局参数（模型名、温度、路由阈值等） |
| 4 | `llm_client.py` | 封装 ChatOpenAI 客户端，统一管理 LLM 实例的创建 |
| 5 | `state_schema.py` | 定义 LangGraph 全局状态 TypedDict，包含所有节点共享的字段 |
| 6 | `prompts.py` | 集中管理所有节点的 Prompt 模板字符串 |

## 第2层：工具模块

| 序号 | 文件 | 功能 |
|:---:|------|------|
| 7 | `utils/__init__.py` | 声明 utils 为 Python 包 |
| 8 | `utils/json_utils.py` | 从 LLM 输出文本中提取 JSON，支持代码块和嵌入格式 |
| 9 | `utils/text_utils.py` | 格式化对话历史、事实表、异常表，清理 LLM 输出噪音 |
| 10 | `utils/score_utils.py` | 计算谎言指数（加权聚合/动态归一化）和轻量风险分数 |

## 第3层：记忆模块

| 序号 | 文件 | 功能 |
|:---:|------|------|
| 11 | `memory/__init__.py` | 声明 memory 为 Python 包 |
| 12 | `memory/fact_table.py` | 管理对话中抽取的事实记录，支持增删查和摘要生成 |
| 13 | `memory/anomaly_table.py` | 管理发现的异常记录，支持状态更新和未解决异常统计 |

## 第4层：v3 新增轻量预分析节点

| 序号 | 文件 | 功能 |
|:---:|------|------|
| 14 | `nodes/quick_preanalysis_node.py` | 一次 LLM 调用同时完成事实抽取和表层异常检测（v3.2 合并） |
| 15 | `nodes/lightweight_routing_supervisor_node.py` | 根据预分析结果决定是否调用专家以及调用哪些专家 |
| 16 | `nodes/lightweight_risk_aggregator_node.py` | 不调用专家时，根据第一层结果计算低成本谎言指数 |

## 第5层：Specialist Agent 节点（按需并行执行）

| 序号 | 文件 | 功能 |
|:---:|------|------|
| 18 | `nodes/specialists/__init__.py` | 声明 specialists 为 Python 包 |
| 19 | `nodes/specialists/semantic_agent_node.py` | 分析职业身份、岗位、工作内容表述的语义一致性 |
| 20 | `nodes/specialists/logical_agent_node.py` | 分析职业叙述中的时间线、因果关系是否自洽 |
| 21 | `nodes/specialists/domain_agent_node.py` | 判断职业描述是否符合基本职业常识（不联网） |
| 22 | `nodes/specialists/psycho_linguistic_agent_node.py` | 识别文本中的软性风险信号（回避、模糊、过度解释） |

## 第6层：争议处理与聚合节点

| 序号 | 文件 | 功能 |
|:---:|------|------|
| 23 | `nodes/debate_gate_node.py` | 根据分数差异和专家数量判断是否触发 Debate |
| 24 | `nodes/debate_node.py` | 汇总各 Agent 分歧，输出结构化争议总结和调整建议 |
| 25 | `nodes/risk_aggregator_node.py` | 聚合各维度分数，计算综合谎言指数和风险等级 |

## 第7层：策略决策与输出节点

| 序号 | 文件 | 功能 |
|:---:|------|------|
| 26 | `nodes/strategy_supervisor_node.py` | 根据分析结果决定下一步是追问还是生成报告 |
| 27 | `nodes/followup_generation_node.py` | 生成一个自然的追问问题，聚焦优先风险点 |
| 28 | `nodes/report_generation_node.py` | 生成包含谎言指数和多维度分析的最终测评报告 |

## 第8层：图编排与入口

| 序号 | 文件 | 功能 |
|:---:|------|------|
| 29 | `nodes/__init__.py` | 声明 nodes 为 Python 包 |
| 30 | `graph.py` | 用 LangGraph 编排所有节点，构建并行分析和条件路由的工作流图 |
| 31 | `run_cli.py` | CLI 交互入口，管理多轮对话循环，展示每轮分析摘要和最终报告 |
