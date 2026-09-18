import type { Metadata } from "next";
import Link from "next/link";
import { HiOutlineDocumentText } from "react-icons/hi";

export const metadata: Metadata = {
  title: "Terms and Conditions",
  description: "Terms for using the SnapTracer event photo matching service.",
};

const sections = [
  {
    title: "1. Using SnapTracer",
    body: "You may use SnapTracer only for lawful event-photo workflows and only with photos and guest information you have permission to process. You must provide accurate account details and keep your login secure.",
  },
  {
    title: "2. Event organizers",
    body: "Organizers are responsible for telling guests how photos and personal data will be used, collecting any consent required by law, and uploading only content they are allowed to share.",
  },
  {
    title: "3. Guests and face matching",
    body: "Face matching is optional and may make mistakes. Guests should review results before downloading or sharing them. How biometric data is collected, protected, retained, and deleted is explained in our Privacy Policy.",
  },
  {
    title: "4. Prohibited use",
    body: "Do not use the service to identify people outside an authorized event, monitor people without their knowledge, upload illegal or harmful content, probe the service for vulnerabilities, or interfere with other users.",
  },
  {
    title: "5. Your content",
    body: "You keep ownership of content you upload. You give SnapTracer permission to store and process it only as needed to provide, secure, and maintain the service.",
  },
  {
    title: "6. Availability and results",
    body: "We work to keep the service reliable, but we do not promise uninterrupted access or perfect photo matches. The service is provided as available, to the extent allowed by law.",
  },
  {
    title: "7. Suspension and termination",
    body: "We may suspend access that threatens security, breaks these terms, or creates legal risk. You may stop using the service at any time and request deletion as described in the Privacy Policy.",
  },
  {
    title: "8. Changes",
    body: "We may update these terms when the service or the law changes. The date below will be updated when that happens. Continued use after an update means you accept the revised terms.",
  },
];

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-zinc-950 pb-12 text-zinc-100">
      <header className="border-b border-white/5 bg-zinc-950/90 px-6 py-10">
        <div className="mx-auto flex max-w-3xl items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-indigo-500/20 bg-indigo-500/10">
            <HiOutlineDocumentText className="h-6 w-6 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Terms and Conditions</h1>
            <p className="mt-1 text-sm font-medium text-zinc-400">
              Effective September 18, 2026
            </p>
          </div>
        </div>
      </header>

      <main className="px-6 pt-10">
        <div className="mx-auto max-w-3xl space-y-9">
          <p className="leading-relaxed text-zinc-300">
            These terms govern your use of SnapTracer. By creating an account or
            using the service, you agree to them.
          </p>
          {sections.map((section) => (
            <section key={section.title} className="space-y-3">
              <h2 className="text-xl font-bold tracking-tight">{section.title}</h2>
              <p className="leading-relaxed text-zinc-300">{section.body}</p>
            </section>
          ))}
          <div className="flex flex-wrap gap-5 border-t border-white/5 pt-8 text-sm">
            <Link className="font-medium text-indigo-400 hover:text-indigo-300" href="/privacy">
              Privacy Policy
            </Link>
            <Link className="font-medium text-indigo-400 hover:text-indigo-300" href="/">
              Return to home
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
