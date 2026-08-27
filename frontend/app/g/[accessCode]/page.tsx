"use client";

import { useParams } from "next/navigation";
import { useState, useEffect, useCallback, useRef } from "react";
import {
  HiOutlinePhotograph,
  HiOutlineDownload,
  HiOutlineX,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlineCalendar,
  HiOutlineExclamationCircle,
} from "react-icons/hi";

import ZipDownloadButton from "@/components/portal/ZipDownloadButton";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/* ── Types ── */

interface PortalInfo {
  first_name: string;
  event_title: string;
  event_date: string;
  photo_count: number;
}

interface PhotoItem {
  id: string;
  thumb_url: string;
  web_url: string;
  taken_at: string | null;
  filename: string | null;
}

interface PhotosResponse {
  photos: PhotoItem[];
  total: number;
  next_cursor: string | null;
}

type PortalState = "loading" | "ready" | "empty" | "expired" | "invalid" | "error";

/* ── Skeleton loader ── */

function PhotoSkeleton() {
  return (
    <div className="aspect-square rounded-xl bg-white/5 animate-pulse" />
  );
}

/* ── Lightbox ── */

interface LightboxProps {
  photos: PhotoItem[];
  currentIndex: number;
  accessCode: string;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

function Lightbox({ photos, currentIndex, accessCode, onClose, onNavigate }: LightboxProps) {
  const photo = photos[currentIndex];

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && currentIndex > 0) onNavigate(currentIndex - 1);
      if (e.key === "ArrowRight" && currentIndex < photos.length - 1) onNavigate(currentIndex + 1);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [currentIndex, photos.length, onClose, onNavigate]);

  // Swipe detection for mobile
  const touchStart = useRef<number | null>(null);
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStart.current = e.touches[0].clientX;
  };
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStart.current === null) return;
    const diff = touchStart.current - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 60) {
      if (diff > 0 && currentIndex < photos.length - 1) onNavigate(currentIndex + 1);
      if (diff < 0 && currentIndex > 0) onNavigate(currentIndex - 1);
    }
    touchStart.current = null;
  };

  if (!photo) return null;

  const fullWebUrl = photo.web_url.startsWith("http") ? photo.web_url : `${API_URL.replace("/api/v1", "")}${photo.web_url}`;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
      onClick={onClose}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 z-50 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
        aria-label="Close"
      >
        <HiOutlineX className="w-6 h-6" />
      </button>

      {/* Counter */}
      <div className="absolute top-4 left-4 z-50 text-sm text-white/60 bg-black/40 px-3 py-1.5 rounded-full backdrop-blur-sm font-medium tracking-wide">
        {currentIndex + 1} / {photos.length}
      </div>

      {/* Nav arrows */}
      {currentIndex > 0 && (
        <button
          onClick={(e) => { e.stopPropagation(); onNavigate(currentIndex - 1); }}
          className="absolute left-2 md:left-6 z-50 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
          aria-label="Previous"
        >
          <HiOutlineChevronLeft className="w-6 h-6" />
        </button>
      )}
      {currentIndex < photos.length - 1 && (
        <button
          onClick={(e) => { e.stopPropagation(); onNavigate(currentIndex + 1); }}
          className="absolute right-2 md:right-6 z-50 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
          aria-label="Next"
        >
          <HiOutlineChevronRight className="w-6 h-6" />
        </button>
      )}

      {/* Image */}
      <div className="max-w-[90vw] max-h-[85vh] flex flex-col items-center justify-center gap-3" onClick={(e) => e.stopPropagation()}>
        <img
          src={fullWebUrl}
          alt={photo.filename || `Photo ${currentIndex + 1}`}
          className="max-w-full max-h-[75vh] object-contain rounded-lg select-none"
          draggable={false}
        />
        {/* Per-photo metadata — Day 16 spec */}
        <div className="flex items-center gap-3 text-white/50 text-xs tracking-wide">
          {photo.filename && (
            <span className="truncate max-w-[200px]" title={photo.filename}>{photo.filename}</span>
          )}
          {photo.filename && photo.taken_at && <span>•</span>}
          {photo.taken_at && (
            <span>
              {new Date(photo.taken_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          )}
        </div>
      </div>

      {/* Download button */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-50">
        <a
          href={`${API_URL}/public/photos/${photo.id}/download?token=${accessCode}`}
          onClick={(e) => e.stopPropagation()}
          className="flex items-center gap-2 px-6 py-3 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-all shadow-[0_0_15px_-3px_rgba(99,102,241,0.4)] hover:shadow-[0_0_20px_-3px_rgba(99,102,241,0.6)] border border-indigo-500/50 hover:scale-[1.02] active:scale-95"
        >
          <HiOutlineDownload className="w-5 h-5" />
          Download Photo
        </a>
      </div>
    </div>
  );
}

/* ── Main Page ── */

export default function GuestPortalPage() {
  const { accessCode } = useParams<{ accessCode: string }>();
  const [state, setState] = useState<PortalState>("loading");
  const [info, setInfo] = useState<PortalInfo | null>(null);
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [showAll, setShowAll] = useState<boolean>(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // Fetch portal info
  useEffect(() => {
    if (!accessCode) return;

    fetch(`${API_URL}/public/guest/${accessCode}`)
      .then(async (res) => {
        if (res.status === 410) { setState("expired"); return null; }
        if (res.status === 404) { setState("invalid"); return null; }
        if (!res.ok) { setState("error"); return null; }
        return res.json();
      })
      .then((data: PortalInfo | null) => {
        if (!data) return;
        setInfo(data);
        if (data.photo_count === 0) {
          setState("empty");
        } else {
          setState("ready");
          fetchPhotos();
        }
      })
      .catch(() => setState("error"));
  }, [accessCode]);

  // Fetch photos page
  const fetchPhotos = useCallback(
    async (cursor?: string, currentShowAll: boolean = false) => {
      if (!accessCode) return;
      
      const params = new URLSearchParams();
      if (cursor) params.append("cursor", cursor);
      if (currentShowAll) params.append("show_all", "true");
      
      const qs = params.toString();
      const url = `${API_URL}/public/guest/${accessCode}/photos${qs ? `?${qs}` : ""}`;
      try {
        const res = await fetch(url);
        if (!res.ok) return;
        const data: PhotosResponse = await res.json();
        setPhotos((prev) => cursor ? [...prev, ...data.photos] : data.photos);
        setNextCursor(data.next_cursor);
      } catch {
        // silent
      }
    },
    [accessCode]
  );

  // Initial load or toggle change
  useEffect(() => {
    if (state === "ready") {
      setPhotos([]);
      setNextCursor(null);
      fetchPhotos(undefined, showAll);
    }
  }, [showAll, state, fetchPhotos]);

  // Infinite scroll via IntersectionObserver
  useEffect(() => {
    if (!sentinelRef.current || !nextCursor) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && nextCursor && !loadingMore) {
          setLoadingMore(true);
          fetchPhotos(nextCursor, showAll).finally(() => setLoadingMore(false));
        }
      },
      { rootMargin: "200px" }
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [nextCursor, loadingMore, fetchPhotos]);

  // ── Render states ──

  if (state === "loading") {
    return (
      <div className="min-h-screen flex flex-col">
        {/* Skeleton header */}
        <div className="px-4 pt-8 pb-6 text-center space-y-3">
          <div className="h-4 w-48 bg-white/5 rounded-full mx-auto animate-pulse" />
          <div className="h-8 w-64 bg-white/5 rounded-full mx-auto animate-pulse" />
          <div className="h-4 w-32 bg-white/5 rounded-full mx-auto animate-pulse" />
        </div>
        <div className="px-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          {Array.from({ length: 12 }).map((_, i) => (
            <PhotoSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (state === "expired") {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center space-y-4 max-w-sm">
          <div className="mx-auto w-16 h-16 rounded-full bg-amber-500/10 flex items-center justify-center border border-amber-500/20">
            <HiOutlineCalendar className="w-8 h-8 text-amber-400" />
          </div>
          <h1 className="text-xl font-semibold text-white tracking-tight">Link Expired</h1>
          <p className="text-zinc-400 text-sm leading-relaxed">
            This photo link has expired. Please contact your event organizer for a new one.
          </p>
        </div>
      </div>
    );
  }

  if (state === "invalid") {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center space-y-4 max-w-sm">
          <div className="mx-auto w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/20">
            <HiOutlineExclamationCircle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="text-xl font-semibold text-white tracking-tight">Link Not Found</h1>
          <p className="text-zinc-400 text-sm leading-relaxed">
            This photo link is invalid. Please check the link or contact your event organizer.
          </p>
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center space-y-4 max-w-sm">
          <div className="mx-auto w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/20">
            <HiOutlineExclamationCircle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="text-xl font-semibold text-white tracking-tight">Something Went Wrong</h1>
          <p className="text-zinc-400 text-sm leading-relaxed">
            We couldn't load your photos. Please try again later or check your connection.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-all shadow-lg shadow-indigo-600/20"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (state === "empty") {
    return (
      <div className="min-h-screen flex flex-col">
        {info && <PortalHeader info={info} accessCode={accessCode} />}
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="text-center space-y-4 max-w-sm">
            <div className="mx-auto w-16 h-16 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
              <HiOutlinePhotograph className="w-8 h-8 text-indigo-400" />
            </div>
            <h2 className="text-xl font-medium text-white tracking-tight">No Photos Yet</h2>
            <p className="text-zinc-400 text-sm leading-relaxed">
              No photos have been matched to you yet — check back after the photographer uploads.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ── Ready state: gallery ──
  return (
    <div className="min-h-screen flex flex-col pb-8">
      {info && <PortalHeader info={info} accessCode={accessCode} />}

      {/* Gallery Controls */}
      <div className="px-4 py-4 flex justify-end">
        <label className="flex items-center gap-2 text-sm text-zinc-400 cursor-pointer hover:text-white transition-colors group">
          <input 
            type="checkbox" 
            checked={showAll} 
            onChange={(e) => setShowAll(e.target.checked)}
            className="rounded bg-zinc-800 border-zinc-700 text-indigo-500 focus:ring-indigo-500/50 w-4 h-4"
          />
          <span className="font-medium group-hover:text-zinc-200">Show all similar photos</span>
        </label>
      </div>

      {/* Photo grid */}
      <div className="px-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 sm:gap-3">
        {photos.map((photo, idx) => (
          <PhotoTile
            key={photo.id}
            photo={photo}
            index={idx}
            accessCode={accessCode}
            onClick={() => setLightboxIndex(idx)}
          />
        ))}
      </div>

      {/* Infinite-scroll sentinel */}
      {nextCursor && (
        <div ref={sentinelRef} className="flex justify-center py-8">
          <div className="flex items-center gap-2 text-zinc-500 text-sm font-medium">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading more photos...
          </div>
        </div>
      )}

      {/* Lightbox */}
      {lightboxIndex !== null && (
        <Lightbox
          photos={photos}
          currentIndex={lightboxIndex}
          accessCode={accessCode}
          onClose={() => setLightboxIndex(null)}
          onNavigate={setLightboxIndex}
        />
      )}
    </div>
  );
}

/* ── Header component ── */

function PortalHeader({ info, accessCode }: { info: PortalInfo; accessCode: string }) {
  const eventDate = new Date(info.event_date);
  const formattedDate = eventDate.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <header className="px-4 pt-10 pb-6 text-center space-y-3 border-b border-white/5 bg-zinc-950/50 backdrop-blur-md sticky top-0 z-40">
      <p className="text-indigo-400 text-xs font-semibold tracking-widest uppercase">
        {info.event_title}
      </p>
      <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
        Hi {info.first_name} 👋
      </h1>
      <div className="flex items-center justify-center gap-3 text-zinc-400 text-sm font-medium pt-1">
        <span className="flex items-center gap-1.5">
          <HiOutlineCalendar className="w-4 h-4" />
          {formattedDate}
        </span>
        <span className="text-zinc-600">•</span>
        <span className="flex items-center gap-1.5 text-zinc-300 bg-white/5 px-2.5 py-1 rounded-full border border-white/5">
          <HiOutlinePhotograph className="w-4 h-4" />
          {info.photo_count} photo{info.photo_count !== 1 ? "s" : ""}
        </span>
      </div>

      {info.photo_count > 0 && (
        <div className="pt-4 flex justify-center">
          <ZipDownloadButton accessCode={accessCode} photoCount={info.photo_count} />
        </div>
      )}
    </header>
  );
}

/* ── Photo tile ── */

function PhotoTile({
  photo,
  index,
  accessCode,
  onClick,
}: {
  photo: PhotoItem;
  index: number;
  accessCode: string;
  onClick: () => void;
}) {
  const [loaded, setLoaded] = useState(false);
  const thumbUrl = photo.thumb_url.startsWith("http")
    ? photo.thumb_url
    : `${API_URL.replace("/api/v1", "")}${photo.thumb_url}`;

  return (
    <button
      onClick={onClick}
      className="aspect-square rounded-xl overflow-hidden relative group cursor-pointer bg-zinc-900 border border-zinc-800 focus:outline-none focus:ring-4 focus:ring-indigo-500/30 shadow-sm hover:shadow-lg transition-all"
    >
      {!loaded && (
        <div className="absolute inset-0 bg-zinc-800 animate-pulse" />
      )}
      <img
        src={thumbUrl}
        alt={`Photo ${index + 1}`}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        className={`w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.03] ${loaded ? "opacity-100" : "opacity-0"}`}
      />
      {/* Hover overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3">
         <span className="text-white text-xs font-medium translate-y-2 group-hover:translate-y-0 transition-transform duration-300 flex items-center gap-1">
           <HiOutlinePhotograph className="w-4 h-4 opacity-70"/> View Full
         </span>
      </div>
    </button>
  );
}
