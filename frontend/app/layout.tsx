import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const albert = localFont({
  src: "./fonts/albert-sans-latin.woff2",
  weight: "100 900",
  variable: "--font-albert",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://snaptracer.devs.surf",
  ),
  title: {
    default: "SnapTracer — Find Every Event Photo",
    template: "%s | SnapTracer",
  },
  description:
    "Private, AI-powered event photo matching that helps guests quickly find and download the photos they appear in.",
  applicationName: "SnapTracer",
  icons: {
    icon: [{ url: "/favicon-64.png?v=2", type: "image/png", sizes: "64x64" }],
    shortcut: "/favicon.ico?v=2",
    apple: "/apple-touch-icon.png?v=2",
  },
  openGraph: {
    type: "website",
    siteName: "SnapTracer",
    title: "SnapTracer — Find Every Event Photo",
    description:
      "Private, AI-powered event photo matching for guests and event teams.",
  },
  twitter: {
    card: "summary_large_image",
    title: "SnapTracer — Find Every Event Photo",
    description:
      "Private, AI-powered event photo matching for guests and event teams.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${albert.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans bg-zinc-950 text-zinc-100 selection:bg-indigo-500/30">
        {children}
      </body>
    </html>
  );
}
