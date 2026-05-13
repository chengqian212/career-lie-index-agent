# 第二版项目规划书：基于多 Agent 协同的谎言指数测评系统

## 0. 项目名称

**基于 LangGraph 的多 Agent 谎言指数测评系统**

本规划书面向写代码的 Agent 使用。目标是让代码 Agent 能直接据此生成可运行代码。

---

## 1. 第二版目标

第一版已经实现了有状态工作流：

```text
用户回答
→ 事实抽取
→ 异常表达识别
→ 历史事实比对
→ 状态更新
→ 自然追问
→ 最终报告
```

第二版在第一版基础上升级，不推倒重写。

第二版目标是：在已有事实表、异常表、追问机制的基础上，引入**多 Agent 并行分析与轻量争议讨论机制**，让系统从多个维度对同一轮回答进行分析，最终生成更加可解释的**谎言指数**。

系统仍然只做：

```text
对话内部职业身份叙述的谎言指数测评
```

不做外部身份验证，不联网核查个人信息，不输出“对方一定在说谎”。

最终输出：

```text
1. 当前谎言指数：0-100
2. 各维度分数
3. 关键风险证据
4. 多 Agent 分析结果
5. 是否存在待澄清线索
6. 下一轮自然追问
7. 最终测评报告
```

---

## 2. 第二版核心思路

第二版采用：

```text
Hierarchical + Role-based + Static Multi-Agent Workflow
```

中文表述为：

```text
基于层级式角色分工的静态多 Agent 工作流
```

含义如下：

### 2.1 Hierarchical：层级式结构

系统分为三层：

```text
上层：Strategy Supervisor
中层：Specialist Agents
下层：State / Risk / Report 工具节点
```

### 2.2 Role-based：角色分工

每个 Agent 有固定职责，不自由乱聊：

```text
Semantic Agent：语义一致性分析
Logical Agent：逻辑与时间线分析
Domain Agent：职业常识分析
Psycho-Linguistic Agent：心理语言学线索分析
Debate Agent：仅在争议时触发
Strategy Supervisor：综合策略决策
```

### 2.3 Static：静态工作流

流程提前写死，不让 Agent 自由决定随意调用工具。用 LangGraph 的 `StateGraph`、`conditional edges`、`Send` 或等价 fan-out 方式实现。

---

## 3. 技术栈要求

### 3.1 必选

```text
Python 3.10+
LangGraph 最新稳定版
LangChain Core 最新稳定版
langchain-openai 或 OpenAI-compatible 客户端
阿里云百炼 DeepSeek-V4-Pro
python-dotenv
pydantic
```

### 3.2 不使用

```text
不使用已弃用的 LangChain AgentExecutor / initialize_agent 作为核心架构
不使用旧版 Chain 风格写法作为主流程
不使用 Streamlit
不使用向量数据库
不使用外部搜索
不使用 Redis / Postgres
不做模型微调
```

### 3.3 LangGraph 实现策略

优先使用 LangGraph 当前推荐的 Graph API：

```text
StateGraph
START / END
TypedDict 或 Pydantic state
conditional_edges
Send / fan-out 并行节点
Reducer 合并并行结果
checkpointer 可选，用于多轮持久化
```

如 LangGraph 当前版本提供 `Command` 并适合当前代码风格，可以用于“状态更新 + 路由”合并；否则使用 `add_conditional_edges` 即可。

---

## 4. 环境配置要求

### 4.1 `.env` 示例

```env
DASHSCOPE_API_KEY=你的阿里云百炼API_KEY
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=deepseek-v4-pro
MAX_ROUNDS=5
TEMPERATURE=0.2
```

### 4.2 必须关闭代理

在 `config.py` 或 `run_cli.py` 启动时加入：

```python
import os

def disable_proxy():
    for key in [
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ]:
        os.environ.pop(key, None)

disable_proxy()
```

要求：程序启动时默认关闭系统代理，避免 API 调用被本地代理影响。

---

## 5. 第二版总体流程

```text
用户输入
   ↓
第一版基础节点：
   ├── fact_extraction_node
   ├── anomaly_detection_node
   ├── consistency_judge_node
   └── state_update_node
   ↓
第二版新增：Parallel Specialist Analysis Layer
   ├── semantic_agent_node
   ├── logical_agent_node
   ├── domain_agent_node
   └── psycho_linguistic_agent_node
   ↓
debate_gate_node
   ├── 若存在明显分歧 / 潜在不匹配 / 低置信度 → debate_node
   └── 否则 → risk_aggregator_node
   ↓
risk_aggregator_node
   ↓
strategy_supervisor_node
   ↓
route_node
   ├── followup_generation_node
   └── final_report_node
```

第一版节点可以复用，不要重写。

---

## 6. State 设计

建议在第一版 `DialogueState` 基础上新增字段。

```python
from typing import TypedDict, List, Dict, Optional, Annotated
import operator

class DialogueState(TypedDict):
    # 基础对话状态
    round_id: int
    max_rounds: int
    current_user_text: str
    dialogue_history: List[Dict]

    # 第一版已有字段
    current_facts: List[Dict]
    facts_table: List[Dict]
    current_anomalies: List[Dict]
    indicator_history: List[Dict]
    consistency_results: List[Dict]
    anomalies_table: List[Dict]
    last_followup_question: str
    followup_history: List[Dict]

    # 第二版新增字段
    specialist_results: Annotated[List[Dict], operator.add]
    dimension_scores: Dict[str, float]
    agent_votes: Dict[str, Dict]
    debate_needed: bool
    debate_result: Optional[Dict]

    # 谎言指数相关
    lie_index: float
    risk_level: str
    risk_explanation: List[str]

    # 路由
    next_action: str
    final_report: Optional[Dict]
```

### 注意

并行节点如果都写入 `specialist_results`，必须使用 reducer 合并，避免并行更新冲突。

---

## 7. 新增 Specialist Agent 设计

第二版新增 4 个并行分析 Agent。

所有 Agent 必须遵守：

```text
1. 只根据当前对话和已有状态判断
2. 必须引用具体轮次和原文 evidence
3. 不允许直接判定“用户说谎”
4. 输出结构化 JSON
5. 输出 score: 0-100
6. 输出 confidence: low / medium / high
```

---

### 7.1 Semantic Agent：语义一致性分析

文件：

```text
nodes/specialists/semantic_agent_node.py
```

职责：判断用户职业身份、岗位、工作内容等表述在语义上是否一致。

关注点：

```text
1. 同一职业身份是否反复变化
2. 岗位名称和工作内容是否语义匹配
3. 是否出现职业包装或概念偷换
4. 当前回答是否改变了前文的职业叙述
```

输入：

```text
dialogue_history
facts_table
current_facts
consistency_results
```

输出：

```json
{
  "agent": "semantic",
  "score": 0,
  "confidence": "medium",
  "findings": [
    {
      "type": "semantic_mismatch",
      "evidence": ["第1轮：...", "第3轮：..."],
      "explanation": "..."
    }
  ],
  "vote": "low_risk | medium_risk | high_risk"
}
```

---

### 7.2 Logical Agent：逻辑与时间线分析

文件：

```text
nodes/specialists/logical_agent_node.py
```

职责：判断职业叙述中的时间、因果、职业路径是否自洽。

关注点：

```text
1. 当前职业和过去经历的时间阶段是否清楚
2. 时间线是否冲突
3. 因果关系是否合理
4. 追问后的解释是否能闭合原异常
```

示例：

```text
“现在做投行 IPO” 与 “之前银行实习卖理财”不一定冲突；
但 “现在主要做 IPO” 与 “现在主要卖理财产品”可能存在不匹配。
```

输出格式同上，agent 字段为 `"logical"`。

---

### 7.3 Domain Agent：职业常识分析

文件：

```text
nodes/specialists/domain_agent_node.py
```

职责：判断用户对职业内容的描述是否符合基本职业常识。

第一版增强不联网，只使用大模型已有常识。

关注点：

```text
1. 声称的职业身份与工作内容是否大体匹配
2. 岗位职责描述是否明显偏离常识
3. 是否存在“行业相近但岗位差异大”的情况
4. 是否需要进一步追问职业细节
```

不要做外部搜索。不要判断某个人是否真的在某公司工作。

输出格式同上，agent 字段为 `"domain"`。

---

### 7.4 Psycho-Linguistic Agent：心理语言学线索分析

文件：

```text
nodes/specialists/psycho_linguistic_agent_node.py
```

职责：识别文本中的软性风险信号。

关注点：

```text
1. 细节缺失
2. 明显回避
3. 答非所问
4. 表达模糊
5. 过度解释
6. 频繁自我修正
```

注意：心理语言学线索只是辅助信号，不能单独造成高风险结论。

输出格式同上，agent 字段为 `"psycho_linguistic"`。

---

## 8. Debate 机制

### 8.1 触发条件

新增：

```text
nodes/debate_gate_node.py
```

如果满足任一条件，触发 Debate：

```text
1. 任一 Specialist Agent 的 score >= 75
2. Specialist Agent 分数最大差值 >= 40
3. Semantic / Logical / Domain 中任一输出 high_risk，而另一个输出 low_risk
4. consistency_results 中存在“潜在不匹配”或“无法判断”
5. 任一关键 Agent confidence 为 low 且存在 unresolved anomaly
```

否则不触发 Debate。

---

### 8.2 Debate Node

文件：

```text
nodes/debate_node.py
```

Debate 不做长篇自由辩论，只做结构化争议汇总。

输入：

```text
specialist_results
consistency_results
anomalies_table
facts_table
```

输出：

```json
{
  "debate_trigger": "semantic_logical_disagreement",
  "main_disagreement": "Semantic Agent 认为职业内容不匹配，Logical Agent 认为可能是不同时间阶段。",
  "skeptic_view": "存在职业包装风险，因为当前工作内容描述发生变化。",
  "explainer_view": "存在合理解释空间，因为用户提到的理财经历可能属于过去阶段。",
  "consensus": "应标记为可澄清风险，并通过自然追问确认时间阶段。",
  "recommended_followup_focus": "time_stage_clarification",
  "debate_adjustment": {
    "semantic": 5,
    "logical": -5,
    "domain": 0,
    "psycho_linguistic": 0
  }
}
```

要求：

```text
1. 只输出结构化 JSON
2. 不输出完整思维链
3. 必须说明争议点和最终共识
4. 结果用于调整维度分数和追问策略
```

---

## 9. Risk Aggregator：谎言指数计算

文件：

```text
nodes/risk_aggregator_node.py
```

职责：根据 4 个 Specialist Agent 的分数、Debate 结果、未澄清异常数量，计算 `lie_index`。

建议权重：

```python
lie_index = (
    0.30 * semantic_score +
    0.25 * logical_score +
    0.20 * domain_score +
    0.15 * psycho_linguistic_score +
    0.10 * unresolved_followup_score
)
```

### unresolved_followup_score

```python
unresolved_followup_score = min(100, unresolved_count * 20)
```

### Debate 调整

如果有 `debate_adjustment`，则先调整各维度分数，再计算总分。

### 风险等级

```text
0-30：低
31-60：中
61-100：高
```

输出：

```json
{
  "lie_index": 58.0,
  "risk_level": "中",
  "dimension_scores": {
    "semantic": 65,
    "logical": 50,
    "domain": 60,
    "psycho_linguistic": 45,
    "unresolved_followup": 40
  },
  "risk_explanation": [
    "职业内容存在潜在不匹配",
    "当前回答细节较模糊",
    "仍有1个待澄清异常"
  ]
}
```

---

## 10. Strategy Supervisor

文件：

```text
nodes/strategy_supervisor_node.py
```

职责：根据多 Agent 分析结果、谎言指数、当前轮次和异常表，决定下一步策略。

注意：

```text
Supervisor 不重新抽取事实。
Supervisor 不重新判断所有矛盾。
Supervisor 只做策略决策。
```

输入：

```text
lie_index
risk_level
dimension_scores
specialist_results
debate_result
anomalies_table
round_id
max_rounds
```

输出：

```json
{
  "next_action": "generate_followup | final_report",
  "priority_issue": "职业内容潜在不匹配",
  "followup_strategy": "time_stage_clarification",
  "reason_summary": "本轮语义和领域常识维度均提示职业内容存在待澄清点，且异常尚未解决。",
  "target_evidence": [
    "第1轮：...",
    "第3轮：..."
  ]
}
```

路由规则：

```text
如果 round_id >= max_rounds → final_report
否则如果 lie_index >= 30 或存在 unresolved anomaly → generate_followup
否则 → generate_followup
```

第一版为了保持 5 轮对话，未到 max_rounds 时默认继续生成追问。

---

## 11. Follow-up Generator 改造

复用第一版：

```text
nodes/followup_generation_node.py
```

第二版新增输入：

```text
priority_issue
followup_strategy
dimension_scores
debate_result
```

生成问题要求：

```text
1. 只生成一个问题
2. 语气自然，像正常聊天中的好奇
3. 不能使用“谎言”“矛盾”“审查”“核验”等词
4. 优先围绕 priority_issue 追问
5. 如果 debate_result 存在，则优先围绕 consensus 指出的澄清方向追问
```

示例：

```text
你刚才提到现在主要做 IPO 项目，后面又说之前也接触过理财产品。我有点好奇，这两部分是不同阶段的经历，还是现在工作里都会涉及呀？
```

---

## 12. Final Report 改造

复用第一版：

```text
nodes/report_generation_node.py
```

第二版报告新增：

```text
1. 总谎言指数
2. 各维度分数
3. 各 Specialist Agent 的主要发现
4. Debate 结论，如果有
5. 关键证据链
6. 待澄清问题
7. 风险等级
8. 后续建议
```

报告措辞要求：

```text
不要说“对方说谎”
要说“当前职业身份叙述中存在若干待澄清线索”
```

---

## 13. 建议文件结构

在第一版基础上新增：

```text
career_lie_index_agent/
├── run_cli.py
├── config.py
├── llm_client.py
├── graph.py
├── state_schema.py
├── prompts.py
├── nodes/
│   ├── fact_extraction_node.py
│   ├── anomaly_detection_node.py
│   ├── consistency_judge_node.py
│   ├── state_update_node.py
│   ├── debate_gate_node.py
│   ├── debate_node.py
│   ├── risk_aggregator_node.py
│   ├── strategy_supervisor_node.py
│   ├── followup_generation_node.py
│   ├── report_generation_node.py
│   └── specialists/
│       ├── semantic_agent_node.py
│       ├── logical_agent_node.py
│       ├── domain_agent_node.py
│       └── psycho_linguistic_agent_node.py
├── memory/
│   ├── fact_table.py
│   └── anomaly_table.py
├── utils/
│   ├── json_utils.py
│   ├── text_utils.py
│   └── score_utils.py
└── outputs/
    ├── logs/
    └── reports/
```

不需要 `app.py`。不做 Streamlit。

---

## 14. Graph 实现建议

### 14.1 基础顺序

```text
START
→ fact_extraction
→ anomaly_detection
→ consistency_judge
→ state_update
→ fanout_specialists
→ debate_gate
→ debate_or_aggregate
→ risk_aggregator
→ strategy_supervisor
→ route_next
→ followup_generation 或 report_generation
→ END
```

### 14.2 Specialist 并行

如果使用 LangGraph `Send`：

```python
from langgraph.types import Send

def fanout_specialists(state):
    return [
        Send("semantic_agent", state),
        Send("logical_agent", state),
        Send("domain_agent", state),
        Send("psycho_linguistic_agent", state),
    ]
```

每个 specialist 返回：

```python
{"specialist_results": [result]}
```

`specialist_results` 使用 reducer 合并。

### 14.3 Debate 路由

```text
debate_gate 返回：
- "debate"：进入 debate_node
- "aggregate"：进入 risk_aggregator_node
```

### 14.4 最终路由

```text
strategy_supervisor 输出 next_action：
- generate_followup
- final_report
```

然后 conditional edge 路由到对应节点。

---

## 15. 实现步骤

### Step 1：备份第一版

复制第一版项目为第二版分支：

```text
career_lie_index_agent_v2/
```

不要直接覆盖第一版。

---

### Step 2：扩展 State

修改：

```text
state_schema.py
```

新增：

```text
specialist_results
dimension_scores
agent_votes
debate_needed
debate_result
lie_index
risk_level
risk_explanation
```

---

### Step 3：新增 4 个 Specialist Agent

实现：

```text
semantic_agent_node.py
logical_agent_node.py
domain_agent_node.py
psycho_linguistic_agent_node.py
```

每个节点都调用 DeepSeek-V4-Pro。每个节点输出统一 JSON。

---

### Step 4：实现 specialist fan-out

修改：

```text
graph.py
```

将 4 个 specialist 节点并行执行，并合并 `specialist_results`。

---

### Step 5：实现 Debate Gate

实现：

```text
debate_gate_node.py
```

根据分数差异、风险等级、consistency_results 判断是否进入 debate。

---

### Step 6：实现 Debate Node

实现：

```text
debate_node.py
```

只做结构化争议总结，不做自由长篇辩论。

---

### Step 7：实现 Risk Aggregator

实现：

```text
risk_aggregator_node.py
utils/score_utils.py
```

用固定公式计算 `lie_index`。

---

### Step 8：实现 Strategy Supervisor

实现：

```text
strategy_supervisor_node.py
```

让 Supervisor 只做：

```text
追问策略选择
是否继续
优先问题选择
简短理由总结
```

---

### Step 9：改造 Follow-up Generator

修改：

```text
followup_generation_node.py
```

让它使用：

```text
priority_issue
followup_strategy
debate_result
dimension_scores
```

生成更聚焦的自然追问。

---

### Step 10：改造 Final Report

修改：

```text
report_generation_node.py
```

加入多 Agent 维度分析结果和谎言指数解释。

---

### Step 11：CLI 测试

修改：

```text
run_cli.py
```

要求启动时关闭代理。要求支持 5 轮对话。要求每轮输出：

```text
1. 系统追问
2. 当前谎言指数
3. 各维度分数
4. 是否触发 Debate
5. 主要风险理由
```

---

## 16. 命令行运行效果示例

```text
系统：你平时是做什么方向的工作呀？

用户：我现在在投行，最近主要做新能源 IPO。

系统：
当前谎言指数：22 / 100
主要风险：暂无明显不一致。
追问：你平时在 IPO 项目里主要负责哪一块呀？

用户：其实主要就是给客户推荐理财产品。

系统：
当前谎言指数：64 / 100
语义分：72
逻辑分：58
领域分：70
心理语言分：45
触发 Debate：是
主要风险：当前工作内容与前文职业描述存在待澄清点。
追问：你刚才提到做 IPO 项目，后面又说到推荐理财产品，我有点好奇，这两部分是同一份工作里的不同内容，还是不同阶段的经历呀？
```

---

## 17. 第二版验收标准

第二版完成后，应满足：

```text
1. 能连续进行 5 轮文本对话
2. 每轮能运行 4 个 Specialist Agent
3. 能输出各维度分数
4. 能计算总谎言指数
5. 能在争议场景触发 Debate
6. 能生成更聚焦的自然追问
7. 最终报告包含多 Agent 分析结果
8. CLI 可完整展示全过程
```

---

## 18. 测试样例

至少准备 20 条测试样例。

```text
1. 一致型：5 条
2. 明显冲突型：5 条
3. 可澄清型：5 条
4. 模糊回避型：5 条
```

每条样例记录：

```text
gold_label
关键异常点
期望是否触发 debate
期望主要追问方向
最终谎言指数区间
```

---

## 19. 后续可选增强

第二版完成后，后续再考虑：

```text
1. 加入外部职业常识库
2. 加入语音语速、停顿等特征
3. 加入视频表情特征
4. 加入 Human-in-the-loop
5. 加入 LangGraph checkpoint 持久化
6. 加入 Mermaid 图可视化
```

这些不属于第二版必须完成内容。

---

## 20. 最终总结

第二版的核心不是重新做一个系统，而是在第一版基础上加入：

```text
多 Agent 并行分析
+
争议触发式 Debate
+
可解释维度评分
+
谎言指数聚合
```

最终系统应体现：

```text
不是一个 LLM 直接判断，
而是多个角色 Agent 从语义、逻辑、职业常识和心理语言学四个维度共同分析，
再由规则化聚合得到谎言指数。
```
