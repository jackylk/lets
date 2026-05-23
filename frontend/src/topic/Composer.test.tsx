import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { Composer } from "./Composer";

describe("<Composer />", () => {
  it("calls onSend with text on Enter; submit button enables when text present", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<Composer onSend={onSend} />);

    const textarea = screen.getByRole("textbox");
    const button = screen.getByRole("button", { name: /发送/ });

    expect(button).toBeDisabled();
    await user.type(textarea, "hello");
    expect(button).toBeEnabled();

    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledWith({ body: "hello", addressedTo: null });
    expect((textarea as HTMLTextAreaElement).value).toBe("");
  });

  it("extracts @mentions and feeds typed addresses into addressedTo", async () => {
    const onSend = vi.fn();
    const resolver = {
      resolveAddresses: vi.fn((mentions: string[]) => {
        const map: Record<string, string> = { cc: "agent:7", trinity: "human:2" };
        return mentions.map((m) => map[m]).filter((v): v is string => typeof v === "string");
      }),
      resolveHumanIds: vi.fn((mentions: string[]) => {
        const map: Record<string, number> = { cc: 1, codex: 1, jacky: 1, trinity: 2 };
        return mentions.map((m) => map[m]).filter((n): n is number => typeof n === "number");
      }),
    };
    const user = userEvent.setup();
    renderWithProviders(<Composer onSend={onSend} resolver={resolver} />);

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "@cc 你能帮我看看吗？ @trinity");
    await user.keyboard("{Enter}");

    expect(resolver.resolveAddresses).toHaveBeenCalledWith(["cc", "trinity"]);
    expect(onSend).toHaveBeenCalledWith({
      body: "@cc 你能帮我看看吗？ @trinity",
      addressedTo: "agent:7,human:2",
    });
  });

  it("treats plain CC/Codex calls as addressed agent mentions", async () => {
    const onSend = vi.fn();
    const resolver = {
      resolveAddresses: vi.fn((mentions: string[]) => {
        const map: Record<string, string> = { cc: "agent:7", cx: "agent:8" };
        return mentions.map((m) => map[m]).filter((v): v is string => typeof v === "string");
      }),
      resolveHumanIds: vi.fn(() => []),
    };
    const user = userEvent.setup();
    renderWithProviders(<Composer onSend={onSend} resolver={resolver} />);

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "CC在吗");
    await user.keyboard("{Enter}");

    expect(resolver.resolveAddresses).toHaveBeenCalledWith(["cc"]);
    expect(onSend).toHaveBeenCalledWith({
      body: "CC在吗",
      addressedTo: "agent:7",
    });
  });

  it("shows mention candidates after @ and inserts the selected alias", async () => {
    const onSend = vi.fn();
    const resolver = {
      resolveAddresses: vi.fn((mentions: string[]) => {
        const map: Record<string, string> = { cc: "agent:7" };
        return mentions.map((m) => map[m]).filter((v): v is string => typeof v === "string");
      }),
      resolveHumanIds: vi.fn(() => []),
    };
    const user = userEvent.setup();
    renderWithProviders(
      <Composer
        onSend={onSend}
        resolver={resolver}
        mentionCandidates={[
          { key: "cc", label: "claude · mac16", detail: "online", kind: "agent" },
        ]}
      />,
    );

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "@");
    expect(screen.getByText("claude · mac16")).toBeInTheDocument();

    await user.keyboard("{Enter}");
    expect(textarea.value).toBe("@cc ");
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    await user.type(textarea, "hi");
    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledWith({ body: "@cc hi", addressedTo: "agent:7" });
  });

  it("@c prefix-matches @cc and Enter auto-selects (case-insensitive)", async () => {
    const onSend = vi.fn();
    const resolver = {
      resolveHumanIds: vi.fn((mentions: string[]) => {
        const map: Record<string, number> = { cc: 1, codex: 2, jacky: 3 };
        return mentions.map((m) => map[m]).filter((n): n is number => typeof n === "number");
      }),
    };
    const user = userEvent.setup();
    renderWithProviders(
      <Composer
        onSend={onSend}
        resolver={resolver}
        mentionCandidates={[
          { key: "cc", label: "claude · mac16", detail: "online", kind: "agent" },
          { key: "cx", label: "codex · mbp", detail: "offline", kind: "agent" },
          { key: "jacky", label: "Jacky", detail: "human", kind: "human" },
        ]}
      />,
    );

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "@C");  // uppercase → still prefix-matches "cc"
    expect(screen.getByText("claude · mac16")).toBeInTheDocument();

    await user.keyboard("{Enter}");
    expect(textarea.value).toBe("@cc ");
  });

  it("does not show unresolved while a partial mention has candidates", async () => {
    const onSend = vi.fn();
    const resolver = {
      resolveAddresses: vi.fn((mentions: string[]) => {
        const map: Record<string, string> = { neo: "agent:7" };
        return mentions.map((m) => map[m]).filter((v): v is string => typeof v === "string");
      }),
      resolveHumanIds: vi.fn(() => []),
    };
    const user = userEvent.setup();
    renderWithProviders(
      <Composer
        onSend={onSend}
        resolver={resolver}
        mentionCandidates={[
          { key: "neo", label: "Neo", detail: "online · by Jacky Li", kind: "agent" },
        ]}
      />,
    );

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "@n");
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.queryByText(/无法解析/)).toBeNull();

    await user.keyboard("{Enter}");
    expect(textarea.value).toBe("@neo ");
    expect(screen.getByText(/@neo to agent:7/)).toBeInTheDocument();
  });

  it("Enter during IME composition does not send (Sogou/Pinyin candidate confirm)", async () => {
    const { fireEvent } = await import("@testing-library/react");
    const onSend = vi.fn();
    renderWithProviders(<Composer onSend={onSend} />);
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    // Simulate user typing "ppt" inside an IME session.
    fireEvent.compositionStart(textarea);
    fireEvent.change(textarea, { target: { value: "ppt" } });
    // The IME forwards Enter to commit a candidate. Browsers set
    // isComposing=true / keyCode=229. We must NOT send.
    fireEvent.keyDown(textarea, {
      key: "Enter",
      keyCode: 229,
      isComposing: true,
    });
    expect(onSend).not.toHaveBeenCalled();
    // Composition ends after the IME finishes its own handling.
    fireEvent.compositionEnd(textarea, { data: "ppt" });
    expect(textarea.value).toBe("ppt");
  });

  it("Shift+Enter inserts newline without sending", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<Composer onSend={onSend} />);
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "line1");
    await user.keyboard("{Shift>}{Enter}{/Shift}line2");
    expect(onSend).not.toHaveBeenCalled();
    expect((textarea as HTMLTextAreaElement).value).toBe("line1\nline2");
  });
});
