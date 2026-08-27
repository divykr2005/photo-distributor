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

import NotifyGuestsModal from "@/components/notifications/NotifyGuestsModal";
import ShareEventModal from "@/components/events/ShareEventModal";
import { HiOutlineShare, HiOutlineSpeakerphone } from "react-icons/hi";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ||
  "http://localhost:8000";

const PAGE_SIZE = 20;

const embeddingColors: Record<string, string> = {
  pending: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  success: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  failed: "bg-red-500/20 text-red-300 border-red-500/30",
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

  const [isNotifyModalOpen, setIsNotifyModalOpen] = useState(false);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);

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
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-white tracking-tight">Guests</h1>
          <p className="text-sm text-zinc-400 mt-1">
            {total} guest{total !== 1 ? "s" : ""} registered
          </p>
        </div>
        <div className="flex gap-2">
          {filterEvent && (
            <>
              <Button variant="secondary" onClick={() => setIsShareModalOpen(true)}>
                <HiOutlineShare className="w-5 h-5 mr-2" /> Share Registration
              </Button>
              <Button variant="secondary" onClick={() => setIsNotifyModalOpen(true)}>
                <HiOutlineSpeakerphone className="w-5 h-5 mr-2" /> Notify Guests
              </Button>
            </>
          )}
          <Link href="/guests/new">
            <Button variant="primary">
              <HiOutlinePlus className="w-5 h-5 mr-2" />
              Register Guest
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <Toast message={error} type="error" onClose={() => setError("")} />
        </div>
      )}
      {success && (
        <div className="mb-6">
          <Toast message={success} type="success" onClose={() => setSuccess("")} />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        <div className="relative flex-1 max-w-md group">
          <HiOutlineSearch className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500 group-focus-within:text-indigo-400 transition-colors" />
          <input
            type="text"
            placeholder="Search by name, phone, email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-zinc-800/80 bg-zinc-900/60 backdrop-blur-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-sm shadow-inner"
          />
        </div>
        <div className="relative">
          <select
            value={filterEvent}
            onChange={(e) => setFilterEvent(e.target.value)}
            className="px-4 py-2.5 pr-10 rounded-xl border border-zinc-800/80 bg-zinc-900/60 backdrop-blur-sm text-white text-sm focus:outline-none focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 appearance-none min-w-[200px]"
          >
            <option value="">All Events</option>
            {events.map((e) => (
              <option key={e.id} value={e.id}>
                {e.title}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-zinc-400">
            <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
          </div>
        </div>
      </div>

      {/* Guest list */}
      {loading && guests.length === 0 ? (
        <div className="flex justify-center py-20">
          <Spinner />
        </div>
      ) : guests.length === 0 ? (
        <Card gradient>
          <div className="text-center py-16">
            <div className="inline-flex p-4 rounded-2xl bg-zinc-800/50 mb-5 border border-zinc-700/50 shadow-inner">
              <HiOutlineUserGroup className="w-10 h-10 text-zinc-500" />
            </div>
            <h3 className="text-xl font-medium text-white tracking-tight">No guests found</h3>
            <p className="text-sm text-zinc-400 mt-3 max-w-sm mx-auto leading-relaxed">
              {search || filterEvent
                ? "Try adjusting your search or filter criteria."
                : events.length === 0
                ? "Create an event first, then register guests."
                : "Register your first guest to get started."}
            </p>
            {!search && !filterEvent && events.length > 0 && (
              <div className="mt-6">
                <Link href="/guests/new">
                  <Button variant="primary">Register Guest</Button>
                </Link>
              </div>
            )}
          </div>
        </Card>
      ) : (
        <Card gradient className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b border-zinc-800/80 bg-zinc-900/30">
                  <th className="py-4 px-6 text-zinc-400 font-medium">Photo</th>
                  <th className="py-4 px-6 text-zinc-400 font-medium">Name</th>
                  <th className="py-4 px-6 text-zinc-400 font-medium">Phone</th>
                  <th className="py-4 px-6 text-zinc-400 font-medium">Event</th>
                  <th className="py-4 px-6 text-zinc-400 font-medium">Status</th>
                  <th className="py-4 px-6 text-zinc-400 font-medium">Date</th>
                  <th className="py-4 px-6 text-right text-zinc-400 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {guests.map((guest) => {
                  const event = events.find((e) => e.id === guest.event_id);
                  return (
                    <tr
                      key={guest.id}
                      className="hover:bg-zinc-800/30 transition-colors group"
                    >
                      <td className="py-3 px-6">
                        {guest.image_path ? (
                          <img
                            src={`${API_BASE}/${guest.image_path}`}
                            alt=""
                            className="w-10 h-10 rounded-xl object-cover border border-zinc-700/80 shadow-sm"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-xl bg-zinc-800/80 flex items-center justify-center text-zinc-500 text-xs border border-zinc-700/50">
                            N/A
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-6">
                        <Link
                          href={`/guests/${guest.id}`}
                          className="text-zinc-100 hover:text-indigo-400 transition-colors font-medium tracking-tight"
                        >
                          {guest.first_name} {guest.last_name}
                        </Link>
                        {guest.email && (
                          <p className="text-xs text-zinc-500 mt-0.5">{guest.email}</p>
                        )}
                      </td>
                      <td className="py-3 px-6 text-zinc-300 font-medium">{guest.phone}</td>
                      <td className="py-3 px-6 text-zinc-400 text-xs font-medium">
                        {event?.title ? (
                          <span className="px-2.5 py-1 rounded-md bg-zinc-800/50 border border-zinc-700/50">
                            {event.title}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="py-3 px-6">
                        <span
                          className={`text-xs font-medium px-2.5 py-1 rounded-md border ${
                            embeddingColors[guest.embedding_status]
                          }`}
                        >
                          {guest.embedding_status}
                        </span>
                      </td>
                      <td className="py-3 px-6 text-zinc-500 text-xs font-medium tracking-wide">
                        {new Date(guest.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-6 text-right">
                        <button
                          onClick={() => handleDelete(guest.id)}
                          disabled={deleting === guest.id}
                          className="p-2 rounded-lg text-zinc-500 opacity-0 group-hover:opacity-100 hover:text-red-400 hover:bg-zinc-800 transition-all cursor-pointer disabled:opacity-50"
                          title="Delete Guest"
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
            <div className="flex items-center justify-between px-6 py-4 border-t border-zinc-800/80 bg-zinc-900/20">
              <p className="text-xs text-zinc-500 font-medium">
                Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
              </p>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed border border-transparent hover:border-zinc-700/50"
                >
                  <HiOutlineChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs font-medium text-zinc-400 px-3 py-1.5 rounded-lg bg-zinc-900/50 border border-zinc-800/80">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed border border-transparent hover:border-zinc-700/50"
                >
                  <HiOutlineChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </Card>
      )}
      {/* Modals */}
      {filterEvent && (
        <>
          <NotifyGuestsModal
            eventId={filterEvent}
            isOpen={isNotifyModalOpen}
            onClose={() => setIsNotifyModalOpen(false)}
          />
          
          <ShareEventModal
            eventId={filterEvent}
            isOpen={isShareModalOpen}
            onClose={() => setIsShareModalOpen(false)}
          />
        </>
      )}
    </div>
  );
}
