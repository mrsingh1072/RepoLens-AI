import { useCallback, useState } from "react";
import { Check, Copy } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";

import { strataCodeTheme } from "@/components/chat/codeTheme";
import { cn } from "@/utils/cn";
import type { Citation } from "@/types";

interface MarkdownMessageProps {
  content: string;
  citations?: Citation[];
  fileReferences?: string[];
  functionReferences?: string[];
  onFileClick?: (path: string, line?: number) => void;
  className?: string;
}

/** Code block: stratum 2 with a title bar — traffic dots, mono language tag, copy. */
function CodeBlock({ language, value }: { language: string | undefined; value: string }) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }, [value]);

  return (
    <div className="group relative my-4 overflow-hidden rounded-md border border-edge bg-raised shadow-stratum">
      <div className="flex items-center justify-between border-b border-edge px-3.5 py-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-edge-strong" />
          <span className="h-2 w-2 rounded-full bg-edge-strong" />
          <span className="h-2 w-2 rounded-full bg-edge-strong" />
          <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3">
            {language || "text"}
          </span>
        </div>
        <button
          type="button"
          onClick={copy}
          className="inline-flex items-center gap-1.5 rounded-sm px-2 py-1 font-mono text-[11px] text-ink-3 transition-colors hover:bg-overlay hover:text-ink-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {copied ? <Check className="h-3 w-3 text-moss" /> : <Copy className="h-3 w-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={strataCodeTheme}
        customStyle={{
          margin: 0,
          padding: "0.875rem 1rem",
          background: "transparent",
          fontSize: "13px",
        }}
        PreTag="div"
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
}

function linkifyPath(
  text: string,
  knownPaths: Set<string>,
  onFileClick?: (path: string, line?: number) => void,
): React.ReactNode[] {
  if (!onFileClick || knownPaths.size === 0) return [text];

  const pattern = new RegExp(
    `(\`?)((?:[\\w.-]+/)+[\\w.-]+\\.[\\w]+)(\`?)(?::(\\d+)(?:-(\\d+))?)?`,
    "g",
  );
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    const [full, openTick, path, closeTick, lineStr] = match;
    const start = match.index;
    if (start > lastIndex) nodes.push(text.slice(lastIndex, start));

    const normalized = path.replace(/\\/g, "/");
    const isKnown = [...knownPaths].some(
      (p) => p === normalized || p.endsWith(`/${normalized}`) || normalized.endsWith(p),
    );

    if (isKnown && openTick === closeTick) {
      const line = lineStr ? Number(lineStr) : undefined;
      nodes.push(
        <button
          key={`${normalized}-${start}`}
          type="button"
          onClick={() => onFileClick(normalized, line)}
          className="font-mono text-[0.92em] text-ember underline decoration-ember/40 underline-offset-2 hover:decoration-ember"
        >
          {openTick}
          {path}
          {closeTick}
          {lineStr ? `:${lineStr}` : ""}
        </button>,
      );
    } else {
      nodes.push(full);
    }
    lastIndex = start + full.length;
  }

  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes.length ? nodes : [text];
}

export function MarkdownMessage({
  content,
  citations = [],
  fileReferences = [],
  functionReferences = [],
  onFileClick,
  className,
}: MarkdownMessageProps) {
  const knownPaths = new Set<string>([...fileReferences, ...citations.map((c) => c.path)]);

  return (
    <div className={cn("strata-prose max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p({ children }) {
            const text = String(children);
            if (typeof children === "string") {
              return <p>{linkifyPath(text, knownPaths, onFileClick)}</p>;
            }
            return <p>{children}</p>;
          },
          li({ children }) {
            if (typeof children === "string") {
              return <li>{linkifyPath(children, knownPaths, onFileClick)}</li>;
            }
            return <li>{children}</li>;
          },
          code({ className: codeClass, children, ...props }) {
            const match = /language-(\w+)/.exec(codeClass || "");
            const value = String(children).replace(/\n$/, "");
            const inline = !match && !value.includes("\n");
            if (inline) {
              const raw = value.replace(/`/g, "");
              const isFile = [...knownPaths].some((p) => p.includes(raw) || raw.includes(p));
              const isFn = functionReferences.includes(raw);
              if (isFile && onFileClick) {
                return (
                  <button
                    type="button"
                    onClick={() => onFileClick(raw)}
                    className="rounded-sm border border-ember/30 bg-ember/10 px-1.5 py-0.5 font-mono text-xs text-ember transition-colors hover:bg-ember/20"
                  >
                    {value}
                  </button>
                );
              }
              if (isFn) {
                return (
                  <code className="rounded-sm border border-edge bg-raised px-1.5 py-0.5 font-mono text-xs text-moss">
                    {value}
                  </code>
                );
              }
              return (
                <code
                  className="rounded-sm border border-edge bg-raised px-1.5 py-0.5 font-mono text-xs text-ink"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return <CodeBlock language={match?.[1]} value={value} />;
          },
          pre({ children }) {
            return <>{children}</>;
          },
          a({ href, children }) {
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
