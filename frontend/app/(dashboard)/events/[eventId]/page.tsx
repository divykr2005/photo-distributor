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
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-white">Edit Event</h1>
          <p className="text-sm text-slate-400 mt-1">
            Update event details
          </p>
        </div>
        <Button
          type="button"
          onClick={() => setIsNotifyModalOpen(true)}
          className="flex items-center gap-2"
        >
          <span>📢</span> Notify Guests
        </Button>
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
