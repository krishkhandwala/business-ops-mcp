import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NEXUS — AI-Native Business Operations Platform",
  description:
    "Enterprise Model Context Protocol (MCP) Command Center & Agentic Workflow Engine.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0B0D10] text-[#F5F7FA] min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}

