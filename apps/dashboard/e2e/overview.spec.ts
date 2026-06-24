import { expect, test } from "@playwright/test";

// Overview landing: showcases the capabilities and the AI copilot, and routes to
// the tools.
test("overview highlights features and links to the match tool", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("AI copilot").first()).toBeVisible();
  await expect(page.getByText(/Deterministic engine/i)).toBeVisible();
  await expect(page.getByText(/Regression-safe rate cards/i)).toBeVisible();

  await page.getByRole("link", { name: /Run a match/i }).first().click();
  await expect(page).toHaveURL(/\/match$/);
  await expect(page.getByTestId("borrower-form")).toBeVisible();
});
