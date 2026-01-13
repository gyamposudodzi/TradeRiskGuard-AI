"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Header } from "@/components/layout/header"
import { Footer } from "@/components/layout/footer"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/contexts/auth-context"
import { Shield, ArrowLeft } from "lucide-react"

export default function SignUpPage() {
  const router = useRouter()
  const { signUp, isAuthenticated, isLoading: authLoading } = useAuth()
  const [name, setName] = useState("")
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPassword = e.target.value
    // Backend truncates to 72 characters, so check if those 72 chars are <= 72 bytes
    const first72Chars = newPassword.slice(0, 72)
    const bytes = new TextEncoder().encode(first72Chars).length
    
    if (bytes <= 72) {
      setPassword(newPassword)
      setError("")
    } else {
      setError("Password contains characters that exceed byte limit. Try using simpler characters.")
    }
  }

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.push("/dashboard")
    }
  }, [isAuthenticated, authLoading, router])

  if (authLoading || isAuthenticated) {
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    
    // Validate password: first 72 chars must be <= 72 bytes (backend truncates by char)
    const first72Chars = password.slice(0, 72)
    const bytes = new TextEncoder().encode(first72Chars).length
    if (bytes > 72) {
      setError("Password contains characters that exceed byte limit. Try using simpler characters.")
      return
    }
    
    setIsLoading(true)

    try {
      const result = await signUp(email, password, name, username)
      if (result.success) {
        router.push("/dashboard")
      } else {
        setError(result.error || "Registration failed. Please check your details and try again.")
      }
    } catch (err) {
      setError("Something went wrong. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="flex flex-col min-h-screen bg-background">
      <Header />
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to home
            </Link>
            <div className="flex justify-center mb-4">
              <div className="p-3 bg-gradient-to-br from-primary to-accent rounded-lg">
                <Shield className="w-8 h-8 text-primary-foreground" />
              </div>
            </div>
            <h1 className="text-3xl font-bold text-foreground mb-2">Sign Up</h1>
            <p className="text-muted-foreground">Create your Trade Guard AI account</p>
          </div>

          <div className="bg-card border border-border rounded-lg p-6 shadow-lg">
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded-md text-sm">
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="johndoe"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Create a password"
                  value={password}
                  onChange={handlePasswordChange}
                  required
                  disabled={isLoading}
                />
                {password && (() => {
                  const first72 = password.slice(0, 72)
                  const bytes = new TextEncoder().encode(first72).length
                  const chars = password.length
                  if (chars > 50 || bytes > 50) {
                    return (
                      <p className={`text-xs ${bytes > 72 ? 'text-destructive font-medium' : 'text-muted-foreground'}`}>
                        {chars} chars, {bytes}/72 bytes {bytes > 72 && '(too long!)'}
                      </p>
                    )
                  }
                  return null
                })()}
              </div>

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" />
                    Creating account...
                  </>
                ) : (
                  "Sign Up"
                )}
              </Button>

              <p className="text-center text-sm text-muted-foreground">
                Already have an account?{" "}
                <Link href="/signin" className="text-primary hover:underline font-medium">
                  Sign in
                </Link>
              </p>
            </form>
          </div>

        </div>
      </div>
      <Footer />
    </main>
  )
}
