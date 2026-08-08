"use client";

import { useRef, useState, useCallback } from "react";
import Button from "@/components/ui/Button";

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  currentImage?: string | null;
}

export default function CameraCapture({ onCapture, currentImage }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [streaming, setStreaming] = useState(false);
  const [preview, setPreview] = useState<string | null>(currentImage || null);
  const [error, setError] = useState("");

  const startCamera = useCallback(async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 640, height: 480 },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setStreaming(true);
        setPreview(null);
      }
    } catch {
      setError("Camera access denied. Please allow camera access or upload a photo instead.");
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (videoRef.current?.srcObject) {
      const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
      tracks.forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setStreaming(false);
  }, []);

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
        setPreview(URL.createObjectURL(blob));
        onCapture(file);
        stopCamera();
      },
      "image/jpeg",
      0.9
    );
  }, [onCapture, stopCamera]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Only JPEG, PNG, or WebP images are accepted");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Image must be under 5MB");
      return;
    }
    setError("");
    setPreview(URL.createObjectURL(file));
    onCapture(file);
  };

  const retake = () => {
    setPreview(null);
    setError("");
  };

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-slate-300">
        Guest Photo
      </label>

      {error && (
        <p className="text-xs text-rose-400">{error}</p>
      )}

      {/* Preview */}
      {preview && (
        <div className="relative">
          <img
            src={preview}
            alt="Guest"
            className="w-full max-w-sm rounded-xl border border-slate-700 object-cover aspect-[4/3]"
          />
          <button
            type="button"
            onClick={retake}
            className="absolute top-2 right-2 px-2 py-1 text-xs bg-slate-900/80 text-white rounded-lg border border-slate-600 hover:bg-slate-800 cursor-pointer"
          >
            Retake
          </button>
        </div>
      )}

      {/* Camera stream */}
      {streaming && !preview && (
        <div className="relative">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full max-w-sm rounded-xl border border-slate-700 aspect-[4/3] object-cover bg-black"
          />
          <div className="flex gap-2 mt-3">
            <Button type="button" onClick={capturePhoto} size="sm">
              📸 Capture
            </Button>
            <Button type="button" variant="secondary" size="sm" onClick={stopCamera}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Actions when no preview and not streaming */}
      {!preview && !streaming && (
        <div className="flex gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={startCamera}>
            📷 Open Camera
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
          >
            📁 Upload Photo
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={handleFileUpload}
          />
        </div>
      )}

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
