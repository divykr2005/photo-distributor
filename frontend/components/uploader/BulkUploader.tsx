"use client";

import React, { useState, useRef, useEffect } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { createUploadBatch, getUploadBatch, uploadSinglePhoto, UploadBatch } from "@/services/uploads";

interface FileState {
  id: string;
  file: File;
  status: "queued" | "uploading" | "done" | "duplicate" | "failed";
  progress: number;
  error?: string;
  photo_id?: string;
}

const MAX_CONCURRENT = 6;
const MAX_FILE_SIZE = 25 * 1024 * 1024;

export default function BulkUploader({ eventId }: { eventId: string }) {
  const [files, setFiles] = useState<FileState[]>([]);
  const [batch, setBatch] = useState<UploadBatch | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const activeCountRef = useRef(0);
  const parentRef = useRef<HTMLDivElement>(null);

  // Virtualizer for rendering large file lists (up to 5,000 files)
  const rowVirtualizer = useVirtualizer({
    count: files.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48,
    overscan: 10,
  });

  // Batch status polling
  useEffect(() => {
    if (!batch || batch.status === "completed") return;

    const interval = setInterval(async () => {
      try {
        const updated = await getUploadBatch(batch.id);
        setBatch(updated);
      } catch (err) {
        console.error("Failed to poll upload batch status:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [batch]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    const selectedFiles = Array.from(e.target.files);
    const validStates: FileState[] = [];

    for (const f of selectedFiles) {
      const ext = f.name.rsplit ? f.name.split(".").pop()?.toLowerCase() : "jpg";
      if (!["jpg", "jpeg", "png", "heic", "heif", "webp"].includes(ext || "")) {
        continue;
      }

      validStates.push({
        id: `${f.name}-${f.size}-${Math.random()}`,
        file: f,
        status: f.size > MAX_FILE_SIZE ? "failed" : "queued",
        progress: 0,
        error: f.size > MAX_FILE_SIZE ? "Exceeds 25MB limit" : undefined,
      });
    }

    setFiles((prev) => [...prev, ...validStates]);

    if (!batch && validStates.length > 0) {
      try {
        const newBatch = await createUploadBatch(eventId, validStates.length);
        setBatch(newBatch);
      } catch (err) {
        console.error("Failed to create upload batch", err);
      }
    }
  };

  const processQueue = async () => {
    if (activeCountRef.current >= MAX_CONCURRENT) return;

    setFiles((prevFiles) => {
      const queuedIdx = prevFiles.findIndex((f) => f.status === "queued");
      if (queuedIdx === -1) return prevFiles;

      const target = prevFiles[queuedIdx];
      activeCountRef.current += 1;

      // Start upload async
      (async () => {
        try {
          setFiles((curr) =>
            curr.map((item) => (item.id === target.id ? { ...item, status: "uploading", progress: 50 } : item))
          );

          const res = await uploadSinglePhoto(eventId, target.file, batch?.id);

          setFiles((curr) =>
            curr.map((item) =>
              item.id === target.id
                ? {
                    ...item,
                    status: res.duplicate ? "duplicate" : "done",
                    progress: 100,
                    photo_id: res.photo_id,
                  }
                : item
            )
          );
        } catch (err: any) {
          setFiles((curr) =>
            curr.map((item) =>
              item.id === target.id
                ? { ...item, status: "failed", progress: 0, error: err.response?.data?.detail || "Upload failed" }
                : item
            )
          );
        } finally {
          activeCountRef.current -= 1;
        }
      })();

      return prevFiles;
    });
  };

  useEffect(() => {
    if (isUploading) {
      const timer = setInterval(() => {
        processQueue();
      }, 100);
      return () => clearInterval(timer);
    }
  }, [isUploading, files]);

  const startUpload = () => {
    setIsUploading(true);
  };

  const retryFailed = () => {
    setFiles((prev) =>
      prev.map((f) => (f.status === "failed" ? { ...f, status: "queued", error: undefined, progress: 0 } : f))
    );
    setIsUploading(true);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-white">Bulk Photo Ingestion</h2>
          <p className="text-sm text-slate-400">Streamed 1MB chunks, client validation, 6 concurrent uploads.</p>
        </div>
        <div className="flex gap-3">
          <label className="cursor-pointer px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white rounded-lg text-sm font-medium transition">
            Select Files / Folders
            <input type="file" multiple accept="image/jpeg,image/png,image/heic" onChange={handleFileSelect} className="hidden" />
          </label>
          <button
            onClick={startUpload}
            disabled={isUploading || files.filter((f) => f.status === "queued").length === 0}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition"
          >
            {isUploading ? "Uploading..." : "Start Batch Upload"}
          </button>
          <button
            onClick={retryFailed}
            disabled={files.filter((f) => f.status === "failed").length === 0}
            className="px-3 py-2 bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-500/30 rounded-lg text-sm transition"
          >
            Retry Failed
          </button>
        </div>
      </div>

      {batch && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-slate-950/60 rounded-lg border border-slate-800 text-xs">
          <div>
            <span className="text-slate-400">Total Received:</span>
            <p className="text-lg font-semibold text-indigo-400">{batch.received_files} / {batch.total_files}</p>
          </div>
          <div>
            <span className="text-slate-400">Duplicates Detected:</span>
            <p className="text-lg font-semibold text-amber-400">{batch.duplicate_files}</p>
          </div>
          <div>
            <span className="text-slate-400">Processed by AI:</span>
            <p className="text-lg font-semibold text-emerald-400">{batch.processed_files}</p>
          </div>
          <div>
            <span className="text-slate-400">Faces / Matches:</span>
            <p className="text-lg font-semibold text-purple-400">{batch.faces_found} faces ({batch.matches_created} confirmed)</p>
          </div>
        </div>
      )}

      {/* Virtualized File List */}
      <div
        ref={parentRef}
        className="h-80 overflow-y-auto border border-slate-800 rounded-lg bg-slate-950/40 p-2 space-y-1"
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: "100%",
            position: "relative",
          }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const f = files[virtualRow.index];
            return (
              <div
                key={f.id}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                className="flex items-center justify-between px-3 py-2 border-b border-slate-800/50 text-xs text-slate-300 hover:bg-slate-800/30"
              >
                <div className="truncate max-w-md font-mono">
                  {f.file.name} ({(f.file.size / (1024 * 1024)).toFixed(2)} MB)
                </div>
                <div className="flex items-center gap-4">
                  {f.status === "queued" && <span className="text-slate-500">Queued</span>}
                  {f.status === "uploading" && <span className="text-indigo-400 animate-pulse">Uploading...</span>}
                  {f.status === "done" && <span className="text-emerald-400 font-medium">Uploaded</span>}
                  {f.status === "duplicate" && <span className="text-amber-400 font-medium">Duplicate</span>}
                  {f.status === "failed" && <span className="text-rose-400 font-medium">{f.error || "Failed"}</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
