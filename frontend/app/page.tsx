"use client";

import { useState } from "react";
import { Header } from "@/components/header";
import { HeroSection } from "@/components/hero-section";
import { ResultsDashboard } from "@/components/results-dashboard";
import { ThemeProvider } from "@/components/theme-provider";

export interface AnalysisResult {
  medications: {
    name: string;
    genericName: string;
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
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [rawResult, setRawResult] = useState<Record<string, unknown>>({});
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // ✅ UPDATED: now accepts multiple files
  const handleAnalyze = async (files: File[]) => {
    setIsAnalyzing(true);

    try {
      const formData = new FormData();

      files.forEach((file) => {
        formData.append("files", file); // IMPORTANT: backend expects "files"
      });

      const response = await fetch("http://127.0.0.1:8000/api/analyze-multiple", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Failed to analyze prescription");

      const dataResponse = await response.json();
      console.log("API RESPONSE:", dataResponse);

      setRawResult(dataResponse);

      const formattedResult: AnalysisResult = {
        medications:
          dataResponse.medication_summary?.map((m: any) => ({
            name: m.original_name || m.canonical_name || "Unknown",
            genericName: m.canonical_name || "",
            dosage: m.dose_mg ? `${m.dose_mg}mg` : "N/A",
            frequency:
              m.freq_per_day && m.freq_per_day > 0
                ? `${m.freq_per_day}x/day`
                : "N/A",
            purpose:
              [m.notes, m.duration].filter(Boolean).join(" · ") || "—",
          })) || [],

        warnings:
  dataResponse.clinical_alerts
    ?.filter((w: any) => w.severity !== "low")   // 🔥 REMOVE LOW
    .map((w: any) => ({
      type:
        w.severity === "high"
          ? "high"
          : "moderate",
      title: w.drugs_involved?.join(" + ") || "Drug Interaction",
      description: `${w.what_happens || w.mechanism || w.message || "Interaction detected"} — ${w.what_to_do || w.recommendation || ""}`.trim(),
    })) || [],

        duplicates:
          dataResponse.duplicate_alerts?.map((d: any) => d.message) || [],

        instructions: [
          ...(dataResponse.overdose_alerts?.map(
            (o: any) => `⚠️ Overdose risk: ${o.message}`
          ) || []),
          ...(dataResponse.duplicate_alerts?.map(
            (d: any) => `🔁 ${d.message} — ${d.recommendation}`
          ) || []),
          "Always follow your doctor's prescribed dosage and timing.",
        ],

        // ✅ shows number of prescriptions analyzed
        summary: `Analyzed ${
          dataResponse.total_prescriptions || files.length
        } prescription(s) — Patient: ${
          dataResponse.patient_name || "User"
        } — Risk Level: ${
          dataResponse.risk_score?.label || "Unknown"
        }`,
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
    setRawResult({});
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

        <div className="relative z-10">
          <Header />

          {analysisResult ? (
            <ResultsDashboard
              result={analysisResult}
              rawResult={rawResult}
              onReset={handleReset}
            />
          ) : (
            <HeroSection
              onAnalyze={handleAnalyze}   // ✅ now expects File[]
              isAnalyzing={isAnalyzing}
            />
          )}
        </div>
      </div>
    </ThemeProvider>
  );
}