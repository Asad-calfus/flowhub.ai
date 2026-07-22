import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { FeedbackTable } from "@/components/FeedbackTable";
import type { AnalysisOut, FeedbackOut } from "@/lib/types";

const feedback: FeedbackOut[] = [
  {
    id: "FB-0001",
    feedback_text: "The dashboard keeps logging me out every few minutes, very frustrating.",
    source: "Support ticket",
    feedback_created_at: "2026-05-04T00:00:00Z",
    customer_id: "CUST-1",
    customer_tier: "Enterprise",
    product_version: "v2.5.0",
    rating: 2,
    language: "en",
    processing_status: "classified",
    created_at: "2026-05-04T00:00:00Z",
    updated_at: "2026-05-04T00:00:00Z",
  },
];

const analysis: AnalysisOut = {
  feedback_id: "FB-0001",
  feedback_type: "Bug report",
  category: "Technical Issue",
  product_module: "Authentication",
  sentiment: "Negative",
  urgency: "High",
  confidence: 0.91,
  reasoning: "Explicit bug description.",
  model_name: "baseline",
  prompt_version: null,
  created_at: "2026-05-04T00:00:00Z",
};

describe("FeedbackTable", () => {
  it("renders feedback rows with source, tier, and a link to the detail page", () => {
    render(<FeedbackTable items={feedback} analysisById={{ "FB-0001": analysis }} />);

    expect(screen.getByText(/dashboard keeps logging me out/i)).toBeInTheDocument();
    expect(screen.getByText("Support ticket")).toBeInTheDocument();
    expect(screen.getByText("Enterprise")).toBeInTheDocument();
    expect(screen.getByText("Authentication")).toBeInTheDocument();
    expect(screen.getByText("Negative")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /dashboard keeps logging me out/i })).toHaveAttribute("href", "/feedback/FB-0001");
  });

  it("shows a placeholder instead of fabricating classification fields when no analysis exists yet", () => {
    render(<FeedbackTable items={feedback} analysisById={{ "FB-0001": null }} />);

    const cells = screen.getAllByText("—");
    expect(cells.length).toBeGreaterThan(0);
  });
});
