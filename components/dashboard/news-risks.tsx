"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { AlertCircle, Calendar, Newspaper, ShieldCheck } from "lucide-react"

interface NewsRisksProps {
    eventRisks: any
}

export function NewsRisks({ eventRisks }: NewsRisksProps) {
    // If no news risks, show a "Safe" card
    if (!eventRisks) {
        return (
            <Card className="h-full border-l-4 border-l-green-500 bg-gradient-to-br from-green-500/5 to-transparent">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <ShieldCheck className="w-5 h-5 text-green-600" />
                        <div className="space-y-1">
                            <CardTitle>News Event Analysis</CardTitle>
                            <CardDescription>Event impact on trading performance</CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col items-center justify-center h-32 text-center">
                        <ShieldCheck className="w-10 h-10 text-green-500/20 mb-3" />
                        <h3 className="font-medium text-foreground">Safe Trading Detected</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            No trades were executed during known high-impact economic events (like NFP or FOMC).
                        </p>
                    </div>
                </CardContent>
            </Card>
        )
    }

    // If risks detected
    return (
        <Card className="h-full border-l-4 border-l-red-500 bg-gradient-to-br from-red-500/5 to-transparent">
            <CardHeader>
                <div className="flex items-center gap-2">
                    <Newspaper className="w-5 h-5 text-red-600" />
                    <div className="space-y-1">
                        <CardTitle>High Impact News Risk</CardTitle>
                        <CardDescription>Trading during major economic releases</CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="p-4 rounded-xl bg-background/50 border border-red-200/50 shadow-sm">
                    <div className="flex gap-4">
                        <div className="p-2 h-fit rounded-lg bg-red-100 text-red-600">
                            <AlertCircle className="w-5 h-5" />
                        </div>
                        <div className="space-y-2">
                            <h4 className="font-semibold text-red-900 dark:text-red-200">
                                {eventRisks.name || "News Event Trading Detected"}
                            </h4>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                {eventRisks.description}
                            </p>

                            <div className="flex items-center gap-4 pt-2">
                                <div className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                                    <AlertCircle className="w-3.5 h-3.5 text-red-500" />
                                    <span>Severity: {eventRisks.severity}%</span>
                                </div>
                                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                    <Calendar className="w-3.5 h-3.5" />
                                    <span>{eventRisks.occurrences || "Multiple"} Events</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="mt-4 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-700 dark:text-amber-400">
                    <strong>Tip:</strong> Avoid trading 30 mins before/after high-impact news (Red Folders) to prevent slippage.
                </div>
            </CardContent>
        </Card>
    )
}
