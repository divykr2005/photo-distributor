"use client";

import React, { useState, useEffect } from "react";
import { getClusters, getClusterDetails, PhotoCluster, excludePhoto, breakCluster } from "@/services/clusters";
import { Photo } from "@/services/photos";
import { useAuthImage } from "@/hooks/useAuthImage";

function ClusterPhotoItem({ photo, clusterId, onExclude }: { photo: Photo; clusterId: string; onExclude: () => void }) {
  const { objectUrl } = useAuthImage(`/media/photos/${photo.id}/thumb`);

  return (
    <div className="relative group bg-slate-900 border border-slate-700 rounded-lg overflow-hidden">
      <div className="aspect-square bg-slate-950 flex items-center justify-center overflow-hidden">
        {objectUrl ? (
          <img src={objectUrl} alt="Photo" className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="text-xs text-slate-500 animate-pulse">Loading...</div>
        )}
      </div>
      <div className="p-2 flex flex-col gap-2">
        <div className="text-[10px] text-slate-400 break-all">{photo.original_filename}</div>
        <button
          onClick={onExclude}
          className="w-full py-1 bg-slate-800 hover:bg-rose-600/80 text-white text-[10px] rounded transition"
        >
          Not a duplicate
        </button>
      </div>
    </div>
  );
}

export default function ClusterReviewModal({ eventId, onClose }: { eventId: string; onClose: () => void }) {
  const [clusters, setClusters] = useState<PhotoCluster[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeCluster, setActiveCluster] = useState<PhotoCluster | null>(null);
  const [activePhotos, setActivePhotos] = useState<Photo[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    fetchSuspiciousClusters();
  }, [eventId]);

  const fetchSuspiciousClusters = async () => {
    setLoading(true);
    try {
      const allClusters = await getClusters(eventId);
      // "suspicious clusters (size >= 8, or time span > 20s) for eyeballing"
      const suspicious = allClusters.filter(c => c.size >= 8 || (c.time_span_s && c.time_span_s > 20));
      setClusters(suspicious);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const viewCluster = async (cluster: PhotoCluster) => {
    setActiveCluster(cluster);
    setDetailLoading(true);
    try {
      const details = await getClusterDetails(eventId, cluster.id);
      setActivePhotos(details.photos);
    } catch (err) {
      console.error(err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleExclude = async (photoId: string) => {
    if (!activeCluster) return;
    try {
      await excludePhoto(eventId, activeCluster.id, photoId);
      setActivePhotos(prev => prev.filter(p => p.id !== photoId));
      if (activePhotos.length <= 2) {
        // Breaking the cluster essentially if it falls below 2
        setClusters(prev => prev.filter(c => c.id !== activeCluster.id));
        setActiveCluster(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleBreakCluster = async () => {
    if (!activeCluster) return;
    try {
      await breakCluster(eventId, activeCluster.id);
      setClusters(prev => prev.filter(c => c.id !== activeCluster.id));
      setActiveCluster(null);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
          <div>
            <h2 className="text-lg font-semibold text-white">Review Suspicious Clusters</h2>
            <p className="text-xs text-slate-400">Clusters with ≥8 photos or spanning &gt;20 seconds.</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition text-2xl leading-none">
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar: Cluster List */}
          <div className="w-1/3 border-r border-slate-800 overflow-y-auto bg-slate-900/30 p-4 space-y-3">
            {loading ? (
              <div className="text-sm text-slate-500 text-center py-10">Loading clusters...</div>
            ) : clusters.length === 0 ? (
              <div className="text-sm text-slate-500 text-center py-10">No suspicious clusters found.</div>
            ) : (
              clusters.map(c => (
                <div
                  key={c.id}
                  onClick={() => viewCluster(c)}
                  className={`p-3 rounded-xl border cursor-pointer transition ${
                    activeCluster?.id === c.id
                      ? "bg-indigo-600/20 border-indigo-500"
                      : "bg-slate-800 border-slate-700 hover:border-slate-500"
                  }`}
                >
                  <div className="font-medium text-sm text-white">Cluster ({c.size} photos)</div>
                  <div className="text-xs text-slate-400 mt-1">Span: {c.time_span_s?.toFixed(1) || 0}s</div>
                </div>
              ))
            )}
          </div>

          {/* Main Area: Photos in active cluster */}
          <div className="w-2/3 p-6 overflow-y-auto bg-slate-950">
            {activeCluster ? (
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <h3 className="text-md font-medium text-white">
                    Photos in Cluster <span className="text-slate-500 text-sm">({activePhotos.length})</span>
                  </h3>
                  <button
                    onClick={handleBreakCluster}
                    className="px-3 py-1.5 bg-rose-600/20 text-rose-400 hover:bg-rose-600 hover:text-white text-xs rounded-lg transition"
                  >
                    Break entire cluster
                  </button>
                </div>
                
                {detailLoading ? (
                  <div className="text-sm text-slate-500 text-center py-10">Loading photos...</div>
                ) : (
                  <div className="grid grid-cols-3 gap-4">
                    {activePhotos.map(p => (
                      <ClusterPhotoItem key={p.id} photo={p} clusterId={activeCluster.id} onExclude={() => handleExclude(p.id)} />
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-sm">
                Select a cluster from the sidebar to review its photos.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
