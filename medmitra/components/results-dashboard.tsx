"use client"

import { ArrowLeft, Pill, AlertTriangle, AlertCircle, CheckCircle, ClipboardList, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { AnalysisResult } from "@/app/page"
import { cn } from "@/lib/utils"

interface ResultsDashboardProps {
  result: AnalysisResult
  onReset: () => void
}

export function ResultsDashboard({ result, onReset }: ResultsDashboardProps) {
  return (
    <main className="container mx-auto px-4 py-8 md:py-12">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={onReset}
          className="gap-2 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          New Analysis
        </Button>
        <h1 className="text-2xl font-bold text-foreground">Analysis Results</h1>
        <div className="w-24" /> {/* Spacer for centering */}
      </div>

      {/* Summary Card */}
      <div className="mb-8 rounded-2xl border border-border/50 bg-card/70 p-6 backdrop-blur-xl">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 to-accent/20">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h2 className="mb-2 text-lg font-semibold text-foreground">Summary</h2>
            <p className="text-muted-foreground">{result.summary}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Medications */}
        <section className="rounded-2xl border border-border/50 bg-card/70 p-6 backdrop-blur-xl">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent">
              <Pill className="h-5 w-5 text-primary-foreground" />
            </div>
            <h2 className="text-lg font-semibold text-foreground">Medications ({result.medications.length})</h2>
          </div>
          <div className="space-y-3">
            {result.medications.map((med, index) => (
              <div
                key={index}
                className="group rounded-xl border border-border/50 bg-background/50 p-4 transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
              >
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="font-semibold text-foreground">{med.name}</h3>
                  <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
                    {med.dosage}
                  </span>
                </div>
                <p className="mb-1 text-sm text-muted-foreground">{med.purpose}</p>
                <p className="text-xs text-muted-foreground/70">Frequency: {med.frequency}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Safety Alerts */}
        <section className="rounded-2xl border border-border/50 bg-card/70 p-6 backdrop-blur-xl">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-warning to-danger">
              <AlertTriangle className="h-5 w-5 text-primary-foreground" />
            </div>
            <h2 className="text-lg font-semibold text-foreground">Safety Alerts ({result.warnings.length})</h2>
          </div>
          <div className="space-y-3">
            {result.warnings.map((warning, index) => (
              <div
                key={index}
                className={cn(
                  "rounded-xl border p-4 transition-all",
                  warning.type === "high" && "border-danger/50 bg-gradient-to-r from-danger/10 to-danger/5",
                  warning.type === "moderate" && "border-warning/50 bg-gradient-to-r from-warning/10 to-warning/5",
                  warning.type === "low" && "border-safe/50 bg-gradient-to-r from-safe/10 to-safe/5"
                )}
              >
                <div className="mb-2 flex items-center gap-2">
                  {warning.type === "high" && <AlertCircle className="h-5 w-5 text-danger" />}
                  {warning.type === "moderate" && <AlertTriangle className="h-5 w-5 text-warning" />}
                  {warning.type === "low" && <CheckCircle className="h-5 w-5 text-safe" />}
                  <h3 className="font-semibold text-foreground">{warning.title}</h3>
                  <span
                    className={cn(
                      "ml-auto rounded-full px-2 py-0.5 text-xs font-medium",
                      warning.type === "high" && "bg-danger/20 text-danger",
                      warning.type === "moderate" && "bg-warning/20 text-warning",
                      warning.type === "low" && "bg-safe/20 text-safe"
                    )}
                  >
                    {warning.type === "high" ? "High Risk" : warning.type === "moderate" ? "Moderate" : "Low Risk"}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{warning.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Instructions */}
        <section className="rounded-2xl border border-border/50 bg-card/70 p-6 backdrop-blur-xl lg:col-span-2">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-safe to-primary">
              <ClipboardList className="h-5 w-5 text-primary-foreground" />
            </div>
            <h2 className="text-lg font-semibold text-foreground">Instructions & Recommendations</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {result.instructions.map((instruction, index) => (
              <div
                key={index}
                className="flex items-start gap-3 rounded-xl border border-border/50 bg-background/50 p-4"
              >
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                  {index + 1}
                </div>
                <p className="text-sm text-muted-foreground">{instruction}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Disclaimer */}
      <div className="mt-8 rounded-xl border border-border/50 bg-muted/30 p-4 text-center">
        <p className="text-xs text-muted-foreground">
          <strong>Disclaimer:</strong> This analysis is for informational purposes only and should not replace professional medical advice. 
          Always consult with your healthcare provider or pharmacist before making any changes to your medication regimen.
        </p>
      </div>
    </main>
  )
}
