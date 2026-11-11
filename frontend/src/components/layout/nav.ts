import { ArrowLeftRight, FileSearch, Landmark, LayoutDashboard, ShieldCheck, type LucideIcon } from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

export const navItems: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/trades", label: "Trades", icon: ArrowLeftRight },
  { to: "/risk", label: "Risk", icon: ShieldCheck },
  { to: "/accounts", label: "Accounts", icon: Landmark },
  { to: "/research", label: "Research", icon: FileSearch },
];
