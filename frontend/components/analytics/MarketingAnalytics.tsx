"use client";

import { useEffect, useState } from "react";
import Script from "next/script";

const CONSENT_KEY = "snaptracer_analytics_consent";

type AnalyticsWindow = typeof window & {
  dataLayer?: unknown[];
  gtag?: (...args: unknown[]) => void;
};

function prepareGoogleTag() {
  const analyticsWindow = window as AnalyticsWindow;
  analyticsWindow.dataLayer = analyticsWindow.dataLayer || [];
  analyticsWindow.gtag = (...args) => {
    analyticsWindow.dataLayer?.push(args);
  };
}

export default function MarketingAnalytics({ measurementId }: { measurementId: string }) {
  const [consent, setConsent] = useState<"accepted" | "declined" | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(CONSENT_KEY);
    if (saved === "accepted") prepareGoogleTag();
    if (saved === "accepted" || saved === "declined") setConsent(saved);
    setReady(true);
  }, []);

  function choose(value: "accepted" | "declined") {
    if (value === "accepted") prepareGoogleTag();
    window.localStorage.setItem(CONSENT_KEY, value);
    setConsent(value);
  }

  if (!ready) return null;

  return <>
    {consent === "accepted" && <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${measurementId}`}
        strategy="lazyOnload"
        onReady={() => {
          const analyticsWindow = window as AnalyticsWindow;
          const gtag = analyticsWindow.gtag;
          if (!gtag) return;
          gtag("js", new Date());
          gtag("consent", "default", {
            analytics_storage: "granted",
            ad_storage: "denied",
            ad_user_data: "denied",
            ad_personalization: "denied",
          });
          gtag("config", measurementId, {
            send_page_view: false,
            allow_google_signals: false,
            allow_ad_personalization_signals: false,
          });
          gtag("event", "page_view", {
            page_location: window.location.origin + "/",
            page_path: "/",
            page_title: document.title,
          });
        }}
      />
    </>}
    {consent === null && <aside aria-label="Analytics preference" className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-xl rounded-xl border border-zinc-700 bg-zinc-950 p-4 text-sm text-zinc-100 shadow-2xl">
      <p>Can we use Google Analytics to understand visits to this homepage? We do not send your photos, name, or email. <a className="underline" href="/privacy">Privacy details</a></p>
      <div className="mt-3 flex gap-3">
        <button className="rounded-lg bg-white px-4 py-2 font-semibold text-zinc-950" onClick={() => choose("accepted")}>Allow analytics</button>
        <button className="rounded-lg border border-zinc-600 px-4 py-2" onClick={() => choose("declined")}>No thanks</button>
      </div>
    </aside>}
  </>;
}
