"use client";

import React, { use } from "react";
import PhotoGrid from "@/components/photo-grid/PhotoGrid";

export default function EventPhotosPage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = use(params);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Organizer Photo Grid</h1>
        <p className="text-sm text-slate-400">Inspect uploaded photos, face detections, and bounding box details.</p>
      </div>

      <PhotoGrid eventId={eventId} />
    </div>
  );
}
