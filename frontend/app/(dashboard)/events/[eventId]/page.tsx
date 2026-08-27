"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  HiOutlineCloudUpload,
  HiOutlinePhotograph,
  HiOutlineUserGroup,
  HiOutlineSparkles,
  HiOutlineSpeakerphone,
  HiOutlineDuplicate,
} from "react-icons/hi";
import api from "@/lib/api";
import type { Event } from "@/types";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";

import NotifyGuestsModal from "@/components/notifications/NotifyGuestsModal";
import ShareEventModal from "@/components/events/ShareEventModal";
import { HiOutlineShare } from "react-icons/hi";

const STATUS_OPTIONS = ["draft", "active", "completed", "cancelled"] as const;

export default function EditEventPage() {
  const router = useRouter();
  const params = useParams();
  const eventId = params.eventId as string;

  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isNotifyModalOpen, setIsNotifyModalOpen] = useState(false);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState<any>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    const fetchStatus = async () => {
      try {
        const { data } = await api.get(`/events/${eventId}/pipeline-status`);
        setPipelineStatus(data);
      } catch (e) {
        // ignore
      }
    };
    fetchStatus();
    interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [eventId]);

  useEffect(() => {
    const fetchEvent = async () => {
      try {
        const { data } = await api.get<Event>(`/events/${eventId}`);
        setEvent(data);
      } catch {
        setError("Event not found");
      } finally {
        setLoading(false);
      }
    };
    fetchEvent();
  }, [eventId]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);

    const formData = new FormData(e.currentTarget);
    const body = {
      title: formData.get("title") as string,
      description: (formData.get("description") as string) || null,
      location: (formData.get("location") as string) || null,
      date: new Date(formData.get("date") as string).toISOString(),
      status: formData.get("status") as string,
    };

    try {
      const { data } = await api.put<Event>(`/events/${eventId}`, body);
      setEvent(data);
      setSuccess("Event updated successfully");
    } catch {
      setError("Failed to update event");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }

  if (!event) {
    return (
      <div className="text-center py-20">
        <p className="text-zinc-400">Event not found</p>
        <Button
          variant="secondary"
          className="mt-6"
          onClick={() => router.push("/events")}
        >
          Back to Events
        </Button>
      </div>
    );
  }

  // Format date for datetime-local input
  const dateValue = new Date(event.date).toISOString().slice(0, 16);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-10 flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div className="flex-1">
          <h1 className="text-3xl font-semibold text-white tracking-tight">{event.title}</h1>
          <p className="text-sm text-zinc-400 mt-2 leading-relaxed max-w-lg">
            Manage event settings, upload photos, and notify guests. The global task tracker will monitor background AI processing.
          </p>
          
          {pipelineStatus && pipelineStatus.pending > 0 && (
            <div className="mt-6 p-5 glass-panel rounded-xl">
              <div className="flex justify-between text-xs font-semibold text-indigo-300 mb-3">
                <span>AI Processing Pipeline</span>
                <span>{pipelineStatus.processed} / {pipelineStatus.total} photos</span>
              </div>
              <div className="w-full bg-zinc-800/50 h-2.5 rounded-full overflow-hidden border border-zinc-700/30">
                <div 
                  className="bg-indigo-500 h-full transition-all duration-500 ease-out shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                  style={{ width: `${Math.max(5, (pipelineStatus.processed / (pipelineStatus.total || 1)) * 100)}%` }}
                />
              </div>
              <div className="text-[11px] text-zinc-500 mt-3 flex justify-between font-medium">
                <span>{pipelineStatus.pending} pending</span>
                {pipelineStatus.failed > 0 && <span className="text-red-400">{pipelineStatus.failed} failed</span>}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-start justify-end gap-3 md:max-w-xs">
          <Button
            type="button"
            variant="primary"
            onClick={() => router.push(`/events/${eventId}/upload`)}
            className="w-full justify-start gap-2"
          >
            <HiOutlineCloudUpload className="w-5 h-5" /> Upload Photos
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={() => setIsShareModalOpen(true)}
            className="w-full justify-start gap-2 bg-zinc-800 border-zinc-700 hover:bg-zinc-700 text-white"
          >
            <HiOutlineShare className="w-5 h-5" /> Share Event
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={() => setIsNotifyModalOpen(true)}
            className="w-full justify-start gap-2"
          >
            <HiOutlineSpeakerphone className="w-5 h-5" /> Notify Guests
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {error && <Toast message={error} type="error" onClose={() => setError("")} />}
          {success && <Toast message={success} type="success" onClose={() => setSuccess("")} />}

          <Card gradient title="Event Details">
            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="Event Title"
                name="title"
                defaultValue={event.title}
                required
              />
              <Input
                label="Description"
                name="description"
                defaultValue={event.description || ""}
              />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Input
                  label="Location"
                  name="location"
                  defaultValue={event.location || ""}
                />
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1.5 transition-colors">
                    Event Date
                  </label>
                  <div className="relative">
                    <input
                      type="datetime-local"
                      name="date"
                      defaultValue={dateValue}
                      required
                      className="w-full px-4 py-2.5 rounded-xl border border-zinc-800/80 bg-zinc-900/60 backdrop-blur-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 focus:bg-zinc-900 transition-all text-sm"
                    />
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                  Status
                </label>
                <div className="relative">
                  <select
                    name="status"
                    defaultValue={event.status}
                    className="w-full px-4 py-2.5 rounded-xl border border-zinc-800/80 bg-zinc-900/60 backdrop-blur-sm text-white focus:outline-none focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 focus:bg-zinc-900 transition-all text-sm appearance-none"
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {s.charAt(0).toUpperCase() + s.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-4 pt-4 border-t border-zinc-800/80">
                <Button type="submit" isLoading={saving} variant="primary">
                  Save Changes
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => router.push("/events")}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </Card>
        </div>

        {/* Sidebar Tools */}
        <div className="space-y-6">
          <Card title="Quick Links" className="bg-zinc-900/30">
            <div className="flex flex-col gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => router.push(`/events/${eventId}/photos`)}
                className="w-full justify-start gap-3"
              >
                <HiOutlinePhotograph className="w-5 h-5 text-indigo-400" />
                Photo Gallery
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => router.push(`/guests?eventId=${eventId}`)}
                className="w-full justify-start gap-3"
              >
                <HiOutlineUserGroup className="w-5 h-5 text-indigo-400" />
                Manage Guests
              </Button>
            </div>
          </Card>

          <Card title="AI Tools" className="bg-zinc-900/30">
            <div className="flex flex-col gap-3">
              <Button
                type="button"
                variant="glass"
                onClick={async () => {
                  try {
                    await api.post(`/events/${eventId}/clusters/run`);
                    setSuccess("Clustering started in background");
                  } catch {
                    setError("Failed to start clustering");
                  }
                }}
                className="w-full justify-start gap-3"
              >
                <HiOutlineDuplicate className="w-5 h-5 text-zinc-400" />
                Group Duplicates
              </Button>
              <Button
                type="button"
                variant="glass"
                onClick={async () => {
                  try {
                    await api.post(`/events/${eventId}/quality-runs`);
                    setSuccess("Quality ranking started in background");
                  } catch {
                    setError("Failed to start quality ranking");
                  }
                }}
                className="w-full justify-start gap-3"
              >
                <HiOutlineSparkles className="w-5 h-5 text-zinc-400" />
                Rank Photo Quality
              </Button>
            </div>
          </Card>

          <Card title="Danger Zone" className="border-red-900/30 bg-red-950/10">
            <div className="flex flex-col gap-3">
              <Button
                type="button"
                variant="danger"
                className="w-full bg-red-900/20 text-red-400 border border-red-900/50 hover:bg-red-900/40 hover:text-red-300"
                onClick={async () => {
                  if (window.confirm("Are you sure you want to delete bulk photos for this event?")) {
                    try {
                      await api.delete(`/events/${eventId}/photos`);
                      setSuccess("Bulk photos deleted successfully");
                    } catch {
                      setError("Failed to delete bulk photos");
                    }
                  }
                }}
              >
                Delete All Photos
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={async () => {
                  if (window.confirm("Are you sure to delete ALL data including guests, face embeddings, and photos?")) {
                    try {
                      await api.post(`/events/${eventId}/purge`);
                      setSuccess("All event data purged successfully");
                    } catch {
                      setError("Failed to purge event data");
                    }
                  }
                }}
              >
                Purge Event Data
              </Button>
            </div>
          </Card>
        </div>
      </div>

      <NotifyGuestsModal
        eventId={eventId}
        isOpen={isNotifyModalOpen}
        onClose={() => setIsNotifyModalOpen(false)}
      />
      
      <ShareEventModal
        eventId={eventId}
        isOpen={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
      />
    </div>
  );
}
