interface Props {
  workspaceName: string;
  joinUrl: string;
  onClose: () => void;
}

export function InviteDialog({ workspaceName, joinUrl, onClose }: Props) {
  return (
    <div className="fixed inset-0 bg-black/40 grid place-items-center z-50">
      <div className="bg-bg border border-border rounded p-6 max-w-md w-full">
        <h2 className="text-lg font-[var(--font-display)] mb-3">
          邀请新成员加入「{workspaceName}」
        </h2>
        <p className="text-sm text-text-dim mb-3">把这个链接发给 ta：</p>
        <div className="flex items-center gap-2 mb-4">
          <code className="flex-1 bg-hover px-3 py-2 rounded text-xs break-all">
            {joinUrl}
          </code>
          <button
            type="button"
            onClick={() => navigator.clipboard.writeText(joinUrl)}
            className="text-xs px-3 py-2 border border-border rounded hover:bg-hover"
          >
            复制
          </button>
        </div>
        <p className="text-xs text-text-dim mb-4">
          收到链接的人点击进入，登录 GitHub 后会自动成为成员。
        </p>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="text-sm px-4 py-2 border border-border rounded hover:bg-hover"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  );
}
