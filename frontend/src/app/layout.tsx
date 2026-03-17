import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mini Outfit Builder",
  description:
    "AI-powered outfit generation from Zappos, Amazon, and SSENSE. Search by vibe – date night, streetwear, casual, and more.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 font-sans">{children}</body>
    </html>
  );
}
