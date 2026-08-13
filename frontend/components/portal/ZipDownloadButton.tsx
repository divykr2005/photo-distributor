"use client";

import { useState, useEffect, useRef } from "react";
import { HiOutlineDownload, HiOutlineExclamation, HiOutlineCheck } from "react-icons/hi";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface ZipJobStatusResponse {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  photo_count: number;
  total_bytes: number;
  processed_photos: number;
  processed_bytes: number;
  error_message?: string | null;
  download_url?: string | null;
}

interface ZipDownloadButtonProps {
  accessCode: string;
  photoCount: number;
}

export default function ZipDownloadButton({ accessCode, photoCount }: ZipDownloadButtonProps) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "initiating" | "processing" | "completed" | "failed">("idle");
  const [progress, setProgress] = useState<{ processedPhotos: number; totalPhotos: number; processedBytes: number; totalBytes: number }>({
    processedPhotos: 0,
    totalPhotos: photoCount,
    processedBytes: 0,
    totalBytes: 0,
  });
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const storageKey = `guest_zip_job_${accessCode}`;

  // Check sessionStorage on mount to resume any existing in-flight job
  useEffect(() => {
    try {
      const savedJobId = sessionStorage.getItem(storageKey);
      if (savedJobId) {
        setJobId(savedJobId);
        setStatus("processing");
      }
    } catch {
      // Ignore storage errors
    }
  }, [storageKey]);

  // Polling effect
  useEffect(() => {
    if (!jobId || status === "completed" || status === "failed") {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      return;
    }

    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/public/guest/${accessCode}/zip/${jobId}`);
        if (!res.ok) {
          if (res.status === 404) {
            // Job expired or invalid -> reset
            sessionStorage.removeItem(storageKey);
            setJobId(null);
            setStatus("idle");
          }
          return;
        }

        const data: ZipJobStatusResponse = await res.json();
        setProgress({
          processedPhotos: data.processed_photos || 0,
          totalPhotos: data.photo_count || photoCount,
          processedBytes: data.processed_bytes || 0,
          totalBytes: data.total_bytes || 0,
        });

        if (data.status === "completed") {
          setStatus("completed");
          if (data.download_url) {
            setDownloadUrl(`${API_URL.replace("/api/v1", "")}${data.download_url}`);
          }
        } else if (data.status === "failed") {
          setStatus("failed");
          setErrorMsg(data.error_message || "ZIP generation failed");
          sessionStorage.removeItem(storageKey);
        } else {
          setStatus("processing");
        }
      } catch (err) {
        console.error("Error polling ZIP status:", err);
      }
    };

    // Initial check
    checkStatus();
    pollTimerRef.current = setInterval(checkStatus, 2000);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [jobId, status, accessCode, storageKey, photoCount]);

  const handleInitiateZip = async () => {
    if (photoCount === 0) return;
    setStatus("initiating");
    setErrorMsg(null);

    try {
      const res = await fetch(`${API_URL}/public/guest/${accessCode}/zip`, {
        method: "POST",
      });

      if (res.status === 503) {
        const errData = await res.json().catch(() => ({}));
        setStatus("failed");
        setErrorMsg(errData.detail || "Server storage full. Please try again later.");
        return;
      }

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        setStatus("failed");
        setErrorMsg(errData.detail || "Failed to start ZIP creation.");
        return;
      }

      const data: ZipJobStatusResponse = await res.json();
      setJobId(data.job_id);

      try {
        sessionStorage.setItem(storageKey, data.job_id);
      } catch {
        // Storage fallback
      }

      if (data.status === "completed" && data.download_url) {
        setStatus("completed");
        setDownloadUrl(`${API_URL.replace("/api/v1", "")}${data.download_url}`);
      } else {
        setStatus("processing");
      }
    } catch (err) {
      setStatus("failed");
      setErrorMsg("Network error. Please check connection.");
    }
  };

  const handleDownload = () => {
    if (!downloadUrl) return;
    // Trigger download link
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Clear session storage on successful download trigger
    try {
      sessionStorage.removeItem(storageKey);
    } catch {}
  };

  const percent = progress.totalPhotos > 0
    ? Math.min(100, Math.round((progress.processedPhotos / progress.totalPhotos) * 100))
    : 0;

  const formatMb = (bytes: number) => {
    if (!bytes) return "0 MB";
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (photoCount === 0) {
    return null;
  }

  return (
    <div className="flex flex-col items-center sm:items-start gap-2">
      {status === "idle" && (
        <button
          onClick={handleInitiateZip}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs sm:text-sm font-medium transition-all shadow-md hover:shadow-violet-500/20 active:scale-95"
        >
          <HiOutlineDownload className="w-4 h-4" />
          <span>Download All ({photoCount} photos)</span>
        </button>
      )}

      {status === "initiating" && (
        <button
          disabled
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 text-slate-400 text-xs sm:text-sm font-medium border border-slate-700 cursor-not-allowed opacity-80"
        >
          <svg className="animate-spin h-4 w-4 text-violet-400" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span>Preparing ZIP...</span>
        </button>
      )}

      {status === "processing" && (
        <div className="flex flex-col gap-1.5 w-full sm:w-64 bg-slate-800/90 border border-slate-700/80 p-2.5 rounded-xl shadow-lg">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-300 font-medium">Creating ZIP archive</span>
            <span className="text-violet-400 font-semibold">{percent}%</span>
          </div>

          <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-300 ease-out"
              style={{ width: `${percent}%` }}
            />
          </div>

          <div className="flex justify-between items-center text-[10px] text-slate-400">
            <span>{progress.processedPhotos} / {progress.totalPhotos} photos</span>
            <span>{formatMb(progress.processedBytes)}</span>
          </div>

          <span className="text-[10px] text-slate-500 italic text-center mt-0.5">
            This may take a minute...
          </span>
        </div>
      )}

      {status === "completed" && (
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs sm:text-sm font-semibold transition-all shadow-lg shadow-emerald-500/20 active:scale-95 animate-pulse"
          >
            <HiOutlineCheck className="w-4 h-4" />
            <span>Download Ready (.zip)</span>
          </button>
        </div>
      )}

      {status === "failed" && (
        <div className="flex flex-col gap-1">
          <button
            onClick={handleInitiateZip}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-rose-900/40 border border-rose-700/50 hover:bg-rose-900/60 text-rose-300 text-xs font-medium transition-colors"
          >
            <HiOutlineExclamation className="w-4 h-4" />
            <span>Retry ZIP Download</span>
          </button>
          {errorMsg && <span className="text-[10px] text-rose-400">{errorMsg}</span>}
        </div>
      )}
    </div>
  );
}
