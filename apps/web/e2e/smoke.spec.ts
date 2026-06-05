import { expect, test } from "@playwright/test";

test("runs a sample backtest and asks the research copilot", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /运行回测/i }).click();
  await expect(page.getByText("总收益")).toBeVisible();
  await expect(page.getByLabel("资金曲线")).toBeVisible();
  await page.getByLabel("输入研究问题").fill("下一步应该检查什么？");
  await page.getByRole("button", { name: /询问 AI/i }).click();
  await expect(page.getByText(/研究模式摘要/)).toBeVisible();
});
