"use client";

import { FormEvent, useState } from "react";
import { Bot, Send } from "lucide-react";
import { askResearchCopilot } from "@/lib/api";
import type { ResearchResponse } from "@/lib/types";

type Props = {
  backtestId?: string;
};

export function ResearchCopilot({ backtestId }: Props) {
  const [question, setQuestion] = useState("基于当前账户状态，AI 生成交易信号前应该检查哪些风险？");
  const [response, setResponse] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const nextResponse = await askResearchCopilot(question, backtestId);
      setResponse(nextResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "研究请求失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="copilot" onSubmit={submit}>
      <label>
        输入研究问题
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
      </label>
      <button type="submit" disabled={loading || question.trim().length < 3}>
        <Send size={16} />
        {loading ? "分析中" : "询问 AI"}
      </button>

      {error ? <p className="error" role="alert">{error}</p> : null}

      {response ? (
        <>
          <div className="copilot-answer">
            <Bot size={16} aria-hidden="true" /> {response.answer}
          </div>
          <ul className="suggestions" aria-label="建议实验">
            {response.suggested_experiments.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="empty-state">AI 只生成信号假设和风控检查，不直接提交订单。</p>
      )}
    </form>
  );
}
