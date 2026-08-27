"use client";

import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";

interface NotifyGuestsModalProps {
  eventId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface PreviewData {
  channel: string;
  total_guests: number;
  eligible_recipients: number;
  skipped_zero_photos: number;
  skipped_opt_out: number;
  skipped_duplicate: number;
  sample_preview: {
    subject: string;
    text_content: string;
    sample_recipient: string;
  };
}

interface NotificationLogItem {
  id: string;
  guest_id: string;
  guest_name: string;
  channel: string;
  status: string;
  recipient: string | null;
  error_message: string | null;
  retry_count: number;
  next_retry_at: string | null;
  created_at: string;
  updated_at: string;
}

interface StatusResponse {
  summary: {
    total: number;
    queued: number;
    sent: number;
    failed: number;
    skipped: number;
  };
  logs: NotificationLogItem[];
}

export default function NotifyGuestsModal({
  eventId,
  isOpen,
  onClose,
}: NotifyGuestsModalProps) {
  const [channel, setChannel] = useState<string>("console");
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [statusData, setStatusData] = useState<StatusResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testRecipient, setTestRecipient] = useState("");
  const [testSuccess, setTestSuccess] = useState("");
  const [error, setError] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [activeTab, setActiveTab] = useState<"preview" | "status">("preview");

  const fetchPreview = useCallback(async () => {
    setLoadingPreview(true);
    setError("");
    try {
      const { data } = await api.get<PreviewData>(
        `/events/${eventId}/notifications/preview?channel=${channel}`
      );
      setPreview(data);
    } catch {
      setError("Failed to fetch notification preview");
    } finally {
      setLoadingPreview(false);
    }
  }, [eventId, channel]);

  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await api.get<StatusResponse>(
        `/events/${eventId}/notifications/status`
      );
      setStatusData(data);
    } catch {
      // silent catch for polling
    }
  }, [eventId]);

  useEffect(() => {
    if (isOpen) {
      fetchPreview();
      fetchStatus();
    }
  }, [isOpen, fetchPreview, fetchStatus]);

  // Polling status when status tab is active or dispatching
  useEffect(() => {
    if (!isOpen) return;
    const interval = setInterval(() => {
      fetchStatus();
    }, 2000);
    return () => clearInterval(interval);
  }, [isOpen, fetchStatus]);

  if (!isOpen) return null;

  const handleDispatch = async () => {
    setDispatching(true);
    setError("");
    try {
      await api.post(`/events/${eventId}/notifications/dispatch`, {
        channel,
      });
      setShowConfirm(false);
      setActiveTab("status");
      await fetchStatus();
    } catch {
      setError("Failed to dispatch notifications");
    } finally {
      setDispatching(false);
    }
  };

  const handleTestNotification = async () => {
    if (!testRecipient) {
      setError("Please enter a test recipient contact info");
      return;
    }
    setTesting(true);
    setTestSuccess("");
    setError("");
    try {
      await api.post(`/events/${eventId}/notifications/test`, {
        channel,
        recipient: testRecipient,
      });
      setTestSuccess(`Test notification sent successfully to ${testRecipient}`);
    } catch {
      setError("Failed to send test notification");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span>📢</span> Notify Guests (Magic Links)
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Send personalized photo gallery links directly to matched guests
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors text-lg"
          >
            ✕
          </button>
        </div>

        {/* Tab Header */}
        <div className="flex border-b border-slate-800 bg-slate-950/50 px-6 pt-2">
          <button
            onClick={() => setActiveTab("preview")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "preview"
                ? "border-violet-500 text-violet-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Preview & Dispatch
          </button>
          <button
            onClick={() => setActiveTab("status")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "status"
                ? "border-violet-500 text-violet-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Delivery Status Log
            {statusData && statusData.summary.total > 0 && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-violet-950 text-violet-300 border border-violet-800">
                {statusData.summary.total}
              </span>
            )}
          </button>
        </div>

        {/* Modal Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {error && (
            <Toast message={error} type="error" onClose={() => setError("")} />
          )}
          {testSuccess && (
            <Toast
              message={testSuccess}
              type="success"
              onClose={() => setTestSuccess("")}
            />
          )}

          {activeTab === "preview" ? (
            <div className="space-y-6">
              {/* Channel Selector */}
              <div>
                <label className="block text-sm font-semibold text-slate-200 mb-2">
                  Select Notification Channel
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {[
                    { id: "console", label: "Console Log", desc: "Dev Mode" },
                    { id: "smtp", label: "Email", desc: "SMTP Magic Link" },
                    { id: "webhook", label: "Webhook", desc: "HTTP Event" },
                    { id: "twilio_sms", label: "SMS", desc: "Twilio SMS" },
                    { id: "twilio_whatsapp", label: "WhatsApp", desc: "Twilio WA" },
                  ].map((ch) => (
                    <button
                      key={ch.id}
                      onClick={() => setChannel(ch.id)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        channel === ch.id
                          ? "border-violet-500 bg-violet-950/30 text-white"
                          : "border-slate-800 bg-slate-800/40 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <div className="font-semibold text-xs text-white">
                        {ch.label}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        {ch.desc}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Preview Breakdown Card */}
              {loadingPreview ? (
                <div className="flex justify-center py-8">
                  <Spinner />
                </div>
              ) : preview ? (
                <div className="space-y-4">
                  {/* Recipient Breakdown Stats */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-emerald-950/30 border border-emerald-800/50 p-3.5 rounded-xl">
                      <div className="text-xs text-emerald-400 font-medium">
                        Eligible Recipients
                      </div>
                      <div className="text-2xl font-bold text-emerald-300 mt-1">
                        {preview.eligible_recipients}
                      </div>
                    </div>
                    <div className="bg-slate-800/40 border border-slate-700/50 p-3.5 rounded-xl">
                      <div className="text-xs text-slate-400 font-medium">
                        Skipped (0 Photos)
                      </div>
                      <div className="text-2xl font-bold text-slate-300 mt-1">
                        {preview.skipped_zero_photos}
                      </div>
                    </div>
                    <div className="bg-amber-950/30 border border-amber-800/50 p-3.5 rounded-xl">
                      <div className="text-xs text-amber-400 font-medium">
                        Skipped (Opt-out)
                      </div>
                      <div className="text-2xl font-bold text-amber-300 mt-1">
                        {preview.skipped_opt_out}
                      </div>
                    </div>
                    <div className="bg-blue-950/30 border border-blue-800/50 p-3.5 rounded-xl">
                      <div className="text-xs text-blue-400 font-medium">
                        Skipped (Duplicate)
                      </div>
                      <div className="text-2xl font-bold text-blue-300 mt-1">
                        {preview.skipped_duplicate}
                      </div>
                    </div>
                  </div>

                  {/* Sample Message Card */}
                  {preview.sample_preview && (
                    <Card gradient className="p-4 space-y-2">
                      <div className="text-xs font-semibold text-violet-400 uppercase tracking-wider">
                        Sample Rendered Message
                      </div>
                      {preview.sample_preview.subject && (
                        <div className="text-sm font-semibold text-white">
                          Subject: {preview.sample_preview.subject}
                        </div>
                      )}
                      <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">
                        {preview.sample_preview.text_content || ""}
                      </div>
                    </Card>
                  )}

                  {/* Test Dispatch Form */}
                  <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-3">
                    <div className="text-xs font-semibold text-slate-300">
                      Send Test Notification
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder={
                          channel === "smtp"
                            ? "test@example.com"
                            : channel === "twilio_sms" || channel === "twilio_whatsapp"
                            ? "+1234567890"
                            : "Console / Webhook URL"
                        }
                        value={testRecipient}
                        onChange={(e) => setTestRecipient(e.target.value)}
                        className="flex-1 px-3 py-2 text-xs rounded-xl border border-slate-700 bg-slate-900 text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                      />
                      <Button
                        variant="secondary"
                        size="sm"
                        isLoading={testing}
                        onClick={handleTestNotification}
                      >
                        Send Test
                      </Button>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            /* Status Log Tab */
            <div className="space-y-4">
              {statusData && (
                <div className="grid grid-cols-5 gap-2">
                  <div className="bg-slate-800/40 border border-slate-700/50 p-2.5 rounded-xl text-center">
                    <div className="text-[11px] text-slate-400">Total</div>
                    <div className="text-lg font-bold text-white">
                      {statusData.summary.total}
                    </div>
                  </div>
                  <div className="bg-amber-950/30 border border-amber-800/50 p-2.5 rounded-xl text-center">
                    <div className="text-[11px] text-amber-400">Queued</div>
                    <div className="text-lg font-bold text-amber-300">
                      {statusData.summary.queued}
                    </div>
                  </div>
                  <div className="bg-emerald-950/30 border border-emerald-800/50 p-2.5 rounded-xl text-center">
                    <div className="text-[11px] text-emerald-400">Sent</div>
                    <div className="text-lg font-bold text-emerald-300">
                      {statusData.summary.sent}
                    </div>
                  </div>
                  <div className="bg-red-950/30 border border-red-800/50 p-2.5 rounded-xl text-center">
                    <div className="text-[11px] text-red-400">Failed</div>
                    <div className="text-lg font-bold text-red-300">
                      {statusData.summary.failed}
                    </div>
                  </div>
                  <div className="bg-blue-950/30 border border-blue-800/50 p-2.5 rounded-xl text-center">
                    <div className="text-[11px] text-blue-400">Skipped</div>
                    <div className="text-lg font-bold text-blue-300">
                      {statusData.summary.skipped}
                    </div>
                  </div>
                </div>
              )}

              {/* Logs Table */}
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/50">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="px-4 py-3">Guest Name</th>
                      <th className="px-4 py-3">Channel</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Details / Next Retry</th>
                      <th className="px-4 py-3">Sent At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {statusData?.logs.length === 0 ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="px-4 py-8 text-center text-slate-500"
                        >
                          No notification dispatch logs recorded yet.
                        </td>
                      </tr>
                    ) : (
                      statusData?.logs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-900/40">
                          <td className="px-4 py-2.5 font-medium text-white">
                            {log.guest_name}
                          </td>
                          <td className="px-4 py-2.5 uppercase text-[10px] tracking-wider text-slate-400">
                            {log.channel}
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                log.status === "sent" || log.status === "delivered"
                                  ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                  : log.status === "queued"
                                  ? "bg-amber-950 text-amber-300 border border-amber-800"
                                  : log.status === "failed"
                                  ? "bg-red-950 text-red-300 border border-red-800"
                                  : "bg-slate-800 text-slate-400 border border-slate-700"
                              }`}
                            >
                              {log.status}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-slate-400 truncate max-w-xs">
                            {log.error_message ||
                              (log.next_retry_at
                                ? `Retry scheduled at ${new Date(
                                    log.next_retry_at
                                  ).toLocaleTimeString()}`
                                : "—")}
                          </td>
                          <td className="px-4 py-2.5 text-slate-400">
                            {new Date(log.created_at).toLocaleTimeString()}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer / Actions */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/50 flex justify-between items-center">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>

          {activeTab === "preview" && (
            <div className="flex gap-2">
              {showConfirm ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-amber-400 font-medium">
                    Confirm send to {preview?.eligible_recipients || 0} guests?
                  </span>
                  <Button
                    size="sm"
                    isLoading={dispatching}
                    onClick={handleDispatch}
                  >
                    Confirm & Send
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setShowConfirm(false)}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <Button
                  size="sm"
                  disabled={!preview || preview.eligible_recipients === 0}
                  onClick={() => setShowConfirm(true)}
                >
                  Dispatch Notifications ({preview?.eligible_recipients || 0})
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
