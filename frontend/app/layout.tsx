import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentOrg",
  description: "Multi-agent workflow command center",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <nav className="border-b border-zinc-800 px-6 py-3 flex items-center gap-6">
          <span className="font-bold text-white tracking-tight">AgentOrg</span>
          <Link href="/runs" className="text-zinc-400 hover:text-white text-sm transition-colors">Runs</Link>
          <Link href="/workflows" className="text-zinc-400 hover:text-white text-sm transition-colors">Workflows</Link>
          <Link href="/agents" className="text-zinc-400 hover:text-white text-sm transition-colors">Agents</Link>
        </nav>
        <main className="px-6 py-6 max-w-6xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
