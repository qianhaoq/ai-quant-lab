import { expect, test } from "@playwright/test";

test("runs a sample backtest and asks the research copilot", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /run backtest/i }).click();
  await expect(page.getByText("Total Return")).toBeVisible();
  await expect(page.getByLabel("Equity curve")).toBeVisible();
  await page.getByLabel("Ask research question").fill("What should I inspect next?");
  await page.getByRole("button", { name: /ask ai/i }).click();
  await expect(page.getByText(/Research-only summary/)).toBeVisible();
});
