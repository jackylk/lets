import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { BaseMessage } from "./BaseMessage";

describe("<BaseMessage />", () => {
  it("renders name, meta, and body", () => {
    renderWithProviders(
      <BaseMessage
        actor={{ kind: "human", initial: "N", displayName: "Neo" }}
        timeIso="2026-05-19T09:14:00Z"
        body={<p>hi</p>}
      />,
    );
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("hi")).toBeInTheDocument();
    expect(screen.getByText("N")).toBeInTheDocument();
  });

  it("renders optional tag chip", () => {
    renderWithProviders(
      <BaseMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude · neo-mbp" }}
        timeIso="2026-05-19T09:18:00Z"
        body={<p>x</p>}
        tag="status"
      />,
    );
    expect(screen.getByText("status")).toBeInTheDocument();
  });
});
