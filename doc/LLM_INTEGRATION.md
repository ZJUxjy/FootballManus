# LLM 集成设计文档

**状态**: ✅ 已实现  
**模块**: `fm_manager/engine/llm_client.py`

---

## 核心功能

### 1. 多提供商支持

```python
class LLMProvider(Enum):
    OPENAI = "openai"          # GPT-4, GPT-3.5
    ANTHROPIC = "anthropic"    # Claude 3
    LOCAL = "local"            # 本地模型
    MOCK = "mock"              # 测试用
```

### 2. 响应缓存

```python
class ResponseCache:
    - 内存缓存
    - TTL过期 (默认1小时)
    - 最大容量限制
    - 缓存命中率追踪
```

### 3. Token 使用追踪

```python
@dataclass
class TokenUsage:
    total_prompt_tokens: int
    total_completion_tokens: int
    estimated_cost_usd: float
    
    # 定价 (per 1K tokens)
    PRICING = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
    }
```

---

## 使用示例

### 基础使用

```python
from fm_manager.engine.llm_client import LLMClient, LLMProvider

# 创建客户端
client = LLMClient(
    provider=LLMProvider.OPENAI,
    model="gpt-3.5-turbo",
    temperature=0.7,
    max_tokens=1000,
)

# 生成文本
response = client.generate(
    prompt="Describe a football match moment",
    system_prompt="You are a sports commentator",
)

print(response.content)
print(f"Tokens used: {response.tokens_used}")
```

### 环境变量配置

```bash
export LLM_PROVIDER="openai"  # openai/anthropic/local/mock
export LLM_MODEL="gpt-3.5-turbo"
export OPENAI_API_KEY="sk-..."
export LLM_TEMPERATURE="0.7"
export LLM_MAX_TOKENS="1000"
```

### 预置提示模板

```python
from fm_manager.engine.llm_client import FMPrompts

prompt = FMPrompts.MATCH_NARRATIVE.format(
    home_team="Manchester City",
    away_team="Liverpool",
    minute=85,
    event_type="Goal",
    details="Haaland scores",
)
```

---

## API 参考

### LLMResponse

| 字段 | 类型 | 说明 |
|-----|------|------|
| content | str | 生成的文本 |
| provider | LLMProvider | 提供商 |
| model | str | 模型名称 |
| tokens_used | int | 总token数 |
| prompt_tokens | int | 提示token数 |
| completion_tokens | int | 生成token数 |
| latency_ms | float | 延迟(毫秒) |
| cached | bool | 是否缓存命中 |

---

## 测试验证

```
Mock Response Test:
  Provider: mock
  Model: mock-model
  Tokens: 14
  Latency: 100.1ms

Cache Test:
  Cache hit: False
  Cache size: 2

Usage Stats:
  Total tokens: 31
  Est. cost: $0.0001
  Requests: 2
```
