"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import api from "@/lib/api";
import type { Guest, Event } from "@/types";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") || "http://localhost:8000";

const embeddingColors: Record<string, string> = {
  pending: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  success: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  failed: "bg-rose-500/20 text-rose-300 border-rose-500/30",
};

export default function GuestProfilePage() {
  const router = useRouter();
  const params = useParams();
  const guestId = params.guestId as string;

  const [guest, setGuest] = useState<Guest | null>(null);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchGuest = async () => {
      try {
        const { data } = await api.get<Guest>(`/guests/${guestId}`);
        setGuest(data);
        const { data: ev } = await api.get<Event>(`/events/${data.event_id}`);
        setEvent(ev);
      } catch {
        setError("Guest not found");
      } finally {
        setLoading(false);
      }
    };
    fetchGuest();
  }, [guestId]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }

  if (!guest) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400">Guest not found</p>
        <Button variant="secondary" className="mt-4" onClick={() => router.push("/guests")}>
          Back to Guests
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">
          {guest.first_name} {guest.last_name}
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Guest Profile
        </p>
      </div>

      {error && (
        <div className="mb-6">
          <Toast message={error} type="error" onClose={() => setError("")} />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Photo */}
        <Card gradient>
          <div className="text-center">
            {guest.image_path ? (
              <img
                src={`${API_BASE}/${guest.image_path}`}
                alt={`${guest.first_name} ${guest.last_name}`}
                className="w-full rounded-xl border border-slate-700 object-cover aspect-square"
              />
            ) : (
              <div className="w-full rounded-xl bg-slate-700/30 border border-slate-700 aspect-square flex items-center justify-center">
                <span className="text-4xl text-slate-500">
                  {guest.first_name[0]}{guest.last_name[0]}
                </span>
              </div>
            )}
            <div className="mt-3">
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-lg border ${
                  embeddingColors[guest.embedding_status]
                }`}
              >
                Embedding: {guest.embedding_status}
              </span>
            </div>
          </div>
        </Card>

        {/* Details */}
        <div className="md:col-span-2">
          <Card gradient>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider">First Name</p>
                  <p className="text-white mt-0.5">{guest.first_name}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider">Last Name</p>
                  <p className="text-white mt-0.5">{guest.last_name}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider">Phone</p>
                  <p className="text-white mt-0.5">{guest.phone}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider">Email</p>
                  <p className="text-white mt-0.5">{guest.email || "—"}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider">Gender</p>
                  <p className="text-white mt-0.5 capitalize">{guest.gender || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider">Event</p>
                  <p className="text-white mt-0.5">{event?.title || "—"}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider">Registered</p>
                  <p className="text-white mt-0.5">
                    {new Date(guest.created_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider">Expires</p>
                  <p className="text-white mt-0.5">
                    {new Date(guest.expires_at).toLocaleString()}
                  </p>
                </div>
              </div>
              {guest.notes && (
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider">Notes</p>
                  <p className="text-slate-300 mt-0.5 text-sm">{guest.notes}</p>
                </div>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-slate-700/50">
              <Button variant="secondary" onClick={() => router.push("/guests")}>
                ← Back to Guests
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
