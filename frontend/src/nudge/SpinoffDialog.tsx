import { useState } from "react";

interface Props {
  suggestedTitle: string;
  onSubmit: (title: string) => Promise<void>;
  onCancel: () => void;
}

export function SpinoffDialog({ suggestedTitle, onSubmit, onCancel }: Props) {
  const [title, setTitle] = useState(suggestedTitle);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(title.trim());
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 grid place-items-center z-50">
      <form
        onSubmit={submit}
        className="bg-bg border border-border rounded-xl w-full max-w-md p-5 flex flex-col gap-3"
      >
        <h2 className="font-[var(--font-display)] text-lg">独立成新 topic</h2>
        <p className="text-[12px] text-text-muted">
          原讨论会保留在当前 topic。新 topic 会从一条系统消息开始，记录摘要。
        </p>
        <label className="text-[12px] text-text-muted flex flex-col gap-1">
          新 topic 标题
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="border border-border rounded px-2 py-1.5 bg-surface-elev"
            autoFocus
          />
        </label>
        <div className="flex gap-2 mt-1">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 rounded border border-border text-[13px]"
          >
            取消
          </button>
          <div className="flex-1" />
          <button
            type="submit"
            disabled={submitting || !title.trim()}
            className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium disabled:opacity-50"
          >
            创建
          </button>
        </div>
      </form>
    </div>
  );
}
