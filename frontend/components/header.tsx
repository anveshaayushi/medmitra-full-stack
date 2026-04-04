"use client"

import { Moon, Sun, Pill } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useTheme } from "@/components/theme-provider"

export function Header({ onFeaturesClick }: { onFeaturesClick: () => void }) {
  const { setTheme, resolvedTheme } = useTheme()

  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark")
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-card/60 backdrop-blur-xl supports-[backdrop-filter]:bg-card/40">
      <div className="mx-auto flex h-16 items-center justify-between px-4">
        
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent">
            <Pill className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-semibold tracking-tight text-foreground">
            Med<span className="text-primary">Mitra</span>
          </span>
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-3">
          
          {/* Features Button */}
          <Button
            onClick={onFeaturesClick}
            className="bg-orange-500 hover:bg-orange-600 text-white rounded-full px-4"
          >
            Features
          </Button>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="rounded-full"
            aria-label="Toggle theme"
          >
            {resolvedTheme === "dark" ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </Button>

        </div>
      </div>
    </header>
  )
}