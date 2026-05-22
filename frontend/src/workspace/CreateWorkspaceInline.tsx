import { useState } from "react";

interface Props {
  onSubmit: (name: string) => void;
  onCancel: () => void;
}

export function CreateWorkspaceInline({ onSubmit, onCancel }: Props) {
  const [value, setValue] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) onSubmit(value.trim());
      }}
      className="px-3 py-2 border-b border-border"
    >
      <input
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") onCancel();
        }}
        placeholder="工作区名字…"
        aria-label="工作区名字"
        className="w-full text-sm bg-transparent border border-border rounded px-2 py-1 focus:outline-none focus:border-accent"
      />
    </form>
  );
}
