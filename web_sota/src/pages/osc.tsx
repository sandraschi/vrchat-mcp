import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Radio, Send } from "lucide-react";

export function OSC() {
    const [address, setAddress] = useState("/avatar/parameters/");
    const [value, setValue] = useState("");
    const [logs, setLogs] = useState<string[]>([
        "[12:00:01] System ready.",
        "[12:00:02] Listening on 127.0.0.1:9001"
    ]);

    const handleSend = () => {
        const timestamp = new Date().toLocaleTimeString();
        setLogs(prev => [`[${timestamp}] Sent ${address}: ${value}`, ...prev]);
        setValue("");
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold tracking-tight text-white">OSC Debugger</h2>
                <p className="text-slate-400">Send and monitor Open Sound Control messages.</p>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
                <Card className="col-span-1 bg-slate-900/50 border-slate-800">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-white">
                            <Send className="h-5 w-5 text-blue-500" />
                            Send Message
                        </CardTitle>
                        <CardDescription>Manually dispatch OSC packet.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="address">OSC Address</Label>
                            <Input
                                id="address"
                                value={address}
                                onChange={(e) => setAddress(e.target.value)}
                                className="bg-slate-950 border-slate-700 font-mono text-xs"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="value">Value</Label>
                            <Input
                                id="value"
                                placeholder="1.0, true, or string"
                                value={value}
                                onChange={(e) => setValue(e.target.value)}
                                className="bg-slate-950 border-slate-700"
                            />
                        </div>
                        <Button onClick={handleSend} className="w-full">
                            Send Packet
                        </Button>
                    </CardContent>
                </Card>

                <Card className="col-span-2 bg-slate-900/50 border-slate-800 h-[500px] flex flex-col">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-white">
                            <Radio className="h-5 w-5 text-emerald-500" />
                            Live Logs
                        </CardTitle>
                        <CardDescription>Incoming and outgoing traffic.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex-1 overflow-hidden p-0">
                        <ScrollArea className="h-full p-6 pt-0">
                            <div className="space-y-2 font-mono text-sm">
                                {logs.map((log, i) => (
                                    <div key={i} className="text-slate-300 border-b border-slate-800/50 pb-1">
                                        {log}
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
