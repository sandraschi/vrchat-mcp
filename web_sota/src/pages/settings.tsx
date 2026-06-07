import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function Settings() {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold tracking-tight text-white">Settings</h2>
                <p className="text-slate-400">Configure connection and application preferences.</p>
            </div>

            <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader>
                    <CardTitle className="text-white">OSC Configuration</CardTitle>
                    <CardDescription>Network settings for VRChat communication.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Send Host</Label>
                            <Input defaultValue="127.0.0.1" className="bg-slate-950 border-slate-700" />
                        </div>
                        <div className="space-y-2">
                            <Label>Send Port</Label>
                            <Input defaultValue="9000" className="bg-slate-950 border-slate-700" />
                        </div>
                        <div className="space-y-2">
                            <Label>Receive Host</Label>
                            <Input defaultValue="127.0.0.1" className="bg-slate-950 border-slate-700" />
                        </div>
                        <div className="space-y-2">
                            <Label>Receive Port</Label>
                            <Input defaultValue="9001" className="bg-slate-950 border-slate-700" />
                        </div>
                    </div>
                    <Button className="bg-emerald-600 hover:bg-emerald-700">Save Configuration</Button>
                </CardContent>
            </Card>
        </div>
    );
}
