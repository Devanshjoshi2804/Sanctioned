import { expect, test } from "@playwright/test";

// New home-loan journey: run the default borrower, see the ranked grid, and open
// a lender's full reason trace.
test("runs a new-loan match and shows reason traces", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("run-match").click();

  const grid = page.getByTestId("match-grid");
  await expect(grid).toBeVisible();

  const rows = page.getByTestId("lender-row");
  await expect(rows).toHaveCount(4);

  // Summary reflects the run.
  await expect(page.getByTestId("summary")).toBeVisible();

  // Expand the top lender and confirm the audit ledger renders with traces.
  await rows.first().getByRole("button").click();
  const ledger = page.getByTestId("reason-ledger");
  await expect(ledger).toBeVisible();
  await expect(ledger.locator("li").first()).toBeVisible();
});

test("links from a lender to its policy dossier", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("run-match").click();
  const firstRow = page.getByTestId("lender-row").first();
  await firstRow.getByRole("button").click();
  await firstRow.getByRole("link", { name: /view policy/i }).click();
  await expect(page.getByText(/Provenance/i)).toBeVisible();
  await expect(page.getByText(/indicative/i).first()).toBeVisible();
});
