import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmptyState, ErrorState, SkeletonBlock } from "@/components/States";

describe("loading, empty, and error states", () => {
  it("ErrorState shows the message and calls onRetry when clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Could not reach the backend API." onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Could not reach the backend API.");
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("ErrorState omits the retry button when no handler is given", () => {
    render(<ErrorState message="boom" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("EmptyState renders title and description without fabricating data", () => {
    render(<EmptyState title="No feedback matches these filters" description="Try clearing a filter." />);
    expect(screen.getByText("No feedback matches these filters")).toBeInTheDocument();
    expect(screen.getByText("Try clearing a filter.")).toBeInTheDocument();
  });

  it("SkeletonBlock renders the requested number of placeholder rows", () => {
    const { container } = render(<SkeletonBlock rows={3} />);
    expect(container.querySelectorAll(".animate-pulse")).toHaveLength(3);
  });
});
