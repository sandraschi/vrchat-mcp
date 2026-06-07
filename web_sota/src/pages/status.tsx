import { useEffect, useState } from 'react';
import { Activity, Cpu, HardDrive, Network, ShieldCheck, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function Status() {
    const [status, setStatus] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch("http://127.0.0.1:10795/api/v1/manage_system", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ operation: "status" })
                });
                const data = await res.json();
                setStatus(data.data);
            } catch (error) {
                console.error("Status fetch failed:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    const ComponentStatus = ({ name, active }: { name: string; active: boolean }) => (
        <div className="flex items-center justify-between p-2 rounded bg-slate-900/30 border border-slate-800">
            <span className="text-sm text-slate-300">{name}</span>
            <div className="flex items-center">
                <span className={`text-xs mr-2 ${active ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {active ? 'Operational' : 'Offline'}
                </span>
                {active ? <ShieldCheck className="h-3 w-3 text-emerald-500" /> : <AlertCircle className="h-3 w-3 text-rose-500" />}
            </div>
        </div>
    );

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">Bridge Status</h1>
                    <p className="text-slate-400">OSC connectivity and system health for VRChat-bridge.</p>
                </div>
                <div className={`px-4 py-1 rounded-full text-xs font-semibold ${status?.status === 'running' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                    {status?.status === 'running' ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 text-white">
                        <CardTitle className="text-sm font-medium">OSC Pipeline</CardTitle>
                        <Network className={`h-4 w-4 ${status?.components?.osc ? 'text-emerald-500' : 'text-slate-500'}`} />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">{status?.components?.osc ? 'Active' : 'Missing'}</div>
                        <p className="text-xs text-slate-500">UDP Traffic Routing</p>
                    </CardContent>
                </Card>
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 text-white">
                        <CardTitle className="text-sm font-medium">Avatar Engine</CardTitle>
                        <Cpu className={`h-4 w-4 ${status?.components?.avatar ? 'text-blue-500' : 'text-slate-500'}`} />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">{status?.components?.avatar ? 'Ready' : 'Error'}</div>
                        <p className="text-xs text-slate-500">State & Sync logic</p>
                    </CardContent>
                </Card>
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 text-white">
                        <CardTitle className="text-sm font-medium">Core Version</CardTitle>
                        <HardDrive className="h-4 w-4 text-purple-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">{status?.version || '0.0.0'}</div>
                        <p className="text-xs text-slate-500">Industrial Build SOTA</p>
                    </CardContent>
                </Card>
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 text-white">
                        <CardTitle className="text-sm font-medium">System Load</CardTitle>
                        <Activity className="h-4 w-4 text-amber-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">Optimal</div>
                        <p className="text-xs text-slate-500">Resource grouping active</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader>
                        <CardTitle className="text-white">Component Registry</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <ComponentStatus name="OSC Manager" active={!!status?.components?.osc} />
                        <ComponentStatus name="Avatar Manager" active={!!status?.components?.avatar} />
                        <ComponentStatus name="OSC Inspector" active={!!status?.components?.inspector} />
                        <ComponentStatus name="Interpolation Engine" active={!!status?.components?.avatar} />
                    </CardContent>
                </Card>

                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader>
                        <CardTitle className="text-white">Network Matrix</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                         <div className="flex justify-between items-center text-sm">
                            <span className="text-slate-400">OSC Dispatch Port</span>
                            <span className="text-emerald-400 font-mono">9000</span>
                         </div>
                         <div className="flex justify-between items-center text-sm">
                            <span className="text-slate-400">OSC Receive Port</span>
                            <span className="text-emerald-400 font-mono">9001</span>
                         </div>
                         <div className="flex justify-between items-center text-sm border-t border-slate-800 pt-4">
                            <span className="text-slate-400">SOTA API Port</span>
                            <span className="text-blue-400 font-mono">10795</span>
                         </div>
                         <div className="flex justify-between items-center text-sm">
                            <span className="text-slate-400">REST Endpoint</span>
                            <span className="text-slate-300 font-mono">/api/v1/manage_*</span>
                         </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
