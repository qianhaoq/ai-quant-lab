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
        answer: "研究模式摘要：先和买入并持有基准对比。",
        suggested_experiments: ["运行样本外测试。"],
        used_mock: true
      })
    } as Response);

    render(<ResearchCopilot backtestId="bt_123" />);
    await user.clear(screen.getByLabelText("输入研究问题"));
    await user.type(screen.getByLabelText("输入研究问题"), "下一步？");
    await user.click(screen.getByRole("button", { name: /询问 AI/i }));

    await waitFor(() => {
      expect(screen.getByText(/研究模式摘要/)).toBeInTheDocument();
    });
    expect(screen.getByText("运行样本外测试。")).toBeInTheDocument();
  });
});
