"use client";

import React, { useState, useEffect } from "react";
import { getEventMatches, updateMatchAction, manualAssignMatch, Match } from "@/services/matches";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function ReviewQueue({ eventId }: { eventId: string }) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const data = await getEventMatches(eventId, { decision: "review", status: "active", limit: 100 });
      setMatches(data);
      setCurrentIndex(0);
    } catch (err) {
      console.error("Failed to fetch review queue", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [eventId]);

  const currentMatch = matches[currentIndex];

  const handleConfirm = async () => {
    if (!currentMatch) return;
    try {
      await updateMatchAction(currentMatch.id, "confirm");
      advance();
    } catch (err) {
      console.error("Failed to confirm match", err);
    }
  };

  const handleReject = async () => {
    if (!currentMatch) return;
    try {
      await updateMatchAction(currentMatch.id, "reject");
      advance();
    } catch (err) {
      console.error("Failed to reject match", err);
    }
  };

  const advance = () => {
    setMatches((prev) => prev.filter((_, idx) => idx !== currentIndex));
  };

  // Keyboard navigation shortcuts (ArrowLeft, ArrowRight, Enter, R)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") {
        setCurrentIndex((prev) => Math.max(0, prev - 1));
      } else if (e.key === "ArrowRight") {
        setCurrentIndex((prev) => Math.min(matches.length - 1, prev + 1));
      } else if (e.key === "Enter") {
        handleConfirm();
      } else if (e.key === "r" || e.key === "R") {
        handleReject();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentMatch, matches]);

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Loading review queue...</div>;
  }

  if (!currentMatch || matches.length === 0) {
    return (
      <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl space-y-3">
        <p className="text-xl font-bold text-emerald-400">🎉 Review Queue Empty!</p>
        <p className="text-sm text-slate-400">All uncertain matches have been reviewed for this event.</p>
        <button
          onClick={fetchQueue}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs rounded-lg font-medium text-white transition"
        >
          Check Again
        </button>
      </div>
    );
  }

  const cropUrl = `${API_URL}/media/faces/${currentMatch.photo_face_id}`;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 max-w-3xl mx-auto space-y-6 shadow-2xl">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white">Uncertain Match Review Queue</h2>
          <p className="text-xs text-slate-400">Item {currentIndex + 1} of {matches.length} pending review</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
          <span className="px-2 py-1 bg-slate-800 rounded">← Prev</span>
          <span className="px-2 py-1 bg-slate-800 rounded">→ Next</span>
          <span className="px-2 py-1 bg-emerald-900/40 text-emerald-300 rounded">Enter (Confirm)</span>
          <span className="px-2 py-1 bg-rose-900/40 text-rose-300 rounded">R (Reject)</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        {/* Detected Face Crop */}
        <div className="flex flex-col items-center bg-black/60 p-6 rounded-xl border border-slate-800">
          <img
            src={cropUrl}
            alt="Face Crop"
            className="w-48 h-48 object-cover rounded-xl border-2 border-slate-700 shadow-lg"
          />
          <div className="mt-4 text-center text-xs space-y-1">
            <p className="text-slate-400">Review Reason:</p>
            <span className="px-2 py-0.5 bg-amber-950 text-amber-300 border border-amber-800/50 rounded-full font-mono uppercase font-semibold">
              {currentMatch.review_reason || "uncertain"}
            </span>
          </div>
        </div>

        {/* Candidate Breakdown */}
        <div className="space-y-4">
          <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
            <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase">Top Candidate</span>
            <div className="flex justify-between items-center">
              <span className="font-semibold text-lg text-white">Guest ID: {currentMatch.guest_id.substring(0, 8)}...</span>
              <span className="text-xl font-bold text-indigo-400">{(currentMatch.similarity * 100).toFixed(1)}%</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-2">
              <span>Top-2 Margin: <strong className="text-amber-400">{((currentMatch.margin || 0) * 100).toFixed(1)}%</strong></span>
              <span>2nd Score: {((currentMatch.second_similarity || 0) * 100).toFixed(1)}%</span>
            </div>
          </div>

          {currentMatch.top_candidates && currentMatch.top_candidates.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-semibold text-slate-400">Top 3 Candidate Breakdown</span>
              {currentMatch.top_candidates.map((cand, idx) => (
                <div key={idx} className="flex justify-between items-center px-3 py-1.5 bg-slate-800/40 rounded border border-slate-800 text-xs">
                  <span className="text-slate-300">#{cand.rank} Guest {cand.guest_id.substring(0, 6)}...</span>
                  <span className="font-mono text-indigo-300 font-semibold">{(cand.score * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Review Actions */}
      <div className="flex gap-4 pt-4 border-t border-slate-800">
        <button
          onClick={handleReject}
          className="flex-1 py-3 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 rounded-xl font-semibold text-sm transition"
        >
          Reject Match (R)
        </button>
        <button
          onClick={handleConfirm}
          className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-semibold text-sm transition shadow-lg shadow-emerald-600/20"
        >
          Confirm Match (Enter)
        </button>
      </div>
    </div>
  );
}
