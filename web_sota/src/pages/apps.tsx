import { LayoutGrid } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function Apps() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">App Hub</h1>
        <p className="text-slate-400">Manage VRChat OSC integrations.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center gap-4 pb-2 text-white">
            <LayoutGrid className="h-6 w-6 text-emerald-500" />
            <CardTitle className="text-lg">OSC Visualizer</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-400">
              Real-time data visualization for OSC traffic.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
