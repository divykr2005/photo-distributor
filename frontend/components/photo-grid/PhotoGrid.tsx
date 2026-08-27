"use client";

import React, { useState, useEffect } from "react";
import { getEventPhotos, Photo } from "@/services/photos";
import PhotoDetailModal from "./PhotoDetailModal";
import { useAuthImage } from "@/hooks/useAuthImage";
import { getClusters, PhotoCluster, runDeduplication } from "@/services/clusters";
import ClusterReviewModal from "./ClusterReviewModal";
import BurstModal from "./BurstModal";

function PhotoGridItem({ photo, cluster, onClick, selected, onSelectToggle }: { photo: Photo; cluster?: PhotoCluster; onClick: () => void; selected?: boolean; onSelectToggle?: (selected: boolean) => void }) {
  const { objectUrl } = useAuthImage(`/media/photos/${photo.id}/thumb`);

  return (
    <div
      onClick={onClick}
      className="group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden cursor-pointer hover:border-indigo-500/50 transition duration-200 shadow-md hover:shadow-indigo-500/10"
    >
      <div className="aspect-square bg-slate-950 flex items-center justify-center overflow-hidden">
        {objectUrl ? (
          <img
            src={objectUrl}
            alt={photo.original_filename}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
          />
        ) : (
          <div className="w-full h-full bg-slate-950 animate-pulse flex items-center justify-center text-slate-700 text-xs">
            Loading...
          </div>
        )}
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

      {/* Cluster Badge */}
      {cluster && cluster.size > 1 && (
        <div className="absolute top-2 right-2 flex items-center gap-1 bg-indigo-600/90 backdrop-blur-sm px-2 py-0.5 rounded-md text-[10px] border border-indigo-500 font-bold text-white shadow-md">
          ×{cluster.size}
        </div>
      )}

      {/* Selection Checkbox */}
      {onSelectToggle && (
        <div 
          className="absolute top-2 right-2 z-10" 
          onClick={(e) => { e.stopPropagation(); onSelectToggle(!selected); }}
        >
          <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${selected ? 'bg-indigo-500 border-indigo-500' : 'bg-slate-900/50 border-slate-400 hover:border-slate-300'}`}>
            {selected && <span className="text-white text-xs">✓</span>}
          </div>
        </div>
      )}
    </div>
  );
}

export default function PhotoGrid({ eventId }: { eventId: string }) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [zeroFaceFilter, setZeroFaceFilter] = useState<string>("");
  const [nextCursor, setNextCursor] = useState<string | undefined>(undefined);
  const [hasMore, setHasMore] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  const [loading, setLoading] = useState(false);
  const [groupDuplicates, setGroupDuplicates] = useState(false);
  const [clustersMap, setClustersMap] = useState<Record<string, PhotoCluster>>({});
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [activeBurst, setActiveBurst] = useState<PhotoCluster | null>(null);
  const [dedupRunning, setDedupRunning] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectionMode, setSelectionMode] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchPhotos = async (reset = false) => {
    setLoading(true);
    try {
      const res = await getEventPhotos(eventId, {
        status: statusFilter || undefined,
        face_count_zero: zeroFaceFilter === "zero" ? true : zeroFaceFilter === "faces" ? false : undefined,
        group_duplicates: groupDuplicates ? true : undefined,
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
  }, [eventId, statusFilter, zeroFaceFilter, groupDuplicates]);

  useEffect(() => {
    if (groupDuplicates) {
      getClusters(eventId).then(clusters => {
        const cmap: Record<string, PhotoCluster> = {};
        clusters.forEach(c => cmap[c.id] = c);
        setClustersMap(cmap);
      }).catch(console.error);
    } else {
      setClustersMap({});
    }
  }, [groupDuplicates, eventId]);

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

        <div className="flex items-center gap-3 ml-auto">
          <label className="flex items-center gap-2 text-xs text-slate-300 font-medium cursor-pointer bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 hover:bg-slate-900 transition">
            <input 
              type="checkbox" 
              checked={groupDuplicates} 
              onChange={e => setGroupDuplicates(e.target.checked)}
              className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-600 bg-slate-900"
            />
            Group Duplicates
          </label>
          <button
            onClick={async () => {
              setDedupRunning(true);
              try {
                await runDeduplication(eventId);
                alert("Deduplication started in background. Refresh the grid in a few seconds.");
              } catch (e) {
                console.error(e);
              } finally {
                setDedupRunning(false);
              }
            }}
            disabled={dedupRunning}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs rounded-lg font-medium transition"
          >
            {dedupRunning ? "Running..." : "Run Dedup"}
          </button>
          <button
            onClick={() => setReviewModalOpen(true)}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded-lg font-medium transition shadow-md shadow-indigo-500/20"
          >
            Review Clusters
          </button>
          <button
            onClick={() => {
              if (selectionMode) {
                setSelectionMode(false);
                setSelectedIds(new Set());
              } else {
                setSelectionMode(true);
              }
            }}
            className={`px-3 py-1.5 text-white text-xs rounded-lg font-medium transition shadow-md ${selectionMode ? 'bg-slate-600 hover:bg-slate-500' : 'bg-slate-800 hover:bg-slate-700'}`}
          >
            {selectionMode ? "Cancel Selection" : "Select Photos"}
          </button>
          <button
            onClick={() => fetchPhotos(true)}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded-lg font-medium transition"
          >
            Refresh Grid
          </button>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {photos.map((photo) => (
          <PhotoGridItem
            key={photo.id}
            photo={photo}
            cluster={photo.dup_cluster_id ? clustersMap[photo.dup_cluster_id] : undefined}
            selected={selectedIds.has(photo.id)}
            onSelectToggle={selectionMode ? (sel) => {
              const next = new Set(selectedIds);
              if (sel) next.add(photo.id); else next.delete(photo.id);
              setSelectedIds(next);
            } : undefined}
            onClick={() => {
              if (selectionMode) {
                const next = new Set(selectedIds);
                if (next.has(photo.id)) next.delete(photo.id); else next.add(photo.id);
                setSelectedIds(next);
                return;
              }
              const cluster = photo.dup_cluster_id ? clustersMap[photo.dup_cluster_id] : undefined;
              if (groupDuplicates && cluster && cluster.size > 1) {
                setActiveBurst(cluster);
              } else {
                setSelectedPhoto(photo);
              }
            }}
          />
        ))}
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
      {reviewModalOpen && (
        <ClusterReviewModal eventId={eventId} onClose={() => setReviewModalOpen(false)} />
      )}
      {activeBurst && (
        <BurstModal cluster={activeBurst} eventId={eventId} onClose={() => setActiveBurst(null)} />
      )}

      {/* Floating Action Bar for Bulk Selection */}
      {selectionMode && selectedIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-slate-900 border border-slate-700 shadow-2xl rounded-2xl px-6 py-4 flex items-center gap-6 z-50">
          <div className="text-sm font-medium text-white">{selectedIds.size} photos selected</div>
          <button
            onClick={async () => {
              if (!confirm(`Are you sure you want to delete ${selectedIds.size} photos permanently?`)) return;
              setDeleting(true);
              try {
                await fetch(`/api/v1/events/${eventId}/photos/bulk-delete`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ photo_ids: Array.from(selectedIds) })
                });
                setSelectionMode(false);
                setSelectedIds(new Set());
                fetchPhotos(true);
              } catch (e) {
                console.error(e);
                alert("Failed to delete photos.");
              } finally {
                setDeleting(false);
              }
            }}
            disabled={deleting}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-sm rounded-lg font-semibold transition"
          >
            {deleting ? "Deleting..." : "Delete Selected"}
          </button>
        </div>
      )}
    </div>
  );
}
