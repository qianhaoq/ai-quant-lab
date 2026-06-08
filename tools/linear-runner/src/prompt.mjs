function formatLabels(issue) {
  return (issue.labels?.nodes ?? []).map((label) => label.name).join(", ") || "无";
}

function formatComments(issue) {
  const comments = issue.comments?.nodes ?? [];
  if (!comments.length) {
    return "无";
  }

  return comments
    .slice(-10)
    .map((comment) => {
      const author = comment.user?.name || "unknown";
      return `### ${author} @ ${comment.createdAt}\n${comment.body}`;
    })
    .join("\n\n");
}

export function buildCodexPrompt({ issue, config }) {
  return `你是 ai-quant-lab 的自动队列 Runner 调起的 Codex 实现 Agent。

请在当前 git worktree 中完成 Linear issue，不要切换仓库，不要创建/推送分支，不要创建 PR，不要修改 Linear；这些由 Runner 负责。

## 必须遵守

- 用中文写面向人的说明、文档和 PR 内容。
- 遵守仓库 AGENTS.md。
- 默认保持内部沙箱、mock fallback 和无 key 可运行。
- 不得加入未受保护的真实下单能力，不得绕过风控预检、确认短语、功能开关或人工评审。
- 不得写入真实 secret、token、账号凭证或券商密钥。
- 修改代码后补必要测试。
- 保持改动小、可审查、可回滚。

## Linear issue

- ID: ${issue.identifier}
- 标题: ${issue.title}
- URL: ${issue.url}
- Priority: ${issue.priority || "none"}
- Estimate: ${issue.estimate || "none"}
- Labels: ${formatLabels(issue)}

## 描述

${issue.description || "无描述"}

## 最近评论

${formatComments(issue)}

## Runner 验收

Runner 会在你完成后执行这些命令：

${config.testCommands.map((command) => `- \`${command}\``).join("\n")}

请直接完成实现。最终回复只需要简要说明改了什么、跑了什么测试、还有什么风险。`;
}
