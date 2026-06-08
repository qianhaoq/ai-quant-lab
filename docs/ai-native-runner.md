# AI-native Linear 队列 Runner

`tools/linear-runner` 是 v0 队列调度器，用来把 Linear 中的 `待 Agent 处理` issue 自动转成隔离 worktree 中的 Codex 实现任务。

它不是生产发布器，也不会自动 merge。默认只处理不带 `risk:trading` 的 issue；交易相关 issue 必须显式允许后才能自动实现，并且完成后仍进入人工评审。

## 状态机

```text
待 Agent 处理
  -> Agent 执行中
  -> AI 评审 / 人工评审
  -> 预览验证
  -> 待合并
```

失败时默认回到 `待 Agent 处理`，并在 Linear 评论中写入错误摘要和 `run_id`。

## 本地 dry-run

dry-run 只读取 Linear，不会修改 Linear、GitHub 或本地文件。

```bash
export LINEAR_API_KEY=<linear-api-key>
pnpm runner:dry-run
```

定向查看某个 issue：

```bash
pnpm runner:dry-run -- --issue ONE-5
```

## 单次执行

单次执行会产生外部副作用：更新 Linear 状态和评论、创建 git worktree、调用 `codex exec`、push 分支、创建 GitHub draft PR。

```bash
export LINEAR_API_KEY=<linear-api-key>
export RUNNER_REPO=qianhaoq/ai-quant-lab
pnpm runner:once
```

定向执行：

```bash
pnpm runner:once -- --issue ONE-6
```

执行前请确认：

- `gh auth status` 已通过，或者设置了 `GH_TOKEN` / `GITHUB_TOKEN`。
- `codex` 已安装并完成登录，或者为单次 `codex exec` 提供 `CODEX_API_KEY`。
- 当前 repo 工作区是干净的。
- 目标 issue 有 `ai-agent-ready` 标签。

## 默认命令

Runner 默认会先准备环境：

```bash
pnpm install --frozen-lockfile
pnpm api:install
```

然后在 Codex 完成修改后执行：

```bash
pnpm api:test
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm test:e2e
```

可以用环境变量覆盖：

```bash
export RUNNER_SETUP_COMMANDS='pnpm install --frozen-lockfile|pnpm api:install'
export RUNNER_TEST_COMMANDS='pnpm api:test|pnpm lint|pnpm typecheck|pnpm test|pnpm build'
```

命令之间用 `|` 或换行分隔。

## 交易风险策略

默认策略：

- 带 `risk:trading` 的 issue 会在 dry-run 中显示为跳过。
- Runner 不会自动处理真实交易、券商 secret、live trading 开关相关 issue。
- 即使允许自动实现，最终状态也会进入 `人工评审`，不会进入自动合并路径。

如果只是要自动生成代码和 draft PR，可以显式开启：

```bash
export RUNNER_ALLOW_TRADING_RISK=true
pnpm runner:once -- --issue ONE-5
```

开启后仍然不能自动 merge，也不能写入真实 Alpaca 或其他券商凭证。

## 定时轮询版本

macOS `launchd` 或 cron 可以每 5 分钟执行一次：

```bash
cd /Users/qianhao02/codex/ai-quant-lab
pnpm runner:once
```

建议先运行一周 dry-run 或手动 `--issue`，确认队列和策略稳定后再开启定时执行。

## Webhook 版本

v1 可以把轮询替换成 Linear Webhook：

1. 在 Linear API 设置中创建 webhook，订阅 `Issue`。
2. Webhook endpoint 校验 `Linear-Signature`。
3. 当 issue 状态变成 `待 Agent 处理` 且有 `ai-agent-ready` 标签时，将 issue id 放入队列。
4. 后台 worker 调用当前 Runner 的 `--issue <id>` 路径。

Webhook endpoint 必须是公网 HTTPS；本地开发可用 tunnel，但不要在 tunnel 中暴露 secret。

## GitHub Actions 版本

不建议直接在同一个 job 中把 `CODEX_API_KEY` 暴露给仓库脚本。更安全的做法是：

- job A 只读 checkout，运行 Codex 并产出 patch artifact。
- job B 没有 Codex key，应用 patch、push 分支、创建 PR。

本地 Runner 当前更适合自托管机器或受控 dev box。

## 产物

每次运行会在 ignored 目录中写入运行材料：

```text
tools/linear-runner/state/runs/<issue>-<run_id>/
  issue.json
  prompt.md
  codex.jsonl
```

这些文件不入库，用于本地审计和排障。
