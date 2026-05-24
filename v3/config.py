"""项目配置模块：读取 .env 并提供全局配置

支持通过 .env 文件配置 API 密钥、基础 URL、模型名称等信息。
默认值适用于 DeepSeek 开放平台，如需使用其他提供商只需修改对应环境变量。
"""

import os
from dotenv import load_dotenv

# 加载 .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)


def disable_proxy():
    """关闭系统代理，避免 API 调用被本地代理影响
    
    做两件事：
    1. 清除代理相关环境变量
    2. 设置 NO_PROXY='*' 绕过 Windows 系统级代理（注册表/IE设置）
       httpx/openai 底层会自动读取系统代理，仅清环境变量不够
    """
    for key in [
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ]:
        os.environ.pop(key, None)
    # 关键：设置 NO_PROXY='*' 让 httpx/openai 跳过所有系统代理
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


# 启动时默认关闭代理
disable_proxy()

# --- 配置项 ---

# DeepSeek API 密钥
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

# API 基础地址（OpenAI SDK 会自动拼接 /chat/completions 等路径）
BAILIAN_BASE_URL: str = os.getenv(
    "BAILIAN_BASE_URL", "https://api.deepseek.com"
)

# 默认模型名称（deepseek-chat 为 DeepSeek 最新对话模型）
MODEL_NAME: str = os.getenv("MODEL_NAME", "deepseek-chat")
MAX_ROUNDS: int = int(os.getenv("MAX_ROUNDS", "5"))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.2"))

# 风险等级阈值
RISK_LOW_THRESHOLD: int = 30
RISK_HIGH_THRESHOLD: int = 60

# 谎言指数权重
WEIGHT_SEMANTIC: float = 0.30           # 语义一致性权重
WEIGHT_LOGICAL: float = 0.25            # 逻辑一致性权重
WEIGHT_DOMAIN: float = 0.20             # 领域一致性权重
WEIGHT_PSYCHO_LINGUISTIC: float = 0.15  # 心理语言学权重
WEIGHT_UNRESOLVED_FOLLOWUP: float = 0.10  # 未解决追问权重

# Debate 触发阈值
DEBATE_SCORE_THRESHOLD: int = 75           # Debate 触发分数阈值：谎言指数达到此值时触发辩论
DEBATE_SCORE_DIFF_THRESHOLD: int = 40      # Debate 分数差阈值：专家评分差异超过此值时触发辩论
UNRESOLVED_FOLLOWUP_PER_SCORE: int = 20    # 未解决追问每项扣分：每个未解决的追问按此分值计入谎言指数

# ---- v3 新增：路由配置 ----
# 是否启用按需专家调用
ENABLE_ON_DEMAND_SPECIALISTS: bool = True

# 低风险阈值：低于此值不调用专家
LOW_RISK_SKIP_THRESHOLD: int = 30

# 中风险阈值：低于此值只调用1个专家
MEDIUM_RISK_THRESHOLD: int = 50

# 高风险阈值：高于此值调用多个或全部专家
HIGH_RISK_THRESHOLD: int = 70

# Debate 最少专家数：调用少于该数量专家时不触发 Debate
MIN_SPECIALISTS_FOR_DEBATE: int = 2
