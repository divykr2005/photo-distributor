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
      portal_enabled: formData.get("portal_enabled") === "on",
      selfie_search_enabled: formData.get("selfie_search_enabled") === "on",
      upload_mode: formData.get("controlled_upload") === "on" ? "controlled" : "open",
      min_age_confirmed: formData.get("min_age_confirmed") === "on",
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
      await api.post("/events/", body);
      router.push("/events");
    } catch (err: unknown) {
      let msg: string | undefined = undefined;
      if (err && typeof err === "object" && "response" in err) {
        const detail = (err as any).response?.data?.detail;
        if (typeof detail === "string") {
          msg = detail;
        } else if (Array.isArray(detail) && detail.length > 0) {
          msg = detail.map((d: any) => d.msg || "Unknown error").join(", ");
        } else if ((err as any).message) {
          msg = (err as any).message;
        }
      }
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

          <div className="space-y-3 rounded-xl border border-slate-700 bg-slate-900/40 p-4 text-sm text-slate-300">
            <label className="flex items-start gap-3">
              <input type="checkbox" name="portal_enabled" className="mt-1" />
              <span>Enable the guest photo portal for this event.</span>
            </label>
            <label className="flex items-start gap-3">
              <input type="checkbox" name="selfie_search_enabled" className="mt-1" />
              <span>Enable public guest registration and selfie search.</span>
            </label>
            <label className="flex items-start gap-3">
              <input type="checkbox" name="controlled_upload" className="mt-1" />
              <span>I confirm every person in uploaded photos has explicitly consented to facial-feature processing.</span>
            </label>
            <label className="flex items-start gap-3">
              <input type="checkbox" name="min_age_confirmed" className="mt-1" />
              <span>I confirm the uploaded photos do not contain subjects under 16.</span>
            </label>
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
