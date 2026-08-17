"use client";

import React, { useEffect, useState } from "react";
import { Photo } from "@/services/photos";
import { getClusterDetails, PhotoCluster } from "@/services/clusters";
import { useAuthImage } from "@/hooks/useAuthImage";
import PhotoDetailModal from "./PhotoDetailModal";

function BurstPhotoItem({ photo, onClick }: { photo: Photo; onClick: () => void }) {
  const { objectUrl } = useAuthImage(`/media/photos/${photo.id}/thumb`);

  return (
    <div
      onClick={onClick}
      className="group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden cursor-pointer hover:border-indigo-500/50 transition duration-200"
    >
      <div className="aspect-square bg-slate-950 flex items-center justify-center overflow-hidden">
        {objectUrl ? (
          <img src={objectUrl} alt="Burst photo" className="w-full h-full object-cover group-hover:scale-105 transition" loading="lazy" />
        ) : (
          <div className="text-xs text-slate-500 animate-pulse">Loading...</div>
        )}
      </div>
      {photo.is_cluster_representative && (
        <div className="absolute top-2 right-2 bg-indigo-600/90 text-white text-[10px] px-2 py-0.5 rounded-md border border-indigo-500 font-bold">
          Best
        </div>
      )}
    </div>
  );
}

export default function BurstModal({ cluster, eventId, onClose }: { cluster: PhotoCluster; eventId: string; onClose: () => void }) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);

  useEffect(() => {
    setLoading(true);
    getClusterDetails(eventId, cluster.id)
      .then(res => setPhotos(res.photos))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [cluster.id, eventId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
          <h2 className="text-lg font-semibold text-white">Burst ({cluster.size} photos)</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition text-2xl leading-none">
            &times;
          </button>
        </div>
        <div className="p-6 overflow-y-auto">
          {loading ? (
            <div className="text-center py-10 text-slate-400">Loading burst photos...</div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {photos.map(p => (
                <BurstPhotoItem key={p.id} photo={p} onClick={() => setSelectedPhoto(p)} />
              ))}
            </div>
          )}
        </div>
      </div>
      {selectedPhoto && <PhotoDetailModal photo={selectedPhoto} onClose={() => setSelectedPhoto(null)} />}
    </div>
  );
}
