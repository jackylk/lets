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

test("Adopt task_tree_proposal — button flips to Adopted", async ({ page }) => {
  await page.goto("/");
  // Scroll to the task_tree_proposal message
  const adoptBtn = page.getByRole("button", { name: /Adopt as task tree/i });
  await expect(adoptBtn).toBeVisible();
  await adoptBtn.click();
  await expect(page.getByText(/Adopted/i)).toBeVisible();
});

test("Nudge 略过 dismisses the nudge inline", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "略过" }).click();
  await expect(page.getByText(/已处理：略过/)).toBeVisible();
});

test("Spinoff dialog creates new topic + footer updates", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "独立成新 topic" }).click();
  // Default title prefilled from drift_summary
  await page.getByLabel(/新 topic 标题/).fill("周五团建");
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByText(/已处理：迁移到 topic/)).toBeVisible();
});
