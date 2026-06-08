import assert from "node:assert/strict";
import test from "node:test";
import {
  branchNameForIssue,
  policyDecision,
  reviewStateForIssue,
  selectNextIssue,
  slugify,
} from "../src/policy.mjs";

const config = {
  requiredLabel: "ai-agent-ready",
  allowTradingRisk: false,
  aiReviewState: "AI 评审",
  humanReviewState: "人工评审",
};

function issue(overrides) {
  return {
    identifier: "ONE-5",
    title: "订单台账与审计记录",
    priority: 2,
    createdAt: "2026-06-05T00:00:00.000Z",
    labels: {
      nodes: [{ name: "ai-agent-ready" }],
    },
    ...overrides,
  };
}

test("slugify keeps ASCII parts and falls back for Chinese-only titles", () => {
  assert.equal(slugify("Alpaca Paper 交易适配器"), "alpaca-paper");
  assert.equal(slugify("订单台账与审计记录", "one-5"), "one-5");
});

test("branchNameForIssue always includes the Linear identifier", () => {
  assert.equal(branchNameForIssue(issue({ title: "订单台账与审计记录" })), "one-5");
  assert.equal(branchNameForIssue(issue({ title: "PR 预览环境" })), "one-5-pr");
});

test("policy blocks trading-risk issues unless explicitly allowed", () => {
  const decision = policyDecision(
    issue({
      labels: {
        nodes: [{ name: "ai-agent-ready" }, { name: "risk:trading" }],
      },
    }),
    config,
  );

  assert.equal(decision.allowed, false);
  assert.match(decision.reason, /risk:trading/);
});

test("selectNextIssue chooses allowed high-priority item first", () => {
  const blocked = issue({
    identifier: "ONE-8",
    priority: 1,
    labels: {
      nodes: [{ name: "ai-agent-ready" }, { name: "risk:trading" }],
    },
  });
  const allowed = issue({
    identifier: "ONE-6",
    title: "PR 预览环境",
    priority: 2,
  });

  const selected = selectNextIssue([allowed, blocked], config).selected;
  assert.equal(selected.issue.identifier, "ONE-6");
});

test("reviewStateForIssue sends trading risk to human review", () => {
  assert.equal(reviewStateForIssue(issue({}), config), "AI 评审");
  assert.equal(
    reviewStateForIssue(
      issue({
        labels: {
          nodes: [{ name: "ai-agent-ready" }, { name: "risk:trading" }],
        },
      }),
      config,
    ),
    "人工评审",
  );
});
