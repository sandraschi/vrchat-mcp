import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Bot, Zap } from "lucide-react";

export function Avatars() {
    const [avatarId, setAvatarId] = useState("");
    const [paramName, setParamName] = useState("Voice");
    const [paramValue, setParamValue] = useState("0.5");

    const handleLoadAvatar = () => {
        console.log(`Loading avatar: ${avatarId}`);
        // TODO: Call MCP Tool
    };

    const handleSetParameter = () => {
        console.log(`Setting parameter ${paramName} to ${paramValue}`);
        // TODO: Call MCP Tool
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold tracking-tight text-white">Avatar Control</h2>
                <p className="text-slate-400">Manage your VRChat avatar and parameters.</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <Card className="bg-slate-900/50 border-slate-800">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-white">
                            <Bot className="h-5 w-5 text-emerald-500" />
                            Load Avatar
                        </CardTitle>
                        <CardDescription>Switch your current avatar by ID or preset.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="avatar-id">Avatar ID / Preset Name</Label>
                            <Input
                                id="avatar-id"
                                placeholder="avtr_..."
                                value={avatarId}
                                onChange={(e) => setAvatarId(e.target.value)}
                                className="bg-slate-950 border-slate-700"
                            />
                        </div>
                        <Button onClick={handleLoadAvatar} className="w-full bg-emerald-600 hover:bg-emerald-700">
                            Load Avatar
                        </Button>
                    </CardContent>
                </Card>

                <Card className="bg-slate-900/50 border-slate-800">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-white">
                            <Zap className="h-5 w-5 text-amber-500" />
                            Set Parameter
                        </CardTitle>
                        <CardDescription>Control float, int, or bool parameters.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="param-name">Parameter Name</Label>
                                <Input
                                    id="param-name"
                                    placeholder="e.g. VISEME"
                                    value={paramName}
                                    onChange={(e) => setParamName(e.target.value)}
                                    className="bg-slate-950 border-slate-700"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="param-value">Value</Label>
                                <Input
                                    id="param-value"
                                    placeholder="0 - 1.0"
                                    value={paramValue}
                                    onChange={(e) => setParamValue(e.target.value)}
                                    className="bg-slate-950 border-slate-700"
                                />
                            </div>
                        </div>
                        <Button onClick={handleSetParameter} variant="secondary" className="w-full">
                            Send Parameter
                        </Button>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
