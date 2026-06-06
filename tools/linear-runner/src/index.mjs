#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { runCodex, runCommandSequence } from "./codex.mjs";
import { printHelp, readConfig, validateConfig } from "./config.mjs";
import {
  commitAndPush,
  createDraftPr,
  discoverRepoRoot,
  ensureCleanWorktree,
  prepareWorktree,
} from "./git.mjs";
import {
  LinearClient,
  countRunnerAttempts,
  createAttachment,
  createComment,
  getIssueDetails,
  listQueueIssues,
  loadTeamContext,
  updateIssueState,
} from "./linear.mjs";
import { buildCodexPrompt } from "./prompt.mjs";
import { reviewStateForIssue, selectNextIssue, shortIssueLine } from "./policy.mjs";
import { assertCommandExists } from "./process.mjs";

async function main() {
  const config = readConfig();

  if (config.help) {
    printHelp();
    return;
  }

  validateConfig(config);
  config.repoDir = await discoverRepoRoot(config.repoDir);

  const client = new LinearClient(config.linearApiKey);
  const context = await loadTeamContext(client, config);
  const queueIssues = await listQueueIssues(client, config, context);
  const { evaluated, selected } = selectNextIssue(queueIssues, config);

  if (config.dryRun) {
    printDryRun(config, context, evaluated);
    return;
  }

  await runOnce({ config, client, context, selected });
}

function printDryRun(config, context, evaluated) {
  console.log("Linear Runner dry-run：不会修改 Linear、GitHub 或本地文件。");
  console.log(`Team: ${context.team.name} (${context.team.key})`);
  console.log(`状态: ${config.readyState}`);
  console.log(`必要标签: ${config.requiredLabel}`);
  console.log(`允许 risk:trading: ${config.allowTradingRisk ? "是" : "否"}`);

  if (!evaluated.length) {
    console.log("\n未找到符合状态和标签的候选 issue。");
    return;
  }

  console.log("\n候选队列：");
  for (const item of evaluated) {
    console.log(`- ${shortIssueLine(item.issue, item.decision)}`);
  }

  const next = evaluated.find((item) => item.decision.allowed);
  if (next) {
    console.log(`\n下一条将处理：${next.issue.identifier} ${next.issue.title}`);
  } else {
    console.log("\n当前没有通过策略检查的 issue。");
  }
}

async function runOnce({ config, client, context, selected }) {
  if (!selected) {
    console.log("没有可执行的 issue，Runner 退出。");
    return;
  }

  await assertCommandExists("git");
  await assertCommandExists("gh");
  await assertCommandExists(config.codexCommand);
  await ensureCleanWorktree(config.repoDir);

  const issue = await getIssueDetails(client, selected.issue.identifier);
  const attempts = countRunnerAttempts(issue);
  if (attempts >= config.maxAttempts) {
    throw new Error(`${issue.identifier} 已达到最大自动尝试次数：${attempts}/${config.maxAttempts}`);
  }

  const runRoot = path.join(config.repoDir, "tools", "linear-runner", "state", "runs", `${issue.identifier}-${config.runId}`);
  const lockPath = path.join(config.repoDir, "tools", "linear-runner", "state", "locks", `${issue.identifier}.json`);
  await acquireLock(lockPath, { issue: issue.identifier, runId: config.runId, createdAt: new Date().toISOString() });

  let worktree = null;
  try {
    console.log(`认领 issue：${issue.identifier} ${issue.title}`);
    await updateIssueState(client, issue, context.states.get(config.runningState));
    await createComment(
      client,
      issue,
      `Agent Runner 已认领。\n\n- run_id: \`${config.runId}\`\n- base: \`${config.baseBranch}\`\n- 策略：自动实现、自动测试、创建 draft PR；不自动 merge。`,
    );

    worktree = await prepareWorktree({ config, issue });
    await fs.mkdir(runRoot, { recursive: true });
    await fs.writeFile(path.join(runRoot, "issue.json"), JSON.stringify(issue, null, 2), "utf8");

    const setup = await runCommandSequence(config.setupCommands, worktree.worktreePath, "Setup");
    if (!setup.ok) {
      throw commandFailure("环境准备失败", setup.failed);
    }

    const prompt = buildCodexPrompt({ issue, config });
    await fs.writeFile(path.join(runRoot, "prompt.md"), prompt, "utf8");
    const codexResult = await runCodex({ config, worktreePath: worktree.worktreePath, prompt, runDir: runRoot });
    if (codexResult.code !== 0) {
      throw commandFailure("Codex 执行失败", codexResult);
    }

    const tests = await runCommandSequence(config.testCommands, worktree.worktreePath, "Test");
    if (!tests.ok) {
      throw commandFailure("测试失败", tests.failed);
    }

    const testSummary = config.testCommands.map((command) => `- [x] \`${command}\``).join("\n");
    const riskSummary = riskSummaryForIssue(issue);
    await commitAndPush({
      issue,
      worktreePath: worktree.worktreePath,
      branch: worktree.branch,
      testSummary: config.testCommands.join("; "),
    });

    const prUrl = await createDraftPr({
      config,
      issue,
      worktreePath: worktree.worktreePath,
      branch: worktree.branch,
      testSummary,
      riskSummary,
    });

    await createAttachment(client, issue, {
      title: `${issue.identifier} Draft PR`,
      url: prUrl,
    }).catch((error) => {
      console.warn(`创建 Linear 附件失败，继续写评论：${error.message}`);
    });
    await createComment(
      client,
      issue,
      `Agent Runner 已完成实现并创建草稿 PR：\n${prUrl}\n\n验证结果：\n${testSummary}\n\n下一步状态将进入 \`${reviewStateForIssue(issue, config)}\`。`,
    );

    await updateIssueState(client, issue, context.states.get(reviewStateForIssue(issue, config)));
    console.log(`完成：${issue.identifier} -> ${prUrl}`);
  } catch (error) {
    await createComment(
      client,
      issue,
      `Agent Runner 本次执行失败。\n\n- run_id: \`${config.runId}\`\n- 错误：\n\n\`\`\`\n${String(error.message).slice(0, 3500)}\n\`\`\`\n\nRunner 会把 issue 放回 \`${config.failureState}\`，等待人工检查或下一次重试。`,
    ).catch(() => {});
    await updateIssueState(client, issue, context.states.get(config.failureState)).catch(() => {});
    throw error;
  } finally {
    await fs.rm(lockPath, { force: true }).catch(() => {});
  }
}

async function acquireLock(lockPath, payload) {
  await fs.mkdir(path.dirname(lockPath), { recursive: true });
  const exists = await fs
    .stat(lockPath)
    .then(() => true)
    .catch(() => false);
  if (exists) {
    throw new Error(`issue 已被锁定：${lockPath}`);
  }
  await fs.writeFile(lockPath, JSON.stringify(payload, null, 2), { flag: "wx" });
}

function commandFailure(prefix, result) {
  const output = `${result.stdout || ""}\n${result.stderr || ""}`.trim().slice(-4000);
  return new Error(`${prefix}：${result.title}\n${output}`);
}

function riskSummaryForIssue(issue) {
  const labels = (issue.labels?.nodes ?? []).map((label) => label.name);
  const lines = ["- PR 默认为 draft，必须人工 review 后才能合并。"];
  if (labels.includes("risk:trading")) {
    lines.push("- 当前 issue 带 `risk:trading`，不得自动合并或自动开启 live trading。");
    lines.push("- 请人工检查风控、确认短语、功能开关、券商模式和密钥边界。");
  }
  if (labels.includes("risk:security")) {
    lines.push("- 当前 issue 带 `risk:security`，请人工检查 secret、日志和权限边界。");
  }
  return lines.join("\n");
}

main().catch((error) => {
  console.error(`Runner 失败：${error.message}`);
  process.exitCode = 1;
});
