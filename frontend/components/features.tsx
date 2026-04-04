"use client"

export function Features({ onBack }: { onBack: () => void }) {
  return (
    <div className="min-h-screen px-6 py-16 bg-background text-foreground">
      
      {/* 🔥 Back Button */}
      <button
        onClick={onBack}
        className="mb-6 text-orange-500 hover:underline"
      >
        ← Back
      </button>

      <div className="max-w-4xl mx-auto">
        
        <h1 className="text-4xl font-bold mb-6 text-center">
          MedMitra Features
        </h1>

        <p className="text-lg text-muted-foreground mb-10 text-center">
          AI-powered healthcare assistance to make prescriptions safer and smarter.
        </p>

        <div className="space-y-6">
          
          <div className="p-6 rounded-xl border bg-card shadow-sm">
            <h2 className="text-xl font-semibold mb-2">
              🔍 Prescription Analysis
            </h2>
            <p className="text-muted-foreground">
              Upload prescriptions and let AI extract and understand medicines automatically.
            </p>
          </div>

          <div className="p-6 rounded-xl border bg-card shadow-sm">
            <h2 className="text-xl font-semibold mb-2">
              ⚠️ Drug Interaction Detection
            </h2>
            <p className="text-muted-foreground">
              Detect harmful interactions between medicines to ensure patient safety.
            </p>
          </div>

          <div className="p-6 rounded-xl border bg-card shadow-sm">
            <h2 className="text-xl font-semibold mb-2">
              💡 Personalized Recommendations
            </h2>
            <p className="text-muted-foreground">
              Get AI-based suggestions for safer and optimized medication usage.
            </p>
          </div>

        </div>
      </div>
    </div>
  )
}