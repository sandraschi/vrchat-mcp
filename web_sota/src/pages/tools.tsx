import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Terminal } from "lucide-react";

export function Tools() {
    const [tools, setTools] = useState<any[]>([]);

    useEffect(() => {
        fetch('http://localhost:10795/api/v1/tools/')
            .then(res => res.json())
            .then(setTools)
            .catch(console.error);
    }, []);

    return (
        <div className="space-y-6 text-white">
            <h2 className="text-2xl font-bold">OSC Tools</h2>
            <div className="grid gap-4">
                {tools.map(t => (
                    <Card key={t.name} className="border-slate-800 bg-slate-950/50">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Terminal className="h-4 w-4 text-emerald-500" />
                                {t.name}
                            </CardTitle>
                        </CardHeader>
                    </Card>
                ))}
            </div>
        </div>
    );
}
