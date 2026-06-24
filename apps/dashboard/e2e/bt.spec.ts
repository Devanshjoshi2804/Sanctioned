import { expect, test } from "@playwright/test";

// Balance-transfer journey: switch product, supply the outstanding and existing
// rate, and confirm the indicative monthly saving surfaces in the trace panel.
test("balance transfer surfaces the monthly saving", async ({ page }) => {
  await page.goto("/");

  await page.selectOption('select[name="product_type"]', "BALANCE_TRANSFER");
  await page.fill('input[name="existing_loan_outstanding"]', "4000000");
  await page.fill('input[name="existing_rate_pct"]', "9.5");
  await page.getByTestId("run-match").click();

  const rows = page.getByTestId("lender-row");
  await expect(rows).toHaveCount(4);

  // Expand the top lender; an approved transfer to a cheaper lender shows a saving.
  await rows.first().getByRole("button").click();
  await expect(page.getByTestId("monthly-saving")).toBeVisible();
});
