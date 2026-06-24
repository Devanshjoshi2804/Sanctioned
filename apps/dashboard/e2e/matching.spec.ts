import { expect, test } from "@playwright/test";

// Matching journey: a sub-prime borrower should produce a mix of verdicts, and the
// grid must rank eligible lenders ahead of rejected ones.
test("ranks eligible lenders first and shows rejections for weak credit", async ({ page }) => {
  await page.goto("/");

  await page.fill('input[name="cibil"]', "690");
  await page.fill('input[name="net_monthly_income"]', "45000");
  await page.getByTestId("run-match").click();

  const rows = page.getByTestId("lender-row");
  await expect(rows).toHaveCount(4);

  // At least one lender rejects this borrower.
  await expect(page.locator('[data-testid="lender-row"][data-decision="REJECT"]').first()).toBeVisible();

  // Eligible-first ordering: no eligible row appears after a rejected one.
  const decisions = await rows.evaluateAll((els) =>
    els.map((el) => el.getAttribute("data-decision")),
  );
  const firstReject = decisions.indexOf("REJECT");
  if (firstReject !== -1) {
    expect(decisions.slice(firstReject).every((d) => d === "REJECT")).toBe(true);
  }
});

test("policy-diff replays personas and reports impact", async ({ page }) => {
  await page.goto("/policy-diff");
  await page.getByTestId("run-diff").click();
  await expect(page.getByTestId("diff-report")).toBeVisible();
  await expect(page.getByText(/Replayed/i)).toBeVisible();
});
