import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResearchCopilot } from "@/components/ResearchCopilot";

describe("ResearchCopilot", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("asks the research API and renders the response", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        answer: "Research-only summary: compare against buy-and-hold.",
        suggested_experiments: ["Run an out-of-sample test."],
        used_mock: true
      })
    } as Response);

    render(<ResearchCopilot backtestId="bt_123" />);
    await user.clear(screen.getByLabelText("Ask research question"));
    await user.type(screen.getByLabelText("Ask research question"), "What next?");
    await user.click(screen.getByRole("button", { name: /ask ai/i }));

    await waitFor(() => {
      expect(screen.getByText(/Research-only summary/)).toBeInTheDocument();
    });
    expect(screen.getByText("Run an out-of-sample test.")).toBeInTheDocument();
  });
});
