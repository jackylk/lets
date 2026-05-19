import { SlideThumb } from "../messages/SlideThumb";
import { cn } from "../lib/cn";

interface Props {
  artifactName: string;
  currentVersion: string;
  versions: string[];
  totalSlides: number;
}

export function ArtifactPanel({ artifactName, currentVersion, versions, totalSlides }: Props) {
  const shown = Math.min(4, totalSlides);
  const hidden = Math.max(0, totalSlides - shown);
  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-center gap-2 text-[13px]">
        <span className="font-mono truncate flex-1">{artifactName}</span>
        <span className="bg-artifact text-bg px-1.5 py-px rounded text-[10px] font-mono">{currentVersion}</span>
      </div>
      <div className="flex gap-1.5 flex-wrap">
        {Array.from({ length: shown }).map((_, i) => (
          <SlideThumb key={i} num={i + 1} variant={i === 0 ? "title" : i === 2 ? "chart" : i === 3 ? "grid" : "text"} />
        ))}
      </div>
      <div className="flex items-center gap-2 text-[10.5px]">
        {versions.map((v) => (
          <span
            key={v}
            className={cn(
              "px-1.5 py-px rounded font-mono",
              v === currentVersion ? "bg-artifact text-bg" : "bg-surface text-text-muted",
            )}
          >
            {v}
          </span>
        ))}
        {hidden > 0 && (
          <span className="ml-auto text-text-dim">+ {hidden} 页未显示</span>
        )}
      </div>
    </div>
  );
}
