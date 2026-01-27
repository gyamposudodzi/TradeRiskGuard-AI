"use client"

import { useEffect, useState } from "react"
import { apiClient } from "@/lib/api"
import { AlertTriangle } from "lucide-react"

type RiskInsightsProps = {
  analysis: any | null
}

export function RiskInsights({ analysis }: RiskInsightsProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<string | null>(null)
  const [keyStrengths, setKeyStrengths] = useState<string[]>([])
  const [keyRisks, setKeyRisks] = useState<string[]>([])

  useEffect(() => {
    const fetchExplanations = async () => {
      if (!analysis) return

      setLoading(true)
      setError(null)

      try {
        const res = await apiClient.riskExplanations({
          metrics: analysis.metrics || {},
          risk_results: analysis.risk_results || {},
          score_result: analysis.score_result || {},
          format_for_display: false,
        })

        if (!res.success || !res.data) {
          setError(res.error || res.message || "Could not load risk insights.")
          return
        }

        const explanations = res.data.explanations || {}
        setSummary(explanations.risk_summary || null)
        setKeyStrengths(explanations.key_strengths || [])
        setKeyRisks(explanations.key_risks || [])
      } catch (e) {
        setError("Failed to load risk insights. Please try again.")
      } finally {
        setLoading(false)
      }
    }

    fetchExplanations()
  }, [analysis])

  return (
    <div className="mb-8 rounded-xl border border-border/30 bg-card/50 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">Risk AI Insights</h3>
        {loading && <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />}
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {!error && !loading && !summary && (
        <p className="text-sm text-muted-foreground">No analysis found yet. Upload trades to generate insights.</p>
      )}

      {!error && summary && (
        <div className="space-y-4">
          {summary.includes("[Offline Mode:") && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-2 rounded border border-red-500/30 bg-red-500/10 text-xs text-red-500 font-medium">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Offline Mode: AI explanations paused (Quota Reached)</span>
            </div>
          )}

          <p className="text-sm text-foreground leading-relaxed">
            {summary.replace(/⚠️ \[Offline Mode:.*?\]/, "").trim()}
          </p>

          {keyStrengths.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase mb-2">Key strengths</p>
              <ul className="space-y-1">
                {keyStrengths.map((item, idx) => (
                  <li key={idx} className="text-sm text-foreground">• {item}</li>
                ))}
              </ul>
            </div>
          )}

          {keyRisks.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase mb-2">Key risks</p>
              <ul className="space-y-1">
                {keyRisks.map((item, idx) => (
                  <li key={idx} className="text-sm text-foreground">• {item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
