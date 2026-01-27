"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter } from "next/navigation"
import { Header } from "@/components/layout/header"
import { Footer } from "@/components/layout/footer"
import { useAuth } from "@/contexts/auth-context"
import { apiClient, UserSettings, AlertSettings } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  User,
  Settings,
  Bell,
  Link2,
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Shield,
  TrendingUp,
  Brain,
  Mail,
  Smartphone,
  Clock,
  BarChart3,
  Target,
  Percent,
  Trash2
} from "lucide-react"

export default function SettingsPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading, user } = useAuth()

  // Profile state
  const [profile, setProfile] = useState<any>(null)
  const [profileLoading, setProfileLoading] = useState(true)

  // User settings state
  const [userSettings, setUserSettings] = useState<UserSettings>({
    max_position_size_pct: 5,
    min_win_rate: 50,
    max_drawdown_pct: 20,
    min_rr_ratio: 1.5,
    min_sl_usage_rate: 80,
    ai_enabled: true,
    preferred_model: "gpt-4",
    openai_api_key_configured: false
  })
  const [openaiKeyInput, setOpenaiKeyInput] = useState("")
  const [userSettingsLoading, setUserSettingsLoading] = useState(true)
  const [userSettingsSaving, setUserSettingsSaving] = useState(false)

  // Alert settings state
  const [alertSettings, setAlertSettings] = useState<AlertSettings>({
    enabled: true,
    min_confidence: 70,
    in_app_alerts: true,
    email_alerts: false,
    push_notifications: false,
    show_pattern_alerts: true,
    show_behavioral_alerts: true,
    show_time_based_alerts: true,
    show_market_alerts: true,
    real_time_alerts: true,
    daily_summary: true,
    weekly_report: false,
    default_snooze_hours: 24
  })
  const [alertSettingsLoading, setAlertSettingsLoading] = useState(true)
  const [alertSettingsSaving, setAlertSettingsSaving] = useState(false)

  // Deriv connection state
  // Deriv connection state
  const [derivConnection, setDerivConnection] = useState<any>(null)
  const [derivApiToken, setDerivApiToken] = useState("")
  const [derivConnecting, setDerivConnecting] = useState(false)
  const [derivSyncing, setDerivSyncing] = useState(false)

  // Save status
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error' | null, message: string }>({ type: null, message: '' })

  const dataFetchedRef = useRef(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    // Redirect if not authenticated
    if (!isLoading && !isAuthenticated) {
      router.push("/signin")
      return
    }


    // Only fetch data if authenticated and not already fetched
    if (isAuthenticated && !isLoading && !dataFetchedRef.current) {
      dataFetchedRef.current = true

      const loadAllData = async () => {
        try {
          // Load profile
          const profileRes = await apiClient.getProfile()
          if (profileRes.success) setProfile(profileRes.data)

          // Load user settings
          const settingsRes = await apiClient.getUserSettings()
          if (settingsRes.success && settingsRes.data) setUserSettings(settingsRes.data)

          // Load alert settings
          const alertsRes = await apiClient.getAlertSettings()
          if (alertsRes.success && alertsRes.data) setAlertSettings(alertsRes.data)

          // Load connections
          const connRes = await apiClient.listDerivConnections()
          if (connRes.success && connRes.data && connRes.data.connections.length > 0) {
            const conn = connRes.data.connections[0]
            setDerivConnection(conn)
            // Pre-fill token if backend provides it (persistence feature)
            if (conn.api_token) {
              setDerivApiToken(conn.api_token)
            }
          } else {
            setDerivConnection(null)
          }
        } catch (e) {
          console.error("Error loading settings data:", e)
        } finally {
          setProfileLoading(false)
          setUserSettingsLoading(false)
          setAlertSettingsLoading(false)
        }
      }

      loadAllData()
    }
  }, [isAuthenticated, isLoading, router])

  const handleSaveOpenAIKey = async () => {
    if (!openaiKeyInput.trim()) return

    setUserSettingsSaving(true)
    setSaveStatus({ type: null, message: '' })

    try {
      // Send key to backend for encryption
      const res = await apiClient.updateUserSettings({
        ...userSettings,
        openai_api_key: openaiKeyInput.trim()
      })

      if (res.success) {
        setSaveStatus({ type: 'success', message: 'OpenAI Key saved securely!' })
        setUserSettings(prev => ({ ...prev, openai_api_key_configured: true }))
        setOpenaiKeyInput("") // Clear input for security
      } else {
        setSaveStatus({ type: 'error', message: res.error || 'Failed to save key' })
      }
    } catch (e) {
      setSaveStatus({ type: 'error', message: 'An error occurred while saving key' })
    } finally {
      setUserSettingsSaving(false)
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 3000)
    }
  }

  const handleClearOpenAIKey = async () => {
    if (!confirm("Remove your custom OpenAI Key? You will revert to the default shared quota limits.")) return

    setUserSettingsSaving(true)

    try {
      const res = await apiClient.updateUserSettings({
        ...userSettings,
        openai_api_key: "" // Empty string clears it in backend
      })

      if (res.success) {
        setSaveStatus({ type: 'success', message: 'OpenAI Key removed.' })
        setUserSettings(prev => ({ ...prev, openai_api_key_configured: false }))
      } else {
        setSaveStatus({ type: 'error', message: 'Failed to remove key' })
      }
    } catch (e) {
      console.error(e)
    } finally {
      setUserSettingsSaving(false)
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 3000)
    }
  }

  const handleSaveUserSettings = async () => {
    setUserSettingsSaving(true)
    setSaveStatus({ type: null, message: '' })

    try {
      const res = await apiClient.updateUserSettings(userSettings)
      if (res.success) {
        setSaveStatus({ type: 'success', message: 'Trading settings saved successfully!' })
      } else {
        setSaveStatus({ type: 'error', message: res.error || 'Failed to save settings' })
      }
    } catch (e) {
      setSaveStatus({ type: 'error', message: 'An error occurred while saving' })
    } finally {
      setUserSettingsSaving(false)
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 3000)
    }
  }

  const handleSaveAlertSettings = async () => {
    setAlertSettingsSaving(true)
    setSaveStatus({ type: null, message: '' })

    try {
      const res = await apiClient.updateAlertSettings(alertSettings)
      if (res.success) {
        setSaveStatus({ type: 'success', message: 'Alert settings saved successfully!' })
      } else {
        setSaveStatus({ type: 'error', message: res.error || 'Failed to save alert settings' })
      }
    } catch (e) {
      setSaveStatus({ type: 'error', message: 'An error occurred while saving' })
    } finally {
      setAlertSettingsSaving(false)
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 3000)
    }
  }

  const handleConnectDeriv = async () => {
    if (!derivApiToken.trim()) {
      setSaveStatus({ type: 'error', message: 'Please enter your Deriv API token' })
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 3000)
      return
    }

    setDerivConnecting(true)
    setSaveStatus({ type: null, message: '' })

    try {
      const res = await apiClient.connectDeriv({
        api_token: derivApiToken.trim(),
        connection_name: "My Deriv Account",
        app_id: "1089",
        auto_sync: true,
        sync_days_back: 30
      })

      if (res.success) {
        setDerivConnection(res.data.connection)
        setSaveStatus({ type: 'success', message: 'Deriv account connected successfully!' })
        // We do NOT clear the token here so it persists in the UI during this session
        // setDerivApiToken("") 
      } else {
        setSaveStatus({ type: 'error', message: res.error || 'Failed to connect account' })
      }
    } catch (e) {
      setSaveStatus({ type: 'error', message: 'An error occurred while connecting' })
    } finally {
      setDerivConnecting(false)
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 5000)
    }
  }

  const handleDisconnectDeriv = async () => {
    if (!derivConnection) return

    if (!confirm("Are you sure you want to disconnect? This will stop automatic syncing.")) {
      return
    }

    try {
      const res = await apiClient.disconnectDeriv(derivConnection.id)
      if (res.success) {
        setDerivConnection(null)
        setSaveStatus({ type: 'success', message: 'Deriv account disconnected' })
      } else {
        setSaveStatus({ type: 'error', message: res.error || 'Failed to disconnect' })
      }
    } catch (e) {
      setSaveStatus({ type: 'error', message: 'An error occurred while disconnecting' })
    } finally {
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 3000)
    }
  }

  const handleSyncDeriv = async () => {
    if (!derivConnection) return

    setDerivSyncing(true)
    try {
      const res = await apiClient.syncDeriv({
        connection_id: derivConnection.id,
        force_full_sync: false,
        analyze_after_sync: true
      })

      if (res.success) {
        setSaveStatus({ type: 'success', message: 'Sync started successfully. Check dashboard shortly.' })
      } else {
        setSaveStatus({ type: 'error', message: res.error || 'Failed to start sync' })
      }
    } catch (e) {
      setSaveStatus({ type: 'error', message: 'Failed to trigger sync' })
    } finally {
      setDerivSyncing(false)
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 5000)
    }
  }

  if (isLoading || !mounted) {
    return (
      <main className="flex flex-col min-h-screen bg-background">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
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
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Page Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-foreground mb-2">Settings</h1>
            <p className="text-muted-foreground">Manage your account, trading preferences, and notifications</p>
          </div>

          {/* Save Status Toast */}
          {saveStatus.type && (
            <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${saveStatus.type === 'success'
              ? 'bg-green-500/10 border border-green-500/20 text-green-600'
              : 'bg-destructive/10 border border-destructive/20 text-destructive'
              }`}>
              {saveStatus.type === 'success' ? (
                <CheckCircle2 className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
              <span className="text-sm font-medium">{saveStatus.message}</span>
            </div>
          )}

          <Tabs defaultValue="profile" className="space-y-6">
            <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-grid">
              <TabsTrigger value="profile" className="gap-2">
                <User className="w-4 h-4" />
                <span className="hidden sm:inline">Profile</span>
              </TabsTrigger>
              <TabsTrigger value="trading" className="gap-2">
                <Settings className="w-4 h-4" />
                <span className="hidden sm:inline">Trading</span>
              </TabsTrigger>
              <TabsTrigger value="alerts" className="gap-2">
                <Bell className="w-4 h-4" />
                <span className="hidden sm:inline">Alerts</span>
              </TabsTrigger>
              <TabsTrigger value="connections" className="gap-2">
                <Link2 className="w-4 h-4" />
                <span className="hidden sm:inline">Connections</span>
              </TabsTrigger>
            </TabsList>

            {/* Profile Tab */}
            <TabsContent value="profile" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <User className="w-5 h-5 text-primary" />
                    Profile Information
                  </CardTitle>
                  <CardDescription>Your account details and information</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {profileLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-2xl font-bold text-white">
                          {(profile?.username || user?.name || user?.email || 'U').charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-foreground">{profile?.username || user?.name || 'User'}</h3>
                          <p className="text-sm text-muted-foreground">{profile?.email || user?.email}</p>
                        </div>
                      </div>

                      <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2">
                          <Label htmlFor="username">Username</Label>
                          <Input
                            id="username"
                            value={profile?.username || user?.name || ''}
                            disabled
                            className="bg-muted/50"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="email">Email</Label>
                          <Input
                            id="email"
                            type="email"
                            value={profile?.email || user?.email || ''}
                            disabled
                            className="bg-muted/50"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="created">Member Since</Label>
                          <Input
                            id="created"
                            value={profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : 'N/A'}
                            disabled
                            className="bg-muted/50"
                          />
                        </div>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Trading Settings Tab */}
            <TabsContent value="trading" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-primary" />
                    Risk Management Thresholds
                  </CardTitle>
                  <CardDescription>Set your personal risk limits and trading parameters</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {userSettingsLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : (
                    <>
                      <div className="grid gap-6 sm:grid-cols-2">
                        <div className="space-y-2">
                          <Label htmlFor="max_position" className="flex items-center gap-2">
                            <Percent className="w-4 h-4 text-muted-foreground" />
                            Max Position Size (%)
                          </Label>
                          <Input
                            id="max_position"
                            type="number"
                            min="0"
                            max="100"
                            value={userSettings.max_position_size_pct}
                            onChange={(e) => setUserSettings({ ...userSettings, max_position_size_pct: parseFloat(e.target.value) || 0 })}
                          />
                          <p className="text-xs text-muted-foreground">Maximum % of portfolio per trade</p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="min_win_rate" className="flex items-center gap-2">
                            <Target className="w-4 h-4 text-muted-foreground" />
                            Min Win Rate (%)
                          </Label>
                          <Input
                            id="min_win_rate"
                            type="number"
                            min="0"
                            max="100"
                            value={userSettings.min_win_rate}
                            onChange={(e) => setUserSettings({ ...userSettings, min_win_rate: parseFloat(e.target.value) || 0 })}
                          />
                          <p className="text-xs text-muted-foreground">Target minimum win rate</p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="max_drawdown" className="flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-muted-foreground" />
                            Max Drawdown (%)
                          </Label>
                          <Input
                            id="max_drawdown"
                            type="number"
                            min="0"
                            max="100"
                            value={userSettings.max_drawdown_pct}
                            onChange={(e) => setUserSettings({ ...userSettings, max_drawdown_pct: parseFloat(e.target.value) || 0 })}
                          />
                          <p className="text-xs text-muted-foreground">Maximum acceptable drawdown</p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="min_rr" className="flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-muted-foreground" />
                            Min Risk/Reward Ratio
                          </Label>
                          <Input
                            id="min_rr"
                            type="number"
                            min="0"
                            step="0.1"
                            value={userSettings.min_rr_ratio}
                            onChange={(e) => setUserSettings({ ...userSettings, min_rr_ratio: parseFloat(e.target.value) || 0 })}
                          />
                          <p className="text-xs text-muted-foreground">Minimum R:R for each trade</p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="min_sl" className="flex items-center gap-2">
                            <Shield className="w-4 h-4 text-muted-foreground" />
                            Min Stop-Loss Usage (%)
                          </Label>
                          <Input
                            id="min_sl"
                            type="number"
                            min="0"
                            max="100"
                            value={userSettings.min_sl_usage_rate}
                            onChange={(e) => setUserSettings({ ...userSettings, min_sl_usage_rate: parseFloat(e.target.value) || 0 })}
                          />
                          <p className="text-xs text-muted-foreground">Target stop-loss usage rate</p>
                        </div>
                      </div>

                      <div className="pt-4 border-t">
                        <h4 className="text-sm font-semibold mb-4 flex items-center gap-2">
                          <Brain className="w-4 h-4 text-primary" />
                          AI Configuration
                        </h4>
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>AI Analysis Enabled</Label>
                              <p className="text-xs text-muted-foreground">Get AI-powered insights on your trades</p>
                            </div>
                            <Switch
                              checked={userSettings.ai_enabled}
                              onCheckedChange={(checked) => setUserSettings({ ...userSettings, ai_enabled: checked })}
                            />
                          </div>

                          {userSettings.ai_enabled && (
                            <div className="pt-2 pb-4 border-b">
                              <Label className="text-base font-medium block mb-1">Custom OpenAI Key (Optional)</Label>
                              <p className="text-sm text-muted-foreground mb-3">
                                Provide your own API key to bypass usage limits.
                                {userSettings.openai_api_key_configured && <span className="text-green-600 font-medium ml-2">✓ Key Configured</span>}
                              </p>

                              <div className="flex gap-2">
                                <Input
                                  type="password"
                                  placeholder={userSettings.openai_api_key_configured ? "•••••••••••••••• (Configured)" : "sk-..."}
                                  value={openaiKeyInput}
                                  onChange={(e) => setOpenaiKeyInput(e.target.value)}
                                  className="flex-1"
                                />
                                <Button
                                  variant="outline"
                                  onClick={handleSaveOpenAIKey}
                                  disabled={!openaiKeyInput || userSettingsSaving}
                                  size="sm"
                                  className="whitespace-nowrap"
                                >
                                  {userSettings.openai_api_key_configured ? "Update Key" : "Save Key"}
                                </Button>

                                {userSettings.openai_api_key_configured && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                                    onClick={() => {
                                      setOpenaiKeyInput("");
                                      handleClearOpenAIKey();
                                    }}
                                    title="Clear Key"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                )}
                              </div>
                              <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
                                <Shield className="w-3 h-3" />
                                Your key is encrypted securely. We never store it in plain text.
                              </p>
                            </div>
                          )}

                          {userSettings.ai_enabled && (
                            <div className="space-y-2">
                              <Label htmlFor="ai_model">Preferred AI Model</Label>
                              <select
                                id="ai_model"
                                value={userSettings.preferred_model}
                                onChange={(e) => setUserSettings({ ...userSettings, preferred_model: e.target.value })}
                                className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm"
                              >
                                <option value="gpt-4">GPT-4 (Recommended)</option>
                                <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Faster)</option>
                                <option value="claude-3">Claude 3</option>
                              </select>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex justify-end pt-4">
                        <Button onClick={handleSaveUserSettings} disabled={userSettingsSaving}>
                          {userSettingsSaving ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Saving...
                            </>
                          ) : (
                            <>
                              <Save className="w-4 h-4 mr-2" />
                              Save Settings
                            </>
                          )}
                        </Button>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Alerts Tab */}
            <TabsContent value="alerts" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Bell className="w-5 h-5 text-primary" />
                    Alert Preferences
                  </CardTitle>
                  <CardDescription>Configure how and when you receive alerts</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {alertSettingsLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : (
                    <>
                      {/* Master Toggle */}
                      <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                        <div className="space-y-0.5">
                          <Label className="text-base font-semibold">Enable All Alerts</Label>
                          <p className="text-sm text-muted-foreground">Master toggle for all alert notifications</p>
                        </div>
                        <Switch
                          checked={alertSettings.enabled}
                          onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, enabled: checked })}
                        />
                      </div>

                      {alertSettings.enabled && (
                        <>
                          {/* Notification Channels */}
                          <div className="space-y-4">
                            <h4 className="text-sm font-semibold">Notification Channels</h4>
                            <div className="grid gap-4 sm:grid-cols-3">
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <div className="flex items-center gap-2">
                                  <Bell className="w-4 h-4 text-muted-foreground" />
                                  <Label>In-App</Label>
                                </div>
                                <Switch
                                  checked={alertSettings.in_app_alerts}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, in_app_alerts: checked })}
                                />
                              </div>
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <div className="flex items-center gap-2">
                                  <Mail className="w-4 h-4 text-muted-foreground" />
                                  <Label>Email</Label>
                                </div>
                                <Switch
                                  checked={alertSettings.email_alerts}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, email_alerts: checked })}
                                />
                              </div>
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <div className="flex items-center gap-2">
                                  <Smartphone className="w-4 h-4 text-muted-foreground" />
                                  <Label>Push</Label>
                                </div>
                                <Switch
                                  checked={alertSettings.push_notifications}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, push_notifications: checked })}
                                />
                              </div>
                            </div>
                          </div>

                          {/* Alert Types */}
                          <div className="space-y-4 pt-4 border-t">
                            <h4 className="text-sm font-semibold">Alert Types</h4>
                            <div className="grid gap-3 sm:grid-cols-2">
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <Label>Pattern Alerts</Label>
                                <Switch
                                  checked={alertSettings.show_pattern_alerts}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, show_pattern_alerts: checked })}
                                />
                              </div>
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <Label>Behavioral Alerts</Label>
                                <Switch
                                  checked={alertSettings.show_behavioral_alerts}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, show_behavioral_alerts: checked })}
                                />
                              </div>
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <Label>Time-based Alerts</Label>
                                <Switch
                                  checked={alertSettings.show_time_based_alerts}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, show_time_based_alerts: checked })}
                                />
                              </div>
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <Label>Market Alerts</Label>
                                <Switch
                                  checked={alertSettings.show_market_alerts}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, show_market_alerts: checked })}
                                />
                              </div>
                            </div>
                          </div>

                          {/* Frequency & Sensitivity */}
                          <div className="space-y-4 pt-4 border-t">
                            <h4 className="text-sm font-semibold">Frequency & Sensitivity</h4>
                            <div className="grid gap-4 sm:grid-cols-2">
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <div className="space-y-0.5">
                                  <Label>Real-time Alerts</Label>
                                  <p className="text-xs text-muted-foreground">Get alerts instantly</p>
                                </div>
                                <Switch
                                  checked={alertSettings.real_time_alerts}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, real_time_alerts: checked })}
                                />
                              </div>
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <div className="space-y-0.5">
                                  <Label>Daily Summary</Label>
                                  <p className="text-xs text-muted-foreground">Daily digest email</p>
                                </div>
                                <Switch
                                  checked={alertSettings.daily_summary}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, daily_summary: checked })}
                                />
                              </div>
                              <div className="flex items-center justify-between p-3 rounded-lg border">
                                <div className="space-y-0.5">
                                  <Label>Weekly Report</Label>
                                  <p className="text-xs text-muted-foreground">Weekly performance summary</p>
                                </div>
                                <Switch
                                  checked={alertSettings.weekly_report}
                                  onCheckedChange={(checked) => setAlertSettings({ ...alertSettings, weekly_report: checked })}
                                />
                              </div>
                              <div className="space-y-2 p-3 rounded-lg border">
                                <Label htmlFor="min_confidence" className="flex items-center gap-2">
                                  Min Confidence (%)
                                </Label>
                                <Input
                                  id="min_confidence"
                                  type="number"
                                  min="0"
                                  max="100"
                                  value={alertSettings.min_confidence}
                                  onChange={(e) => setAlertSettings({ ...alertSettings, min_confidence: parseInt(e.target.value) || 0 })}
                                />
                              </div>
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor="snooze_hours" className="flex items-center gap-2">
                                <Clock className="w-4 h-4 text-muted-foreground" />
                                Default Snooze Duration (hours)
                              </Label>
                              <Input
                                id="snooze_hours"
                                type="number"
                                min="1"
                                max="168"
                                value={alertSettings.default_snooze_hours}
                                onChange={(e) => setAlertSettings({ ...alertSettings, default_snooze_hours: parseInt(e.target.value) || 24 })}
                              />
                            </div>
                          </div>
                        </>
                      )}

                      <div className="flex justify-end pt-4">
                        <Button onClick={handleSaveAlertSettings} disabled={alertSettingsSaving}>
                          {alertSettingsSaving ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Saving...
                            </>
                          ) : (
                            <>
                              <Save className="w-4 h-4 mr-2" />
                              Save Alert Settings
                            </>
                          )}
                        </Button>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Connections Tab */}
            <TabsContent value="connections" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Link2 className="w-5 h-5 text-primary" />
                    Trading Platform Connections
                  </CardTitle>
                  <CardDescription>Connect your trading accounts for automatic data sync</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Deriv Connection */}
                  <div className="p-6 rounded-xl border-2 border-dashed hover:border-primary/50 transition-colors">
                    <div className="flex flex-col sm:flex-row items-start gap-4">
                      <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center text-white font-bold text-lg shrink-0">
                        D
                      </div>
                      <div className="flex-1 w-full">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div>
                            <h3 className="text-lg font-semibold text-foreground">Deriv</h3>
                            <p className="text-sm text-muted-foreground">Connect your Deriv trading account</p>
                          </div>
                          {derivConnection && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/10 text-green-600 rounded-full text-xs font-medium self-start sm:self-auto">
                              <CheckCircle2 className="w-3 h-3" />
                              Connected
                            </span>
                          )}
                        </div>

                        <div className="mt-4 space-y-4">
                          {!derivConnection ? (
                            <>
                              <div className="space-y-2">
                                <Label htmlFor="deriv_token">API Token</Label>
                                <Input
                                  id="deriv_token"
                                  type="password"
                                  placeholder="Enter your Deriv API token"
                                  value={derivApiToken}
                                  onChange={(e) => setDerivApiToken(e.target.value)}
                                />
                                <p className="text-xs text-muted-foreground">
                                  You can create an API token in your{" "}
                                  <a
                                    href="https://app.deriv.com/account/api-token"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary hover:underline"
                                  >
                                    Deriv account settings
                                  </a>
                                </p>
                              </div>

                              <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                <div className="flex items-start gap-2">
                                  <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                                  <div className="text-sm text-amber-700">
                                    <p className="font-medium">Required Permissions</p>
                                    <ul className="mt-1 text-xs space-y-1 text-amber-600">
                                      <li>• Read: To fetch your trading history</li>
                                      <li>• Trade: Optional, for automated features</li>
                                    </ul>
                                  </div>
                                </div>
                              </div>

                              <Button onClick={handleConnectDeriv} disabled={derivConnecting} className="w-full">
                                {derivConnecting ? (
                                  <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Connecting...
                                  </>
                                ) : (
                                  <>
                                    <Link2 className="w-4 h-4 mr-2" />
                                    Connect Deriv Account
                                  </>
                                )}
                              </Button>
                            </>
                          ) : (
                            <div className="space-y-4">
                              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                                <div className="flex items-center gap-2 text-green-600 mb-2">
                                  <CheckCircle2 className="w-4 h-4" />
                                  <span className="text-sm font-medium">Your Deriv account is connected</span>
                                </div>

                                {derivConnection.account_info && (
                                  <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
                                    <div className="bg-background/80 p-2 rounded border shadow-sm">
                                      <span className="text-muted-foreground block text-[10px] uppercase tracking-wider">Login ID</span>
                                      <span className="font-mono font-medium">{derivConnection.account_info.loginid || 'Unknown'}</span>
                                    </div>
                                    <div className="bg-background/80 p-2 rounded border shadow-sm">
                                      <span className="text-muted-foreground block text-[10px] uppercase tracking-wider">Balance</span>
                                      <span className="font-mono font-medium">
                                        {derivConnection.account_info.balance} {derivConnection.account_info.currency}
                                      </span>
                                    </div>
                                  </div>
                                )}

                                {derivConnection.account_info?.mt5_accounts?.length > 0 && (
                                  <div className="mt-4">
                                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Linked MT5 Accounts (CFDs)</h4>
                                    <div className="grid gap-2">
                                      {derivConnection.account_info.mt5_accounts.map((acc: any, i: number) => (
                                        <div key={i} className="bg-background/80 p-3 rounded border shadow-sm flex justify-between items-center text-xs">
                                          <div>
                                            <span className="font-mono font-medium block">{acc.login}</span>
                                            <span className="text-muted-foreground text-[10px]">{acc.name || acc.group}</span>
                                          </div>
                                          <div className="text-right">
                                            <span className="font-mono font-bold block">{acc.balance} {acc.currency}</span>
                                            <span className="text-muted-foreground text-[10px]">{acc.leverage}x Leverage</span>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                <p className="text-xs text-green-600/80">
                                  TradeGuard AI is syncing your data automatically. Last sync: {derivConnection.last_sync_at ? new Date(derivConnection.last_sync_at).toLocaleString() : 'Pending'}
                                </p>
                              </div>

                              <div className="p-4 rounded-lg border bg-muted/30">
                                <Label className="text-sm font-medium mb-1.5 block">Stored API Token</Label>
                                <div className="flex gap-2">
                                  <Input
                                    type="password"
                                    value={derivApiToken}
                                    readOnly
                                    className="bg-background text-muted-foreground font-mono text-xs"
                                  />
                                </div>
                                <p className="text-[10px] text-muted-foreground mt-1.5">
                                  To update your token, please disconnect and reconnect.
                                </p>
                              </div>

                              <div className="flex flex-col sm:flex-row gap-2">
                                <Button variant="outline" className="flex-1" onClick={handleSyncDeriv} disabled={derivSyncing}>
                                  {derivSyncing ? (
                                    <>
                                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                      Syncing...
                                    </>
                                  ) : (
                                    <>
                                      <TrendingUp className="w-4 h-4 mr-2" />
                                      Sync Now
                                    </>
                                  )}
                                </Button>
                                <Button variant="destructive" onClick={handleDisconnectDeriv} className="sm:w-auto">
                                  Disconnect
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Coming Soon Connections */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="p-4 rounded-lg border bg-muted/30 opacity-60">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-500 font-bold">
                          MT
                        </div>
                        <div>
                          <h4 className="font-medium text-foreground">MetaTrader 4/5</h4>
                          <p className="text-xs text-muted-foreground">Coming Soon</p>
                        </div>
                      </div>
                    </div>
                    <div className="p-4 rounded-lg border bg-muted/30 opacity-60">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center text-green-500 font-bold">
                          TV
                        </div>
                        <div>
                          <h4 className="font-medium text-foreground">TradingView</h4>
                          <p className="text-xs text-muted-foreground">Coming Soon</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
      <Footer />
    </main >
  )
}
