import Link from "next/link";
import type { Metadata } from "next";
import { HiOutlineShieldCheck } from "react-icons/hi";

export const metadata: Metadata = {
  title: "Privacy and Biometric Data Policy",
  description: "How SnapTracer collects, protects, retains, and deletes personal and biometric data.",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="px-6 pt-12 pb-8 border-b border-white/5 bg-zinc-950/50 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
            <HiOutlineShieldCheck className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight leading-tight">
              Privacy & Biometric Data Policy
            </h1>
            <p className="text-zinc-400 text-sm mt-1 font-medium">
              Last Updated: September 2026
            </p>
          </div>
        </div>
      </header>

      <main className="px-6 pt-12">
        <div className="max-w-3xl mx-auto space-y-12">

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-white tracking-tight">1. Overview</h2>
            <p className="text-zinc-300 leading-relaxed">
              At SnapTracer, we process biometric data strictly for the purpose of matching you with event photos you attend. We do not sell, rent, or trade your facial geometry to any third party. Your data is encrypted at rest and mathematically transformed in a way that prevents reconstruction of your actual face.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-white tracking-tight">2. Biometric Data Collection & Processing</h2>
            <ul className="space-y-3 text-zinc-300 list-disc pl-5">
              <li><strong>What we collect:</strong> We collect a single "selfie" image when you register for an event.</li>
              <li><strong>How it's used:</strong> Our AI extracts a mathematical representation (a "vector") of your face. This vector is compared against photos taken at the event to find matches.</li>
              <li><strong>Encryption:</strong> Your vector is encrypted at rest in our PostgreSQL database using envelope encryption. The original selfie image is stored securely on an isolated cloud bucket.</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-white tracking-tight">3. Retention & Permanent Erasure</h2>
            <p className="text-zinc-300 leading-relaxed">
              We employ a strict data minimization policy to comply with GDPR, CCPA, and BIPA guidelines:
            </p>
            <div className="bg-zinc-900/50 p-6 rounded-2xl border border-zinc-800 space-y-4">
              <p className="text-zinc-200 font-medium">
                <strong>Default Retention:</strong> Your biometric vectors, your selfie, and any match linkages are automatically and permanently purged <span className="text-indigo-400 font-bold">15 days</span> after you register for an event.
              </p>
              <p className="text-sm text-zinc-400">
                The event organizer retains basic registration records (name and email) for their attendance logs, but all biometric capability is destroyed.
              </p>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-white tracking-tight">4. Right to Erasure</h2>
            <p className="text-zinc-300 leading-relaxed">
              You do not have to wait 15 days. You can request the immediate deletion of your biometric data at any time by contacting the event organizer or clicking the deletion link provided in your notification messages.
            </p>
          </section>

          <div className="flex justify-center gap-5 pt-8 text-center border-t border-white/5">
            <Link href="/terms" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
              Terms and Conditions
            </Link>
            <Link href="/" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
              Return to Home
            </Link>
          </div>

        </div>
      </main>
    </div>
  );
}
