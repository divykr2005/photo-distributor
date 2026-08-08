"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  HiOutlineCalendar,
  HiOutlinePlus,
  HiOutlinePencil,
  HiOutlineTrash,
  HiOutlineMapPin,
} from "react-icons/hi";
import api from "@/lib/api";
import type { Event } from "@/types";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";

const statusColors: Record<string, string> = {
  draft: "bg-slate-500/20 text-slate-300 border-slate-500/30",
  active: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  completed: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  cancelled: "bg-rose-500/20 text-rose-300 border-rose-500/30",
};

export default function EventsPage() {
  const router = useRouter();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchEvents = async () => {
    try {
      const { data } = await api.get<Event[]>("/events");
      setEvents(data);
    } catch {
      setError("Failed to load events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this event? This cannot be undone.")) return;
    setDeleting(id);
    try {
      await api.delete(`/events/${id}`);
      setEvents((prev) => prev.filter((e) => e.id !== id));
    } catch {
      setError("Failed to delete event");
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Events</h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage your events and guest registrations
          </p>
        </div>
        <Link href="/events/new">
          <Button>
            <HiOutlinePlus className="w-4 h-4 mr-2" />
            New Event
          </Button>
        </Link>
      </div>

      {error && (
        <div className="mb-6">
          <Toast message={error} type="error" onClose={() => setError("")} />
        </div>
      )}

      {/* Events grid */}
      {events.length === 0 ? (
        <Card gradient>
          <div className="text-center py-12">
            <div className="inline-flex p-4 rounded-2xl bg-slate-700/30 mb-4">
              <HiOutlineCalendar className="w-10 h-10 text-slate-500" />
            </div>
            <h3 className="text-lg font-semibold text-white">
              No events yet
            </h3>
            <p className="text-sm text-slate-400 mt-2 max-w-sm mx-auto">
              Create your first event to start registering guests and distributing photos.
            </p>
            <Link href="/events/new" className="inline-block mt-4">
              <Button>
                <HiOutlinePlus className="w-4 h-4 mr-2" />
                Create Event
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {events.map((event) => (
            <Card
              key={event.id}
              gradient
              className="group hover:scale-[1.02] transition-transform duration-300"
            >
              <div className="flex flex-col h-full">
                {/* Status badge */}
                <div className="flex items-center justify-between mb-3">
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-lg border ${
                      statusColors[event.status]
                    }`}
                  >
                    {event.status}
                  </span>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => router.push(`/events/${event.id}`)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-violet-300 hover:bg-slate-700/50 transition-colors cursor-pointer"
                      title="Edit"
                    >
                      <HiOutlinePencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(event.id)}
                      disabled={deleting === event.id}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-rose-300 hover:bg-slate-700/50 transition-colors cursor-pointer disabled:opacity-50"
                      title="Delete"
                    >
                      <HiOutlineTrash className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Title */}
                <h3 className="text-base font-semibold text-white group-hover:text-violet-200 transition-colors">
                  {event.title}
                </h3>

                {/* Description */}
                {event.description && (
                  <p className="text-sm text-slate-400 mt-1 line-clamp-2">
                    {event.description}
                  </p>
                )}

                {/* Meta */}
                <div className="mt-auto pt-4 flex items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <HiOutlineCalendar className="w-3.5 h-3.5" />
                    {new Date(event.date).toLocaleDateString()}
                  </span>
                  {event.location && (
                    <span className="flex items-center gap-1">
                      <HiOutlineMapPin className="w-3.5 h-3.5" />
                      {event.location}
                    </span>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
