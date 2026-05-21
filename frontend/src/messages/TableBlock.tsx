import type { ReactNode } from "react";

/**
 * Minimal markdown-table renderer — covers the shape agents produce when
 * asked to compare options. Not a general markdown lib: only handles the
 * standard "| col | col |" + "|------|------|" syntax with optional
 * column alignment (`:---`, `:---:`, `---:`).
 */

export interface ParsedTable {
  headers: string[];
  rows: string[][];
  alignments: Array<"left" | "center" | "right" | null>;
}

const ROW_RE = /^\s*\|(.+)\|\s*$/;
const ALIGN_RE = /^\s*:?-{2,}:?\s*$/;

function splitRow(line: string): string[] {
  const m = line.match(ROW_RE);
  if (!m) return [];
  return (m[1] ?? "")
    .split("|")
    .map((c) => c.trim());
}

function parseAlignment(cell: string): "left" | "center" | "right" | null {
  const c = cell.trim();
  if (!ALIGN_RE.test(c)) return null;
  const left = c.startsWith(":");
  const right = c.endsWith(":");
  if (left && right) return "center";
  if (right) return "right";
  if (left) return "left";
  return null;
}

/**
 * Try to parse a 3+ line block as a markdown table. Returns the parsed
 * table + the count of lines consumed; null if the block doesn't look like
 * one.
 */
export function tryParseTable(lines: string[], start: number): { table: ParsedTable; consumed: number } | null {
  if (start + 1 >= lines.length) return null;
  const headerLine = lines[start];
  const sepLine = lines[start + 1];
  if (!headerLine || !sepLine) return null;
  const headers = splitRow(headerLine);
  const seps = splitRow(sepLine);
  if (headers.length === 0 || headers.length !== seps.length) return null;
  // Separator row must look like |---|:---:| etc.
  for (const s of seps) {
    if (!ALIGN_RE.test(s)) return null;
  }
  const alignments = seps.map(parseAlignment);

  const rows: string[][] = [];
  let i = start + 2;
  while (i < lines.length) {
    const line = lines[i] ?? "";
    if (!ROW_RE.test(line)) break;
    const cells = splitRow(line);
    // Pad / truncate to header count so render doesn't crash.
    while (cells.length < headers.length) cells.push("");
    rows.push(cells.slice(0, headers.length));
    i++;
  }
  if (rows.length === 0) return null;
  return { table: { headers, rows, alignments }, consumed: i - start };
}

export type TableSegment =
  | { kind: "text"; value: string }
  | { kind: "table"; table: ParsedTable };

/**
 * Walk a text body line-by-line, pulling out any markdown tables into
 * their own segments. Returns interleaved text + table segments.
 */
export function splitTables(body: string): TableSegment[] {
  const lines = body.split("\n");
  const out: TableSegment[] = [];
  let buf: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const parsed = tryParseTable(lines, i);
    if (parsed) {
      if (buf.length > 0) {
        out.push({ kind: "text", value: buf.join("\n") });
        buf = [];
      }
      out.push({ kind: "table", table: parsed.table });
      i += parsed.consumed;
    } else {
      buf.push(lines[i] ?? "");
      i++;
    }
  }
  if (buf.length > 0) {
    out.push({ kind: "text", value: buf.join("\n") });
  }
  return out;
}

function alignToClass(a: "left" | "center" | "right" | null): string {
  if (a === "center") return "text-center";
  if (a === "right") return "text-right";
  return "text-left";
}

export function TableBlock({
  table,
  renderCell,
}: {
  table: ParsedTable;
  /** Caller-supplied cell renderer so we get @mention / bold / code inside. */
  renderCell: (text: string) => ReactNode;
}) {
  return (
    <div className="my-2 overflow-x-auto">
      <table className="border-collapse text-[13px] leading-snug">
        <thead>
          <tr>
            {table.headers.map((h, i) => (
              <th
                key={i}
                className={
                  "border border-border-soft bg-surface-hover px-2.5 py-1.5 font-semibold " +
                  alignToClass(table.alignments[i] ?? null)
                }
              >
                {renderCell(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, c) => (
                <td
                  key={c}
                  className={
                    "border border-border-soft px-2.5 py-1.5 align-top " +
                    alignToClass(table.alignments[c] ?? null)
                  }
                >
                  {renderCell(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
