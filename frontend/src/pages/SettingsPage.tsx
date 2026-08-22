import { useState } from "react";
import { motion } from "framer-motion";
import { Eye, EyeOff, Moon, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Overline } from "@/components/common/Overline";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useAppStore } from "@/store/appStore";
import { cn } from "@/utils/cn";
import { fadeInUp, staggerContainer } from "@/utils/motion";

/* The utility closet — plain stacked sections, hairline-separated. Calm. */

function Section({
  overline,
  description,
  children,
}: {
  overline: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div variants={fadeInUp}>
      <Card className="p-6">
        <Overline>{overline}</Overline>
        <p className="mt-1.5 text-sm text-ink-2">{description}</p>
        <div className="mt-5">{children}</div>
      </Card>
    </motion.div>
  );
}

function Row({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div>
        <p className="text-sm font-medium text-ink">{label}</p>
        {hint && <p className="mt-0.5 text-xs text-ink-3">{hint}</p>}
      </div>
      {children}
    </div>
  );
}

export function SettingsPage() {
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const sidebarCollapsed = useAppStore((s) => s.sidebarCollapsed);
  const setSidebarCollapsed = useAppStore((s) => s.setSidebarCollapsed);

  const [showKey, setShowKey] = useState(false);
  const [apiKey, setApiKey] = useState("sk-••••••••••••••••••••••••");
  const [provider, setProvider] = useState<"openai" | "groq">("groq");

  const saveKeys = () =>
    toast.success("Settings saved", { description: "Your provider configuration was updated." });

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader
        overline="Configuration"
        title="Settings"
        description="Account, appearance, and integrations."
      />

      <motion.div variants={staggerContainer(0.06)} initial="hidden" animate="show" className="space-y-6">
        <Section overline="Profile" description="How you appear across the workspace.">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium text-ink" htmlFor="name">
                Display name
              </label>
              <Input id="name" defaultValue="Saurabh Kumar" className="mt-1.5" />
            </div>
            <div>
              <label className="text-sm font-medium text-ink" htmlFor="email">
                Email
              </label>
              <Input id="email" type="email" defaultValue="saurabh@repolens.ai" className="mt-1.5" />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <Button variant="secondary" onClick={() => toast.success("Profile updated")}>
              <Save />
              Save profile
            </Button>
          </div>
        </Section>

        <Section overline="Appearance" description="The look and layout of the app.">
          <Row label="Dark theme" hint="Warm graphite strata; light mode is warm paper.">
            <div className="flex items-center gap-2">
              <Moon className="h-4 w-4 text-ink-3" />
              <Switch checked={theme === "dark"} onCheckedChange={toggleTheme} />
            </div>
          </Row>
          <Separator />
          <Row label="Collapse sidebar by default" hint="Start each session with a compact sidebar.">
            <Switch checked={sidebarCollapsed} onCheckedChange={setSidebarCollapsed} />
          </Row>
        </Section>

        <Section overline="LLM Provider" description="Model provider for retrieval and generation.">
          <Row label="Provider" hint="Used for embeddings and answer generation.">
            <div className="flex gap-1 rounded-md border border-edge bg-raised p-1">
              {(["openai", "groq"] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => setProvider(p)}
                  className={cn(
                    "rounded-sm px-3 py-1 font-mono text-[13px] capitalize transition-colors",
                    provider === p ? "bg-overlay text-ink shadow-stratum" : "text-ink-3 hover:text-ink-2",
                  )}
                >
                  {p}
                </button>
              ))}
            </div>
          </Row>
          <Separator />
          <div className="py-3">
            <label className="text-sm font-medium text-ink" htmlFor="key">
              API key
            </label>
            <div className="mt-1.5 flex gap-2">
              <div className="relative flex-1">
                <Input
                  id="key"
                  type={showKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="pr-10 font-mono text-[13px]"
                />
                <button
                  onClick={() => setShowKey((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-3 transition-colors hover:text-ink-2"
                  aria-label={showKey ? "Hide key" : "Show key"}
                >
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <Button onClick={saveKeys}>
                <Save />
                Save
              </Button>
            </div>
            <p className="mt-1.5 text-xs text-ink-3">Keys are encrypted at rest and never logged.</p>
          </div>
        </Section>

        <motion.div variants={fadeInUp}>
          <Card className="border-rust/25 p-6">
            <Overline className="text-rust">Danger zone</Overline>
            <p className="mt-1.5 text-sm text-ink-2">
              Irreversible actions that affect your entire workspace.
            </p>
            <div className="mt-5">
              <Row label="Delete all indexed data" hint="Removes every repository, graph, and vector index.">
                <Dialog>
                  <DialogTrigger asChild>
                    <Button variant="destructive">
                      <Trash2 />
                      Delete
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Delete all indexed data?</DialogTitle>
                      <DialogDescription>
                        This permanently removes all repositories and their knowledge graphs and
                        embeddings. This action cannot be undone.
                      </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                      <DialogClose asChild>
                        <Button variant="secondary">Cancel</Button>
                      </DialogClose>
                      <DialogClose asChild>
                        <Button
                          variant="destructive"
                          onClick={() =>
                            toast.error("All data deleted", {
                              description: "Your workspace has been reset.",
                            })
                          }
                        >
                          <Trash2 />
                          Yes, delete everything
                        </Button>
                      </DialogClose>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </Row>
            </div>
          </Card>
        </motion.div>
      </motion.div>
    </div>
  );
}
