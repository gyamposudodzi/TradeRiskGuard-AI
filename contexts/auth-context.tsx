"use client"

import React, { createContext, useContext, useState, useEffect } from "react"
import { apiClient, AuthResponse } from "@/lib/api"

interface User {
  id: string
  email: string
  name: string
  username: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  signUp: (email: string, password: string, name: string, username: string) => Promise<{ success: boolean; error?: string }>
  signOut: () => void
  isLoading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const AUTH_TOKEN_KEY = "auth_token"
const AUTH_USER_KEY = "auth_user"

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Get auth token from localStorage
  const getAuthToken = (): string | null => {
    if (typeof window === "undefined") return null
    return localStorage.getItem(AUTH_TOKEN_KEY)
  }

  // Set up API client auth token getter and unauthorized handler
  useEffect(() => {
    apiClient.setAuthTokenGetter(getAuthToken)
    // We cannot use the signOut function directly from context here because it's not defined yet
    // But we can define a standalone logout function or use the state updater
    apiClient.setOnUnauthorized(() => {
      // Clear storage
      localStorage.removeItem(AUTH_TOKEN_KEY)
      localStorage.removeItem(AUTH_USER_KEY)
      // Update state
      setUser(null)
      // Optionally redirect to signin
      window.location.href = '/signin'
    })
  }, [])

  // Check for stored auth on mount and validate token
  useEffect(() => {
    const storedUser = localStorage.getItem(AUTH_USER_KEY)
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY)

    if (storedUser && storedToken) {
      try {
        const parsedUser = JSON.parse(storedUser)
        setUser(parsedUser)
        // Optionally verify token is still valid by fetching profile
        // For now, we'll trust the stored user
      } catch (e) {
        // Invalid stored data, clear it
        localStorage.removeItem(AUTH_USER_KEY)
        localStorage.removeItem(AUTH_TOKEN_KEY)
      }
    }
    setIsLoading(false)
  }, [])

  const signIn = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await apiClient.login({ email, password })

      if (response.success && response.data) {
        const { user: userData, access_token } = response.data

        const user: User = {
          id: userData.id,
          email: userData.email,
          name: userData.username, // Use username as name for now
          username: userData.username,
        }

        // Store token and user
        localStorage.setItem(AUTH_TOKEN_KEY, access_token)
        localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
        setUser(user)

        return { success: true }
      } else {
        const errorMessage = response.error || response.message || "Login failed"
        console.error("Login failed:", errorMessage)
        return { success: false, error: errorMessage }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Network error occurred"
      console.error("Login error:", error)
      return { success: false, error: errorMessage }
    }
  }

  const signUp = async (
    email: string,
    password: string,
    name: string,
    username: string
  ): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await apiClient.register({
        email,
        username,
        password,
      })

      if (response.success && response.data) {
        const { user: userData, access_token } = response.data

        const user: User = {
          id: userData.id,
          email: userData.email,
          name: name || username,
          username: userData.username,
        }

        // Store token and user
        localStorage.setItem(AUTH_TOKEN_KEY, access_token)
        localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
        setUser(user)

        return { success: true }
      } else {
        const errorMessage = response.error || response.message || "Registration failed"
        console.error("Registration failed:", errorMessage)
        return { success: false, error: errorMessage }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Network error occurred"
      console.error("Registration error:", error)
      return { success: false, error: errorMessage }
    }
  }

  const signOut = () => {
    setUser(null)
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(AUTH_USER_KEY)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        signIn,
        signUp,
        signOut,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
