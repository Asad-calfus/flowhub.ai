import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ReportGenerationForm, validateReportForm } from "@/components/ReportGenerationForm";

describe("validateReportForm", () => {
  it("requires both start and end dates", () => {
    const errors = validateReportForm({ start_date: "", end_date: "", product_module: "", customer_tier: "" });
    expect(errors.start_date).toBeDefined();
    expect(errors.end_date).toBeDefined();
  });

  it("rejects an end date before the start date", () => {
    const errors = validateReportForm({
      start_date: "2026-05-10",
      end_date: "2026-05-04",
      product_module: "",
      customer_tier: "",
    });
    expect(errors.end_date).toMatch(/on or after/i);
  });

  it("accepts a valid date range", () => {
    const errors = validateReportForm({
      start_date: "2026-05-04",
      end_date: "2026-05-10",
      product_module: "",
      customer_tier: "",
    });
    expect(errors).toEqual({});
  });

  it("skips date requirements when all_time is set", () => {
    const errors = validateReportForm({
      start_date: "",
      end_date: "",
      product_module: "",
      customer_tier: "",
      all_time: true,
    });
    expect(errors).toEqual({});
  });
});

describe("ReportGenerationForm", () => {
  const originalFetch = global.fetch;

  // ProcessingModeToggle fires a GET /status on mount regardless of what the test is
  // exercising - the mock needs to answer that too, distinctly from the report-generation
  // call, or every test here would need to know about an unrelated child component.
  function mockFetch(reportResponse: { ok: boolean; status: number; json: () => Promise<unknown> }) {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (String(url).includes("/status")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ llm_provider: "openai", llm_model: "gpt-4o-mini", llm_configured: true }),
        });
      }
      return Promise.resolve(reportResponse);
    });
    global.fetch = fetchMock as unknown as typeof fetch;
    return fetchMock;
  }

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("blocks submission and shows an inline error when dates are missing", async () => {
    const onGenerated = vi.fn();
    const fetchMock = mockFetch({ ok: true, status: 201, json: async () => ({ id: "RPT-0005" }) });

    render(<ReportGenerationForm onGenerated={onGenerated} />);
    fireEvent.click(screen.getByRole("button", { name: /generate report/i }));

    expect(await screen.findByText(/start date is required/i)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("/reports/weekly"), expect.anything());
    expect(onGenerated).not.toHaveBeenCalled();
  });

  it("submits with mode=deterministic and reports success", async () => {
    const onGenerated = vi.fn();
    const fetchMock = mockFetch({ ok: true, status: 201, json: async () => ({ id: "RPT-0005" }) });

    render(<ReportGenerationForm onGenerated={onGenerated} />);
    fireEvent.change(screen.getByLabelText(/start date/i), { target: { value: "2026-05-04" } });
    fireEvent.change(screen.getByLabelText(/end date/i), { target: { value: "2026-05-10" } });
    fireEvent.click(screen.getByRole("button", { name: /generate report/i }));

    await waitFor(() => expect(onGenerated).toHaveBeenCalledWith({ id: "RPT-0005" }));

    const postCall = fetchMock.mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === "POST");
    const body = JSON.parse((postCall![1] as RequestInit).body as string);
    expect(body.mode).toBe("deterministic");
    expect(body.start_date).toBe("2026-05-04");
  });

  it("submits null dates when 'All-time report' is checked", async () => {
    const onGenerated = vi.fn();
    const fetchMock = mockFetch({ ok: true, status: 201, json: async () => ({ id: "RPT-0006" }) });

    render(<ReportGenerationForm onGenerated={onGenerated} />);
    fireEvent.click(screen.getByLabelText(/all-time report/i));
    fireEvent.click(screen.getByRole("button", { name: /generate report/i }));

    await waitFor(() => expect(onGenerated).toHaveBeenCalledWith({ id: "RPT-0006" }));

    const postCall = fetchMock.mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === "POST");
    const body = JSON.parse((postCall![1] as RequestInit).body as string);
    expect(body.start_date).toBeNull();
    expect(body.end_date).toBeNull();
  });

  it("fills in the last 7 days when 'Past week' is clicked", () => {
    const onGenerated = vi.fn();
    mockFetch({ ok: true, status: 201, json: async () => ({ id: "RPT-0005" }) });

    render(<ReportGenerationForm onGenerated={onGenerated} />);
    fireEvent.click(screen.getByRole("button", { name: /past week/i }));

    const startInput = screen.getByLabelText(/start date/i) as HTMLInputElement;
    const endInput = screen.getByLabelText(/end date/i) as HTMLInputElement;
    expect(startInput.value).not.toBe("");
    expect(endInput.value).not.toBe("");

    const start = new Date(startInput.value);
    const end = new Date(endInput.value);
    const diffDays = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
    expect(diffDays).toBe(6);
  });
});
