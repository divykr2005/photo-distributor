"use client";

import React, { use } from "react";
import ReviewQueue from "@/components/face-review/ReviewQueue";

export default function EventReviewPage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = use(params);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Uncertain Match Review Queue</h1>
        <p className="text-sm text-slate-400">Review low-margin or review-band face detections to confirm or reject guest matches.</p>
      </div>

      <ReviewQueue eventId={eventId} />
    </div>
  );
}
