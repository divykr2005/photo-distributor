"use client";

import { useState } from "react";
import { HiOutlineLink, HiOutlineQrcode, HiOutlineX, HiCheck } from "react-icons/hi";
import Button from "@/components/ui/Button";

interface ShareEventModalProps {
  eventId: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function ShareEventModal({ eventId, isOpen, onClose }: ShareEventModalProps) {
  const [copied, setCopied] = useState(false);
  
  if (!isOpen) return null;

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || (typeof window !== 'undefined' ? window.location.origin : '');
  const registrationLink = `${appUrl}/register/${eventId}`;
  
  // Free public API for generating QR codes
  const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(registrationLink)}&color=09090b&bgcolor=ffffff`;

  const handleCopy = () => {
    navigator.clipboard.writeText(registrationLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/80 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl animate-in fade-in zoom-in-95 duration-200 overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-zinc-800/80">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <HiOutlineQrcode className="w-5 h-5 text-indigo-400" />
            Share Registration
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-zinc-400 hover:text-white transition-colors rounded-lg hover:bg-zinc-800"
          >
            <HiOutlineX className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-zinc-400 text-sm mb-6 text-center">
            Print this QR code or share the link so guests can upload their selfies and register for notifications.
          </p>

          {/* QR Code display */}
          <div className="flex justify-center mb-6">
            <div className="bg-white p-4 rounded-xl shadow-lg inline-block ring-4 ring-indigo-500/10">
              <img 
                src={qrCodeUrl} 
                alt="Registration QR Code" 
                className="w-48 h-48 rounded"
              />
            </div>
          </div>

          {/* Copy Link field */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
              Direct Link
            </label>
            <div className="flex flex-col sm:flex-row items-center gap-2">
              <div className="flex-1 w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-zinc-300 text-sm truncate select-all">
                {registrationLink}
              </div>
              <Button
                variant={copied ? "primary" : "secondary"}
                onClick={handleCopy}
                className="w-full sm:w-auto h-11 px-4 flex items-center justify-center gap-2 whitespace-nowrap"
              >
                {copied ? (
                  <>
                    <HiCheck className="w-4 h-4" /> Copied!
                  </>
                ) : (
                  <>
                    <HiOutlineLink className="w-4 h-4" /> Copy
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>

        <div className="p-5 bg-zinc-950/50 border-t border-zinc-800/80 flex justify-end">
          <Button variant="ghost" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  );
}
