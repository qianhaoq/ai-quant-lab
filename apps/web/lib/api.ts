import type { BacktestRequest, BacktestResult, ResearchResponse, SymbolInfo } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail || `Request failed with ${response.status}`;
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function fetchSymbols() {
  return apiFetch<SymbolInfo[]>("/symbols");
}

export function createBacktest(payload: BacktestRequest) {
  return apiFetch<BacktestResult>("/backtests", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function askResearchCopilot(question: string, backtestId?: string) {
  return apiFetch<ResearchResponse>("/research/chat", {
    method: "POST",
    body: JSON.stringify({ question, backtest_id: backtestId })
  });
}
