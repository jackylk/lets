import { test, expect } from "@playwright/test";

// Real-mode smoke: exercises the SPA against a live FastAPI backend
// (no MSW). Gated by LETS_REAL_API_BASE — `pnpm e2e` skips this file
// when the env var is unset, so the default 3-test fixture suite is
// unaffected.

test.describe.configure({ mode: "serial" });

test("real-mode: posting a chat round-trips through the backend SSE", async ({
  page,
  request,
}) => {
  test.skip(
    !process.env.LETS_REAL_API_BASE,
    "set LETS_REAL_API_BASE to run",
  );

  const base = process.env.LETS_REAL_API_BASE!;
  const session = process.env.LETS_REAL_SESSION;

  test.skip(!session, "set LETS_REAL_SESSION to run");

  const appUrl = new URL(base);
  await page.context().addCookies([
    {
      name: "lets_session",
      value: session!,
      url: appUrl.origin,
      httpOnly: true,
      sameSite: "Lax",
      secure: appUrl.protocol === "https:",
    },
  ]);

  // Sanity: browser-session auth works before loading the SPA.
  const me = await request.get(`${base}/auth/me`, {
    headers: { Cookie: `lets_session=${session}` },
  });
  expect(me.ok()).toBeTruthy();

  // Visit the served SPA on the same origin as the API.
  await page.goto(`${base}/app`);
  await expect(page.getByText("seeded real backend message")).toBeVisible({
    timeout: 10_000,
  });

  await page.getByRole("textbox").fill("real-mode hello");
  await page.getByRole("textbox").press("Enter");
  await expect(page.getByText("real-mode hello")).toBeVisible();
});
