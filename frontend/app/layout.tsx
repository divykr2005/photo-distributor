import type { Metadata } from "next";
import { Albert_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { TaskProvider } from "@/contexts/TaskContext";
import GlobalTaskWidget from "@/components/ui/GlobalTaskWidget";

const albert = Albert_Sans({
  subsets: ["latin"],
  variable: "--font-albert",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PhotoDistro — AI Event Photo Distribution",
  description:
    "Automated event photo distribution using AI-powered facial recognition. Match photos to guests and deliver via gallery or WhatsApp.",
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
