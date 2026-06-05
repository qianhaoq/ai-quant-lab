import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI 量化交易平台",
  description: "带交易网关、风控预检和 AI 信号研究的 AI-native 量化交易平台"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
