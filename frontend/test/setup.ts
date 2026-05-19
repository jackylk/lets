import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "../src/fixtures/server";
import { resetFixtures } from "../src/fixtures/handlers";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => {
  localStorage.setItem(
    "lets.identity",
    JSON.stringify({ humanName: "Neo", agentRole: null, deviceLabel: null }),
  );
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
  resetFixtures();
  localStorage.clear();
});
afterAll(() => server.close());
