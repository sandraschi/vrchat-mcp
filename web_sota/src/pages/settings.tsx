import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState, useEffect } from "react";

function LLMSettings() {
    const [providers, setProviders] = useState<Record<string, {name:string}[]>>({});
    const [selectedProvider, setSelectedProvider] = useState("ollama");
    const [selectedModel, setSelectedModel] = useState("");
    const [status, setStatus] = useState<"loading"|"ready"|"error">("loading");
    useEffect(() => {
        fetch("/api/llm/providers").then(r => r.json()).then(d => {
            setProviders(d);
            const savedP = localStorage.getItem("llm_provider") || "ollama";
            const savedM = localStorage.getItem("llm_model") || "";
            setSelectedProvider(savedP);
            const models = d[savedP === "ollama" ? "ollama" : "lm_studio"] || [];
            setSelectedModel(savedM && models.some((m:{name:string}) => m.name === savedM) ? savedM : (models[0]?.name || ""));
            setStatus(models.length > 0 ? "ready" : "error");
        }).catch(() => {
            setProviders({ ollama: [{name:"llama3.2:3b"}] });
            setSelectedModel(localStorage.getItem("llm_model") || "llama3.2:3b");
            setStatus("ready");
        });
    }, []);
    const save = (p:string, m:string) => { localStorage.setItem("llm_provider", p); localStorage.setItem("llm_model", m); };
    const models = providers[selectedProvider === "ollama" ? "ollama" : "lm_studio"] || [];
    return (
        <Card className="bg-slate-900/50 border-slate-800">
            <CardHeader>
                <CardTitle className="text-white">Local LLM</CardTitle>
                <CardDescription>Provider and model selection</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label>Provider</Label>
                    <select className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-3 text-sm text-slate-200"
                        value={selectedProvider} onChange={(e) => { setSelectedProvider(e.target.value); save(e.target.value, ""); }}>
                        <option value="ollama">Ollama</option>
                        <option value="lm_studio">LM Studio</option>
                    </select>
                </div>
                <div className="space-y-2">
                    <Label>Model</Label>
                    <select className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-3 text-sm text-slate-200"
                        value={selectedModel} onChange={(e) => { setSelectedModel(e.target.value); save(selectedProvider, e.target.value); }}>
                        {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
                    </select>
                </div>
            </CardContent>
        </Card>
    );
}

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

            <LLMSettings />
        </div>
    );
}
