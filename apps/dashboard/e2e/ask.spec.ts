import { expect, test } from "@playwright/test";

// Copilot journey: ask an ops question and get a grounded answer with citations.
test("answers an ops question with source citations", async ({ page }) => {
  await page.goto("/ask");

  await page.getByTestId("ask-input").fill("Which lenders accept self-employed with two years of ITR?");
  await page.getByTestId("ask-submit").click();

  const answer = page.getByTestId("ask-answer");
  await expect(answer).toBeVisible();
  await expect(answer.getByText(/Sources/i)).toBeVisible();
  // At least one citation chip is rendered.
  await expect(answer.locator("li").first()).toBeVisible();
});
