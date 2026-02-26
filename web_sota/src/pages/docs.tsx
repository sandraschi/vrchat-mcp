import { useState, useEffect } from "react";
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

// Since we can't easily fetch local files outside public in Vite dev without config,
// we'll fetch the README from the public folder or just embed a placeholder if not set up to copy.
// Ideally, the build process should copy README.md to public/docs/README.md

export function Docs() {
    const [content, setContent] = useState("# Loading documentation...");

    useEffect(() => {
        // In a real app, we'd fetch specific docs. 
        // For now, we'll try to fetch a localized version or default to instructions.
        setContent(`# VRChat MCP Documentation

**FastMCP 2.12+ implementation for controlling VRChat avatars and assets via OSC protocol.**

## Tool Reference

### \`load_avatar(preset_name, parameters)\`
Loads an avatar by name or ID.

### \`set_parameter(parameter_name, value)\`
Sets a VRChat avatar parameter (float, int, bool).

### \`start_conversation(npc_id, message)\`
Initiates a conversation with an intelligent NPC.

## Setup
1. Enable OSC in VRChat (Settings -> OSC -> Enabled).
2. Ensure port 9000/9001 are open.
3. Run \`vrchat-mcp\` server.
`);
    }, []);

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div>
                <h2 className="text-3xl font-bold tracking-tight text-white">Documentation</h2>
                <p className="text-slate-400">Reference guide for VRChat MCP tools and features.</p>
            </div>

            <Card className="flex-1 bg-slate-900/50 border-slate-800 overflow-hidden">
                <CardContent className="p-0 h-full">
                    <ScrollArea className="h-full p-6">
                        <div className="prose prose-invert max-w-none prose-headings:text-white prose-p:text-slate-300 prose-strong:text-white prose-code:text-emerald-400">
                            <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
                        </div>
                    </ScrollArea>
                </CardContent>
            </Card>
        </div>
    );
}
