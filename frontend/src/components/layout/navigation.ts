import {
  BarChart3,
  GitBranch,
  LayoutDashboard,
  Layers,
  MessagesSquare,
  Network,
  Settings,
  UploadCloud,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  /** Optional keyboard hint shown in the command palette. */
  shortcut?: string;
}

/** Primary navigation, shared by the sidebar and the command palette. */
export const navItems: NavItem[] = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard, shortcut: "G D" },
  { label: "Upload Repository", to: "/upload", icon: UploadCloud, shortcut: "G U" },
  { label: "Repository", to: "/repository", icon: GitBranch, shortcut: "G R" },
  { label: "Analytics", to: "/analytics", icon: BarChart3, shortcut: "G N" },
  { label: "Chat", to: "/chat", icon: MessagesSquare, shortcut: "G C" },
  { label: "Diagrams", to: "/diagrams", icon: Workflow, shortcut: "G A" },
  { label: "Architecture", to: "/architecture", icon: Layers, shortcut: "G H" },
  { label: "Dependencies", to: "/dependencies", icon: Network, shortcut: "G P" },
  { label: "Settings", to: "/settings", icon: Settings, shortcut: "G S" },
];
