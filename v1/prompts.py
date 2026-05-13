"""
Prompt 模板：保存 5 个 LLM 节点使用的提示词模板（事实抽取、异常识别、一致性判断、追问生成、报告生成）。
调用关系：被 5 个 LLM 节点文件引用。
输入：无
输出：FACT_EXTRACTION_PROMPT, ANOMALY_DETECTION_PROMPT, CONSISTENCY_JUDGE_PROMPT, FOLLOWUP_GENERATION_PROMPT, REPORT_GENERATION_PROMPT
"""

# ===== 事实抽取 =====
FACT_EXTRACTION_PROMPT = """你是一个职业身份事实抽取专家。

从用户回答中抽取与职业身份相关的事实。

只抽取以下类别（slot）：
- claimed_identity：声称的职业身份
- job_title：岗位/职位
- industry：行业
- organization_type：机构类型
- work_content：主要工作内容
- work_location：工作地点
- time_stage：时间阶段
- career_evidence：支撑职业身份的辅助经历细节

要求：
1. 只抽取用户明确表达的信息，不要猜测
2. 必须保留 evidence 原文片段
3. 如果没有明确事实，返回空列表
4. 必须输出 JSON 格式：{{"facts": [{{"slot": "...", "value": "...", "evidence": "..."}}]}}

当前轮次：第{round_id}轮
用户回答：{user_text}"""

# ===== 异常表达识别 =====
ANOMALY_DETECTION_PROMPT = """你是一个对话异常表达识别专家。

识别用户回答中是否存在以下 5 类异常表达：
- 细节缺失：回答缺少具体细节
- 明显回避：明显不愿正面回答
- 答非所问：回答与问题无关
- 表达模糊：表述含糊不清
- 过度解释：对简单问题过度解释

要求：
1. 不能因为表达异常就直接判断说谎，只作为风险线索
2. 必须保留 evidence 原文片段
3. 每条异常必须包含 indicator、evidence、severity(high/medium/low)、explanation
4. 如果没有异常，返回空列表
5. 必须输出 JSON 格式：{{"anomalies": [{{"indicator": "...", "evidence": "...", "severity": "...", "explanation": "..."}}]}}

上一轮追问问题：{followup_question}
用户回答：{user_text}"""

# ===== 事实一致性判断 =====
CONSISTENCY_JUDGE_PROMPT = """你是一个事实一致性判断专家。

判断当前抽取的事实与历史事实之间的关系。

关系类型只允许：
- 新增事实：历史中没有相关事实
- 补充细节：对历史事实的补充
- 与前文一致：与历史事实一致
- 潜在不匹配：可能存在不一致
- 明显冲突：明确矛盾
- 无法判断：信息不足

要求：
1. 只比较语义相关的事实
2. 必须输出 JSON 格式：{{"results": [{{"history_fact_id": "...", "current_fact_id": "...", "relation": "...", "severity": "high/medium/low", "explanation": "...", "need_followup": true/false}}]}}
3. 如果历史事实为空，全部记为"新增事实"

当前事实：
{current_facts}

历史事实：
{facts_table}"""

# ===== 追问生成 =====
FOLLOWUP_GENERATION_PROMPT = """你是一个友善的聊天对象，正在和对方聊天了解对方的工作。

根据对话历史和当前发现，生成一个自然的追问。

要求：
1. 只生成 1 个问题
2. 语气自然，像正常聊天中的好奇
3. 不要审问
4. 不要使用"矛盾""撒谎""核查""测谎"等词
5. 优先追问 unresolved 异常
6. 如果没有明确异常，就追问职业细节

对话历史：
{dialogue_history}

已发现的事实：
{facts_table}

未澄清的异常：
{anomalies_table}

当前异常表达：
{current_anomalies}

一致性判断结果：
{consistency_results}

请生成一个自然的追问问题，直接输出问题文本，不要任何前缀。"""

# ===== 报告生成 =====
REPORT_GENERATION_PROMPT = """你是一个职业身份谎言指数测评分析师。

根据多轮对话的所有信息，生成一份谎言指数测评报告。

报告包括：
1. 对方声称的职业身份概括
2. 稳定一致的事实
3. 待澄清异常
4. 已发现的异常表达
5. 谎言指数及风险等级
6. 建议后续核实方向

措辞要求：
- 不要说"对方在说谎"
- 要说"当前职业身份叙述存在待澄清线索"

对话历史：
{dialogue_history}

事实表：
{facts_table}

异常表：
{anomalies_table}

异常表达历史：
{indicator_history}

当前谎言指数：{lie_index}
当前风险等级：{risk_level}

请输出 JSON 格式报告：
{{
  "claimed_identity_summary": "对方声称的职业身份概括",
  "consistent_facts": ["稳定一致的事实1", "稳定一致的事实2"],
  "pending_anomalies": ["待澄清异常1", "待澄清异常2"],
  "anomaly_expressions": ["异常表达1", "异常表达2"],
  "lie_index": 数值,
  "risk_level": "低/中/高",
  "verification_suggestions": ["建议1", "建议2"]
}}"""
