import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VERITY",
  description:
    "Ask a question or paste a URL. VERITY runs multiple intelligence agents to surface what is verified, contested, and hidden.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased bg-[var(--bg-base)] text-[var(--text-primary)]">
        {children}
      </body>
    </html>
  );
}
