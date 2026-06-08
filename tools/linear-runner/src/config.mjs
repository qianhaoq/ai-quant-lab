import path from "node:path";
import { splitCommandList, shellSplit } from "./process.mjs";

const DEFAULT_SETUP_COMMANDS = "pnpm install --frozen-lockfile|pnpm api:install";
const DEFAULT_TEST_COMMANDS = "pnpm api:test|pnpm lint|pnpm typecheck|pnpm test|pnpm build|pnpm test:e2e";

export function parseArgs(argv) {
  const args = {
    dryRun: false,
    once: false,
    issue: null,
    limit: null,
    help: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--dry-run") {
      args.dryRun = true;
    } else if (arg === "--once") {
      args.once = true;
    } else if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else if (arg === "--issue") {
      args.issue = argv[index + 1];
      index += 1;
    } else if (arg.startsWith("--issue=")) {
      args.issue = arg.slice("--issue=".length);
    } else if (arg === "--limit") {
      args.limit = Number(argv[index + 1]);
      index += 1;
    } else if (arg.startsWith("--limit=")) {
      args.limit = Number(arg.slice("--limit=".length));
    } else {
      throw new Error(`未知参数：${arg}`);
    }
  }

  if (!args.once) {
    args.dryRun = true;
  }
  if (args.once && args.dryRun) {
    throw new Error("`--once` 和 `--dry-run` 不能同时使用。");
  }

  return args;
}

function envBoolean(env, key, fallback = false) {
  const value = env[key];
  if (value === undefined || value === "") {
    return fallback;
  }
  return ["1", "true", "yes", "y"].includes(value.toLowerCase());
}

function envNumber(env, key, fallback) {
  const value = Number(env[key]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

export function readConfig({ argv = process.argv.slice(2), env = process.env, cwd = process.cwd() } = {}) {
  const args = parseArgs(argv);
  const repoDir = path.resolve(env.RUNNER_REPO_DIR || cwd);
  const defaultWorktreesDir = path.resolve(path.dirname(repoDir), ".runner-worktrees");

  return {
    ...args,
    linearApiKey: env.LINEAR_API_KEY || "",
    repo: env.RUNNER_REPO || "qianhaoq/ai-quant-lab",
    repoDir,
    baseBranch: env.RUNNER_BASE_BRANCH || "main",
    worktreesDir: path.resolve(env.RUNNER_WORKTREES_DIR || defaultWorktreesDir),
    teamKey: env.RUNNER_TEAM_KEY || "ONE",
    readyState: env.RUNNER_READY_STATE || "待 Agent 处理",
    runningState: env.RUNNER_RUNNING_STATE || "Agent 执行中",
    aiReviewState: env.RUNNER_AI_REVIEW_STATE || "AI 评审",
    humanReviewState: env.RUNNER_HUMAN_REVIEW_STATE || "人工评审",
    failureState: env.RUNNER_FAILURE_STATE || "待 Agent 处理",
    requiredLabel: env.RUNNER_REQUIRED_LABEL || "ai-agent-ready",
    allowTradingRisk: envBoolean(env, "RUNNER_ALLOW_TRADING_RISK", false),
    selectionLimit: args.limit || envNumber(env, "RUNNER_SELECTION_LIMIT", 20),
    maxAttempts: envNumber(env, "RUNNER_MAX_ATTEMPTS", 2),
    setupCommands: splitCommandList(env.RUNNER_SETUP_COMMANDS, DEFAULT_SETUP_COMMANDS),
    testCommands: splitCommandList(env.RUNNER_TEST_COMMANDS, DEFAULT_TEST_COMMANDS),
    codexCommand: env.RUNNER_CODEX_COMMAND || "codex",
    codexArgs: shellSplit(env.RUNNER_CODEX_ARGS || "exec --json --sandbox workspace-write -"),
    runId: env.RUNNER_RUN_ID || new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14),
  };
}

export function printHelp() {
  console.log(`Linear 队列 Runner v0

用法：
  pnpm runner:dry-run
  pnpm runner:once
  pnpm runner:once -- --issue ONE-5

关键环境变量：
  LINEAR_API_KEY              Linear API token，dry-run/once 都需要
  RUNNER_REPO                 GitHub repo，默认 qianhaoq/ai-quant-lab
  RUNNER_TEAM_KEY             Linear team key，默认 ONE
  RUNNER_READY_STATE          队列入口状态，默认 待 Agent 处理
  RUNNER_RUNNING_STATE        认领状态，默认 Agent 执行中
  RUNNER_ALLOW_TRADING_RISK   是否允许自动处理 risk:trading，默认 false
  RUNNER_TEST_COMMANDS        用 | 或换行分隔的测试命令
`);
}

export function validateConfig(config) {
  if (!config.linearApiKey) {
    throw new Error("缺少 LINEAR_API_KEY。请在本地 shell 或 runner secret 中配置 Linear API token。");
  }
}
