import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { AttentionGroup } from "./AttentionGroup";

describe("<AttentionGroup />", () => {
  it("renders heading with count and children", () => {
    renderWithProviders(
      <AttentionGroup heading="需要决定" count={2}>
        <div>row 1</div>
        <div>row 2</div>
      </AttentionGroup>,
    );
    expect(screen.getByRole("heading", { name: /需要决定/ })).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("row 1")).toBeInTheDocument();
  });
});
