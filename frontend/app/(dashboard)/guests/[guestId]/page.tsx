"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import api from "@/lib/api";
import type { Guest, Event } from "@/types";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";
import {
  HiOutlineArrowLeft,
  HiOutlineUpload,
  HiOutlineUser,
  HiOutlinePhone,
  HiOutlineMail,
  HiOutlineCalendar,
  HiOutlineTag,
  HiOutlineAnnotation,
} from "react-icons/hi";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ||
  "http://localhost:8000";

const statusStyles: Record<string, string> = {
  pending: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  success: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  failed: "bg-rose-500/20 text-rose-300 border-rose-500/30",
};

const statusLabel: Record<string, string> = {
  pending: "Pending",
  success: "Generated",
  failed: "Failed",
};

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-slate-700/40 last:border-0">
      <div className="mt-0.5 text-slate-500">{icon}</div>
      <div>
        <p className="text-xs text-slate-500 mb-0.5">{label}</p>
        <p className="text-sm text-white">{value || "—"}</p>
      </div>
    </div>
  );
}

export default function GuestProfilePage() {
  const router = useRouter();
  const { guestId } = useParams() as { guestId: string };
  const [guest, setGuest] = useState<Guest | null>(null);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    try {
      const { data: g } = await api.get<Guest>(`/guests/${guestId}`);
      setGuest(g);
      const { data: ev } = await api.get<Event>(`/events/${g.event_id}`);
      setEvent(ev);
    } catch {
      setError("Failed to load guest");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [guestId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePhotoUpload = async (file: File) => {
    setUploading(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      await api.post(`/guests/${guestId}/photo`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setSuccess("Photo updated and embedding generated");
      load();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(msg || "Failed to upload photo");
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }

  if (!guest) {
    return (
      <div className="mb-4">
        <Toast message={error || "Guest not found"} type="error" onClose={() => router.push("/guests")} />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back */}
      <button
        onClick={() => router.push("/guests")}
        className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors mb-6 cursor-pointer"
      >
        <HiOutlineArrowLeft className="w-4 h-4" />
        Back to Guests
      </button>

      {error && (
        <div className="mb-4">
          <Toast message={error} type="error" onClose={() => setError("")} />
        </div>
      )}
      {success && (
        <div className="mb-4">
          <Toast message={success} type="success" onClose={() => setSuccess("")} />
        </div>
      )}

      {/* Header card */}
      <Card gradient className="mb-4">
        <div className="flex items-center gap-5">
          {/* Photo */}
          <div className="relative group">
            {guest.image_path ? (
              <img
                src={`${API_BASE}/${guest.image_path}`}
                alt={`${guest.first_name} ${guest.last_name}`}
                className="w-24 h-24 rounded-2xl object-cover border-2 border-slate-600"
              />
            ) : (
              <div className="w-24 h-24 rounded-2xl bg-slate-700/60 flex items-center justify-center border-2 border-slate-600">
                <HiOutlineUser className="w-10 h-10 text-slate-500" />
              </div>
            )}
            {/* Overlay to retake */}
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="absolute inset-0 rounded-2xl bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer disabled:cursor-wait"
              title="Upload new photo"
            >
              {uploading ? (
                <Spinner />
              ) : (
                <HiOutlineUpload className="w-6 h-6 text-white" />
              )}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handlePhotoUpload(f);
                e.target.value = "";
              }}
            />
          </div>

          {/* Name + status */}
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-white truncate">
              {guest.first_name} {guest.last_name}
            </h1>
            <p className="text-sm text-slate-400 mt-0.5">{event?.title || "—"}</p>
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-lg border ${
                  statusStyles[guest.embedding_status]
                }`}
              >
                Face embedding: {statusLabel[guest.embedding_status]}
              </span>
              {guest.gender && (
                <span className="text-xs text-slate-500 capitalize">
                  {guest.gender}
                </span>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Details card */}
      <Card gradient>
        <h2 className="text-sm font-semibold text-slate-300 mb-2">
          Registration Details
        </h2>
        <InfoRow
          icon={<HiOutlinePhone className="w-4 h-4" />}
          label="Phone"
          value={guest.phone}
        />
        <InfoRow
          icon={<HiOutlineMail className="w-4 h-4" />}
          label="Email"
          value={guest.email}
        />
        <InfoRow
          icon={<HiOutlineCalendar className="w-4 h-4" />}
          label="Registered"
          value={new Date(guest.created_at).toLocaleString()}
        />
        <InfoRow
          icon={<HiOutlineTag className="w-4 h-4" />}
          label="Event"
          value={event?.title}
        />
        {guest.notes && (
          <InfoRow
            icon={<HiOutlineAnnotation className="w-4 h-4" />}
            label="Notes"
            value={guest.notes}
          />
        )}
        {guest.embedding_status === "failed" && (
          <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-300">
            Embedding generation failed. Hover the photo above and upload a
            clearer image (well-lit, single face, not blurry).
          </div>
        )}
        {guest.embedding_status === "pending" && !guest.image_path && (
          <div className="mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-sm text-amber-300">
            No photo yet. Hover the photo area above to upload one.
          </div>
        )}
      </Card>
    </div>
  );
}
