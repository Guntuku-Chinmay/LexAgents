import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LexAgents: Multi-Agent Collaborative Legal RAG System",
  description: "An AI-assisted legal research platform with specialized search agents, citation claim verification, and iterative self-reflection.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${geistSans.className} ${geistMono.className} bg-[#090d16] text-gray-200 antialiased`}>
        {children}
      </body>
    </html>
  );
}
