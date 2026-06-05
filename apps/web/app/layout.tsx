import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Quant Lab",
  description: "Research-only AI-native quantitative backtesting lab"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
