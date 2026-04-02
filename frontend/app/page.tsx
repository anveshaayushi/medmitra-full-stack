"use client";

import { useState } from "react";
import { Header } from "@/components/header";
import { HeroSection } from "@/components/hero-section";
import { ResultsDashboard } from "@/components/results-dashboard";
import { ThemeProvider } from "@/components/theme-provider";

export interface AnalysisResult {
  medications: {
    name: string;
    dosage: string;
    frequency: string;
    purpose: string;
  }[];
  warnings: {
    type: "high" | "moderate" | "low";
    title: string;
    description: string;
  }[];
  duplicates: string[];
  instructions: string[];
  summary: string;
}

export default function DawaAI() {
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null,
  );
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // 🔥 FINAL HANDLE ANALYZE
  const handleAnalyze = async (file: File) => {
    setIsAnalyzing(true);

    try {
      // 1. Send file to backend
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://127.0.0.1:8000/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to analyze prescription");
      }

      const dataResponse = await response.json();
      console.log("API RESPONSE:", dataResponse);

      // 2. Map backend → frontend UI
      const formattedResult: AnalysisResult = {
        medications:
          dataResponse.medication_summary?.map((m: any) => ({
            name: m.canonical_name || m.original_name || "Unknown",
            dosage: m.dosage || "N/A",
            frequency: m.frequency || "N/A",
            purpose: "—",
          })) || [],

        warnings:
          dataResponse.clinical_alerts?.map((w: any) => ({
            type:
              w.severity === "high"
                ? "high"
                : w.severity === "medium"
                  ? "moderate"
                  : "low",
            title: "Drug Interaction",
            description: w.message || "Interaction detected",
          })) || [],

        duplicates:
          dataResponse.duplicate_alerts?.map((d: any) => d.message) || [],

        instructions: ["Follow doctor's advice"],

        summary: `Risk Level: ${dataResponse.risk_score?.label || "Unknown"}`,
      };

      setAnalysisResult(formattedResult);
    } catch (error) {
      console.error("ERROR:", error);
      alert("Something went wrong while analyzing.");
    }

    setIsAnalyzing(false);
  };

  const handleReset = () => {
    setAnalysisResult(null);
  };

  return (
    <ThemeProvider>
      <div className="min-h-screen relative overflow-hidden">
        {/* Background */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-96 h-96 bg-orange-glow/20 rounded-full blur-3xl" />
          <div className="absolute top-1/4 -left-32 w-80 h-80 bg-coral/15 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-peach/20 rounded-full blur-3xl" />
          <div className="absolute -bottom-20 left-1/3 w-96 h-96 bg-orange-glow/10 rounded-full blur-3xl" />
        </div>

        {/* Main UI */}
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
  );
}
