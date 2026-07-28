import {
  Activity,
  BookOpen,
  Bot,
  ChevronLeft,
  ChevronRight,
  Grid,
  HelpCircle,
  LayoutDashboard,
  Radio,
  Settings,
  Wrench,
} from "lucide-react";
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/common/utils";

const MENU_ITEMS = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: Wrench, label: "Tools", path: "/tools" },
  { icon: Activity, label: "Status", path: "/status" },
  { icon: Grid, label: "Apps Hub", path: "/apps" },
  { icon: Bot, label: "Avatars & NPCs", path: "/avatars" },
  { icon: Radio, label: "OSC Control", path: "/osc" },
  { icon: BookOpen, label: "Documentation", path: "/docs" },
  { icon: HelpCircle, label: "Help", path: "/help" },
  { icon: Settings, label: "Settings", path: "/settings" },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-slate-800 bg-slate-950/50 backdrop-blur-xl transition-all duration-300",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div className="flex h-14 items-center justify-between px-4 border-b border-slate-800">
        {!collapsed && (
          <div className="flex items-center gap-2 font-semibold text-white">
            <Activity className="h-5 w-5 text-emerald-500" />
            <span>VRChat MCP</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="rounded-lg p-1 hover:bg-slate-800 text-slate-400 hover:text-white"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {MENU_ITEMS.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-white",
                collapsed && "justify-center px-2",
              )}
            >
              <item.icon
                className={cn("h-5 w-5", isActive && "text-emerald-500")}
              />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 p-2">
        <div
          className={cn(
            "flex items-center gap-3 rounded-lg bg-slate-900/50 px-3 py-2",
            collapsed && "justify-center px-2",
          )}
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
            <div className="h-2 w-2 rounded-full bg-current animate-pulse" />
          </div>
          {!collapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="text-xs font-medium text-white truncate">
                Connected
              </span>
              <span className="text-[10px] text-slate-500 truncate">
                127.0.0.1:9000
              </span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
