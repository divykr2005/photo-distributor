"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import api from "@/lib/api";
import type { Event } from "@/types";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";

import NotifyGuestsModal from "@/components/notifications/NotifyGuestsModal";

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
        <p className="text-slate-400">Event not found</p>
        <Button
          variant="secondary"
          className="mt-4"
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
    <div className="max-w-2xl mx-auto">
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{event.title}</h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage event settings, photos, and guest notifications
          </p>
          {pipelineStatus && pipelineStatus.pending > 0 && (
            <div className="mt-4 p-4 bg-indigo-900/30 border border-indigo-800 rounded-xl">
              <div className="flex justify-between text-xs font-semibold text-indigo-200 mb-2">
                <span>Processing Pipeline</span>
                <span>{pipelineStatus.processed} / {pipelineStatus.total} photos</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-indigo-500 h-full transition-all duration-500 ease-out"
                  style={{ width: `${Math.max(5, (pipelineStatus.processed / (pipelineStatus.total || 1)) * 100)}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-400 mt-2 flex justify-between">
                <span>{pipelineStatus.pending} pending</span>
                {pipelineStatus.failed > 0 && <span className="text-rose-400">{pipelineStatus.failed} failed</span>}
              </div>
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            onClick={() => router.push(`/events/${eventId}/upload`)}
            className="flex items-center gap-1.5 text-xs px-3.5 py-2"
          >
            <span>📤</span> Upload Photos
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push(`/events/${eventId}/photos`)}
            className="flex items-center gap-1.5 text-xs px-3.5 py-2"
          >
            <span>🖼️</span> Gallery
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push(`/guests?eventId=${eventId}`)}
            className="flex items-center gap-1.5 text-xs px-3.5 py-2"
          >
            <span>👥</span> Guests
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={async () => {
              try {
                await api.post(`/events/${eventId}/clusters/run`);
                setSuccess("Clustering started in background");
              } catch {
                setError("Failed to start clustering");
              }
            }}
            className="flex items-center gap-1.5 text-xs px-3.5 py-2"
          >
            <span>🔄</span> Group Duplicates
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push(`/events/${eventId}/clusters`)}
            className="flex items-center gap-1.5 text-xs px-3.5 py-2"
          >
            <span>👯</span> Review Clusters
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={() => setIsNotifyModalOpen(true)}
            className="flex items-center gap-1.5 text-xs px-3.5 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500"
          >
            <span>📢</span> Notify Guests
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <Toast message={error} type="error" onClose={() => setError("")} />
        </div>
      )}
      {success && (
        <div className="mb-6">
          <Toast
            message={success}
            type="success"
            onClose={() => setSuccess("")}
          />
        </div>
      )}

      <Card gradient>
        <form onSubmit={handleSubmit} className="space-y-5">
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
          <Input
            label="Location"
            name="location"
            defaultValue={event.location || ""}
          />
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Event Date
            </label>
            <input
              type="datetime-local"
              name="date"
              defaultValue={dateValue}
              required
              className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/50 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Status
            </label>
            <select
              name="status"
              defaultValue={event.status}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/50 text-white focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all text-sm"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-3 pt-2">
            <Button type="submit" isLoading={saving}>
              Save Changes
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push("/events")}
            >
              Back
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="bg-orange-900/50 text-orange-200 border-orange-800 hover:bg-orange-900/70 hover:text-white"
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
              Delete Bulk
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="bg-red-900/50 text-red-200 border-red-800 hover:bg-red-900/70 hover:text-white"
              onClick={async () => {
                if (window.confirm("are you sure to delete all including guests bulk photos face embedding registrations and all")) {
                  try {
                    await api.post(`/events/${eventId}/purge`);
                    setSuccess("All event data purged successfully");
                  } catch {
                    setError("Failed to purge event data");
                  }
                }
              }}
            >
              Delete All Data
            </Button>
          </div>
        </form>
      </Card>

      <NotifyGuestsModal
        eventId={eventId}
        isOpen={isNotifyModalOpen}
        onClose={() => setIsNotifyModalOpen(false)}
      />
    </div>
  );
}
