import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Your Event Photos",
  description: "View and download your event photos",
  robots: { index: false, follow: false }, // D21: magic links must not end up in search
};

/**
 * Layout for /g/* routes — no dashboard chrome, no navbar, no login prompt.
 * Standalone public page as specified in Day 16.
 */
export default function GuestPortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white">
      {children}
    </div>
  );
}
