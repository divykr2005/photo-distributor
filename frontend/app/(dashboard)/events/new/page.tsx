"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Toast from "@/components/ui/Toast";

export default function NewEventPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const formData = new FormData(e.currentTarget);
    const body = {
      title: formData.get("title") as string,
      description: (formData.get("description") as string) || undefined,
      location: (formData.get("location") as string) || undefined,
      date: new Date(formData.get("date") as string).toISOString(),
    };

    if (!body.title.trim()) {
      setError("Title is required");
      setLoading(false);
      return;
    }
    if (!formData.get("date")) {
      setError("Date is required");
      setLoading(false);
      return;
    }

    try {
      await api.post("/events", body);
      router.push("/events");
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setError(msg || "Failed to create event");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Create Event</h1>
        <p className="text-sm text-slate-400 mt-1">
          Set up a new event for guest registration and photo distribution
        </p>
      </div>

      {error && (
        <div className="mb-6">
          <Toast message={error} type="error" onClose={() => setError("")} />
        </div>
      )}

      <Card gradient>
        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            label="Event Title"
            name="title"
            placeholder="e.g., Annual Company Gala 2026"
            required
          />
          <Input
            label="Description"
            name="description"
            placeholder="Brief description of the event (optional)"
          />
          <Input
            label="Location"
            name="location"
            placeholder="e.g., Grand Ballroom, Marriott Hotel"
          />
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Event Date
            </label>
            <input
              type="datetime-local"
              name="date"
              required
              className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/50 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all text-sm"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <Button type="submit" isLoading={loading}>
              Create Event
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push("/events")}
            >
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
