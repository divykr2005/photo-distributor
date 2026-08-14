"use client";

import { useParams } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import {
  HiOutlineCamera,
  HiOutlinePhotograph,
  HiOutlineCheckCircle,
  HiOutlineExclamationCircle,
  HiOutlineX,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlineRefresh,
  HiOutlineDownload,
} from "react-icons/hi";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface EventInfo {
  id: string;
  title: string;
  date: string;
  selfie_search_enabled: boolean;
}

interface PhotoItem {
  id: string;
  thumb_url: string;
  web_url: string;
  taken_at?: string | null;
  filename?: string | null;
}

interface SelfieSearchResponse {
  session_id: string;
  total: number;
  photos: PhotoItem[];
}

export default function SelfieSearchPage() {
  const { eventId } = useParams<{ eventId: string }>();

  const [eventInfo, setEventInfo] = useState<EventInfo | null>(null);
  const [loadingEvent, setLoadingEvent] = useState(true);
  const [eventError, setEventError] = useState(false);

  const [consent, setConsent] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResult, setSearchResult] = useState<SelfieSearchResponse | null>(null);

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!eventId) return;

    fetch(`${API_URL}/public/events/${eventId}/info`)
      .then((res) => {
        if (!res.ok) {
          setEventError(true);
          return null;
        }
        return res.json();
      })
      .then((data: EventInfo | null) => {
        if (data) setEventInfo(data);
      })
      .catch(() => setEventError(true))
      .finally(() => setLoadingEvent(false));
  }, [eventId]);

  const handleFileChange = (selectedFile: File) => {
    if (selectedFile.size > 10 * 1024 * 1024) {
      setSearchError("File size must be under 10MB");
      return;
    }
    setSearchError(null);
    setFile(selectedFile);
    setPreviewUrl(URL.createObjectURL(selectedFile));
  };

  const handleSearch = async () => {
    if (!file || !consent || !eventId) return;

    setSearching(true);
    setSearchError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/public/events/${eventId}/search-selfie`, {
        method: "POST",
        body: formData,
      });

      if (res.status === 422) {
        const errData = await res.json();
        setSearchError(errData.detail || "Quality check failed. Please upload a clear selfie.");
        setSearching(false);
        return;
      }

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        setSearchError(errData.detail || "Search failed. Please try again.");
        setSearching(false);
        return;
      }

      const data: SelfieSearchResponse = await res.json();
      setSearchResult(data);
    } catch {
      setSearchError("Network error. Please check your connection and try again.");
    } finally {
      setSearching(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreviewUrl(null);
    setSearchResult(null);
    setSearchError(null);
  };

  if (loadingEvent) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] text-white flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-white/50">Loading event info…</p>
        </div>
      </div>
    );
  }

  if (eventError || !eventInfo) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] text-white flex items-center justify-center px-6">
        <div className="text-center space-y-4 max-w-sm">
          <div className="mx-auto w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center">
            <HiOutlineExclamationCircle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="text-xl font-semibold">Selfie Search Disabled</h1>
          <p className="text-white/50 text-sm leading-relaxed">
            Selfie search is not enabled for this event, or the event was not found.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white pb-12">
      {/* Header */}
      <header className="px-4 pt-8 pb-6 text-center space-y-2 max-w-2xl mx-auto">
        <p className="text-violet-400 text-xs font-semibold tracking-wider uppercase">
          {eventInfo.title}
        </p>
        <h1 className="text-2xl sm:text-3xl font-bold">Find Your Photos 📸</h1>
        <p className="text-white/50 text-sm">
          Upload a quick selfie to find photos of yourself from this event instantly.
        </p>
      </header>

      <main className="max-w-2xl mx-auto px-4 space-y-6">
        {!searchResult ? (
          <div className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-6">
            {/* Consent Box */}
            <label className="flex items-start gap-3 cursor-pointer p-4 rounded-xl bg-white/5 hover:bg-white/10 transition-colors border border-white/5">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-1 w-4 h-4 rounded border-slate-700 text-violet-600 focus:ring-violet-500"
              />
              <span className="text-xs text-white/70 leading-relaxed">
                I consent to the temporary processing of my facial features solely to search for photos of me from this event. My selfie will be processed in memory and immediately discarded, and will never be stored or enrolled.
              </span>
            </label>

            {/* Error Banner */}
            {searchError && (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3">
                <HiOutlineExclamationCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <p className="text-xs text-rose-300 leading-relaxed">{searchError}</p>
              </div>
            )}

            {/* Preview or Upload */}
            {previewUrl ? (
              <div className="space-y-4">
                <div className="relative aspect-[4/3] w-full max-w-sm mx-auto rounded-xl overflow-hidden border border-white/10 bg-black">
                  <img src={previewUrl} alt="Selfie preview" className="w-full h-full object-cover" />
                </div>

                <div className="flex gap-3 justify-center">
                  <button
                    onClick={handleSearch}
                    disabled={!consent || searching}
                    className="px-6 py-2.5 rounded-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-medium text-sm transition-colors flex items-center gap-2"
                  >
                    {searching ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Searching…
                      </>
                    ) : (
                      <>
                        <HiOutlinePhotograph className="w-5 h-5" />
                        Find My Photos
                      </>
                    )}
                  </button>

                  <button
                    onClick={handleReset}
                    disabled={searching}
                    className="px-4 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white/80 text-sm font-medium transition-colors"
                  >
                    Retake
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 border-2 border-dashed border-white/10 rounded-xl space-y-4">
                <div className="mx-auto w-12 h-12 rounded-full bg-violet-500/10 flex items-center justify-center">
                  <HiOutlineCamera className="w-6 h-6 text-violet-400" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-white">Upload a Selfie</p>
                  <p className="text-xs text-white/40">JPEG, PNG, or WebP up to 10MB</p>
                </div>

                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={!consent}
                  className="px-5 py-2.5 rounded-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white text-sm font-medium transition-colors inline-flex items-center gap-2"
                >
                  Choose File
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/heic"
                  className="hidden"
                  onChange={(e) => {
                    const selected = e.target.files?.[0];
                    if (selected) handleFileChange(selected);
                  }}
                />
              </div>
            )}
          </div>
        ) : (
          /* Results View */
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <HiOutlineCheckCircle className="w-5 h-5 text-emerald-400" />
                Found {searchResult.total} photo{searchResult.total !== 1 ? "s" : ""}
              </h2>
              <button
                onClick={handleReset}
                className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300 font-medium"
              >
                <HiOutlineRefresh className="w-4 h-4" />
                Search Again
              </button>
            </div>

            {searchResult.photos.length === 0 ? (
              <div className="text-center py-16 bg-white/5 border border-white/10 rounded-2xl space-y-3">
                <HiOutlinePhotograph className="w-10 h-10 text-white/20 mx-auto" />
                <h3 className="text-base font-semibold">No Matching Photos Found</h3>
                <p className="text-xs text-white/40 max-w-xs mx-auto">
                  We couldn&apos;t find matching photos. Try uploading another photo with clearer lighting or facing the camera directly.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                {searchResult.photos.map((photo, idx) => (
                  <button
                    key={photo.id}
                    onClick={() => setLightboxIndex(idx)}
                    className="aspect-square rounded-xl overflow-hidden relative group cursor-pointer bg-white/5 border border-white/5"
                  >
                    <img
                      src={photo.thumb_url.startsWith("http") ? photo.thumb_url : `${API_URL.replace("/api/v1", "")}${photo.thumb_url}`}
                      alt={`Match ${idx + 1}`}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Lightbox for selfie results */}
      {lightboxIndex !== null && searchResult && (
        <SelfieLightbox
          photos={searchResult.photos}
          currentIndex={lightboxIndex}
          sessionId={searchResult.session_id}
          onClose={() => setLightboxIndex(null)}
          onNavigate={setLightboxIndex}
        />
      )}
    </div>
  );
}

function SelfieLightbox({
  photos,
  currentIndex,
  sessionId,
  onClose,
  onNavigate,
}: {
  photos: PhotoItem[];
  currentIndex: number;
  sessionId: string;
  onClose: () => void;
  onNavigate: (idx: number) => void;
}) {
  const photo = photos[currentIndex];
  if (!photo) return null;

  const fullWebUrl = photo.web_url.startsWith("http") ? photo.web_url : `${API_URL.replace("/api/v1", "")}${photo.web_url}`;

  return (
    <div className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center" onClick={onClose}>
      <button onClick={onClose} className="absolute top-4 right-4 z-50 p-2 rounded-full bg-white/10 hover:bg-white/20">
        <HiOutlineX className="w-6 h-6" />
      </button>

      {currentIndex > 0 && (
        <button
          onClick={(e) => { e.stopPropagation(); onNavigate(currentIndex - 1); }}
          className="absolute left-4 z-50 p-2 rounded-full bg-white/10 hover:bg-white/20"
        >
          <HiOutlineChevronLeft className="w-6 h-6" />
        </button>
      )}
      {currentIndex < photos.length - 1 && (
        <button
          onClick={(e) => { e.stopPropagation(); onNavigate(currentIndex + 1); }}
          className="absolute right-4 z-50 p-2 rounded-full bg-white/10 hover:bg-white/20"
        >
          <HiOutlineChevronRight className="w-6 h-6" />
        </button>
      )}

      <div className="max-w-[90vw] max-h-[85vh] flex flex-col items-center gap-4" onClick={(e) => e.stopPropagation()}>
        <img src={fullWebUrl} alt={`Match ${currentIndex + 1}`} className="max-w-full max-h-[75vh] object-contain rounded-lg" />
        
        {/* Single photo download button */}
        <a
          href={`${API_URL}/public/photos/${photo.id}/download?session=${sessionId}`}
          onClick={(e) => e.stopPropagation()}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium transition-colors shadow-lg"
        >
          <HiOutlineDownload className="w-4 h-4" />
          Download Original
        </a>
      </div>
    </div>
  );
}
