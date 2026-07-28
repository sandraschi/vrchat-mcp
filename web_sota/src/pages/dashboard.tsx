import { Activity, MessageSquare, Wifi, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function Dashboard() {
  const [status, setStatus] = useState<any>(null);
  const [oscStats, setOscStats] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch System Status
        const statusRes = await fetch(
          "http://127.0.0.1:10795/api/v1/manage_system",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ operation: "status" }),
          },
        );
        const statusData = await statusRes.json();
        setStatus(statusData.data);

        // Fetch OSC Stats
        const oscRes = await fetch("http://127.0.0.1:10795/api/v1/manage_osc", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ operation: "stats" }),
        });
        const oscData = await oscRes.json();
        setOscStats(oscData.data);

        // Fetch Metrics
        const metricsRes = await fetch(
          "http://127.0.0.1:10795/api/v1/manage_system",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ operation: "metrics" }),
          },
        );
        const metricsData = await metricsRes.json();
        setMetrics(metricsData.data);
      } catch (error) {
        console.error("Failed to fetch dashboard telemetry:", error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-white">
          Dashboard
        </h2>
        <p className="text-slate-400">
          Overview of your VRChat connection and status.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              Connection Status
            </CardTitle>
            <Wifi
              className={`h-4 w-4 ${status?.status === "running" ? "text-emerald-500" : "text-slate-500"}`}
            />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white capitalize">
              {status?.status || "Connecting..."}
            </div>
            <p className="text-xs text-slate-400">Port: 10795 (REST/OSC)</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              System Health
            </CardTitle>
            <Zap className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {status?.components?.osc ? "Nominal" : "Degraded"}
            </div>
            <p className="text-xs text-slate-400">
              OSC Pipeline: {status?.components?.osc ? "Active" : "Down"}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              OSC Traffic
            </CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {oscStats?.messages_sent || 0}
            </div>
            <p className="text-xs text-slate-400">Total packets dispatched</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              Request Rate
            </CardTitle>
            <MessageSquare className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {metrics?.throughput_rps || 0.0}
            </div>
            <p className="text-xs text-slate-400">Requests per second</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4 bg-slate-900/50 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white">Recent Activity</CardTitle>
            <CardDescription>
              Latest performance metrics and system load.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center">
                <span className="relative flex h-2 w-2 mr-4">
                  <span
                    className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${status?.status === "running" ? "bg-emerald-400" : "bg-slate-400"}`}
                  ></span>
                  <span
                    className={`relative inline-flex rounded-full h-2 w-2 ${status?.status === "running" ? "bg-emerald-500" : "bg-slate-500"}`}
                  ></span>
                </span>
                <div className="space-y-1">
                  <p className="text-sm font-medium leading-none text-white">
                    {status?.status === "running"
                      ? "System Ready"
                      : "System Offline"}
                  </p>
                  <p className="text-sm text-slate-400">
                    Server Version: {status?.version || "N/A"} | Uptime:{" "}
                    {metrics?.uptime_seconds || 0}s
                  </p>
                </div>
                <div className="ml-auto font-medium text-slate-500 text-xs text-right">
                  <div>Latency: {metrics?.avg_response_ms || 0}ms</div>
                  <div>Errors: {metrics?.error_rate || 0}%</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
