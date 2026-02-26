import { HelpCircle, Book, MessageSquare } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function Help() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-white">Help</h1>
                <p className="text-slate-400">OSC bridge documentation.</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center gap-4 text-white">
                        <Book className="h-5 w-5 text-blue-500" />
                        <CardTitle>OSC Protocol</CardTitle>
                    </CardHeader>
                    <CardContent className="text-slate-400 text-sm"> Documentation on address patterns and data types.</CardContent>
                </Card>
            </div>
        </div>
    );
}
