"use client";

import React from "react";
import { Photo } from "@/services/photos";

interface Props {
  photo: Photo;
  onClose: () => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function PhotoDetailModal({ photo, onClose }: Props) {
  const webUrl = `${API_URL}/media/photos/${photo.id}/web`;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden text-slate-100 shadow-2xl">
        <div className="flex justify-between items-center px-6 py-4 border-b border-slate-800">
          <div>
            <h3 className="font-bold text-lg text-white">{photo.original_filename}</h3>
            <p className="text-xs text-slate-400">ID: {photo.id} | Status: <span className="text-indigo-400 font-semibold">{photo.status}</span></p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Main Image with Normalized Bounding Box Overlays */}
          <div className="md:col-span-2 relative bg-black rounded-lg overflow-hidden flex items-center justify-center min-h-[350px]">
            <img
              src={webUrl}
              alt={photo.original_filename}
              className="w-full h-auto max-h-[60vh] object-contain"
            />
            {/* Normalized BBox Overlays */}
            {photo.faces &&
              photo.faces.map((face) => (
                <div
                  key={face.id}
                  style={{
                    left: `${face.bbox_x * 100}%`,
                    top: `${face.bbox_y * 100}%`,
                    width: `${face.bbox_w * 100}%`,
                    height: `${face.bbox_h * 100}%`,
                  }}
                  className={`absolute border-2 ${
                    face.is_matchable ? "border-emerald-400 bg-emerald-500/10" : "border-rose-400 bg-rose-500/10"
                  } transition-all hover:scale-105 pointer-events-none`}
                >
                  <span className="absolute -top-5 left-0 bg-slate-900/90 text-[10px] px-1 rounded text-white border border-slate-700">
                    {(face.det_score * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
          </div>

          {/* Detected Faces Detail Sidebar */}
          <div className="space-y-4">
            <h4 className="font-semibold text-sm text-slate-300">
              Detected Faces ({photo.faces?.length || 0})
            </h4>
            <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
              {photo.faces && photo.faces.length > 0 ? (
                photo.faces.map((face) => {
                  const cropUrl = `${API_URL}/media/faces/${face.id}`;
                  return (
                    <div
                      key={face.id}
                      className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex items-center gap-3"
                    >
                      <img
                        src={cropUrl}
                        alt="Crop"
                        className="w-14 h-14 object-cover rounded-md border border-slate-700"
                      />
                      <div className="text-xs space-y-1">
                        <p className="font-semibold text-white">
                          Quality: <span className="text-emerald-400">{((face.quality_score || 0) * 100).toFixed(0)}%</span>
                        </p>
                        <p className="text-slate-400">
                          Detection: {(face.det_score * 100).toFixed(1)}%
                        </p>
                        {face.quality_flags && face.quality_flags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {face.quality_flags.map((flag) => (
                              <span
                                key={flag}
                                className="px-1.5 py-0.5 bg-rose-950/60 text-rose-300 border border-rose-800/40 rounded text-[9px]"
                              >
                                {flag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-slate-500 italic">No faces detected in this photo.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
