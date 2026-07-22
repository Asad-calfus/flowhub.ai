"use client";

import { useEffect, useState } from "react";
import { Cpu, Sparkles } from "lucide-react";
import { api } from "@/lib/api";

export type ProcessingMode = "local" | "api";

interface ProcessingModeToggleProps {
  value: ProcessingMode;
  onChange: (mode: ProcessingMode) => void;
  /** What the "local" option computes, e.g. "rule-based classification" or "a template report". */
  localDescription: string;
  /** What the "api" option computes, e.g. "an LLM-classified label" or "an AI-written narrative". */
  apiDescription: string;
}

/** Lets the user choose between the free local pipeline and a real OpenAI API call.
 * Disables the API option (with an explanation) when no key is configured server-side -
 * this never sends or displays the key itself, just whether one is present. */
export function ProcessingModeToggle({ value, onChange, localDescription, apiDescription }: ProcessingModeToggleProps) {
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [llmModel, setLlmModel] = useState<string | null>(null);
  const [llmConfigured, setLlmConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .status()
      .then((s) => {
        if (cancelled) return;
        setLlmProvider(s.llm_provider ?? null);
        setLlmModel(s.llm_model ?? null);
        setLlmConfigured(Boolean(s.llm_configured));
      })
      .catch(() => {
        if (!cancelled) setLlmConfigured(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const apiDisabled = llmConfigured === false;

  return (
    <div className="space-y-1.5">
      <span className="text-xs font-medium text-slate-600">Processing method</span>
      <div className="flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={() => onChange("local")}
          className={`flex flex-1 items-start gap-2 rounded-lg border px-3 py-2 text-left text-xs transition-colors ${
            value === "local" ? "border-brand-400 bg-brand-50 text-brand-900" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
          }`}
        >
          <Cpu className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            <span className="block font-semibold">Local (free)</span>
            <span className="block text-slate-500">{localDescription} - no API calls, no cost.</span>
          </span>
        </button>
        <button
          type="button"
          disabled={apiDisabled}
          onClick={() => onChange("api")}
          title={apiDisabled ? `No ${llmProvider ?? "LLM"} API key configured in the backend .env` : undefined}
          className={`flex flex-1 items-start gap-2 rounded-lg border px-3 py-2 text-left text-xs transition-colors ${
            apiDisabled
              ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
              : value === "api"
                ? "border-brand-400 bg-brand-50 text-brand-900"
                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
          }`}
        >
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            <span className="block font-semibold">OpenAI API key{llmModel ? ` (${llmModel})` : ""}</span>
            <span className="block text-slate-500">
              {apiDisabled ? "Not configured - set an API key in backend/.env to enable this." : `${apiDescription} - uses your configured API key, real cost.`}
            </span>
          </span>
        </button>
      </div>
    </div>
  );
}
