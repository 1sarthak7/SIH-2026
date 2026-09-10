import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chandrayaan-2 Image Correspondence | ISRO Multi-Modal Matching",
  description:
    "AI-powered multi-modal, sun angle and scale invariant image correspondence system for Chandrayaan-2 OHRC, TMC-2 and IIRS instruments. Built for Smart India Hackathon 2026.",
  keywords: [
    "Chandrayaan-2",
    "ISRO",
    "OHRC",
    "TMC",
    "IIRS",
    "image correspondence",
    "feature matching",
    "LoFTR",
    "lunar mapping",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
