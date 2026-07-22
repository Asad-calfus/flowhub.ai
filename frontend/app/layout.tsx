import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Sidebar } from "@/components/Sidebar";
import { CopilotPalette } from "@/components/CopilotPalette";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "FlowHub | Feedback Intelligence",
  description: "Customer feedback intelligence dashboard for FlowHub",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <div className="flex h-screen overflow-hidden bg-slate-50">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">{children}</main>
          <CopilotPalette />
        </div>
      </body>
    </html>
  );
}
