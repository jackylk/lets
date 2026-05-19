import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { MentionText } from "./MentionText";

describe("<MentionText />", () => {
  it("plain text passes through", () => {
    renderWithProviders(<MentionText>hello world</MentionText>);
    expect(screen.getByText("hello world")).toBeInTheDocument();
  });

  it("wraps @name in mention chip", () => {
    renderWithProviders(<MentionText>ping @Trinity and @Morpheus please</MentionText>);
    expect(screen.getByText("@Trinity")).toHaveClass("mention");
    expect(screen.getByText("@Morpheus")).toHaveClass("mention");
  });
});
