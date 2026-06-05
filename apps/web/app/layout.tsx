import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI 量化实验室",
  description: "研究模式的 AI-native 量化回测平台"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
