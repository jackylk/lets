import { cn } from "../lib/cn";

interface Props {
  num: number;
  variant?: "title" | "text" | "chart" | "grid";
  href?: string;
}

export function SlideThumb({ num, variant = "text", href }: Props) {
  const inner = (
    <div className="relative w-[64px] h-[40px] rounded border border-border-soft bg-surface-elev overflow-hidden flex flex-col gap-1 p-1.5">
      {variant === "title" && (
        <>
          <div className="h-1.5 bg-text rounded-sm w-3/4" />
          <div className="h-1 bg-border rounded-sm w-1/2" />
        </>
      )}
      {variant === "text" && (
        <>
          <div className="h-1 bg-text rounded-sm w-2/3" />
          <div className="h-px bg-border rounded-sm w-full mt-auto" />
          <div className="h-px bg-border rounded-sm w-5/6" />
        </>
      )}
      {variant === "chart" && (
        <>
          <div className="h-1 bg-text rounded-sm w-1/2" />
          <div className="flex gap-px items-end h-full mt-1">
            <div className="bg-accent w-1.5 h-1/2" />
            <div className="bg-accent w-1.5 h-3/4" />
            <div className="bg-accent w-1.5 h-2/5" />
            <div className="bg-accent w-1.5 h-full" />
          </div>
        </>
      )}
      {variant === "grid" && (
        <div className="grid grid-cols-4 gap-px h-full">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="bg-border-soft" />
          ))}
        </div>
      )}
      <span className="absolute bottom-0.5 right-1 text-[8px] font-mono text-text-dim">{num}</span>
    </div>
  );
  return href ? <a href={href} target="_blank" rel="noreferrer" className={cn()}>{inner}</a> : inner;
}
