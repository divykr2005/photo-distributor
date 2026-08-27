"use client";

import React, { useState, useEffect } from "react";
import api from "@/lib/api";
import Toast from "@/components/ui/Toast";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { getUploadBatch, UploadBatch } from "@/services/uploads";
import { useTasks } from "@/contexts/TaskContext";

export default function DriveImporter({ eventId }: { eventId: string }) {
  const { addTask } = useTasks();
  const [driveUrl, setDriveUrl] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [batch, setBatch] = useState<UploadBatch | null>(null);

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

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    
    if (!driveUrl.includes("/folders/")) {
      setError("Please provide a valid Google Drive folder link containing '/folders/'");
      return;
    }

    setIsImporting(true);
    try {
      const res = await api.post(`/events/${eventId}/photos/import-drive`, {
        drive_url: driveUrl
      });
      setSuccess("Background import started successfully! Check the progress below.");
      setDriveUrl("");
      
      // Start polling locally for the DriveImporter component
      if (res.data.batch_id) {
        const initialBatch = await getUploadBatch(res.data.batch_id);
        setBatch(initialBatch);
        
        // Register the task with the global TaskContext
        addTask({
          id: res.data.batch_id,
          type: "drive_import",
          title: "Importing from Google Drive",
          eventId,
        });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to start Google Drive import");
      setIsImporting(false);
    }
  };

  const completedBatchFiles = batch ? batch.processed_files + batch.failed_files + batch.duplicate_files + batch.rejected_files : 0;
  // In drive import, total_files is set by the task once it lists the directory
  const hasTotal = batch && batch.total_files && batch.total_files > 0;
  const overallProgress = hasTotal ? Math.round((batch.received_files / batch.total_files) * 100) : 0;
  const aiProgress = batch && batch.received_files > 0 ? Math.round((completedBatchFiles / batch.received_files) * 100) : 0;
  
  const isDownloading = Boolean(batch && batch.status !== "completed" && (!hasTotal || batch.received_files < batch.total_files));
  const isAiProcessing = Boolean(batch && batch.status !== "completed" && hasTotal && batch.received_files === batch.total_files);
  const isCompleted = Boolean(batch && batch.status === "completed");

  return (
    <div className="glass-panel p-8 mt-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-medium text-white flex items-center gap-2 tracking-tight">
            <span>☁️</span> Import from Google Drive
          </h2>
          <p className="text-sm text-zinc-400 mt-2 max-w-2xl leading-relaxed">
            Paste a public Google Drive folder link to import photos directly without downloading them locally. Our AI engine will deduplicate and analyze them automatically.
          </p>
        </div>
      </div>

      {error && <Toast message={error} type="error" onClose={() => setError("")} />}
      {success && <Toast message={success} type="success" onClose={() => setSuccess("")} />}

      <form onSubmit={handleImport} className="flex flex-col md:flex-row gap-4 items-end mt-4">
        <div className="flex-1 w-full">
          <Input
            label="Google Drive Folder URL"
            name="drive_url"
            value={driveUrl}
            onChange={(e) => setDriveUrl(e.target.value)}
            placeholder="https://drive.google.com/drive/folders/..."
            required
            disabled={isDownloading || isAiProcessing}
          />
        </div>
        
        {batch ? (
          <div className="mb-0 w-full md:w-auto relative">
            <button
              disabled
              className={`px-4 py-2.5 h-[46px] ${isCompleted ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' : 'bg-indigo-600 border border-indigo-500/50'} text-white rounded-xl text-sm font-medium transition min-w-[260px] relative overflow-hidden flex items-center justify-center`}
            >
              {!isCompleted && (
                <div 
                  className={`absolute top-0 left-0 h-full ${isAiProcessing ? 'bg-indigo-400/40' : 'bg-indigo-500'} transition-all duration-500 ease-out`}
                  style={{ width: `${isAiProcessing ? aiProgress : overallProgress}%` }}
                />
              )}
              <span className={`relative z-10 flex justify-center w-full tracking-wide ${isAiProcessing ? 'animate-pulse' : ''}`}>
                {isCompleted
                  ? "Import Completed ✅"
                  : isAiProcessing 
                    ? `AI Analysis: ${aiProgress}%` 
                    : `Downloading: ${overallProgress}%`}
              </span>
            </button>
          </div>
        ) : (
          <div className="w-full md:w-auto">
             <Button 
                variant="primary"
                type="submit" 
                isLoading={isImporting} 
                disabled={!driveUrl}
                className="w-full md:w-auto h-[46px] min-w-[140px]"
              >
                Start Import
              </Button>
          </div>
        )}
      </form>
      
      {batch && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 p-6 mt-8 bg-zinc-900/60 rounded-xl border border-zinc-800/80 shadow-inner backdrop-blur-sm">
          <div>
            <span className="text-xs text-zinc-500 font-medium uppercase tracking-wider">Total Received</span>
            <p className="text-xl font-medium text-white mt-1 tracking-tight">{batch.received_files}{hasTotal ? ` / ${batch.total_files}` : ''}</p>
          </div>
          <div>
            <span className="text-xs text-zinc-500 font-medium uppercase tracking-wider">Duplicates</span>
            <p className="text-xl font-medium text-indigo-400 mt-1 tracking-tight">{batch.duplicate_files}</p>
          </div>
          <div>
            <span className="text-xs text-zinc-500 font-medium uppercase tracking-wider">Processed by AI</span>
            <p className="text-xl font-medium text-emerald-400 mt-1 tracking-tight">{batch.processed_files}</p>
          </div>
          <div>
            <span className="text-xs text-zinc-500 font-medium uppercase tracking-wider">Faces / Matches</span>
            <p className="text-xl font-medium text-purple-400 mt-1 tracking-tight">{batch.faces_found} <span className="text-sm text-zinc-400 font-normal">faces ({batch.matches_created} matched)</span></p>
          </div>
        </div>
      )}
    </div>
  );
}
