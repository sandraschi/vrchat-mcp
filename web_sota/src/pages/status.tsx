import { Activity, Cpu, HardDrive, Network } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function Status() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-white">Bridge Status</h1>
                <p className="text-slate-400">OSC connectivity and system health for VRChat-bridge.</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 text-white">
                        <CardTitle className="text-sm font-medium">OSC Latency</CardTitle>
                        <Network className="h-4 w-4 text-emerald-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">4ms</div>
                        <p className="text-xs text-slate-500">Local loopback active</p>
                    </CardContent>
                </Card>
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 text-white">
                        <CardTitle className="text-sm font-medium">Avatar Sync</CardTitle>
                        <Cpu className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">Active</div>
                        <p className="text-xs text-slate-500">12 parameters tracking</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
