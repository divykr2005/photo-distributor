"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  HiOutlineUserGroup,
  HiOutlinePlus,
  HiOutlineSearch,
  HiOutlineTrash,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
} from "react-icons/hi";
import api from "@/lib/api";
import type { Guest, Event, PaginatedGuests } from "@/types";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ||
  "http://localhost:8000";

const PAGE_SIZE = 20;

const embeddingColors: Record<string, string> = {
  pending: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  success: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  failed: "bg-rose-500/20 text-rose-300 border-rose-500/30",
};

export default function GuestsPage() {
  const [guests, setGuests] = useState<Guest[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [search, setSearch] = useState("");
  const [filterEvent, setFilterEvent] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const fetchGuests = useCallback(async (pg: number) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(pg),
        page_size: String(PAGE_SIZE),
      });
      if (search) params.set("search", search);
      if (filterEvent) params.set("event_id", filterEvent);
      const { data } = await api.get<PaginatedGuests>(`/guests?${params}`);
      setGuests(data.data);
      setTotal(data.total);
    } catch {
      setError("Failed to load guests");
    } finally {
      setLoading(false);
    }
  }, [search, filterEvent]);

  // Load events once
  useEffect(() => {
    api.get<Event[]>("/events").then(({ data }) => setEvents(data)).catch(() => {});
  }, []);

  // Debounce search/filter; reset to page 1
  useEffect(() => {
    setPage(1);
    const t = setTimeout(() => fetchGuests(1), 300);
    return () => clearTimeout(t);
  }, [search, filterEvent]); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-fetch on explicit page change
  useEffect(() => {
    fetchGuests(page);
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this guest?")) return;
    setDeleting(id);
    try {
      await api.delete(`/guests/${id}`);
      setSuccess("Guest deleted");
      fetchGuests(page);
    } catch {
      setError("Failed to delete guest");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Guests</h1>
          <p className="text-sm text-slate-400 mt-1">
            {total} guest{total !== 1 ? "s" : ""} registered
          </p>
        </div>
        <Link href="/guests/new">
          <Button>
            <HiOutlinePlus className="w-4 h-4 mr-2" />
            Register Guest
          </Button>
        </Link>
      </div>

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

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <HiOutlineSearch className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search by name, phone, email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/50 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent text-sm"
          />
        </div>
        <select
          value={filterEvent}
          onChange={(e) => setFilterEvent(e.target.value)}
          className="px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/50 text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
        >
          <option value="">All Events</option>
          {events.map((e) => (
            <option key={e.id} value={e.id}>
              {e.title}
            </option>
          ))}
        </select>
      </div>

      {/* Guest list */}
      {loading && guests.length === 0 ? (
        <div className="flex justify-center py-20">
          <Spinner />
        </div>
      ) : guests.length === 0 ? (
        <Card gradient>
          <div className="text-center py-12">
            <div className="inline-flex p-4 rounded-2xl bg-slate-700/30 mb-4">
              <HiOutlineUserGroup className="w-10 h-10 text-slate-500" />
            </div>
            <h3 className="text-lg font-semibold text-white">No guests found</h3>
            <p className="text-sm text-slate-400 mt-2">
              {search || filterEvent
                ? "Try adjusting your search or filter."
                : events.length === 0
                ? "Create an event first, then register guests."
                : "Register your first guest to get started."}
            </p>
            {!search && !filterEvent && events.length > 0 && (
              <Link href="/guests/new" className="inline-block mt-4">
                <Button>Register Guest</Button>
              </Link>
            )}
          </div>
        </Card>
      ) : (
        <Card gradient>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Photo</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Name</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Phone</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Event</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Status</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Date</th>
                  <th className="text-right py-3 px-4 text-slate-400 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {guests.map((guest) => {
                  const event = events.find((e) => e.id === guest.event_id);
                  return (
                    <tr
                      key={guest.id}
                      className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="py-3 px-4">
                        {guest.image_path ? (
                          <img
                            src={`${API_BASE}/${guest.image_path}`}
                            alt=""
                            className="w-10 h-10 rounded-lg object-cover border border-slate-700"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-lg bg-slate-700/50 flex items-center justify-center text-slate-500 text-xs">
                            N/A
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <Link
                          href={`/guests/${guest.id}`}
                          className="text-white hover:text-violet-300 transition-colors font-medium"
                        >
                          {guest.first_name} {guest.last_name}
                        </Link>
                        {guest.email && (
                          <p className="text-xs text-slate-500">{guest.email}</p>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-300">{guest.phone}</td>
                      <td className="py-3 px-4 text-slate-400 text-xs">
                        {event?.title || "—"}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded-md border ${
                            embeddingColors[guest.embedding_status]
                          }`}
                        >
                          {guest.embedding_status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-xs">
                        {new Date(guest.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleDelete(guest.id)}
                          disabled={deleting === guest.id}
                          className="p-1.5 rounded-lg text-slate-500 hover:text-rose-300 hover:bg-slate-700/50 transition-colors cursor-pointer disabled:opacity-50"
                        >
                          <HiOutlineTrash className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700/50 mt-2">
              <p className="text-xs text-slate-500">
                Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                >
                  <HiOutlineChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs text-slate-400 px-2">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                >
                  <HiOutlineChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
