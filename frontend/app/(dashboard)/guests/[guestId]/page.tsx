"use client";

import React, { use, useState, useEffect } from "react";
import { getGuestPhotos, updateMatchAction, Match } from "@/services/matches";
import { Photo } from "@/services/photos";
import { useAuthImage } from "@/hooks/useAuthImage";
import api from "@/lib/api";

function GuestPhotoItem({ photo }: { photo: Photo }) {
  const { objectUrl } = useAuthImage(`/media/photos/${photo.id}/thumb`);

  return (
    <div className="group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      <div className="aspect-square bg-slate-950 flex items-center justify-center overflow-hidden">
        {objectUrl ? (
          <img
            src={objectUrl}
            alt={photo.original_filename}
            className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
          />
        ) : (
          <div className="w-full h-full bg-slate-950 animate-pulse flex items-center justify-center text-xs text-slate-700">
            Loading...
          </div>
        )}
      </div>
      <div className="p-3 flex justify-between items-center bg-slate-900/90 border-t border-slate-800">
        <span className="text-xs text-slate-400 truncate max-w-[120px]">{photo.original_filename}</span>
      </div>
    </div>
  );
}

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

  const handleGenerateLink = async () => {
    try {
      // Find the guest's event_id first
      const guestRes = await api.get(`/guests/${guestId}`);
      const eventId = guestRes.data.event_id;
      
      const res = await api.post(`/events/${eventId}/guests/${guestId}/magic-link`);
      const link = res.data.portal_url;
      navigator.clipboard.writeText(link);
      alert(`Magic Link generated and copied to clipboard!\n\n${link}`);
    } catch (err) {
      console.error(err);
      alert("Failed to generate magic link. Make sure the event exists.");
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 text-slate-100">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Guest Matched Photos</h1>
          <p className="text-sm text-slate-400">Confirmed matched event photos for Guest ID: {guestId}</p>
        </div>
        <button 
          onClick={handleGenerateLink}
          className="bg-violet-600 hover:bg-violet-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
        >
          Generate & Copy Magic Link
        </button>
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
          {photos.map((photo) => (
            <GuestPhotoItem key={photo.id} photo={photo} />
          ))}
        </div>
      )}
    </div>
  );
}
