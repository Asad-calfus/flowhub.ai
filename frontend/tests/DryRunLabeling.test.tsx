import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusPill } from "@/components/Badges";
import EvaluationPage from "@/app/evaluation/page";

describe("dry-run result labeling", () => {
  it("StatusPill clearly marks dry_run reports as not a real model", () => {
    render(<StatusPill status="dry_run" />);
    expect(screen.getByText(/dry-run/i)).toBeInTheDocument();
    expect(screen.getByText(/not a real model/i)).toBeInTheDocument();
  });

  it("StatusPill labels a real live LLM report distinctly from dry-run and deterministic", () => {
    render(<StatusPill status="llm" />);
    expect(screen.getByText(/live llm/i)).toBeInTheDocument();
  });

  it("StatusPill labels the no-LLM deterministic path plainly", () => {
    render(<StatusPill status="deterministic" />);
    expect(screen.getByText(/deterministic/i)).toBeInTheDocument();
  });

  describe("Evaluation page", () => {
    const originalFetch = global.fetch;

    afterEach(() => {
      global.fetch = originalFetch;
      vi.restoreAllMocks();
    });

    it("flags dry-run LLM classification results so they aren't read as real performance", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          classification: {
            baseline: { accuracy_by_field: { sentiment: 0.27 }, is_dry_run: false },
            llm: { accuracy_by_field: { sentiment: 0.27 }, is_dry_run: true, model: "gpt-4o-mini" },
          },
          retrieval: null,
          themes: null,
          report: null,
        }),
      }) as unknown as typeof fetch;

      render(<EvaluationPage />);

      expect(await screen.findByText(/dry-run stub — not a real model result/i)).toBeInTheDocument();
    });
  });
});
