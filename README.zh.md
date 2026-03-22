<p align="center">
  <img src="assets/cc-digest.jpg" width="640" alt="cc-digest">
  <h1 align="center">cc-digest</h1>
  <p align="center">
    使用本地 LLM 提取、摘要和搜索你的 <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> 会话。
  </p>
  <p align="center">
    <a href="https://github.com/vayaSEO/cc-digest/actions/workflows/ci.yml"><img src="https://github.com/vayaSEO/cc-digest/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <img src="https://img.shields.io/pypi/pyversions/cc-digest" alt="Python">
    <img src="https://img.shields.io/github/license/vayaSEO/cc-digest" alt="许可证">
  </p>
  <p align="center">
    <a href="README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.zh.md">中文</a> · <a href="README.ja.md">日本語</a>
  </p>
</p>

---

将数千行对话记录转化为简洁、可搜索的摘要 — 完全离线运行，无需 API 密钥。

<p align="center">
  <video src="https://github.com/user-attachments/assets/15970642-2674-4497-9e8d-eb18d3c60c64" width="700" controls></video>
</p>

## 功能

1. **Extract** — 从 `~/.claude/projects/` 读取 Claude Code 的 JSONL 记录，存储结构化会话数据
2. **Digest** — 使用本地 LLM（通过 [Ollama](https://ollama.com)）将每个会话摘要为约 10 个要点
3. **Embed** — 为摘要生成向量嵌入，用于语义搜索
4. **Search** — 按语义查找相关历史会话，而非仅关键词匹配
5. **Stats** — 会话历史概览

## 安装

```bash
pip install cc-digest
```

或从源码安装：

```bash
git clone https://github.com/vayaSEO/cc-digest.git
cd cc-digest
pip install -e .
```

<details>
<summary>可选：MongoDB 后端</summary>

```bash
pip install cc-digest[mongo]
```

在 `.env` 文件中设置 `STORAGE_BACKEND=mongo` 和 `MONGO_URI`。

</details>

## 快速开始

```bash
# 1. 从 Claude Code 记录中提取会话
cc-digest extract

# 2. 使用本地 LLM 生成摘要（需要 Ollama 运行中）
cc-digest digest

# 3. 生成语义搜索用的向量嵌入
cc-digest embed

# 4. 搜索你的会话
cc-digest search "FastAPI 中的 CORS 错误"

# 5. 查看统计
cc-digest stats
```

## 环境要求

- **Python** >= 3.11
- **Ollama**（用于摘要和搜索）— [安装](https://ollama.com/download)

```bash
# 下载推荐模型
ollama pull qwen3:14b          # 摘要
ollama pull nomic-embed-text   # 嵌入
```

## 命令

### `cc-digest extract`

读取 JSONL 记录并存储会话。

```bash
cc-digest extract                     # 处理所有会话
cc-digest extract --session UUID      # 单个会话
cc-digest extract --dry-run           # 预览，不写入
cc-digest extract --export-md         # 同时保存 .md 文件
cc-digest extract --min-messages 10   # 跳过短会话
```

### `cc-digest digest`

使用本地 LLM 摘要会话。

```bash
cc-digest digest                      # 摘要未处理的会话
cc-digest digest --force              # 重新摘要所有
cc-digest digest --model gemma3:12b   # 使用其他模型
cc-digest digest --limit 10           # 仅处理前 10 个
cc-digest digest --export-md          # 保存摘要为 .md
```

### `cc-digest embed`

为语义搜索生成向量嵌入。

```bash
cc-digest embed                       # 嵌入未处理的摘要
cc-digest embed --force               # 重新嵌入所有
cc-digest embed --limit 10            # 仅处理前 10 个
```

### `cc-digest search`

按查询搜索会话。

```bash
cc-digest search "docker compose 问题"
cc-digest search "auth middleware" --project myapp
cc-digest search "deploy" --mode grep    # 强制文本搜索
cc-digest search "pipeline" --top 10     # 更多结果
```

### `cc-digest stats`

会话数据概览。

```bash
cc-digest stats
cc-digest stats --project myapp
```

## 配置

将 `.env.example` 复制为 `.env` 并按需调整：

```bash
cp .env.example .env
```

<details>
<summary>所有配置变量</summary>

| 变量 | 默认值 | 描述 |
|---|---|---|
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Claude Code 存储记录的位置 |
| `USER_DISPLAY_NAME` | `User` | 导出 markdown 中的用户名 |
| `STORAGE_BACKEND` | `sqlite` | `sqlite`（默认）或 `mongo` |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama 服务器地址 |
| `DIGEST_MODEL` | `qwen3:14b` | 摘要用 LLM 模型 |
| `EMBED_MODEL` | `nomic-embed-text` | 嵌入用模型 |
| `MIN_MESSAGES` | `4` | 跳过消息数少于此值的会话 |

</details>

## 存储

**SQLite**（默认）— 零依赖，所有数据存储在 `~/.local/share/cc-digest/cc-digest.db`。

**MongoDB**（可选）— 使用 `pip install cc-digest[mongo]` 安装，在 `.env` 中设置 `STORAGE_BACKEND=mongo` 和 `MONGO_URI`。

## 性能

在 Apple Silicon M4 Pro 上测试了 8 个模型 — 30 个会话，67K 词输入：

| 模型 | 参数量 | 平均/会话 | 压缩比 | 备注 |
|---|---|---|---|---|
| **`qwen3:14b`** | 14B | ~36s | 15:1 | **默认** — 最佳准确性，尊重对话语言 |
| `glm4:9b` | 9B | ~20s | 18:1 | 最快的可靠选项 |
| `mistral-nemo` | 12B | ~27s | 14:1 | 稳定全能 |
| `gemma3:12b` | 12B | ~34s | 10:1 | 输出更详细 |
| `granite3.3:8b` | 8B | ~26s | 11:1 | 速度和质量的良好平衡 |

> 追求准确性用 `qwen3:14b`。需要更快速度用 `glm4:9b` 或 `granite3.3:8b`。嵌入 + 搜索即时完成（<1s）。

<details>
<summary>完整基准测试详情（3 个额外模型 + 质量分析）</summary>

| 模型 | 参数量 | 平均/会话 | 压缩比 | 备注 |
|---|---|---|---|---|
| `qwen3.5:9b` | 9B | ~32s | 10:1 | 相对于其大小速度偏慢 |
| `phi4-mini` | 3.8B | ~10s | 12:1 | 最快，但引入事实错误 |
| `nemotron-mini` | 4.2B | ~4s | 550:1 | 不推荐 — 8/30 空响应 |

**质量对比**（3 个会话并排比较）：
- `qwen3:14b`：最佳事实准确性，结构化要点，尊重对话语言
- `phi4-mini`：快 3.4 倍但在某会话中颠倒了一个决策
- `granite3.3:8b`：速度和质量之间的良好折中

会话压缩使用智能 head/tail 策略 — 保留开头和结尾的上下文，压缩中间部分。可处理 1K 到 1M+ 字符的会话。

> 时间因会话长度和硬件而异。建议使用 GPU 加速。

</details>

## 工作原理

```
~/.claude/projects/**/*.jsonl
         │
    cc-digest extract
         │
    ┌────▼────┐
    │ SQLite  │（或 MongoDB）
    │ sessions│
    └────┬────┘
         │
    cc-digest digest (Ollama → qwen3:14b)
         │
    ┌────▼────┐
    │ SQLite  │
    │ digests │
    └────┬────┘
         │
    cc-digest embed (Ollama → nomic-embed-text)
         │
    ┌────▼──────┐
    │ SQLite    │
    │ embeddings│
    └────┬──────┘
         │
    cc-digest search "你的查询"
         │
    ┌────▼──┐
    │ 结果  │
    └───────┘
```

## 许可证

MIT
