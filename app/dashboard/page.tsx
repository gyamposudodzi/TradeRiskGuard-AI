"use client"

import { useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Header } from "@/components/layout/header"
import { Footer } from "@/components/layout/footer"
import { DashboardHeader } from "@/components/dashboard/dashboard-header"
import { RiskMetrics } from "@/components/dashboard/risk-metrics"
import { TradeMetrics } from "@/components/dashboard/trade-metrics"
import { RiskCharts } from "@/components/dashboard/risk-charts"
import { TradesList } from "@/components/dashboard/trades-list"
import { RecommendationsBox } from "@/components/dashboard/recommendations"
import { RiskInsights } from "@/components/dashboard/risk-insights"
import { PatternAnalysis } from "@/components/dashboard/pattern-analysis"
import { NewsRisks } from "@/components/dashboard/news-risks"
import { useAuth } from "@/contexts/auth-context"
import { apiClient, DashboardSummary, DashboardInsight } from "@/lib/api"

export default function DashboardPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { isAuthenticated, isLoading } = useAuth()

  const [analysis, setAnalysis] = useState<any | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)

  // New dashboard API states
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary | null>(null)
  const [dashboardInsights, setDashboardInsights] = useState<DashboardInsight[]>([])
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [insightsLoading, setInsightsLoading] = useState(false)

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/signin")
    }
  }, [isAuthenticated, isLoading, router])

  // Load dashboard summary and insights
  useEffect(() => {
    if (!isAuthenticated || isLoading) return

    const loadDashboardData = async () => {
      // Load summary
      setSummaryLoading(true)
      try {
        const summaryRes = await apiClient.getDashboardSummary()
        if (summaryRes.success && summaryRes.data) {
          setDashboardSummary(summaryRes.data)
        }
      } catch (e) {
        console.error("Failed to load dashboard summary:", e)
      } finally {
        setSummaryLoading(false)
      }

      // Load insights
      setInsightsLoading(true)
      try {
        const insightsRes = await apiClient.getDashboardInsights(5)
        if (insightsRes.success && insightsRes.data) {
          setDashboardInsights(insightsRes.data)
        }
      } catch (e) {
        console.error("Failed to load dashboard insights:", e)
      } finally {
        setInsightsLoading(false)
      }
    }

    loadDashboardData()
  }, [isAuthenticated, isLoading])

  // Load latest analysis (or specific one from query) once user is authenticated
  useEffect(() => {
    if (!isAuthenticated || isLoading) return

    const analysisId = searchParams.get("analysisId")

    const load = async () => {
      try {
        setAnalysisLoading(true)
        setAnalysisError(null)

        if (analysisId) {
          const res = await apiClient.getAnalysis(analysisId)
          if (res.success) {
            setAnalysis(res.data)
          } else {
            setAnalysisError(res.error || res.message || "Failed to load analysis.")
          }
          return
        }

        // Fallback: load most recent analysis for this user
        const listRes = await apiClient.listAnalyses({ limit: 1 })
        if (listRes.success && listRes.data && listRes.data.analyses.length > 0) {
          const latest = listRes.data.analyses[0]
          const detailRes = await apiClient.getAnalysis(latest.id)
          if (detailRes.success) {
            setAnalysis(detailRes.data)
          } else {
            setAnalysisError(detailRes.error || detailRes.message || "Failed to load latest analysis.")
          }
        } else {
          // No analyses yet – not an error, just leave analysis as null
          setAnalysis(null)
        }
      } catch (e) {
        setAnalysisError("Something went wrong while loading your latest analysis.")
      } finally {
        setAnalysisLoading(false)
      }
    }

    load()
  }, [isAuthenticated, isLoading, searchParams])

  if (isLoading) {
    return (
      <main className="flex flex-col min-h-screen bg-background">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
        <Footer />
      </main>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <main className="flex flex-col min-h-screen bg-background">
      <Header />
      <div className="flex-1">
        <DashboardHeader />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* In this version, RiskMetrics and other widgets still use mock data.
              Real analysis data is fetched above and can be wired in as needed. */}
          {analysisError && (
            <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {analysisError}
            </div>
          )}



          <RiskInsights analysis={analysis} />
          <RiskMetrics analysis={analysis} />
          <TradeMetrics analysis={analysis} />
          <RiskCharts analysis={analysis} />

          {/* Dedicated Pattern & News Widgets */}
          {analysis && (
            <div className="grid gap-6 mb-8 lg:grid-cols-2">
              <PatternAnalysis patterns={analysis.risk_results?.patterns || []} />
              <NewsRisks eventRisks={analysis.risk_results?.risk_details?.event_trading} />
            </div>
          )}

          <RecommendationsBox analysis={analysis} />
          <TradesList analysis={analysis} />

          {/* Generate Report Section */}
          {analysis && (
            <div className="mt-8 p-6 rounded-xl bg-gradient-to-r from-primary/5 via-accent/5 to-primary/5 border border-primary/20">
              <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="flex-1 text-center md:text-left">
                  <h3 className="text-xl font-bold text-foreground mb-2">Ready to Export Your Analysis?</h3>
                  <p className="text-muted-foreground text-sm max-w-xl">
                    Generate a comprehensive PDF report with all your trading metrics, risk analysis,
                    AI insights, and personalized recommendations. Perfect for record-keeping or sharing with mentors.
                  </p>
                  <div className="flex flex-wrap gap-3 mt-3 justify-center md:justify-start">
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 rounded-full text-xs text-primary">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                      Executive Summary
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 rounded-full text-xs text-primary">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                      Risk Metrics
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 rounded-full text-xs text-primary">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                      AI Insights
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 rounded-full text-xs text-primary">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                      Action Plan
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => router.push(`/report?analysisId=${analysis.id}`)}
                  className="inline-flex items-center gap-2 px-8 py-4 bg-primary text-primary-foreground rounded-xl text-base font-semibold hover:bg-primary/90 transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-105 whitespace-nowrap"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                  </svg>
                  Generate Full Report
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      <Footer />
    </main>
  )
}
