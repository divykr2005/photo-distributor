"use client";

import React, { use } from "react";
import BulkUploader from "@/components/uploader/BulkUploader";

export default function EventUploadPage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = use(params);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Event Photo Ingestion</h1>
          <p className="text-sm text-slate-400">Upload bulk event photos with parallel processing & deduplication.</p>
        </div>
      </div>

      <BulkUploader eventId={eventId} />
    </div>
  );
}
