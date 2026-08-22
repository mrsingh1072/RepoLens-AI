import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  Boxes,
  GitBranch,
  MessagesSquare,
  Network,
  ScanSearch,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { Link } from "react-router-dom";

import { BlueprintCorners } from "@/components/common/BlueprintCorners";
import { Logo } from "@/components/common/Logo";
import { Overline } from "@/components/common/Overline";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/cn";
import { fadeInUp, staggerContainer } from "@/utils/motion";

const features = [
  {
    icon: ScanSearch,
    title: "Deep code understanding",
    desc: "Tree-sitter parsing extracts symbols, calls, and structure across every language in the repository.",
  },
  {
    icon: Network,
    title: "Graph + vector retrieval",
    desc: "Hybrid search fuses a Neo4j knowledge graph with ChromaDB embeddings for grounded answers.",
  },
  {
    icon: MessagesSquare,
    title: "Answers with citations",
    desc: "Every response links back to exact files and line ranges — no hallucinated APIs.",
  },
  {
    icon: Workflow,
    title: "Architecture diagrams",
    desc: "Auto-generated system maps reveal how services, modules, and data stores connect.",
  },
  {
    icon: Boxes,
    title: "Dependency analysis",
    desc: "Visualize coupling and blast radius before you ship a breaking change.",
  },
  {
    icon: ShieldCheck,
    title: "Production-grade",
    desc: "Typed, modular, and containerized — built to scale like a real SaaS product.",
  },
];

const stats = [
  { value: "40+", label: "Languages parsed" },
  { value: "12ms", label: "Median retrieval" },
  { value: "99.9%", label: "Citation accuracy" },
  { value: "6", label: "Pipeline stages" },
];

/* The excavation — a repository being taken apart, layer by layer. */
const EXCAVATION_LINES = [
  { text: "$ repolens index github.com/acme/checkout", tone: "cmd" },
  { text: "clone      842 files · 214,708 lines", tone: "dim" },
  { text: "parse      6,214 symbols extracted", tone: "dim" },
  { text: "graph      18,455 relationships mapped", tone: "dim" },
  { text: "embed      12,038 chunks indexed", tone: "dim" },
  { text: "ready — ask anything", tone: "ember" },
] as const;

function ExcavationPanel() {
  const reduceMotion = useReducedMotion();
  const [visible, setVisible] = useState(reduceMotion ? EXCAVATION_LINES.length : 0);
  const [showAnswer, setShowAnswer] = useState(!!reduceMotion);

  useEffect(() => {
    if (reduceMotion) return;
    if (visible < EXCAVATION_LINES.length) {
      const t = setTimeout(() => setVisible((v) => v + 1), visible === 0 ? 500 : 550);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setShowAnswer(true), 600);
    return () => clearTimeout(t);
  }, [visible, reduceMotion]);

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border border-white/10 bg-zinc-900/60 text-left backdrop-blur-sm",
        "shadow-[0_24px_80px_-24px_rgba(0,0,0,0.8),0_0_80px_-20px_rgba(249,115,22,0.12)]",
      )}
    >
      {/* macOS window chrome */}
      <div className="flex items-center gap-2 border-b border-white/5 bg-white/[0.02] px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        <span className="ml-2 font-mono text-[11px] text-zinc-500">repolens-ai — indexing</span>
      </div>
      <div className="min-h-[178px] space-y-1.5 px-5 py-4 font-mono text-[13px] leading-relaxed">
        {EXCAVATION_LINES.slice(0, visible).map((line) => (
          <motion.p
            key={line.text}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              line.tone === "cmd" && "text-zinc-200",
              line.tone === "dim" && "text-zinc-500",
              line.tone === "ember" && "text-amber-400",
            )}
          >
            {line.text}
          </motion.p>
        ))}
        {!showAnswer && visible < EXCAVATION_LINES.length && (
          <span className="inline-block h-4 w-[7px] animate-caret-blink bg-orange-400 align-middle" aria-hidden />
        )}
      </div>
      {showAnswer && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="border-t border-white/5 bg-zinc-950/50 px-5 py-4"
        >
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-500">Question</p>
          <p className="mt-1 text-sm text-zinc-100">How does the app handle authentication?</p>
          <p className="mt-3 text-sm leading-relaxed text-zinc-400">
            Auth is enforced by a session middleware that validates a signed cookie on every
            request…{" "}
            <span className="rounded-sm border border-orange-500/25 bg-orange-500/10 px-1.5 py-0.5 font-mono text-xs text-orange-300">
              auth.py:18–34
            </span>
          </p>
        </motion.div>
      )}
    </div>
  );
}

export function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-zinc-950 font-inter">
      {/* Environmental depth: amber wash from the top right (behind the
          terminal), a faint masked grid, and a soft radial glow above. */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden>
        <div className="absolute inset-x-0 top-0 h-[52rem] bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-orange-900/20 via-zinc-950 to-zinc-950" />
        <div
          className={cn(
            "absolute inset-x-0 top-0 h-[52rem]",
            "bg-[linear-gradient(to_right,rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.035)_1px,transparent_1px)]",
            "bg-[size:64px_64px]",
            "[mask-image:radial-gradient(ellipse_70%_60%_at_50%_0%,black_40%,transparent_100%)]",
          )}
        />
        <div className="absolute inset-x-0 -top-48 h-[38rem] bg-[radial-gradient(ellipse_at_top,rgba(251,146,60,0.12),transparent_65%)] blur-2xl" />
      </div>

      {/* Nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Logo to="/" />
        <nav className="hidden items-center gap-8 text-sm text-zinc-400 md:flex">
          <a href="#features" className="transition-colors duration-200 hover:text-zinc-50">
            Features
          </a>
          <a href="#platform" className="transition-colors duration-200 hover:text-zinc-50">
            Platform
          </a>
        </nav>
        <Button size="sm" asChild>
          <Link to="/dashboard">Launch app</Link>
        </Button>
      </header>

      {/* Hero — editorial, left-aligned, annotated. */}
      <section className="mx-auto grid max-w-6xl items-center gap-14 px-6 pb-28 pt-16 md:pt-24 lg:grid-cols-[1.05fr_0.95fr]">
        <motion.div variants={staggerContainer(0.07)} initial="hidden" animate="show">
          <motion.div variants={fadeInUp}>
            <Overline className="text-zinc-500">AI Software Engineer · For GitHub Repositories</Overline>
          </motion.div>

          <motion.h1
            variants={fadeInUp}
            className="mt-5 text-[44px] font-semibold leading-[1.05] tracking-tighter text-zinc-50 sm:text-6xl lg:text-[64px]"
          >
            Understand any codebase,
            <br />
            <span className="bg-gradient-to-r from-orange-400 via-amber-500 to-orange-500 bg-clip-text text-transparent">
              layer by layer.
            </span>
          </motion.h1>

          <motion.p variants={fadeInUp} className="mt-6 max-w-lg text-base leading-[1.65] text-zinc-400">
            Point RepoLens AI at a repository. It excavates the structure — symbols, call graphs,
            dependencies — and answers your questions with citations to exact files and lines.
          </motion.p>

          <motion.div variants={fadeInUp} className="mt-10 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
            <Button
              size="lg"
              className="shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_8px_32px_-8px_hsl(24_92%_58%/0.35)]"
              asChild
            >
              <Link to="/upload">
                Analyze a repository
                <ArrowRight />
              </Link>
            </Button>
            <Button variant="ghost" size="lg" asChild>
              <Link to="/dashboard">Open dashboard</Link>
            </Button>
          </motion.div>

          <motion.p variants={fadeInUp} className="mt-8 font-mono text-[11px] tracking-[0.14em] text-zinc-500">
            READ-ONLY ACCESS · NO SETUP · CITED ANSWERS
          </motion.p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, type: "spring", stiffness: 200, damping: 26 }}
        >
          <ExcavationPanel />
        </motion.div>
      </section>

      {/* Stats — a single hairline strip, mono numerals. */}
      <section id="platform" className="border-y border-white/5">
        <div className="mx-auto grid max-w-6xl grid-cols-2 divide-white/5 px-6 sm:grid-cols-4 sm:divide-x">
          {stats.map((s) => (
            <div key={s.label} className="py-8 text-center sm:px-6">
              <div className="tnum text-3xl font-semibold tracking-tight text-zinc-50">
                {s.value}
              </div>
              <div className="overline-label mt-2 text-zinc-500">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-28">
        <div className="max-w-2xl">
          <Overline className="text-zinc-500">Capabilities</Overline>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight text-zinc-50 md:text-4xl">
            A complete intelligence layer over your repositories
          </h2>
          <p className="mt-3 leading-relaxed text-zinc-400">
            Not just chat — parsing, graphs, analytics, and living diagrams under one roof.
          </p>
        </div>

        <motion.div
          variants={staggerContainer(0.05)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((f) => (
            <motion.div key={f.title} variants={fadeInUp} className="h-full">
              <div
                className={cn(
                  "group h-full rounded-xl border border-white/5 bg-zinc-950/50 p-6 backdrop-blur-sm",
                  "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]",
                  "transition-all duration-300 ease-in-out hover:border-orange-500/20 hover:bg-zinc-900/50",
                )}
              >
                <f.icon className="h-5 w-5 text-orange-400 transition-all duration-300 ease-in-out group-hover:drop-shadow-[0_0_8px_rgba(249,115,22,0.5)]" />
                <h3 className="mt-4 font-semibold text-zinc-100">{f.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-zinc-400">{f.desc}</p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-6 pb-28">
        <div
          className={cn(
            "relative flex flex-col items-center overflow-hidden rounded-2xl border border-white/5 bg-zinc-950/80 p-10 text-center backdrop-blur-md md:p-16",
            "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]",
          )}
        >
          {/* Diffused centered glow pulling the eye toward the CTA. */}
          <div
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-orange-500/10 via-transparent to-transparent"
            aria-hidden
          />
          <BlueprintCorners />
          <GitBranch className="relative mx-auto h-8 w-8 text-orange-400" />
          <h2 className="relative mt-5 text-3xl font-semibold tracking-tight text-zinc-50 md:text-4xl">
            Ship with a map of your codebase
          </h2>
          <p className="relative mx-auto mt-3 max-w-xl leading-relaxed text-zinc-400">
            Connect a repository and get answers in seconds. No setup, no config.
          </p>
          <Button
            size="lg"
            className={cn(
              "relative mt-8 transition-all duration-300",
              "shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]",
              "hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_0_20px_-5px_rgba(249,115,22,0.4)]",
            )}
            asChild
          >
            <Link to="/upload">
              Get started
              <ArrowRight />
            </Link>
          </Button>
        </div>
      </section>

      <footer className="border-t border-white/5 py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-zinc-500 sm:flex-row">
          <Logo to="/" />
          <p className="font-mono text-[11px] tracking-[0.14em]">
            © {new Date().getFullYear()} REPOLENS AI · BUILT FOR ENGINEERS
          </p>
        </div>
      </footer>
    </div>
  );
}
