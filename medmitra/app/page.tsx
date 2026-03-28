"use client"

import { useState } from "react"
import { Header } from "@/components/header"
import { HeroSection } from "@/components/hero-section"
import { ResultsDashboard } from "@/components/results-dashboard"
import { ThemeProvider } from "@/components/theme-provider"

export interface AnalysisResult {
  medications: {
    name: string
    dosage: string
    frequency: string
    purpose: string
  }[]
  warnings: {
    type: "high" | "moderate" | "low"
    title: string
    description: string
  }[]
  duplicates: string[]
  instructions: string[]
  summary: string
}

export default function DawaAI() {
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const handleAnalyze = async (file: File) => {
    setIsAnalyzing(true)
    
    // Simulate AI analysis
    await new Promise(resolve => setTimeout(resolve, 2500))
    
    const mockResult: AnalysisResult = {
      medications: [
        { name: "Amoxicillin", dosage: "500mg", frequency: "3 times daily", purpose: "Antibiotic for bacterial infection" },
        { name: "Ibuprofen", dosage: "400mg", frequency: "As needed", purpose: "Pain relief and anti-inflammatory" },
        { name: "Omeprazole", dosage: "20mg", frequency: "Once daily", purpose: "Reduces stomach acid" },
        { name: "Metformin", dosage: "850mg", frequency: "Twice daily", purpose: "Blood sugar control" },
      ],
      warnings: [
        { type: "high", title: "Drug Interaction Alert", description: "Ibuprofen may reduce the effectiveness of blood pressure medications. Consult your doctor." },
        { type: "moderate", title: "Timing Recommendation", description: "Take Omeprazole 30 minutes before meals for optimal effectiveness." },
        { type: "low", title: "Hydration Notice", description: "Increase water intake while taking Amoxicillin to support kidney function." },
      ],
      duplicates: [],
      instructions: [
        "Complete the full course of Amoxicillin even if symptoms improve",
        "Take Metformin with food to minimize stomach upset",
        "Avoid alcohol while taking these medications",
        "Store all medications at room temperature away from moisture",
        "Schedule a follow-up appointment in 2 weeks",
      ],
      summary: "Your prescription contains 4 medications with one notable drug interaction requiring attention. Overall, the prescription is well-balanced with clear dosing instructions."
    }
    
    setAnalysisResult(mockResult)
    setIsAnalyzing(false)
  }

  const handleReset = () => {
    setAnalysisResult(null)
  }

  return (
    <ThemeProvider>
      <div className="min-h-screen relative overflow-hidden">
        {/* Background gradient blobs */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-96 h-96 bg-orange-glow/20 rounded-full blur-3xl" />
          <div className="absolute top-1/4 -left-32 w-80 h-80 bg-coral/15 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-peach/20 rounded-full blur-3xl" />
          <div className="absolute -bottom-20 left-1/3 w-96 h-96 bg-orange-glow/10 rounded-full blur-3xl" />
        </div>

        {/* Main content */}
        <div className="relative z-10">
          <Header />
          
          {analysisResult ? (
            <ResultsDashboard result={analysisResult} onReset={handleReset} />
          ) : (
            <HeroSection onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} />
          )}
        </div>
      </div>
    </ThemeProvider>
  )
}
