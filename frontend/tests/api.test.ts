import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { api, ApiError } from "@/lib/api";

describe("api client error handling", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("throws ApiError with the backend's detail message on a non-ok response", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "Feedback FB-9999 not found." }),
    }) as unknown as typeof fetch;

    await expect(api.getFeedback("FB-9999")).rejects.toMatchObject({
      message: "Feedback FB-9999 not found.",
      status: 404,
    });
  });

  it("falls back to statusText when the error body has no detail field", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => {
        throw new Error("no body");
      },
    }) as unknown as typeof fetch;

    await expect(api.getFeedback("FB-0001")).rejects.toMatchObject({ status: 500 });
  });

  it("wraps network failures in a friendly ApiError", async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError("network down")) as unknown as typeof fetch;

    await expect(api.getFeedback("FB-0001")).rejects.toBeInstanceOf(ApiError);
    await expect(api.getFeedback("FB-0001")).rejects.toMatchObject({ status: 0 });
  });

  it("resolves with parsed JSON on success", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "FB-0001", feedback_text: "hello" }),
    }) as unknown as typeof fetch;

    const result = await api.getFeedback("FB-0001");
    expect(result).toMatchObject({ id: "FB-0001" });
  });
});
