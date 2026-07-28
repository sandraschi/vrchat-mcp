import { Bell, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function Topbar() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-800 bg-slate-950/50 px-6 backdrop-blur-xl">
      <div className="flex items-center gap-4">
        <div className="relative w-64">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-500" />
          <Input
            placeholder="Search tools & documentation..."
            className="h-9 border-slate-700 bg-slate-900/50 pl-8 text-sm focus:border-emerald-500"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          className="text-slate-400 hover:text-white"
        >
          <Bell className="h-5 w-5" />
        </Button>
        <div className="h-8 w-[1px] bg-slate-800" />
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-400">
            OP
          </div>
          <div className="hidden flex-col md:flex">
            <span className="text-sm font-medium text-white">Operator</span>
            <span className="text-xs text-slate-500">Admin</span>
          </div>
        </div>
      </div>
    </header>
  );
}
