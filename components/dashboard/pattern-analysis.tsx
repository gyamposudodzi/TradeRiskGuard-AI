"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { AlertTriangle, Clock, TrendingDown, Target } from "lucide-react"

interface PatternAnalysisProps {
    patterns: any[]
}

export function PatternAnalysis({ patterns }: PatternAnalysisProps) {
    if (!patterns || patterns.length === 0) {
        return (
            <Card className="h-full">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Target className="w-5 h-5 text-primary" />
                        <div className="space-y-1">
                            <CardTitle>Pattern Recognition</CardTitle>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col items-center justify-center p-6 text-center h-48 border-2 border-dashed border-muted rounded-xl bg-muted/20">
                        <Target className="w-10 h-10 text-muted-foreground/40 mb-3" />
                        <h3 className="font-medium text-foreground">No Negative Patterns Detected</h3>
                        <p className="text-sm text-muted-foreground mt-1 max-w-[250px]">
                            Our AI didn't find any recurring "leak" behaviors in this dataset. Great job!
                        </p>
                    </div>
                </CardContent>
            </Card>
        )
    }

    const getIcon = (type: any) => {
        if (!type || typeof type !== 'string') return <AlertTriangle className="w-4 h-4 text-primary" />
        if (type.includes("Streak")) return <TrendingDown className="w-4 h-4 text-destructive" />
        if (type.includes("Time")) return <Clock className="w-4 h-4 text-amber-500" />
        return <AlertTriangle className="w-4 h-4 text-primary" />
    }

    // Grouping Logic
    const groupedPatterns: Record<string, any[]> = {
        "Time Weaknesses": [],
        "Losing Streaks": [],
        "Strategy & Behavior": [],
        "Other Alerts": []
    }

    patterns.forEach(p => {
        if (!p) return;
        const rawName = p.pattern_name;
        // Ensure name is a string
        const name = (typeof rawName === 'string') ? rawName : String(rawName || "");
        const desc = (typeof p.description === 'string') ? p.description : "";

        // Combine name and description for smarter searching
        const textToCheck = (name + " " + desc).toLowerCase();

        if (textToCheck.includes("time") || textToCheck.includes("hour") || textToCheck.includes("minute") || textToCheck.includes("struggle around") || textToCheck.match(/\d+:\d+/)) {
            groupedPatterns["Time Weaknesses"].push(p);
        } else if (textToCheck.includes("streak") || textToCheck.includes("consecutive") || textToCheck.includes("row")) {
            groupedPatterns["Losing Streaks"].push(p);
        } else if (textToCheck.includes("scalp") || textToCheck.includes("duration") || textToCheck.includes("holding") || textToCheck.includes("size") || textToCheck.includes("lot")) {
            groupedPatterns["Strategy & Behavior"].push(p);
        } else {
            groupedPatterns["Other Alerts"].push(p);
        }
    })

    return (
        <Card className="h-full border-l-4 border-l-amber-500">
            <CardHeader>
                <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-amber-600" />
                    <div className="space-y-1">
                        <CardTitle>Hidden Leaks & Patterns</CardTitle>
                        <CardDescription>Recurring behaviors draining your account</CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {Object.entries(groupedPatterns).map(([category, items]) => {
                        if (items.length === 0) return null;

                        // Icon mapping for the category
                        let CategoryIcon = Target;
                        let colorClass = "text-primary";
                        let bgClass = "bg-primary/5 border-primary/10";

                        if (category.includes("Time")) {
                            CategoryIcon = Clock;
                            colorClass = "text-amber-500";
                            bgClass = "bg-amber-500/5 border-amber-500/10";
                        } else if (category.includes("Streak")) {
                            CategoryIcon = TrendingDown;
                            colorClass = "text-destructive";
                            bgClass = "bg-destructive/5 border-destructive/10";
                        } else if (category.includes("Strategy")) {
                            CategoryIcon = Target; // Or Brain/Lightbulb
                            colorClass = "text-purple-500";
                            bgClass = "bg-purple-500/5 border-purple-500/10";
                        } else {
                            CategoryIcon = AlertTriangle;
                            colorClass = "text-blue-500";
                            bgClass = "bg-blue-500/5 border-blue-500/10";
                        }

                        return (
                            <div key={category} className={`rounded-xl border ${bgClass} p-4`}>
                                <div className="flex items-start gap-4">
                                    <div className={`p-2 rounded-full bg-background border shadow-sm ${colorClass}`}>
                                        <CategoryIcon className="w-5 h-5" />
                                    </div>
                                    <div className="flex-1 space-y-1">
                                        <div className="flex items-center justify-between">
                                            <h4 className="font-semibold text-foreground">
                                                {category} Detected
                                            </h4>
                                            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-background border border-border text-muted-foreground">
                                                {items.length} Instances
                                            </span>
                                        </div>
                                        <p className="text-sm text-muted-foreground pb-2">
                                            We found multiple recurring patterns in this category:
                                        </p>

                                        {/* Consolidated List */}
                                        <ul className="space-y-2 mt-2">
                                            {items.map((pattern, idx) => (
                                                <li key={idx} className="text-sm bg-background/60 p-2 rounded border border-border/40">
                                                    <div className="flex items-center justify-between gap-2">
                                                        <span className="font-medium text-foreground">
                                                            {pattern.pattern_name || "Pattern"}
                                                        </span>
                                                        {pattern.metrics && pattern.metrics.avg_loss && (
                                                            <span className="text-xs text-destructive font-mono">
                                                                -${Math.abs(pattern.metrics.avg_loss).toFixed(2)}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-xs text-muted-foreground mt-0.5">
                                                        {pattern.description}
                                                    </p>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </CardContent>
        </Card>
    )
}
