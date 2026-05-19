import { test, expect } from "@playwright/test";

// The app gates posting behind a resolved identity (humanName !== null). In
// unit tests this is seeded via the test setup; in E2E we seed localStorage
// before the page boots so useIdentity() picks up a name.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      "lets.identity",
      JSON.stringify({ humanName: "Neo", agentRole: null, deviceLabel: null }),
    );
  });
});

test("PPT scenario: see seeded stream and post a chat", async ({ page }) => {
  await page.goto("/");

  // Wait for MSW + initial query
  await expect(page.getByRole("heading", { name: /PPT/ })).toBeVisible();

  // 14 messages from fixture
  await expect(page.locator('[data-testid="message-row"]')).toHaveCount(14);

  // All 4 typed-message visual signals present
  await expect(page.getByText("status").first()).toBeVisible();
  await expect(page.getByText("finding").first()).toBeVisible();
  await expect(page.getByText("artifact_revision · v0")).toBeVisible();
  await expect(page.getByText("spec_change")).toBeVisible();

  // Post via composer
  const composer = page.getByRole("textbox");
  await composer.fill("e2e: hello from playwright");
  await composer.press("Enter");

  await expect(page.getByText("e2e: hello from playwright")).toBeVisible();
  await expect(page.locator('[data-testid="message-row"]')).toHaveCount(15);
});

test("Attention view shows 3 groups", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /待处理/ }).click();
  await expect(page.getByRole("heading", { name: /需要决定/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /主动发现/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /同事消息/ })).toBeVisible();
});

test("Spec change Approve flips to Approved state", async ({ page }) => {
  await page.goto("/");
  const approve = page.getByRole("button", { name: "Approve" }).first();
  await approve.click();
  await expect(page.getByText("Approved")).toBeVisible();
});
