import React from "react";
import BulkUploader from "@/components/uploader/BulkUploader";
import DriveImporter from "@/components/uploader/DriveImporter";

export default function EventUploadPage({ params }: { params: { eventId: string } }) {
  const { eventId } = params;

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-white tracking-tight">Event Photo Ingestion</h1>
          <p className="text-sm text-zinc-400 mt-2 max-w-2xl leading-relaxed">
            Upload bulk event photos with parallel processing & deduplication. 
            Choose between local upload or direct Google Drive import.
          </p>
        </div>
      </div>

      <div className="space-y-6">
        <BulkUploader eventId={eventId} />
        <DriveImporter eventId={eventId} />
      </div>
    </div>
  );
}
