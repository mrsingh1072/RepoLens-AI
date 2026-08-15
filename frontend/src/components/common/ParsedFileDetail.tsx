import { Card } from "@/components/ui/card";
import { Overline } from "@/components/common/Overline";
import type { ParsedFileResult } from "@/types/parse";

/** The specimen tray — symbols, routes, and imports for one parsed file. */
export function ParsedFileDetail({ file }: { file: ParsedFileResult }) {
  const symbols = [
    ...file.functions.map((f) => ({ kind: "fn" as const, ...f })),
    ...file.classes.flatMap((c) => [
      {
        kind: "class" as const,
        name: c.name,
        start_line: c.start_line,
        end_line: c.end_line,
        docstring: c.docstring,
      },
      ...c.methods.map((m) => ({
        kind: "method" as const,
        name: `${c.name}.${m.name}`,
        start_line: m.start_line,
        end_line: m.end_line,
        docstring: m.docstring,
      })),
    ]),
  ];

  return (
    <Card className="p-5">
      <Overline>File · Detail</Overline>
      <p className="mt-2 break-all font-mono text-[13px] text-ink">{file.file}</p>
      <p className="tnum mt-1 font-mono text-[11px] text-ink-3">
        {file.language} · {file.metadata.lines} lines · complexity {file.metadata.complexity} ·{" "}
        {file.metadata.symbol_count} symbols
      </p>

      <div className="mt-5 space-y-5 text-sm">
        {file.api_endpoints.length > 0 && (
          <section>
            <Overline className="mb-2.5">API routes</Overline>
            <ul className="space-y-1.5">
              {file.api_endpoints.map((ep) => (
                <li key={`${ep.method}-${ep.route}-${ep.start_line}`} className="font-mono text-xs">
                  <span className="text-ember">{ep.method}</span>{" "}
                  <span className="text-ink">{ep.route}</span>{" "}
                  <span className="text-ink-3">→ {ep.handler}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {symbols.length > 0 && (
          <section>
            <Overline className="mb-2.5">Symbols</Overline>
            <ul className="space-y-1.5">
              {symbols.map((s) => (
                <li
                  key={`${s.kind}-${s.name}-${s.start_line}`}
                  className="rounded-md border border-edge bg-raised px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-mono text-[13px] text-ink">
                      <span className="mr-2 text-[10px] uppercase tracking-wider text-ink-3">
                        {s.kind}
                      </span>
                      {s.name}
                    </span>
                    <span className="tnum shrink-0 font-mono text-[11px] text-ink-3">
                      L{s.start_line}–{s.end_line}
                    </span>
                  </div>
                  {s.docstring && (
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-ink-2">{s.docstring}</p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {file.imports.length > 0 && (
          <section>
            <Overline className="mb-2.5">Imports</Overline>
            <ul className="space-y-1 font-mono text-xs text-ink-2">
              {file.imports.slice(0, 12).map((imp) => (
                <li key={`${imp.module}-${imp.start_line}`} className="flex items-center gap-2">
                  <span
                    className={imp.is_external ? "h-1.5 w-1.5 rounded-full bg-gold" : "h-1.5 w-1.5 rounded-full bg-ink-3/60"}
                    aria-hidden
                  />
                  {imp.module}
                  <span className="text-ink-3">{imp.is_external ? "external" : "internal"}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </Card>
  );
}
