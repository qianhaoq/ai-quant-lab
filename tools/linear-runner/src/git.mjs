import fs from "node:fs/promises";
import path from "node:path";
import { branchNameForIssue } from "./policy.mjs";
import { requireSuccess, runCommand, runShell, stripSensitiveEnv } from "./process.mjs";

export async function discoverRepoRoot(cwd) {
  const result = await runCommand("git", ["rev-parse", "--show-toplevel"], {
    cwd,
    env: stripSensitiveEnv(),
  });
  requireSuccess(result);
  return result.stdout.trim();
}

export async function ensureCleanWorktree(repoDir) {
  const result = await runCommand("git", ["status", "--porcelain"], {
    cwd: repoDir,
    env: stripSensitiveEnv(),
  });
  requireSuccess(result);
  if (result.stdout.trim()) {
    throw new Error(`当前仓库有未提交改动，Runner 不会在脏工作区启动：\n${result.stdout}`);
  }
}

export async function prepareWorktree({ config, issue }) {
  const branch = branchNameForIssue(issue);
  const worktreePath = path.join(config.worktreesDir, branch);

  await fs.mkdir(config.worktreesDir, { recursive: true });

  const pathExists = await fs
    .stat(worktreePath)
    .then(() => true)
    .catch(() => false);
  if (pathExists) {
    throw new Error(`worktree 路径已存在：${worktreePath}`);
  }

  requireSuccess(
    await runCommand("git", ["fetch", "origin", config.baseBranch], {
      cwd: config.repoDir,
      env: stripSensitiveEnv(),
      stream: true,
    }),
  );

  const localBranch = await runCommand("git", ["show-ref", "--verify", "--quiet", `refs/heads/${branch}`], {
    cwd: config.repoDir,
    env: stripSensitiveEnv(),
  });
  if (localBranch.code === 0) {
    throw new Error(`本地分支已存在：${branch}`);
  }

  const remoteBranch = await runCommand("git", ["ls-remote", "--exit-code", "--heads", "origin", branch], {
    cwd: config.repoDir,
    env: stripSensitiveEnv(),
  });
  if (remoteBranch.code === 0) {
    throw new Error(`远端分支已存在：${branch}`);
  }

  requireSuccess(
    await runCommand("git", ["worktree", "add", worktreePath, "-b", branch, `origin/${config.baseBranch}`], {
      cwd: config.repoDir,
      env: stripSensitiveEnv(),
      stream: true,
    }),
  );

  return {
    branch,
    worktreePath,
  };
}

export async function hasChanges(worktreePath) {
  const result = await runCommand("git", ["status", "--porcelain"], {
    cwd: worktreePath,
    env: stripSensitiveEnv(),
  });
  requireSuccess(result);
  return Boolean(result.stdout.trim());
}

function commitMessage(issue, testSummary) {
  return `${issue.identifier} 自动处理队列任务\n\n通过 Linear Runner 将已准备好的 issue 转成可评审代码变更，保持自动化过程可追踪。\n\nConstraint: Linear issue ${issue.identifier} 是本次任务来源\nConfidence: medium\nScope-risk: moderate\nDirective: 真实交易能力仍必须经过风控预检、功能开关、人工确认和人工评审\nTested: ${testSummary || "Runner configured tests"}\nNot-tested: 真实券商凭证和生产部署`;
}

export async function commitAndPush({ issue, worktreePath, branch, testSummary }) {
  if (!(await hasChanges(worktreePath))) {
    throw new Error("Codex 执行后没有产生任何文件改动。");
  }

  requireSuccess(
    await runCommand("git", ["add", "-A"], {
      cwd: worktreePath,
      env: stripSensitiveEnv(),
      stream: true,
    }),
  );

  requireSuccess(
    await runCommand("git", ["commit", "-m", commitMessage(issue, testSummary)], {
      cwd: worktreePath,
      env: stripSensitiveEnv(),
      stream: true,
    }),
  );

  requireSuccess(
    await runCommand("git", ["push", "-u", "origin", branch], {
      cwd: worktreePath,
      env: stripSensitiveEnv(process.env, ["GH_TOKEN", "GITHUB_TOKEN"]),
      stream: true,
    }),
  );
}

export async function createDraftPr({ config, issue, worktreePath, branch, testSummary, riskSummary }) {
  const body = `## 关联任务

- Linear：${issue.identifier} ${issue.title}

## 本次变更

由 Linear Runner 自动处理队列 issue 后生成。请人工检查 diff、交易安全边界和测试结果。

## 验证结果

${testSummary}

## 风险说明

${riskSummary}

## Runner 约束

- PR 默认为 draft。
- 不自动 merge。
- 不写入真实 secret。
- 真实交易相关能力必须继续停在人工评审。`;

  const bodyPath = path.join(worktreePath, ".runner-pr-body.md");
  await fs.writeFile(bodyPath, body, "utf8");

  const result = await runShell(
    `gh pr create --draft --base ${quote(config.baseBranch)} --head ${quote(branch)} --title ${quote(`${issue.identifier} ${issue.title}`)} --body-file .runner-pr-body.md`,
    {
      cwd: worktreePath,
      env: stripSensitiveEnv(process.env, ["GH_TOKEN", "GITHUB_TOKEN"]),
      stream: true,
    },
  );
  requireSuccess(result);
  await fs.rm(bodyPath, { force: true });

  const url = result.stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line.startsWith("https://github.com/"));

  if (!url) {
    throw new Error(`无法从 gh pr create 输出中解析 PR URL：${result.stdout}`);
  }

  return url;
}

function quote(value) {
  return `'${String(value).replace(/'/g, "'\\''")}'`;
}
