"use client";

import { useState, useRef } from "react";
import { Header } from "@/components/header";
import { HeroSection } from "@/components/hero-section";
import { ResultsDashboard } from "@/components/results-dashboard";
import { ThemeProvider } from "@/components/theme-provider";
import { Features } from "@/components/features";

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
  const [showFeatures, setShowFeatures] = useState(false);
  const [showSlowPopup, setShowSlowPopup] = useState(false);
  const [showErrorPopup, setShowErrorPopup] = useState<{
    show: boolean;
    title: string;
    message: string;
  }>({ show: false, title: "", message: "" });
  const slowTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleAnalyze = async (files: File[]) => {
    setIsAnalyzing(true);
    setShowSlowPopup(false);
    setShowErrorPopup({ show: false, title: "", message: "" });

    // 90 seconds baad slow popup dikhao
    slowTimerRef.current = setTimeout(() => {
      setShowSlowPopup(true);
    }, 90000);

    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });

      const response = await fetch("http://127.0.0.1:8000/api/analyze-multiple", {
        method: "POST",
        body: formData,
      });

      const dataResponse = await response.json();
      console.log("API RESPONSE:", dataResponse);

      // ── Backend error handle ───────────────────────────────────────
      if (!response.ok || dataResponse.status === "error") {
        const msg = dataResponse.message || "";
        if (msg === "no_medicines_detected") {
          setShowErrorPopup({
            show: true,
            title: "No Medicines Found 🔍",
            message: "We couldn't detect any medicines in your prescription. Please make sure the image is clear and well-lit, then try again.",
          });
        } else {
          setShowErrorPopup({
            show: true,
            title: "Server is Busy 🌐",
            message: "Our AI server is experiencing high demand right now. Please wait a moment and try again — this is usually temporary!",
          });
        }
        return;
      }

      // ── Success ───────────────────────────────────────────────────
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
            ?.filter((w: any) => {
              if (w.severity === "low") return false;
              if (w.severity === "medium" && (w.drugs_involved?.length ?? 0) > 2) return false;
              return true;
            })
            .map((w: any) => ({
              type: w.severity === "high" ? "high" : "moderate",
              title: w.drugs_involved?.join(" + ") || "Drug Interaction",
              description: `${
                w.what_happens || w.mechanism || w.message || "Interaction detected"
              } — ${
                w.what_to_do || w.recommendation || ""
              }`.trim(),
            })) || [],

        duplicates:
          dataResponse.duplicate_alerts?.map((d: any) => d.message) || [],

        instructions: [
          ...(dataResponse.clinical_alerts
            ?.filter((a: any) => a.severity === "high")
            .map((a: any) => `🚨 ${a.drugs_involved?.join(" + ")}: ${a.recommendation || a.what_to_do || "Consult your doctor immediately."}`)
            || []),
          ...(dataResponse.clinical_alerts
            ?.filter((a: any) => a.severity === "medium")
            .map((a: any) => `⚠️ ${a.drugs_involved?.join(" + ")}: ${a.recommendation || a.what_to_do || "Monitor closely."}`)
            || []),
          ...(dataResponse.clinical_alerts
            ?.filter((a: any) => a.type === "overdose")
            .map((a: any) => `⚠️ ${a.message}`)
            || []),
          ...(dataResponse.clinical_alerts
            ?.filter((a: any) => a.type === "duplicate_therapy" || a.type === "class_duplicate")
            .map((a: any) => `🔁 ${a.message}`)
            || []),
          ...(dataResponse.medication_summary
            ?.filter((m: any) => m.notes)
            .map((m: any) => `💊 ${m.original_name || m.canonical_name}: ${m.notes}`)
            || []),
          "💊 Complete your full course even if symptoms improve.",
          "🩺 Always follow your doctor's prescribed dosage and timing.",
        ],

        summary: `Analyzed ${
          dataResponse.total_prescriptions || files.length
        } prescription(s)`,
      };

      setAnalysisResult(formattedResult);

    } catch (error) {
      console.error("ERROR:", error);
      const msg = error instanceof Error ? error.message : "";
      if (msg.includes("exhausted")) {
        setShowErrorPopup({
          show: true,
          title: "Daily Limit Reached ⏳",
          message: "Our AI service has reached its daily capacity. Please try again tomorrow — we're sorry for the inconvenience!",
        });
      } else {
        setShowErrorPopup({
          show: true,
          title: "Server is Busy 🌐",
          message: "The AI server is experiencing high demand right now. Please wait a minute and try again — this is usually temporary!",
        });
      }
    } finally {
      if (slowTimerRef.current) {
        clearTimeout(slowTimerRef.current);
        slowTimerRef.current = null;
      }
      setShowSlowPopup(false);
      setIsAnalyzing(false);
    }
  };

  const handleReset = () => {
    setAnalysisResult(null);
    setRawResult({});
  };

  return (
    <ThemeProvider>
      <div className="min-h-screen relative overflow-hidden">

        {/* ── Slow Analysis Popup ── */}
        {showSlowPopup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <div className="mx-4 max-w-md rounded-2xl border border-border/50 bg-card p-8 shadow-2xl text-center">
              <div className="mb-4 text-5xl">🧠</div>
              <h3 className="mb-2 text-xl font-semibold text-foreground">
                Still Analyzing...
              </h3>
              <p className="mb-4 text-muted-foreground text-sm leading-relaxed">
                Our AI is carefully checking all your medicines for interactions
                and safety risks. This can take a little longer when servers are busy.
              </p>
              <p className="text-xs text-muted-foreground/70">
                ⏳ Thank you for your patience — your safety is worth the wait! 💊
              </p>
              <div className="mt-6 flex justify-center gap-1">
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        {/* ── Error Popup ── */}
        {showErrorPopup.show && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <div className="mx-4 max-w-md rounded-2xl border border-border/50 bg-card p-8 shadow-2xl text-center">
              <div className="mb-4 text-5xl">😔</div>
              <h3 className="mb-2 text-xl font-semibold text-foreground">
                {showErrorPopup.title}
              </h3>
              <p className="mb-6 text-muted-foreground text-sm leading-relaxed">
                {showErrorPopup.message}
              </p>
              <button
                onClick={() => setShowErrorPopup({ show: false, title: "", message: "" })}
                className="rounded-xl bg-gradient-to-r from-primary to-accent px-6 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90"
              >
                Got it, I'll try again
              </button>
            </div>
          </div>
        )}

        <div className="relative z-10">

          {/* ✅ FIXED HEADER */}
          <Header onFeaturesClick={() => setShowFeatures(true)} />

          {/* ✅ MAIN SWITCH LOGIC */}
          {showFeatures ? (
            <Features onBack={() => setShowFeatures(false)} />
          ) : analysisResult ? (
            <ResultsDashboard
              result={analysisResult}
              rawResult={rawResult}
              onReset={handleReset}
            />
          ) : (
            <HeroSection
              onAnalyze={handleAnalyze}
              isAnalyzing={isAnalyzing}
            />
          )}
        </div>

      </div>
    </ThemeProvider>
  );
}