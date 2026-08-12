"use client";

import React, { use, useState, useEffect } from "react";
import { getGuestPhotos, updateMatchAction, Match } from "@/services/matches";
import { Photo } from "@/services/photos";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function GuestDetailPage({ params }: { params: Promise<{ guestId: string }> }) {
  const { guestId } = use(params);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMatchedPhotos = async () => {
    setLoading(true);
    try {
      const data = await getGuestPhotos(guestId);
      setPhotos(data);
    } catch (err) {
      console.error("Failed to fetch guest photos", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatchedPhotos();
  }, [guestId]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 text-slate-100">
      <div>
        <h1 className="text-2xl font-bold text-white">Guest Matched Photos</h1>
        <p className="text-sm text-slate-400">Confirmed matched event photos for Guest ID: {guestId}</p>
      </div>

      {loading ? (
        <div className="p-8 text-center text-slate-400">Loading matched photos...</div>
      ) : photos.length === 0 ? (
        <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl space-y-2">
          <p className="text-lg font-semibold text-slate-300">No confirmed matched photos found.</p>
          <p className="text-xs text-slate-500">Matches must be in auto_confirmed decision to appear in guest gallery.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {photos.map((photo) => {
            const thumbUrl = `${API_URL}/media/photos/${photo.id}/thumb`;
            return (
              <div
                key={photo.id}
                className="group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg"
              >
                <div className="aspect-square bg-slate-950 flex items-center justify-center overflow-hidden">
                  <img
                    src={thumbUrl}
                    alt={photo.original_filename}
                    className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                  />
                </div>
                <div className="p-3 flex justify-between items-center bg-slate-900/90 border-t border-slate-800">
                  <span className="text-xs text-slate-400 truncate max-w-[120px]">{photo.original_filename}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
