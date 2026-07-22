import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FeedbackCsvImport } from "@/components/FeedbackCsvImport";

function csvFile(name = "feedback.csv", content = "feedback_text\nGreat product!") {
  return new File([content], name, { type: "text/csv" });
}

describe("FeedbackCsvImport", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("rejects a non-CSV file without calling the API", async () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;
    const onImported = vi.fn();

    render(<FeedbackCsvImport onImported={onImported} />);
    const input = screen.getByLabelText(/choose csv file/i) as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["x"], "notes.txt", { type: "text/plain" })] } });

    expect(await screen.findByText(/please choose a \.csv file/i)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(onImported).not.toHaveBeenCalled();
  });

  it("uploads the file as multipart form data and reports the import summary", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        feedback_imported: 3,
        feedback_skipped: 1,
        context_records_imported: 0,
        context_records_skipped: 0,
        analysis_results_imported: 0,
        analysis_results_skipped: 0,
        embeddings_imported: 0,
        embeddings_skipped: 0,
        context_matches_imported: 0,
        context_matches_skipped: 0,
        themes_imported: 0,
        themes_skipped: 0,
        theme_members_imported: 0,
        theme_members_skipped: 0,
        errors: [],
      }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;
    const onImported = vi.fn();

    render(<FeedbackCsvImport onImported={onImported} />);
    const input = screen.getByLabelText(/choose csv file/i) as HTMLInputElement;
    fireEvent.change(input, { target: { files: [csvFile()] } });

    await waitFor(() => expect(onImported).toHaveBeenCalledOnce());

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/feedback/import");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
    // Content-Type must be left for the browser to set (multipart boundary) - never forced to JSON.
    expect(init.headers?.["Content-Type"]).toBeUndefined();

    expect(screen.getByText(/imported/i)).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText(/1 skipped as duplicates/i)).toBeInTheDocument();
  });

  it("surfaces per-row errors returned in the import summary", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        feedback_imported: 1,
        feedback_skipped: 0,
        context_records_imported: 0,
        context_records_skipped: 0,
        analysis_results_imported: 0,
        analysis_results_skipped: 0,
        embeddings_imported: 0,
        embeddings_skipped: 0,
        context_matches_imported: 0,
        context_matches_skipped: 0,
        themes_imported: 0,
        themes_skipped: 0,
        theme_members_imported: 0,
        theme_members_skipped: 0,
        errors: ["line 3: missing feedback_text, skipped"],
      }),
    }) as unknown as typeof fetch;

    render(<FeedbackCsvImport onImported={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/choose csv file/i), { target: { files: [csvFile()] } });

    expect(await screen.findByText(/missing feedback_text/i)).toBeInTheDocument();
  });

  it("shows the backend's error message when the upload is rejected", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "CSV must include columns: ['feedback_text']" }),
    }) as unknown as typeof fetch;
    const onImported = vi.fn();

    render(<FeedbackCsvImport onImported={onImported} />);
    fireEvent.change(screen.getByLabelText(/choose csv file/i), { target: { files: [csvFile()] } });

    expect(await screen.findByText(/csv must include columns/i)).toBeInTheDocument();
    expect(onImported).not.toHaveBeenCalled();
  });
});
