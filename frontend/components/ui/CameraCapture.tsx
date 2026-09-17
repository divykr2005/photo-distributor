"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import Button from "@/components/ui/Button";

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  currentImage?: string | null;
  allowUpload?: boolean;
}

export default function CameraCapture({ onCapture, currentImage, allowUpload = true }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [streaming, setStreaming] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [preview, setPreview] = useState<string | null>(currentImage || null);
  const [error, setError] = useState("");

  const startCamera = useCallback(async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 960 },
        },
        audio: false,
      });
      streamRef.current = stream;
      setCameraReady(false);
      setPreview(null);
      setStreaming(true);
    } catch {
      setError("Camera access was unavailable. Allow camera permission in your browser and try again.");
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraReady(false);
    setStreaming(false);
  }, []);

  useEffect(() => stopCamera, [stopCamera]);

  useEffect(() => {
    const video = videoRef.current;
    const stream = streamRef.current;
    if (!streaming || !video || !stream) return;

    video.srcObject = stream;
    video.play().catch(() => {
      setError("The camera opened, but the preview could not start. Tap Open Camera and try again.");
      stopCamera();
    });
  }, [streaming, stopCamera]);

  const capturePhoto = useCallback(() => {
    if (!cameraReady || !videoRef.current || !canvasRef.current) return;
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
  }, [cameraReady, onCapture, stopCamera]);

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
            onLoadedMetadata={() => setCameraReady(true)}
            className="w-full max-w-sm rounded-xl border border-slate-700 aspect-[4/3] object-cover bg-black"
          />
          {!cameraReady && (
            <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-300 bg-black/60 rounded-xl">
              Starting camera…
            </div>
          )}
          <div className="flex gap-2 mt-3">
            <Button type="button" onClick={capturePhoto} size="sm" disabled={!cameraReady}>
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
          {allowUpload && (
            <>
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
            </>
          )}
        </div>
      )}

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
