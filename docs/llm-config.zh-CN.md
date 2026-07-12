# LLM 配置指南

## 支持的提供商

| 提供商 | 代码 | 默认 API 地址 |
|--------|------|--------------|
| DeepSeek | `deepseek` | `https://api.deepseek.com/v1` |
| OpenAI | `openai` | `https://api.openai.com/v1` |
| 阿里云百炼 (Qwen) | `qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

## 响应速度对比

| LLM | 实测平均响应 | 说明 |
|-----|:----------:|------|
| DeepSeek (deepseek-chat) | 12-16s | 公共 API，高峰时段更慢 |
| Qwen (qwen-plus) | 3-6s | 阿里云百炼，国内访问快 |
| 本地部署 (vLLM + Qwen2) | 1-2s | 需 GPU 资源 |

## 配置方式

### 通过系统管理页面

系统设置 → 模型配置 → 新增，填写以下字段。

### 通过 API

```bash
TOKEN="your_admin_token"

curl -X POST 'http://localhost:8000/api/v1/admin/llm-configs' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "qwen",
    "model": "qwen-plus",
    "api_key": "your-api-key",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "name": "阿里 Qwen",
    "is_default": true,
    "max_tokens": 4096,
    "temperature": 0.7
  }'
```

## 各提供商配置示例

### 阿里云百炼 (Qwen)

1. 前往 [阿里云百炼](https://help.aliyun.com/zh/model-studio/) 获取 API Key
2. 推荐模型：`qwen-plus`（平衡速度与效果）或 `qwen-turbo`（最快）

```json
{
  "provider": "qwen",
  "model": "qwen-plus",
  "api_key": "sk-xxxxxxxx",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
}
```

### OpenAI

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "api_key": "sk-xxxxxxxx",
  "base_url": "https://api.openai.com/v1"
}
```

### 本地部署 (兼容 OpenAI API)

使用 vLLM、Ollama 等工具本地部署模型后：

```json
{
  "provider": "openai",
  "model": "Qwen2.5-7B-Instruct",
  "api_key": "not-needed",
  "base_url": "http://localhost:8000/v1"
}
```

## 注意事项

- 设为默认的配置会在聊天时自动使用
- 部门级配置可覆盖全局默认（部门管理员在部门管理中设置）
- 首次切换 LLM 后，首条消息可能稍慢（客户端缓存连接）
