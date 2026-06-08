export function hasLabel(issue, labelName) {
  return (issue.labels?.nodes ?? issue.labels ?? []).some((label) => label.name === labelName);
}

export function slugify(value, fallback = "issue") {
  const slug = String(value ?? "")
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .toLowerCase()
    .replace(/[_\s]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

  return slug || fallback;
}

export function branchNameForIssue(issue, suffix = "") {
  const identifier = slugify(issue.identifier, "issue");
  const title = slugify(issue.title, "");
  const titlePart = title ? `-${title}` : "";
  const suffixPart = suffix ? `-${slugify(suffix, "run")}` : "";
  return `${identifier}${titlePart}${suffixPart}`.slice(0, 80);
}

function priorityRank(priority) {
  if (!priority || priority <= 0) {
    return 99;
  }
  return priority;
}

export function sortIssuesForQueue(issues) {
  return [...issues].sort((left, right) => {
    const byPriority = priorityRank(left.priority) - priorityRank(right.priority);
    if (byPriority !== 0) {
      return byPriority;
    }
    return new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime();
  });
}

export function policyDecision(issue, config) {
  const labels = issue.labels?.nodes ?? issue.labels ?? [];
  const labelNames = labels.map((label) => label.name);
  const isTradingRisk = labelNames.includes("risk:trading");
  const isSecurityRisk = labelNames.includes("risk:security");

  if (!labelNames.includes(config.requiredLabel)) {
    return {
      allowed: false,
      reason: `缺少必要标签 ${config.requiredLabel}`,
      isTradingRisk,
      isSecurityRisk,
    };
  }

  if (isTradingRisk && !config.allowTradingRisk) {
    return {
      allowed: false,
      reason: "包含 risk:trading，默认不允许全自动执行；需要 RUNNER_ALLOW_TRADING_RISK=true",
      isTradingRisk,
      isSecurityRisk,
    };
  }

  return {
    allowed: true,
    reason: "符合自动执行策略",
    isTradingRisk,
    isSecurityRisk,
  };
}

export function selectNextIssue(issues, config) {
  const ordered = sortIssuesForQueue(issues);
  const evaluated = ordered.map((issue) => ({
    issue,
    decision: policyDecision(issue, config),
  }));

  return {
    evaluated,
    selected: evaluated.find((item) => item.decision.allowed) ?? null,
  };
}

export function reviewStateForIssue(issue, config) {
  const labels = issue.labels?.nodes ?? issue.labels ?? [];
  const hasTradingRisk = labels.some((label) => label.name === "risk:trading");
  return hasTradingRisk ? config.humanReviewState : config.aiReviewState;
}

export function shortIssueLine(issue, decision) {
  const labels = (issue.labels?.nodes ?? issue.labels ?? []).map((label) => label.name).join(", ");
  return `${issue.identifier} ${issue.title} | priority=${issue.priority || "none"} | labels=${labels || "none"} | ${decision.allowed ? "可执行" : `跳过：${decision.reason}`}`;
}
