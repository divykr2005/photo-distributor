"use client";

import { useParams } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { HiOutlinePhotograph, HiOutlineCheckCircle, HiOutlineExclamationCircle, HiCamera } from "react-icons/hi";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Toast from "@/components/ui/Toast";
import api from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface EventInfo {
  id: string;
  title: string;
  date: string;
}

export default function MobileRegistrationPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const [eventInfo, setEventInfo] = useState<EventInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  
  // Form state
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [gender, setGender] = useState("");
  const [selfie, setSelfie] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!eventId) return;

    fetch(`${API_URL}/public/events/${eventId}`)
      .then(async (res) => {
        if (!res.ok) throw new Error("Event not found");
        return res.json();
      })
      .then((data) => {
        setEventInfo(data);
        setLoading(false);
      })
      .catch((err) => {
        setError("Invalid event link or event has ended.");
        setLoading(false);
      });
  }, [eventId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelfie(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!selfie) {
      setError("Please take a selfie to register.");
      return;
    }

    setSubmitting(true);

    const formData = new FormData();
    formData.append("first_name", firstName);
    formData.append("last_name", lastName);
    formData.append("phone", phone);
    if (email) formData.append("email", email);
    if (gender) formData.append("gender", gender);
    formData.append("file", selfie);

    try {
      const res = await fetch(`${API_URL}/public/events/${eventId}/register`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to register. Please try again.");
      }

      setSuccess(true);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
        <p className="text-zinc-400 font-medium">Loading event details...</p>
      </div>
    );
  }

  if (error && !eventInfo) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/20 mb-4">
          <HiOutlineExclamationCircle className="w-8 h-8 text-red-400" />
        </div>
        <h1 className="text-xl font-semibold text-white tracking-tight mb-2">Event Not Found</h1>
        <p className="text-zinc-400 text-sm leading-relaxed">{error}</p>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 rounded-full bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 mb-6 shadow-[0_0_30px_-5px_rgba(16,185,129,0.3)] animate-in zoom-in duration-500">
          <HiOutlineCheckCircle className="w-10 h-10 text-emerald-400" />
        </div>
        <h1 className="text-3xl font-bold text-white tracking-tight mb-3">You're In!</h1>
        <p className="text-zinc-400 text-base leading-relaxed max-w-sm">
          Thanks for registering for <strong className="text-white">{eventInfo?.title}</strong>. 
          <br /><br />
          We will notify you automatically the moment your photos are ready!
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      {error && <Toast message={error} type="error" onClose={() => setError("")} />}

      {/* Header */}
      <header className="px-6 pt-12 pb-8 border-b border-white/5 bg-zinc-950/50 backdrop-blur-md sticky top-0 z-40">
        <p className="text-indigo-400 text-xs font-bold tracking-widest uppercase mb-1">
          Event Registration
        </p>
        <h1 className="text-3xl font-bold text-white tracking-tight leading-tight">
          {eventInfo?.title}
        </h1>
        <p className="text-zinc-400 text-sm mt-2 font-medium">
          Upload a quick selfie so we can find your photos!
        </p>
      </header>

      {/* Form */}
      <main className="px-6 pt-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          
          {/* Selfie Uploader */}
          <div className="flex flex-col items-center">
            <input 
              type="file"
              accept="image/*"
              capture="user"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
            />
            
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className={`relative overflow-hidden w-40 h-40 rounded-full border-2 flex flex-col items-center justify-center transition-all shadow-xl ${
                previewUrl 
                  ? 'border-indigo-500 shadow-indigo-500/20' 
                  : 'border-dashed border-zinc-700 bg-zinc-900 hover:border-indigo-500/50 hover:bg-zinc-800'
              }`}
            >
              {previewUrl ? (
                <>
                  <img src={previewUrl} alt="Selfie preview" className="w-full h-full object-cover" />
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                    <span className="text-white font-medium text-sm flex items-center gap-2">
                      <HiCamera className="w-5 h-5"/> Retake
                    </span>
                  </div>
                </>
              ) : (
                <div className="text-center p-4">
                  <div className="w-12 h-12 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto mb-2">
                    <HiCamera className="w-6 h-6" />
                  </div>
                  <span className="text-sm font-medium text-zinc-300 block">Tap to Take Selfie</span>
                </div>
              )}
            </button>
            {!previewUrl && (
              <p className="text-xs text-zinc-500 mt-3 text-center max-w-xs">
                Take a clear photo of your face. We use this securely to find you in the event gallery.
              </p>
            )}
          </div>

          <div className="h-px w-full bg-white/5 my-4" />

          {/* Guest Details */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="First Name"
                name="firstName"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
                placeholder="John"
              />
              <Input
                label="Last Name"
                name="lastName"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                placeholder="Doe"
              />
            </div>

            <Input
              label="Phone Number"
              name="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              placeholder="+1 (555) 000-0000"
            />

            <Input
              label="Email Address"
              name="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="john@example.com (Optional)"
            />

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Gender (Optional)
              </label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all appearance-none"
              >
                <option value="">Select gender...</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </div>
          </div>

          <div className="pt-4">
            <Button
              variant="primary"
              type="submit"
              isLoading={submitting}
              className="w-full py-4 text-lg rounded-2xl shadow-indigo-500/20 shadow-xl"
            >
              Complete Registration
            </Button>
            <p className="text-center text-xs text-zinc-600 mt-4 px-4 leading-relaxed">
              By registering, you consent to our secure facial recognition AI processing your selfie solely for the purpose of delivering your event photos.
            </p>
          </div>
        </form>
      </main>
    </div>
  );
}
