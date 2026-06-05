"use client";

import { FormEvent, useState } from "react";
import { Bot, Send } from "lucide-react";
import { askResearchCopilot } from "@/lib/api";
import type { ResearchResponse } from "@/lib/types";

type Props = {
  backtestId?: string;
};

export function ResearchCopilot({ backtestId }: Props) {
  const [question, setQuestion] = useState("What should I inspect before trusting this backtest?");
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
      setError(err instanceof Error ? err.message : "Research request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="copilot" onSubmit={submit}>
      <label>
        Ask research question
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
      </label>
      <button type="submit" disabled={loading || question.trim().length < 3}>
        <Send size={16} />
        {loading ? "Asking" : "Ask AI"}
      </button>

      {error ? <p className="error" role="alert">{error}</p> : null}

      {response ? (
        <>
          <div className="copilot-answer">
            <Bot size={16} aria-hidden="true" /> {response.answer}
          </div>
          <ul className="suggestions" aria-label="Suggested experiments">
            {response.suggested_experiments.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="empty-state">Attach a backtest result for more specific analysis.</p>
      )}
    </form>
  );
}
