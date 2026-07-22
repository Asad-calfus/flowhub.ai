import { describe, expect, it, vi, afterEach } from "vitest";
import { api } from "@/lib/api";

describe("filter parameter construction", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("builds a query string containing only the provided filters", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0, page: 1, page_size: 20 }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    await api.listFeedback({ page: 2, page_size: 20, sentiment: "Negative", source: "Chat" });

    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/feedback?");
    expect(calledUrl).toContain("page=2");
    expect(calledUrl).toContain("page_size=20");
    expect(calledUrl).toContain("sentiment=Negative");
    expect(calledUrl).toContain("source=Chat");
  });

  it("omits undefined and empty-string filters entirely", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0, page: 1, page_size: 20 }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    await api.listFeedback({ page: 1, category: undefined, product_module: "" });

    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).not.toContain("category");
    expect(calledUrl).not.toContain("product_module");
  });
});
