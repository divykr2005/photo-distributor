"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import type { Event } from "@/types";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";
import CameraCapture from "@/components/ui/CameraCapture";

export default function NewGuestPage() {
  const router = useRouter();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [photoFile, setPhotoFile] = useState<File | null>(null);

  useEffect(() => {
    api
      .get<Event[]>("/events")
      .then(({ data }) => setEvents(data))
      .catch(() => setError("Failed to load events"))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setSaving(true);

    const fd = new FormData(e.currentTarget);
    const body = {
      event_id: fd.get("event_id") as string,
      first_name: (fd.get("first_name") as string).trim(),
      last_name: (fd.get("last_name") as string).trim(),
      phone: (fd.get("phone") as string).trim(),
      email: (fd.get("email") as string).trim() || undefined,
      gender: (fd.get("gender") as string) || undefined,
      notes: (fd.get("notes") as string).trim() || undefined,
    };

    if (!body.event_id) {
      setError("Please select an event");
      setSaving(false);
      return;
    }
    if (!body.first_name || !body.last_name) {
      setError("First and last name are required");
      setSaving(false);
      return;
    }
    if (!body.phone || body.phone.length < 7) {
      setError("Valid phone number is required");
      setSaving(false);
      return;
    }

    try {
      // Create guest
      const { data: guest } = await api.post("/guests/", body);

      // Upload photo if captured
      if (photoFile) {
        const photoForm = new FormData();
        photoForm.append("file", photoFile);
        await api.post(`/guests/${guest.id}/photo`, photoForm, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      router.push("/guests");
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setError(msg || "Failed to register guest");
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

  if (events.length === 0) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card gradient>
          <div className="text-center py-12">
            <h3 className="text-lg font-semibold text-white">No Events</h3>
            <p className="text-sm text-slate-400 mt-2">
              Create an event first before registering guests.
            </p>
            <Button className="mt-4" onClick={() => router.push("/events/new")}>
              Create Event
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Register Guest</h1>
        <p className="text-sm text-slate-400 mt-1">
          Capture or upload a face photo for automatic photo matching
        </p>
      </div>

      {error && (
        <div className="mb-6">
          <Toast message={error} type="error" onClose={() => setError("")} />
        </div>
      )}

      <Card gradient>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Event selector */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Event *
            </label>
            <select
              name="event_id"
              required
              className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/50 text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            >
              <option value="">Select an event</option>
              {events.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.title}
                </option>
              ))}
            </select>
          </div>

          {/* Name */}
          <div className="grid grid-cols-2 gap-4">
            <Input label="First Name *" name="first_name" required placeholder="John" />
            <Input label="Last Name *" name="last_name" required placeholder="Doe" />
          </div>

          {/* Contact */}
          <div className="grid grid-cols-2 gap-4">
            <Input label="Phone *" name="phone" type="tel" required placeholder="+91 9876543210" />
            <Input label="Email" name="email" type="email" placeholder="john@example.com" />
          </div>

          {/* Gender */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Gender
            </label>
            <select
              name="gender"
              className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/50 text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            >
              <option value="">Prefer not to say</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Notes
            </label>
            <textarea
              name="notes"
              rows={2}
              placeholder="Any additional notes..."
              className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/50 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Camera / Upload */}
          <CameraCapture onCapture={setPhotoFile} />

          {/* Submit */}
          <div className="flex gap-3 pt-2">
            <Button type="submit" isLoading={saving}>
              Register Guest
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push("/guests")}
            >
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
