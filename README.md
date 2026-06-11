# claude-p — bring `claude -p` back to subscription users

> Use what you already paid for: `claude -p`-style automation on top of your
> interactive Claude Code subscription session.

[![PyPI](https://img.shields.io/pypi/v/claude-p.svg)](https://pypi.org/project/claude-p/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/Equality-Machine/claude-p)](https://github.com/Equality-Machine/claude-p/releases)

`claude-p` is a `claude -p` compatible CLI and Python SDK backed by the
interactive Claude Code TUI.

[中文说明](#中文说明) is included below.

It is built for the annoying gap where interactive Claude Code works with your
subscription login, but `claude -p` / programmatic agent workflows are limited,
capped, or unavailable in the environment you are using.

## Why claude-p

Claude Code users increasingly rely on `claude -p` for scripts, agent harnesses,
local evals, CI-like workflows, and one-off automations. But in some setups,
programmatic `claude -p` usage does not behave like the interactive subscription
session you already pay for.

`claude-p` bridges that gap.

It exposes the **interactive** Claude Code TUI through a `claude -p`-compatible
CLI and an Agent-SDK-shaped Python API:

- no Anthropic API key required;
- no new account;
- no new subscription;
- same local Claude Code login state;
- familiar `claude -p` output formats: `text`, `json`, and `stream-json`.

Under the hood, `claude-p` starts interactive `claude` in a pseudo-TTY, assigns a
session id, waits for the response, then reads Claude Code's canonical session
JSONL so the final output is not dependent on lossy terminal scraping.

## 30-second quickstart

Recommended for CLI use:

```bash
uv tool install claude-p --force
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2
```

If you prefer installing into your current Python environment, use Python 3.10+
and call pip through that interpreter:

```bash
python -m pip install claude-p
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2
```

![claude-p CLI demo](assets/claude-p-cli.gif)

Default output is plain text, just like `claude -p`.

Structured outputs work too:

```bash
claude-p "Respond exactly: hello" --output-format json
claude-p "Respond exactly: hello" --output-format stream-json --include-partial-messages
```

If the smoke command does not print `CLAUDE_P_OK`, run:

```bash
claude-p --doctor
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2 --raw-log /tmp/claude-p-smoke.raw.log
```

The raw log shows the real interactive Claude Code TUI state: workspace trust
prompts, auth problems, rate limits, MCP startup failures, or other local blocks.

## Drop-in compatibility

| If you use | Try |
|---|---|
| `claude -p "prompt"` | `claude-p "prompt"` |
| `claude -p --output-format json "prompt"` | `claude-p --output-format json "prompt"` |
| `claude -p --output-format stream-json` | `claude-p --output-format stream-json` |
| `claude -p --model sonnet` | `claude-p --model sonnet` |
| `claude -p --tools ''` | `claude-p --tools ''` |
| `claude -p --permission-mode default` | `claude-p --permission-mode default` |
| `from claude_agent_sdk import query` | `from claude_p import query` |

`claude-p` accepts a broad subset of Claude Code CLI flags, including:

- `-p`, `--print`
- `--model`
- `--tools`
- `--permission-mode`
- `--output-format text|json|stream-json`
- `--include-partial-messages`
- `--session-id`
- `--cwd`
- `--safe-mode`
- `--no-auto-trust` to disable wrapper auto-confirmation of the workspace trust prompt
- common context/config flags such as `--system-prompt`,
  `--append-system-prompt`, `--mcp-config`, `--settings`, `--plugin-dir`,
  `--allowedTools`, `--disallowedTools`, `--resume`, and `--continue`

`--timeout-sec` controls only the `claude-p` wrapper wait time. Set it to `0`
to disable the wrapper timeout for long-running prompts:

```bash
claude-p "Run a long local task and summarize the result" --timeout-sec 0
```

## Python SDK

The API is intentionally shaped like the official Claude Agent SDK.

```python
import asyncio
from claude_p import ClaudePOptions, query


async def main():
    options = ClaudePOptions(
        model="sonnet",
        tools="default",
        permission_mode="default",
    )

    async for message in query("How many files are in this directory?", options=options):
        print(message)


asyncio.run(main())
```

For a single final result:

![claude-p Python SDK demo](assets/claude-p-sdk.gif)

```python
import asyncio
from claude_p import ClaudePClient, ClaudePOptions


async def main():
    async with ClaudePClient(ClaudePOptions(model="sonnet")) as client:
        result = await client.run("Respond exactly: SDK_OK")
        print(result.result)


asyncio.run(main())
```

## How it works

`claude-p` does **not** call `claude -p`.

It:

1. starts interactive `claude` in a pseudo-TTY;
2. passes a deterministic `--session-id`;
3. waits for the TUI response to complete;
4. reads Claude Code's canonical session JSONL from
   `~/.claude/projects/**/<session-id>.jsonl`;
5. emits text/json/stream-json output compatible with `claude -p`.

The session JSONL step matters. Terminal rendering is lossy: cursor redraws,
spinners, and wide glyphs can drop characters in captured TTY output. The JSONL
session record is the stable source of truth for final `assistant` and `result`
text.

## What works today

- Plain text output by default.
- JSON single-result output.
- Core `stream-json` event shape.
- Tool use through the interactive Claude Code session.
- In headless runs, the wrapper auto-confirms Claude Code's standard workspace
  trust prompt, matching `claude -p`'s non-interactive behavior. `--safe-mode` is
  forwarded to Claude Code separately; pass `--no-auto-trust` to disable wrapper
  auto-confirmation. Only run headless prompts in directories you trust.
- Python SDK with `query(...)` and `ClaudePClient(...).run(...)`.
- Global console command after `uv tool install claude-p` or `python -m pip install claude-p`.

## Known limits

`claude-p` is a developer convenience tool, not a replacement for the official
Anthropic API.

Current limits:

- Token usage, cost, and exact rate-limit fields are best-effort placeholders.
- Hook lifecycle events from `claude -p --include-hook-events` are not replayed yet.
- `--input-format stream-json` is accepted but not implemented.
- `--bare` conflicts with the subscription-login goal because Claude bare mode
  bypasses OAuth/keychain auth.
- TUI automation can break if Claude Code significantly changes its interactive
  interface or local session storage.

For production agent workloads, use the official Anthropic API / official Claude
Agent SDK when possible.

## Verification checklist

For a manual install, these two commands should produce the same kind of visible
demo result as the README GIF:

```bash
uv tool install claude-p --force
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2
```

Expected output:

```text
CLAUDE_P_OK
```

For an LLM/agent asked to install and verify this repository from source, use:

```bash
git clone https://github.com/Equality-Machine/claude-p.git
cd claude-p
uv run --with pytest pytest tests -q
uv tool install . --force
claude-p --doctor
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2 --raw-log /tmp/claude-p-smoke.raw.log
```

If the final command does not print `CLAUDE_P_OK`, inspect
`/tmp/claude-p-smoke.raw.log` before guessing. The failure is usually in the
local interactive Claude Code state, not in PyPI installation.

## FAQ

### Is this bypassing authentication?

No. `claude-p` uses your local authenticated Claude Code session. If interactive
Claude Code does not work on your machine, `claude-p` will not magically make it
work.

### Is this avoiding billing or rate limits?

No. It does not remove Anthropic-side rate limits or account policy. It exposes
your interactive Claude Code session through a programmatic interface. Any limits
that apply to your account still apply.

### Why not just use `claude -p`?

If `claude -p` works for your use case, keep using it. `claude-p` is for
environments where interactive Claude Code works with subscription login state,
but `claude -p` / programmatic usage is unavailable or hits a different limit
surface first.

### Why read session JSONL instead of terminal text?

Because terminal capture is not reliable enough for exact agent output. In local
testing, the rendered terminal surface dropped characters during redraws, while
Claude Code's session JSONL contained the exact final assistant message.

### Will this break?

Possibly. It depends on interactive Claude Code behavior and local session JSONL
format. The project is intentionally small so breakages can be fixed quickly.

## Installation troubleshooting

`claude-p` requires Python 3.10+ and an existing local Claude Code login.

The most reliable installation path for end users is:

```bash
uv tool install claude-p --force
claude-p --help
claude-p "Respond exactly: OK" --tools ''
```

If `uv` is not installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL -l
uv tool install claude-p --force
```

If you prefer `pip`, use `python -m pip` from a Python 3.10+ interpreter:

```bash
python --version
python -m pip install claude-p
python -m pip show -f claude-p
which claude-p
```

Common install failures:

| Symptom | Cause | Fix |
|---|---|---|
| `zsh: command not found: pip` | Your shell has no `pip` command on `PATH`. | Use `python -m pip ...` or `uv tool install claude-p`. |
| `No matching distribution found for claude-p` | Usually an old Python/pip pair, or Python < 3.10. | Check `python3 --version`; install with `uv tool install claude-p`, or use a modern Python such as 3.11/3.12. |
| `claude-p: command not found` after install | Python's scripts directory is not on `PATH`. | Add `~/.local/bin` to `PATH`, or use `uv tool run claude-p ...`. |
| Import works in one terminal but not another | `pip` and `python` point to different environments. | Always run `python -m pip install claude-p` inside the environment you will use. |

For conda/venv users, activate the environment first:

```bash
conda activate your-env
python -m pip install claude-p
which python
which claude-p
claude-p "Respond exactly: OK"
```

On macOS, avoid relying on the Apple Command Line Tools `pip3` if it is old. It
may not see modern wheels correctly. Prefer `uv tool install claude-p`, Homebrew
Python, or a conda/venv environment.

## Development and release flow

Branching:

- `main`: released versions only.
- `dev`: integration branch.
- `feat/<name>`: feature branches opened from `dev`.

Local validation:

```bash
uv run --with pytest pytest tests -q
uv build
uvx twine check dist/*
python -m venv /tmp/claude-p-smoke
/tmp/claude-p-smoke/bin/python -m pip install dist/*.whl
/tmp/claude-p-smoke/bin/claude-p "Respond exactly: SMOKE_OK" --tools ''
```

Release:

1. Merge feature branch into `dev`.
2. Open PR from `dev` to `main`.
3. After merge, create a GitHub release tag, for example `v0.1.1`.
4. The `publish.yml` workflow publishes to PyPI when PyPI Trusted Publishing is configured.

## 中文说明

`claude-p` 是一个兼容 `claude -p` 调用方式的命令行工具和 Python SDK。它不调用
`claude -p` 本身，而是把交互式 Claude Code TUI 包装成可编程接口，让你在已经登录
Claude Code 订阅账号的环境里，用类似 `claude -p` 的方式跑脚本、agent harness、本地
评测和一次性自动化任务。

一句话：**把你已经付费、已经登录的交互式 Claude Code subscription 用到程序化工作流里。**

### 为什么需要 claude-p

很多 Claude Code 用户会把 `claude -p` 用在这些场景：

- shell 脚本和本地自动化；
- agent runner / benchmark harness；
- 本地 eval 和 CI-like 工作流；
- 需要 JSON 或 stream-json 输出的工具链；
- Python 代码里调用 Claude agent。

但在一些环境里，交互式 Claude Code 可以正常使用订阅账号登录态，而 `claude -p` 或
programmatic agent workflow 会遇到不同的额度、限制或不可用状态。

`claude-p` 的目标就是补这个 gap：

- 不需要 Anthropic API key；
- 不需要新账号；
- 不需要新订阅；
- 使用本机已有 Claude Code 登录态；
- 默认输出纯文本，支持 `json` 和 `stream-json`；
- 提供接近 Claude Agent SDK 形态的 Python API。

### 30 秒上手

推荐给命令行用户的安装方式：

```bash
uv tool install claude-p --force
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2
```

如果你想安装到当前 Python 环境里，请使用 Python 3.10+，并通过这个 Python 调 pip：

```bash
python -m pip install claude-p
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2
```

默认输出是纯文本，和 `claude -p` 的常用体验一致。

也可以输出结构化结果：

```bash
claude-p "Respond exactly: hello" --output-format json
claude-p "Respond exactly: hello" --output-format stream-json --include-partial-messages
```

如果 smoke 命令没有打印 `CLAUDE_P_OK`，先跑：

```bash
claude-p --doctor
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2 --raw-log /tmp/claude-p-smoke.raw.log
```

raw log 里能看到真实的交互式 Claude Code TUI 状态：workspace trust、auth、额度限制、
MCP 启动失败或其他本地阻塞。不要只看表层“没输出”。

### Drop-in 替换

| 你现在使用 | 可以尝试 |
|---|---|
| `claude -p "prompt"` | `claude-p "prompt"` |
| `claude -p --output-format json "prompt"` | `claude-p --output-format json "prompt"` |
| `claude -p --output-format stream-json` | `claude-p --output-format stream-json` |
| `claude -p --model sonnet` | `claude-p --model sonnet` |
| `claude -p --tools ''` | `claude-p --tools ''` |
| `claude -p --permission-mode default` | `claude-p --permission-mode default` |
| `from claude_agent_sdk import query` | `from claude_p import query` |

当前支持的常用参数包括：

- `-p`, `--print`
- `--model`
- `--tools`
- `--permission-mode`
- `--output-format text|json|stream-json`
- `--include-partial-messages`
- `--session-id`
- `--cwd`
- `--safe-mode`
- `--no-auto-trust` 用来禁用 wrapper 自动确认 workspace trust 提示
- 常见上下文和配置参数，例如 `--system-prompt`、`--append-system-prompt`、
  `--mcp-config`、`--settings`、`--plugin-dir`、`--allowedTools`、
  `--disallowedTools`、`--resume`、`--continue`

`--timeout-sec` 只控制 `claude-p` wrapper 自己等待多久。把它设为 `0` 可以关闭
wrapper timeout，适合长时间运行的 prompt：

```bash
claude-p "Run a long local task and summarize the result" --timeout-sec 0
```

### Python SDK

SDK 的形态尽量贴近官方 Claude Agent SDK，方便已有代码迁移。

```python
import asyncio
from claude_p import ClaudePOptions, query


async def main():
    options = ClaudePOptions(
        model="sonnet",
        tools="default",
        permission_mode="default",
    )

    async for message in query("How many files are in this directory?", options=options):
        print(message)


asyncio.run(main())
```

如果只需要最终结果：

```python
import asyncio
from claude_p import ClaudePClient, ClaudePOptions


async def main():
    async with ClaudePClient(ClaudePOptions(model="sonnet")) as client:
        result = await client.run("Respond exactly: SDK_OK")
        print(result.result)


asyncio.run(main())
```

### 工作原理

`claude-p` 不会直接调用 `claude -p`。

它的流程是：

1. 在 pseudo-TTY 里启动交互式 `claude`；
2. 传入确定性的 `--session-id`；
3. 等待 TUI 响应完成；
4. 从 Claude Code 的本地 session JSONL 读取结果：
   `~/.claude/projects/**/<session-id>.jsonl`；
5. 输出兼容 `claude -p` 的 `text`、`json` 或 `stream-json`。

读取 session JSONL 是关键设计。直接抓终端文本是不可靠的：TUI 的光标重绘、
spinner、宽字符和 redraw 都可能让捕获文本丢字。Claude Code 的 session JSONL 才是
最终 assistant message 和 result 的稳定来源。

### 当前可用能力

- 默认纯文本输出；
- 单次 JSON 结果输出；
- 核心 `stream-json` event shape；
- 通过交互式 Claude Code session 使用工具；
- headless 运行会自动确认 Claude Code 的标准 workspace trust 提示，以匹配
  `claude -p` 的非交互行为；`--safe-mode` 会单独转发给 Claude Code；
  可用 `--no-auto-trust` 禁用 wrapper 自动确认；只在你信任的目录中使用；
- Python SDK：`query(...)` 和 `ClaudePClient(...).run(...)`；
- 通过 `uv tool install claude-p` 或 `python -m pip install claude-p` 安装后提供
  全局命令 `claude-p`。

### 已知限制

`claude-p` 是开发者便利工具，不是官方 Anthropic API 的替代品。

当前限制：

- token usage、cost、rate-limit 字段是 best-effort placeholder；
- 暂不回放 `claude -p --include-hook-events` 的 hook lifecycle events；
- 接受 `--input-format stream-json` 参数，但尚未实现；
- `--bare` 与订阅登录态目标冲突，因为 Claude bare mode 会绕过 OAuth/keychain auth；
- 如果 Claude Code 大幅改变交互式 TUI 或本地 session 存储格式，可能需要适配。

生产级 agent workload 仍建议优先使用官方 Anthropic API / 官方 Claude Agent SDK。

### 验证清单

手动安装时，这两条命令应该给出和 README GIF 同类的可见 demo 结果：

```bash
uv tool install claude-p --force
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2
```

期望输出：

```text
CLAUDE_P_OK
```

如果把仓库交给另一个大模型/agent 安装和验证，让它按这组命令走：

```bash
git clone https://github.com/Equality-Machine/claude-p.git
cd claude-p
uv run --with pytest pytest tests -q
uv tool install . --force
claude-p --doctor
claude-p "Respond exactly: CLAUDE_P_OK" --tools '' --timeout-sec 45 --quiet-after-sec 2 --raw-log /tmp/claude-p-smoke.raw.log
```

如果最后没有打印 `CLAUDE_P_OK`，先检查 `/tmp/claude-p-smoke.raw.log`，不要直接猜原因。
大多数失败来自本机交互式 Claude Code 状态，而不是 PyPI 安装。

### FAQ

#### 这是绕过登录认证吗？

不是。`claude-p` 使用的是你本机已经认证过的 Claude Code session。如果你的机器上交互式
Claude Code 本来不能用，`claude-p` 也不会让它凭空可用。

#### 这是绕过计费或 rate limit 吗？

不是。它不会移除 Anthropic 侧的 rate limit 或账号策略。它只是把你的交互式 Claude
Code session 暴露成程序化接口；所有适用于你账号的限制仍然适用。

#### 为什么不直接用 `claude -p`？

如果 `claude -p` 已经满足你的需求，继续用它即可。`claude-p` 是给这些场景准备的：
交互式 Claude Code 可以用订阅登录态正常工作，但 `claude -p` 或 programmatic usage
不可用，或者先碰到不同的限制面。

#### 为什么读取 session JSONL，而不是读取终端文本？

因为终端捕获不够可靠。实际测试里，TUI 渲染层会在 redraw 过程中丢字符，但 Claude
Code 的 session JSONL 包含准确的最终 assistant message。

#### 会不会失效？

可能。它依赖交互式 Claude Code 行为和本地 session JSONL 格式。项目保持很小，是为了
在 Claude Code 变化时能快速修复。

### 安装排查

`claude-p` 需要 Python 3.10+，并且需要本机已有可用的 Claude Code 登录态。

对普通用户最稳的安装方式是：

```bash
uv tool install claude-p --force
claude-p --help
claude-p "Respond exactly: OK" --tools ''
```

如果还没有 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL -l
uv tool install claude-p --force
```

如果你更想用 `pip`，请从 Python 3.10+ 解释器调用 pip：

```bash
python --version
python -m pip install claude-p
python -m pip show -f claude-p
which claude-p
```

常见安装失败：

| 现象 | 原因 | 解决方式 |
|---|---|---|
| `zsh: command not found: pip` | 当前 shell 里没有 `pip` 命令。 | 用 `python -m pip ...`，或直接 `uv tool install claude-p`。 |
| `No matching distribution found for claude-p` | 通常是 Python/pip 太旧，或 Python 版本低于 3.10。 | 先看 `python3 --version`；推荐 `uv tool install claude-p`，或换 Python 3.11/3.12。 |
| 安装后 `claude-p: command not found` | Python scripts 目录不在 `PATH`。 | 把 `~/.local/bin` 加到 `PATH`，或用 `uv tool run claude-p ...`。 |
| 一个终端能 import，另一个不行 | `pip` 和 `python` 指向不同环境。 | 在目标环境里始终使用 `python -m pip install claude-p`。 |

conda / venv 用户：

```bash
conda activate your-env
python -m pip install claude-p
which python
which claude-p
claude-p "Respond exactly: OK"
```

macOS 用户不要优先依赖 Apple Command Line Tools 自带的旧 `pip3`。它可能看不到现代
Python wheel 或因为 Python 版本太低报 `No matching distribution found`。优先使用
`uv tool install claude-p`、Homebrew Python，或 conda/venv。

### 开发和发布流程

分支约定：

- `main`：只放已经发布的版本；
- `dev`：集成分支；
- `feat/<name>`：从 `dev` 拉出的功能分支。

本地验证：

```bash
uv run --with pytest pytest tests -q
uv build
uvx twine check dist/*
python -m venv /tmp/claude-p-smoke
/tmp/claude-p-smoke/bin/python -m pip install dist/*.whl
/tmp/claude-p-smoke/bin/claude-p "Respond exactly: SMOKE_OK" --tools ''
```

发布流程：

1. 将 feature branch 合并到 `dev`；
2. 从 `dev` 向 `main` 开 PR；
3. 合并后创建 GitHub release tag，例如 `v0.1.1`；
4. 如果 PyPI Trusted Publishing 已配置，`publish.yml` workflow 会自动发布到 PyPI。

## License

MIT
