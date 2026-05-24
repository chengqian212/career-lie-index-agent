# Baseline 项目规划书：直接调用 LLM 的职业身份谎言指数测评系统

## 1. 项目名称

**基于直接 LLM 调用的职业身份谎言指数测评 Baseline**

本版本用于作为后续 LangGraph 有状态工作流、多 Agent 增强版的对比基线。

---

## 2. 项目目标

本项目面向交友聊天场景，围绕用户关于**职业身份**的叙述进行谎言指数测评。

系统不做外部事实核查，也不直接给出“对方一定说谎”的结论，而是根据多轮对话内部信息，评估职业身份叙述中是否存在：

```text
1. 职业身份前后不一致
2. 工作内容描述不稳定
3. 时间阶段或经历说明不清
4. 回避、模糊、答非所问等表达异常
5. 追问后仍未澄清的可疑线索
```

最终输出：

```text
1. 当前对方职业身份画像
2. 关键事实摘要
3. 可疑点和证据片段
4. 建议追问问题
5. 谎言指数 lie_index：0-100
6. 简短解释报告
```

---

## 3. Baseline 设计原则

本版本不使用 LangGraph，不做多节点拆分，不做多 Agent 协同。

核心思想是：

```text
每一轮用户回复后，将完整对话历史 + 上一轮结构化结果 + 当前用户回复
一起交给 deepseek-v3，
让一个 LLM Prompt 一次性完成：
事实抽取、异常识别、历史比对、谎言指数更新、追问生成。
```

也就是说，本版本是一个**单 LLM 全流程 Baseline**。

它的作用不是追求最终最佳效果，而是作为对比对象，用来验证后续版本是否真的比直接调用 LLM 更稳定、更可解释。

---

## 4. 技术路线

使用：

```text
Python
阿里云百炼 OpenAI-compatible API
deepseek-v3
本地 JSON 状态文件
命令行 CLI Demo
```

不使用：

```text
LangGraph
LangChain Agent
Streamlit
向量数据库
外部搜索
模型微调
BERT
多 Agent 协同
```

---

## 5. 系统边界

### 5.1 本版本做什么

```text
1. 多轮文本对话
2. 直接调用 LLM 分析完整历史
3. 生成职业身份画像
4. 识别职业叙述中的可疑线索
5. 生成自然追问
6. 更新谎言指数
7. 多轮结束后生成最终报告
```

### 5.2 本版本不做什么

```text
1. 不做外部联网核查
2. 不验证真实身份
3. 不做司法级测谎
4. 不训练模型
5. 不拆分多个 Agent
6. 不使用 LangGraph
7. 不做 Streamlit 页面
8. 不接语音和视频
```

---

## 6. 整体流程

第一版 Baseline 使用简单 Python 循环。

```text
启动程序
↓
初始化 baseline_state
↓
系统提出初始问题
↓
用户输入回答
↓
调用 deepseek-v3 Baseline Prompt
↓
LLM 一次性输出：
    职业画像
    关键事实
    可疑线索
    异常表达
    谎言指数
    下一轮追问
↓
Python 保存本轮结果
↓
如果未达到最大轮次：继续下一轮
如果达到最大轮次：生成最终报告
```

建议默认最大轮数：

```text
max_rounds = 5
```

---

## 7. 核心状态设计

定义本地状态 `baseline_state`。

```python
baseline_state = {
    "round_id": 0,
    "max_rounds": 5,
    "conversation_history": [],
    "previous_analysis": {},
    "latest_analysis": {},
    "lie_index_history": [],
    "followup_history": [],
    "final_report": {}
}
```

字段说明：

```text
round_id：当前轮次
max_rounds：最大对话轮数
conversation_history：完整对话记录
previous_analysis：上一轮 LLM 的结构化分析结果
latest_analysis：当前轮 LLM 的结构化分析结果
lie_index_history：每轮谎言指数变化
followup_history：系统生成过的追问
final_report：最终报告
```

---

## 8. LLM 输出格式

每轮调用 LLM 后，必须输出 JSON。

### 8.1 每轮分析 JSON

```json
{
  "career_profile": {
    "claimed_identity": "投行从业者",
    "industry": "金融",
    "job_title": "未明确",
    "work_content": "新能源 IPO 项目",
    "organization_type": "券商/投行",
    "time_stage": "当前",
    "confidence": "medium"
  },
  "key_facts": [
    {
      "fact": "用户声称当前在投行做新能源 IPO 项目",
      "evidence": "我现在在投行做新能源 IPO",
      "round_id": 1
    }
  ],
  "suspicious_clues": [
    {
      "type": "工作内容潜在不匹配",
      "description": "用户前文说做 IPO 项目，后文又说主要推荐理财产品，需要澄清是否属于不同阶段或不同工作内容。",
      "evidence": [
        "第1轮：我现在在投行做新能源 IPO",
        "第2轮：主要给客户推荐理财产品"
      ],
      "severity": "medium"
    }
  ],
  "expression_anomalies": [
    {
      "type": "表达模糊",
      "evidence": "反正客户那边的一些事",
      "severity": "low"
    }
  ],
  "lie_index": 45,
  "risk_level": "medium",
  "reason_summary": "当前职业身份主线基本与金融相关，但工作内容描述存在待澄清的不匹配。",
  "next_question": "你刚才提到做 IPO 项目，后面又说到推荐理财产品，我有点好奇，这是同一份工作里的不同内容，还是不同阶段的经历呀？",
  "should_continue": true
}
```

### 8.2 最终报告 JSON

```json
{
  "final_lie_index": 62,
  "risk_level": "medium",
  "career_profile_summary": "对方主要声称自己从事金融相关工作，但具体岗位和工作内容存在多处待澄清点。",
  "stable_facts": [
    "多轮中均围绕金融行业展开"
  ],
  "unresolved_clues": [
    "当前工作内容在 IPO 项目和理财产品推荐之间存在待澄清差异"
  ],
  "expression_patterns": [
    "多次使用模糊表达",
    "对具体职责说明不足"
  ],
  "suggested_verification_direction": [
    "继续询问当前岗位的具体职责",
    "区分当前工作和过往实习经历"
  ],
  "final_summary": "当前对话不能证明对方说谎，但职业身份叙述中存在若干待澄清线索，建议继续通过自然追问了解具体工作内容。"
}
```

---

## 9. Prompt 设计要求

Baseline Prompt 必须包含以下约束：

```text
1. 只根据对话内部信息分析，不做外部猜测。
2. 不要直接说“对方在说谎”。
3. 输出谎言指数是风险提示，不是最终定性。
4. 所有可疑点必须引用具体对话轮次或证据片段。
5. 如果只是正常补充经历，不要误判为冲突。
6. 追问必须自然、温和，像正常聊天中的好奇。
7. 不要使用“矛盾”“撒谎”“审问”“核查”等刺激性词。
8. 必须输出合法 JSON，不要在 JSON 外输出解释。
```

---

## 10. 谎言指数规则

Baseline 中谎言指数由 LLM 直接给出，但 Prompt 中要提供参考规则。

```text
0-30：低风险
31-60：中风险
61-100：高风险
```

参考加分因素：

```text
职业身份前后明显冲突：+30
工作内容潜在不匹配：+20
时间阶段说不清：+10
明显回避：+10
答非所问：+10
表达模糊：+5
过度解释：+5
追问后仍未澄清：+15
```

参考减分因素：

```text
后续解释合理：-20
时间阶段澄清清楚：-15
职业主线稳定：-10
```

注意：

```text
最终 lie_index 必须在 0-100 之间。
```

---

## 11. 建议文件结构

```text
baseline_llm_lie_index/
├── config.py
├── llm_client.py
├── prompts.py
├── state_store.py
├── baseline_analyzer.py
├── report_generator.py
├── run_cli.py
├── run_batch_eval.py
├── utils_json.py
├── utils_text.py
├── data/
│   ├── test_cases.jsonl
│   └── sample_dialogues.json
└── outputs/
    ├── logs/
    ├── states/
    └── reports/
```

---

## 12. 各文件功能说明

### `config.py`

功能：保存 API 配置、模型名称、最大轮次、输出目录等。

必须在文件中关闭代理环境变量。

```python
import os

for key in [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy"
]:
    os.environ.pop(key, None)

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME = os.getenv("DASHSCOPE_MODEL", "deepseek-v3")
MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", "5"))
OUTPUT_DIR = "outputs"
```

---

### `llm_client.py`

功能：封装阿里云百炼  调用。

要求：

```text
1. 使用 OpenAI-compatible API
2. 支持普通文本调用
3. 支持 JSON 输出解析
4. 失败时自动重试
5. 如果 JSON 解析失败，进行一次修复重试
```

---

### `prompts.py`

功能：保存两个 Prompt：

```text
1. BASELINE_ANALYSIS_PROMPT：每轮分析和追问
2. FINAL_REPORT_PROMPT：最终报告生成
```

---

### `state_store.py`

功能：管理 baseline_state。

包括：

```text
1. 初始化 state
2. 添加用户回答
3. 添加 LLM 分析结果
4. 保存 state 到 outputs/states
5. 从文件恢复 state
```

---

### `baseline_analyzer.py`

功能：实现每轮核心分析。

输入：

```text
baseline_state
current_user_text
```

输出：

```text
latest_analysis JSON
```

调用流程：

```text
1. 将 current_user_text 写入 conversation_history
2. 构造 Prompt
3. 调用 LLM
4. 解析 JSON
5. 更新 latest_analysis
6. 更新 lie_index_history
7. 返回 next_question
```

---

### `report_generator.py`

功能：生成最终报告。

输入：

```text
完整 conversation_history
所有 latest_analysis 历史
lie_index_history
```

输出：

```text
final_report JSON
```

---

### `run_cli.py`

功能：命令行运行 Baseline Demo。

启动时必须关闭代理。

建议开头写：

```python
import os

for key in [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy"
]:
    os.environ.pop(key, None)
```

运行逻辑：

```text
1. 初始化 state
2. 打印初始问题
3. 用户输入回答
4. 调用 baseline_analyzer
5. 打印谎言指数和下一轮追问
6. 循环 max_rounds 轮
7. 调用 report_generator
8. 打印最终报告
9. 保存日志
```

---

### `run_batch_eval.py`

功能：批量跑测试集，用于和 LangGraph 版本对比。

输入：

```text
data/test_cases.jsonl
```

输出：

```text
outputs/reports/baseline_eval_results.json
```

至少保存：

```text
dialogue_id
final_lie_index
risk_level
detected_clues
final_report
```

---

### `utils_json.py`

功能：JSON / JSONL 读写、JSON 修复、字段检查。

---

### `utils_text.py`

功能：文本清洗、对话格式化、轮次编号格式化。

---

## 13. 实现步骤

### Step 1：创建项目结构

创建：

```text
baseline_llm_lie_index/
```

并创建上述文件和目录。

---

### Step 2：实现环境配置和代理关闭

先完成：

```text
config.py
run_cli.py
```

要求：

```text
1. 程序启动时关闭 HTTP_PROXY / HTTPS_PROXY 等代理变量
2. 从环境变量读取 DASHSCOPE_API_KEY
3. 支持设置 DASHSCOPE_MODEL
```

---

### Step 3：实现 LLM 调用

完成：

```text
llm_client.py
```

测试：

```text
输入一句简单问题，确认 deepseek-v3 能正常返回。
```

---

### Step 4：实现 Prompt

完成：

```text
prompts.py
```

重点写好：

```text
BASELINE_ANALYSIS_PROMPT
FINAL_REPORT_PROMPT
```

---

### Step 5：实现状态管理

完成：

```text
state_store.py
```

确保每轮结果都能保存到：

```text
outputs/states/
```

---

### Step 6：实现单轮分析

完成：

```text
baseline_analyzer.py
```

测试输入：

```text
我现在在一家券商投行部，最近主要跟一个新能源 IPO 项目。
```

期望输出：

```text
职业画像
关键事实
lie_index
next_question
```

---

### Step 7：实现最终报告

完成：

```text
report_generator.py
```

要求输出 JSON 格式最终报告。

---

### Step 8：实现命令行 Demo

完成：

```text
run_cli.py
```

示例运行：

```bash
python run_cli.py
```

示例效果：

```text
系统：你平时是做什么工作的呀？
用户：我现在在投行做新能源 IPO。
系统：当前谎言指数：25 / 100
系统：你平时在这个项目里主要负责哪一块呀？
```

---

### Step 9：实现批量评估脚本

完成：

```text
run_batch_eval.py
```

用于后续和 LangGraph 版本、多 Agent 版本对比。

---

## 14. 测试样例要求

至少准备 12 条测试样例。

```text
1. 职业身份一致型：3 条
2. 职业内容冲突型：3 条
3. 可澄清型：3 条
4. 模糊回避型：3 条
```

测试样例格式：

```json
{
  "dialogue_id": "D001",
  "type": "conflict",
  "turns": [
    "我现在在投行做新能源 IPO。",
    "其实主要就是给客户推荐理财产品。"
  ],
  "gold_clues": [
    "IPO 项目与理财产品推荐存在工作内容潜在不匹配"
  ],
  "expected_risk_level": "medium"
}
```

---

## 15. Baseline 验收标准

本 Baseline 版本满足以下条件即可：

```text
1. 可以连续进行 3-5 轮文本对话
2. 每轮直接调用 deepseek-v3 生成结构化 JSON
3. 能输出职业画像、可疑线索、谎言指数和下一轮追问
4. 追问语气自然，不像审问
5. 能生成最终报告
6. 能保存对话日志和每轮分析结果
7. 能批量跑测试样例，方便后续和其他版本对比
```

---

## 16. 与后续版本的对比用途

本版本作为 Baseline，用于和以下版本对比：

```text
Version 1：LangGraph 有状态多节点工作流
Version 2：多 Agent 并行分析增强版
```

重点比较：

```text
1. 谎言指数是否稳定
2. 是否准确发现关键可疑点
3. 证据引用是否准确
4. 追问是否聚焦
5. 追问后状态变化是否合理
6. 最终报告是否清晰可解释
```

---

## 17. 最终一句话

Baseline 的核心是：

```text
不用 LangGraph，不拆节点，不做多 Agent，
直接用一个 LLM Prompt 完成职业身份谎言指数测评全流程，
并把它作为后续 LangGraph 工作流和多 Agent 增强版的对比基线。
```
