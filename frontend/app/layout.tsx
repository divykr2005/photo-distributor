import type { Metadata } from "next";
import { Albert_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { TaskProvider } from "@/contexts/TaskContext";
import GlobalTaskWidget from "@/components/ui/GlobalTaskWidget";

// Cloudflare Pages Functions run Next.js server-rendered routes on the Edge
// Runtime. Defining this at the root makes every child route inherit it.
export const runtime = "edge";

const albert = Albert_Sans({
  subsets: ["latin"],
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
        <AuthProvider>
          <TaskProvider>
            <GlobalTaskWidget />
            {children}
          </TaskProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
