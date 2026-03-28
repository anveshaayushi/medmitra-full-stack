"use client"

import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, FileImage, Sparkles, Shield, Clock, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Spinner } from "@/components/ui/spinner"

interface HeroSectionProps {
  onAnalyze: (file: File) => void
  isAnalyzing: boolean
}

export function HeroSection({ onAnalyze, isAnalyzing }: HeroSectionProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (file) {
      setSelectedFile(file)
      const reader = new FileReader()
      reader.onload = () => {
        setPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".png", ".jpg", ".jpeg", ".webp"],
    },
    maxFiles: 1,
    disabled: isAnalyzing,
  })

  const handleAnalyze = () => {
    if (selectedFile) {
      onAnalyze(selectedFile)
    }
  }

  const handleClear = () => {
    setSelectedFile(null)
    setPreview(null)
  }

  return (
    <main className="container mx-auto px-4 py-12 md:py-20">
      {/* Hero text */}
      <div className="mx-auto max-w-3xl text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary">
          <Sparkles className="h-4 w-4" />
          AI-Powered Analysis
        </div>
        <h1 className="mb-4 text-pretty text-4xl font-bold tracking-tight text-foreground md:text-5xl lg:text-6xl">
          Smart Prescription
          <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent"> Analysis</span>
        </h1>
        <p className="mx-auto mb-12 max-w-2xl text-balance text-lg text-muted-foreground md:text-xl">
          Upload your prescription and let our AI analyze medications, detect interactions, and provide personalized safety recommendations.
        </p>
      </div>

      {/* Upload card */}
      <div className="mx-auto max-w-2xl">
        <div className="rounded-2xl border border-border/50 bg-card/70 p-6 shadow-xl backdrop-blur-xl md:p-8">
          <div
            {...getRootProps()}
            className={cn(
              "relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200",
              isDragActive
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50 hover:bg-muted/30",
              isAnalyzing && "pointer-events-none opacity-60"
            )}
          >
            <input {...getInputProps()} />
            
            {preview ? (
              <div className="relative">
                <img
                  src={preview}
                  alt="Prescription preview"
                  className="mx-auto max-h-64 rounded-lg object-contain"
                />
                {!isAnalyzing && (
                  <Button
                    variant="secondary"
                    size="icon"
                    className="absolute -right-2 -top-2 h-8 w-8 rounded-full"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleClear()
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ) : (
              <div className="py-8">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-primary/10 to-accent/10">
                  {isDragActive ? (
                    <FileImage className="h-8 w-8 text-primary" />
                  ) : (
                    <Upload className="h-8 w-8 text-primary" />
                  )}
                </div>
                <p className="mb-2 text-lg font-medium text-foreground">
                  {isDragActive ? "Drop your prescription here" : "Drag & drop your prescription"}
                </p>
                <p className="text-sm text-muted-foreground">
                  or click to browse • PNG, JPG, WEBP
                </p>
              </div>
            )}
          </div>

          <Button
            onClick={handleAnalyze}
            disabled={!selectedFile || isAnalyzing}
            className="mt-6 w-full bg-gradient-to-r from-primary to-accent py-6 text-lg font-semibold text-primary-foreground shadow-lg transition-all hover:opacity-90 hover:shadow-xl disabled:opacity-50"
          >
            {isAnalyzing ? (
              <>
                <Spinner className="mr-2 h-5 w-5" />
                Analyzing Prescription...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-5 w-5" />
                Analyze Prescription
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Feature badges */}
      <div className="mx-auto mt-12 flex max-w-2xl flex-wrap items-center justify-center gap-4">
        <div className="flex items-center gap-2 rounded-full border border-border/50 bg-card/50 px-4 py-2 backdrop-blur-sm">
          <Shield className="h-4 w-4 text-safe" />
          <span className="text-sm text-muted-foreground">Drug Interaction Detection</span>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-border/50 bg-card/50 px-4 py-2 backdrop-blur-sm">
          <Clock className="h-4 w-4 text-primary" />
          <span className="text-sm text-muted-foreground">Instant Results</span>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-border/50 bg-card/50 px-4 py-2 backdrop-blur-sm">
          <Sparkles className="h-4 w-4 text-accent" />
          <span className="text-sm text-muted-foreground">AI-Powered Insights</span>
        </div>
      </div>
    </main>
  )
}
