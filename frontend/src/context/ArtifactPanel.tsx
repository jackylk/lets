import type { ArtifactDTO } from "../api/types";

interface Props {
  artifacts: ArtifactDTO[];
}

export function ArtifactPanel({ artifacts }: Props) {
  return (
    <div className="flex flex-col gap-2">
      {artifacts.map((a) => {
        const versions = a.versions ?? [];
        const current = versions.find((v) => v.id === a.current_version_id);
        const currentLabel = current?.version_label ?? "—";
        return (
          <div
            key={a.id}
            className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2"
          >
            <div className="flex items-center gap-2 text-[13px]">
              <span className="font-mono truncate flex-1">{a.slug}</span>
              <span className="bg-artifact text-bg px-1.5 py-px rounded text-[10px] font-mono">
                {currentLabel}
              </span>
            </div>
            <div className="text-[11.5px] text-text-muted truncate">{a.title}</div>
            <div className="flex items-center gap-2 text-[10.5px] flex-wrap">
              {versions.length === 0 ? (
                <span className="text-text-dim italic">no versions</span>
              ) : (
                versions.map((v) => (
                  <span
                    key={v.id}
                    className={
                      v.version_label === currentLabel
                        ? "px-1.5 py-px rounded font-mono bg-artifact text-bg"
                        : "px-1.5 py-px rounded font-mono bg-surface text-text-muted"
                    }
                    title={v.summary ?? undefined}
                  >
                    {v.version_label}
                  </span>
                ))
              )}
            </div>
            <div className="text-[10.5px] font-mono text-text-dim truncate">
              {a.backend} · {a.backend_ref}
            </div>
          </div>
        );
      })}
    </div>
  );
}
