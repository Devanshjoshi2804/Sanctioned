import { expect, test } from "@playwright/test";

// AA ingestion journey: autofill income from a sandbox statement, then run the
// match on the autofilled borrower.
test("autofills income from a sandbox statement and matches", async ({ page }) => {
  await page.goto("/");

  // Change income to a sentinel so we can prove the autofill overwrote it.
  await page.fill('input[name="net_monthly_income"]', "1");
  await page.getByTestId("autofill-sandbox").click();

  await expect(page.locator('input[name="net_monthly_income"]')).toHaveValue("90000");
  await expect(page.locator('input[name="existing_monthly_obligations"]')).toHaveValue("12000");

  await page.getByTestId("run-match").click();
  await expect(page.getByTestId("match-grid")).toBeVisible();
  await expect(page.getByTestId("lender-row")).toHaveCount(4);
});
