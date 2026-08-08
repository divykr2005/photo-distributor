import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "PhotoDistro — AI Event Photo Distribution",
  description:
    "Automated event photo distribution using AI-powered facial recognition. Match photos to guests and deliver via gallery or WhatsApp.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans bg-[#0a0e1a]">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
