"use client";

import React, { useState, useEffect } from "react";
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

export default function GuestDetailPage({ params }: { params: { guestId: string } }) {
  const { guestId } = params;
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [guest, setGuest] = useState<any>(null);
  
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    email: ""
  });
  const [etag, setEtag] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const fetchGuestData = async () => {
    try {
      const res = await api.get(`/guests/${guestId}`);
      setGuest(res.data);
      setEditForm({
        first_name: res.data.first_name || "",
        last_name: res.data.last_name || "",
        phone: res.data.phone || "",
        email: res.data.email || ""
      });
      if (res.data.updated_at) {
        setEtag(new Date(res.data.updated_at).getTime() / 1000 + "");
      }
    } catch (err) {
      console.error("Failed to fetch guest details", err);
    }
  };

  const fetchMatchedPhotos = async () => {
    try {
      const data = await getGuestPhotos(guestId);
      setPhotos(data);
    } catch (err) {
      console.error("Failed to fetch guest photos", err);
    }
  };

  const loadAllData = async () => {
    setLoading(true);
    await Promise.all([fetchGuestData(), fetchMatchedPhotos()]);
    setLoading(false);
  };

  useEffect(() => {
    loadAllData();
  }, [guestId]);

  const handleGenerateLink = async () => {
    try {
      if (!guest) return;
      const res = await api.post(`/events/${guest.event_id}/guests/${guestId}/magic-link`);
      const link = res.data.portal_url;
      navigator.clipboard.writeText(link);
      alert(`Magic Link generated and copied to clipboard!\n\n${link}`);
    } catch (err) {
      console.error(err);
      alert("Failed to generate magic link.");
    }
  };

  const handleUpdateGuest = async (e: React.FormEvent) => {
    e.preventDefault();
    setUpdateError(null);
    try {
      const headers: Record<string, string> = {};
      if (etag) {
        headers["If-Match"] = `"${etag}"`;
      }
      const res = await api.put(`/guests/${guestId}`, editForm, { headers });
      setGuest(res.data);
      if (res.data.updated_at) {
        setEtag(new Date(res.data.updated_at).getTime() / 1000 + "");
      }
      setIsEditing(false);
    } catch (err: any) {
      console.error(err);
      if (err.response?.status === 412) {
        setUpdateError("This guest was modified by someone else. Please refresh and try again.");
      } else {
        setUpdateError("Failed to update guest.");
      }
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 text-slate-100">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Guest Detail</h1>
          <p className="text-sm text-slate-400">ID: {guestId}</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={async () => {
              if (window.confirm("Are you sure you want to delete this guest? This will delete their registration photo and embeddings.")) {
                try {
                  await api.delete(`/guests/${guestId}`);
                  window.location.href = "/guests";
                } catch (err) {
                  alert("Failed to delete guest");
                }
              }
            }}
            className="bg-red-900/50 border border-red-800 text-red-200 hover:bg-red-900/70 hover:text-white px-4 py-2 rounded-lg text-sm font-medium transition"
          >
            Delete Guest
          </button>
          <button 
            onClick={handleGenerateLink}
            disabled={!guest}
            className="bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
          >
            Generate & Copy Magic Link
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-slate-400">Loading guest data...</div>
      ) : (
        <>
          {guest && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Guest Information</h2>
                {!isEditing && (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="text-sm text-violet-400 hover:text-violet-300"
                  >
                    Edit
                  </button>
                )}
              </div>

              {isEditing ? (
                <form onSubmit={handleUpdateGuest} className="space-y-4">
                  {updateError && (
                    <div className="bg-red-900/50 text-red-200 p-3 rounded-lg text-sm">
                      {updateError}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1">First Name</label>
                      <input
                        type="text"
                        value={editForm.first_name}
                        onChange={(e) => setEditForm({...editForm, first_name: e.target.value})}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-violet-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1">Last Name</label>
                      <input
                        type="text"
                        value={editForm.last_name}
                        onChange={(e) => setEditForm({...editForm, last_name: e.target.value})}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-violet-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1">Phone</label>
                      <input
                        type="text"
                        value={editForm.phone}
                        onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-violet-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1">Email</label>
                      <input
                        type="email"
                        value={editForm.email}
                        onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-violet-500"
                      />
                    </div>
                  </div>
                  <div className="flex gap-3 justify-end pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        setIsEditing(false);
                        setUpdateError(null);
                        setEditForm({
                          first_name: guest.first_name || "",
                          last_name: guest.last_name || "",
                          phone: guest.phone || "",
                          email: guest.email || ""
                        });
                      }}
                      className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="bg-violet-600 hover:bg-violet-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
                    >
                      Save Changes
                    </button>
                  </div>
                </form>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-slate-400">Name</p>
                    <p className="text-lg">{guest.first_name} {guest.last_name}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-400">Phone</p>
                    <p className="text-lg">{guest.phone}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-400">Email</p>
                    <p className="text-lg">{guest.email || "N/A"}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-400">Status</p>
                    <p className="text-lg">{guest.embedding_status}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          <div>
            <h2 className="text-xl font-semibold mb-4">Confirmed Matched Photos</h2>
            {photos.length === 0 ? (
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
        </>
      )}
    </div>
  );
}
