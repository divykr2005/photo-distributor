"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  HiOutlineCalendar,
  HiOutlinePlus,
  HiOutlinePencil,
  HiOutlineTrash,
  HiOutlineLocationMarker,
  HiOutlineChartBar,
} from "react-icons/hi";
import api from "@/lib/api";
import type { Event } from "@/types";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";

const statusColors: Record<string, string> = {
  draft: "bg-zinc-500/20 text-zinc-300 border-zinc-500/30",
  active: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  completed: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
  cancelled: "bg-red-500/20 text-red-300 border-red-500/30",
};

export default function EventsPage() {
  const router = useRouter();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchEvents = async () => {
    try {
      const { data } = await api.get<Event[]>("/events/");
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
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-3xl font-semibold text-white tracking-tight">Events</h1>
          <p className="text-base text-zinc-400 mt-1">
            Manage your events and guest registrations
          </p>
        </div>
        <Link href="/events/new">
          <Button variant="primary">
            <HiOutlinePlus className="w-5 h-5 mr-2" />
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
            <div className="inline-flex p-4 rounded-2xl bg-zinc-800/50 mb-4 border border-zinc-700/50">
              <HiOutlineCalendar className="w-10 h-10 text-zinc-500" />
            </div>
            <h3 className="text-xl font-medium text-white tracking-tight">
              No events yet
            </h3>
            <p className="text-sm text-zinc-400 mt-2 max-w-sm mx-auto">
              Create your first event to start registering guests and distributing photos.
            </p>
            <Link href="/events/new" className="inline-block mt-6">
              <Button variant="primary">
                <HiOutlinePlus className="w-5 h-5 mr-2" />
                Create Event
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {events.map((event) => (
            <Card
              key={event.id}
              gradient
              className="group hover:scale-[1.02] transition-transform duration-300"
            >
              <div className="flex flex-col h-full">
                {/* Status badge */}
                <div className="flex items-center justify-between mb-4">
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-md border ${
                      statusColors[event.status]
                    }`}
                  >
                    {event.status}
                  </span>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => router.push(`/events/${event.id}`)}
                      className="p-1.5 rounded-lg text-zinc-500 hover:text-indigo-400 hover:bg-zinc-800 transition-colors cursor-pointer"
                      title="Edit"
                    >
                      <HiOutlinePencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(event.id)}
                      disabled={deleting === event.id}
                      className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-colors cursor-pointer disabled:opacity-50"
                      title="Delete"
                    >
                      <HiOutlineTrash className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Title */}
                <h3
                  onClick={() => router.push(`/events/${event.id}`)}
                  className="text-lg font-medium text-white group-hover:text-indigo-400 transition-colors cursor-pointer tracking-tight"
                >
                  {event.title}
                </h3>

                {/* Description */}
                {event.description && (
                  <p className="text-sm text-zinc-400 mt-2 line-clamp-2 leading-relaxed">
                    {event.description}
                  </p>
                )}

                {/* Meta */}
                <div className="mt-4 flex items-center gap-4 text-xs font-medium text-zinc-500">
                  <span className="flex items-center gap-1.5">
                    <HiOutlineCalendar className="w-4 h-4 text-zinc-400" />
                    {new Date(event.date).toLocaleDateString()}
                  </span>
                  {event.location && (
                    <span className="flex items-center gap-1.5">
                      <HiOutlineLocationMarker className="w-4 h-4 text-zinc-400" />
                      {event.location}
                    </span>
                  )}
                </div>

                {/* Quick Actions Bar */}
                <div className="mt-6 pt-4 border-t border-zinc-800/80 flex items-center gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => router.push(`/events/${event.id}/upload`)}
                    className="flex-1"
                  >
                    Upload Photos
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => router.push(`/events/${event.id}/photos`)}
                    title="View Photo Gallery"
                  >
                    Gallery
                  </Button>
                  <Button
                    variant="glass"
                    size="sm"
                    onClick={() => router.push(`/events/${event.id}/analytics`)}
                    className="px-2"
                    title="View Analytics"
                  >
                    <HiOutlineChartBar className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
