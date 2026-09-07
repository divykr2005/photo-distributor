"use client";

import { useState } from "react";
import { HiOutlinePencil, HiOutlineCheck, HiOutlineX } from "react-icons/hi";
import api from "@/lib/api";
import type { Guest } from "@/types";

interface InlineGuestEditProps {
  guest: Guest;
  onSaved: (updated: Guest) => void;
}

export default function InlineGuestEdit({ guest, onSaved }: InlineGuestEditProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Local draft mirrors the editable fields
  const [draft, setDraft] = useState({
    first_name: guest.first_name,
    last_name: guest.last_name,
    phone: guest.phone,
    email: guest.email ?? "",
  });

  const startEdit = () => {
    setDraft({
      first_name: guest.first_name,
      last_name: guest.last_name,
      phone: guest.phone,
      email: guest.email ?? "",
    });
    setError("");
    setEditing(true);
  };

  const cancel = () => setEditing(false);

  const save = async () => {
    setSaving(true);
    setError("");

    // Optimistic: we'll revert on failure
    const previous = { ...guest };

    // Build patch — only send fields that actually changed
    const patch: Record<string, string | null> = {};
    if (draft.first_name !== guest.first_name) patch.first_name = draft.first_name;
    if (draft.last_name !== guest.last_name) patch.last_name = draft.last_name;
    if (draft.phone !== guest.phone) patch.phone = draft.phone;
    if (draft.email !== (guest.email ?? "")) patch.email = draft.email || null;

    if (Object.keys(patch).length === 0) {
      setEditing(false);
      setSaving(false);
      return;
    }

    // Send If-Match for optimistic concurrency
    const etag = String(new Date(guest.updated_at).getTime() / 1000);

    try {
      const { data } = await api.put<Guest>(`/guests/${guest.id}`, patch, {
        headers: { "If-Match": `"${etag}"` },
      });
      onSaved(data);
      setEditing(false);
    } catch (err: any) {
      // Rollback optimistic state — caller still has original
      if (err?.response?.status === 412) {
        setError("Someone else updated this guest. Refresh and try again.");
      } else {
        setError("Save failed. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <button
        onClick={startEdit}
        className="p-2 rounded-lg text-zinc-500 opacity-0 group-hover:opacity-100 hover:text-indigo-400 hover:bg-zinc-800 transition-all cursor-pointer"
        title="Edit Guest"
      >
        <HiOutlinePencil className="w-4 h-4" />
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={cancel}>
      <div
        className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-white">Edit Guest</h3>

        {error && (
          <p className="text-sm text-red-400 bg-red-950/30 border border-red-800/50 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-zinc-400 mb-1 font-medium">First Name</label>
            <input
              className="w-full px-3 py-2 rounded-xl border border-zinc-700 bg-zinc-800/60 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={draft.first_name}
              onChange={(e) => setDraft((d) => ({ ...d, first_name: e.target.value }))}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1 font-medium">Last Name</label>
            <input
              className="w-full px-3 py-2 rounded-xl border border-zinc-700 bg-zinc-800/60 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={draft.last_name}
              onChange={(e) => setDraft((d) => ({ ...d, last_name: e.target.value }))}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1 font-medium">Phone</label>
          <input
            className="w-full px-3 py-2 rounded-xl border border-zinc-700 bg-zinc-800/60 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={draft.phone}
            onChange={(e) => setDraft((d) => ({ ...d, phone: e.target.value }))}
          />
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1 font-medium">Email <span className="text-zinc-600">(optional)</span></label>
          <input
            type="email"
            className="w-full px-3 py-2 rounded-xl border border-zinc-700 bg-zinc-800/60 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={draft.email}
            onChange={(e) => setDraft((d) => ({ ...d, email: e.target.value }))}
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={cancel}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors border border-zinc-700"
          >
            <HiOutlineX className="w-4 h-4" /> Cancel
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-60"
          >
            <HiOutlineCheck className="w-4 h-4" />
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
