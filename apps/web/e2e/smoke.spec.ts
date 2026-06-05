import { expect, test } from "@playwright/test";

test("previews a guarded sandbox order and asks the AI researcher", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "AI 量化交易平台" })).toBeVisible();
  await page.getByRole("button", { name: /风控预检/i }).click();
  await expect(page.locator(".preview-banner").filter({ hasText: "预检通过" })).toBeVisible();
  await expect(page.getByLabel("风控检查")).toContainText("标的白名单");
  await page.getByRole("button", { name: /确认提交到沙箱/i }).click();
  await expect(page.getByText("订单已进入内部沙箱")).toBeVisible();
  await page.getByLabel("输入研究问题").fill("下一步应该检查什么？");
  await page.getByRole("button", { name: /询问 AI/i }).click();
  await expect(page.getByText(/交易研究摘要/)).toBeVisible();
});
