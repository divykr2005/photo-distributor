"use client";

import React, { useState, useEffect } from "react";
import { getEventPhotos, Photo } from "@/services/photos";
import PhotoDetailModal from "./PhotoDetailModal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function PhotoGrid({ eventId }: { eventId: string }) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [zeroFaceFilter, setZeroFaceFilter] = useState<string>("");
  const [nextCursor, setNextCursor] = useState<string | undefined>(undefined);
  const [hasMore, setHasMore] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchPhotos = async (reset = false) => {
    setLoading(true);
    try {
      const res = await getEventPhotos(eventId, {
        status: statusFilter || undefined,
        face_count_zero: zeroFaceFilter === "zero" ? true : zeroFaceFilter === "faces" ? false : undefined,
        cursor: reset ? undefined : nextCursor,
        limit: 40,
      });

      if (reset) {
        setPhotos(res.data);
      } else {
        setPhotos((prev) => [...prev, ...res.data]);
      }
      setNextCursor(res.next_cursor);
      setHasMore(res.has_more);
    } catch (err) {
      console.error("Failed to fetch photos", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPhotos(true);
  }, [eventId, statusFilter, zeroFaceFilter]);

  return (
    <div className="space-y-6 text-slate-100">
      {/* Controls & Filters */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-slate-900 border border-slate-800 rounded-xl">
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-400 font-medium">Status Filter:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs rounded-lg px-3 py-1.5 text-white"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="processed">Processed</option>
            <option value="failed">Failed</option>
          </select>

          <label className="text-xs text-slate-400 font-medium ml-2">Faces Filter:</label>
          <select
            value={zeroFaceFilter}
            onChange={(e) => setZeroFaceFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs rounded-lg px-3 py-1.5 text-white"
          >
            <option value="">All Photos</option>
            <option value="faces">Has Faces</option>
            <option value="zero">Zero Faces Found</option>
          </select>
        </div>

        <button
          onClick={() => fetchPhotos(true)}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded-lg font-medium transition"
        >
          Refresh Grid
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {photos.map((photo) => {
          const thumbUrl = `${API_URL}/media/photos/${photo.id}/thumb`;
          return (
            <div
              key={photo.id}
              onClick={() => setSelectedPhoto(photo)}
              className="group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden cursor-pointer hover:border-indigo-500/50 transition duration-200 shadow-md hover:shadow-indigo-500/10"
            >
              <div className="aspect-square bg-slate-950 flex items-center justify-center overflow-hidden">
                <img
                  src={thumbUrl}
                  alt={photo.original_filename}
                  loading="lazy"
                  className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = "none";
                  }}
                />
              </div>

              {/* Status Badge */}
              <div className="absolute top-2 left-2 flex items-center gap-1 bg-slate-950/80 backdrop-blur-sm px-2 py-0.5 rounded-md text-[10px] border border-slate-800 font-mono">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    photo.status === "processed"
                      ? "bg-emerald-400"
                      : photo.status === "failed"
                      ? "bg-rose-400"
                      : "bg-amber-400"
                  }`}
                />
                <span className="capitalize">{photo.status}</span>
              </div>

              {/* Faces count pill */}
              <div className="absolute bottom-2 right-2 bg-slate-950/90 text-white text-[10px] px-2 py-0.5 rounded-md border border-slate-800 font-semibold">
                👤 {photo.face_count}
              </div>
            </div>
          );
        })}
      </div>

      {/* Load More Button */}
      {hasMore && (
        <div className="text-center pt-4">
          <button
            onClick={() => fetchPhotos(false)}
            disabled={loading}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition"
          >
            {loading ? "Loading..." : "Load More Photos"}
          </button>
        </div>
      )}

      {selectedPhoto && (
        <PhotoDetailModal photo={selectedPhoto} onClose={() => setSelectedPhoto(null)} />
      )}
    </div>
  );
}
