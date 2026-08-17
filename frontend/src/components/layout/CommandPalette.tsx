import { useEffect } from "react";
import { Moon, PanelLeft, Plus, Sun } from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from "@/components/ui/command";
import { navItems } from "@/components/layout/navigation";
import { useAppStore } from "@/store/appStore";
import { useRepoStore } from "@/store/repoStore";

/** Global Cmd/Ctrl+K command palette for navigation and quick actions. */
export function CommandPalette() {
  const navigate = useNavigate();
  const open = useAppStore((s) => s.commandOpen);
  const setOpen = useAppStore((s) => s.setCommandOpen);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const theme = useAppStore((s) => s.theme);
  const repositories = useRepoStore((s) => s.repositories);
  const selectRepo = useRepoStore((s) => s.selectRepo);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key?.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(!useAppStore.getState().commandOpen);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [setOpen]);

  const run = (action: () => void) => {
    setOpen(false);
    action();
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Navigation">
          {navItems.map((item) => (
            <CommandItem
              key={item.to}
              value={`go ${item.label}`}
              onSelect={() => run(() => navigate(item.to))}
            >
              <item.icon />
              {item.label}
              {item.shortcut && <CommandShortcut>{item.shortcut}</CommandShortcut>}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandGroup heading="Repositories">
          {repositories.slice(0, 5).map((repo) => (
            <CommandItem
              key={repo.id}
              value={`repo ${repo.owner} ${repo.name}`}
              onSelect={() =>
                run(() => {
                  selectRepo(repo.id);
                  navigate(`/repository/${repo.id}`);
                })
              }
            >
              <span className="text-ink-3">{repo.owner}/</span>
              {repo.name}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandGroup heading="Actions">
          <CommandItem value="new repository upload" onSelect={() => run(() => navigate("/upload"))}>
            <Plus />
            Add repository
          </CommandItem>
          <CommandItem value="toggle theme" onSelect={() => run(toggleTheme)}>
            {theme === "dark" ? <Sun /> : <Moon />}
            Toggle theme
          </CommandItem>
          <CommandItem value="toggle sidebar" onSelect={() => run(toggleSidebar)}>
            <PanelLeft />
            Toggle sidebar
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
