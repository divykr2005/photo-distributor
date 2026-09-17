"use client";

import { useParams } from "next/navigation";
import { useState, useEffect } from "react";
import { HiOutlineCheckCircle, HiOutlineExclamationCircle } from "react-icons/hi";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Toast from "@/components/ui/Toast";
import CameraCapture from "@/components/ui/CameraCapture";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface EventInfo {
  id: string;
  title: string;
  date: string;
  biometric_consent_text_version: string;
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

  // OTP State
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [verificationToken, setVerificationToken] = useState<string | null>(null);
  const [otpBusy, setOtpBusy] = useState(false);

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

  const handleSendOtp = async () => {
    if (!email) return;
    setError("");
    setOtpBusy(true);
    try {
      const response = await fetch(`${API_URL}/public/events/${eventId}/email-otp/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to send verification code.");
      setOtpSent(true);
      setOtp("");
    } catch (err: any) {
      setError(err.message || "Failed to send OTP.");
    } finally {
      setOtpBusy(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!email || !otp) return;
    setError("");
    setOtpBusy(true);
    try {
      const response = await fetch(`${API_URL}/public/events/${eventId}/email-otp/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code: otp }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Invalid verification code.");
      setVerificationToken(data.verification_token);
    } catch (err: any) {
      setError(err.message || "Invalid OTP.");
    } finally {
      setOtpBusy(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!selfie) {
      setError("Please take a selfie to register.");
      return;
    }

    if (!verificationToken) {
      setError("Please verify your email address first.");
      return;
    }

    setSubmitting(true);

    const formData = new FormData();
    formData.append("first_name", firstName);
    formData.append("last_name", lastName);
    formData.append("phone", phone);
    formData.append("email", email);
    formData.append("email_verification_token", verificationToken);
    if (gender) formData.append("gender", gender);
    formData.append("file", selfie);
    // Required by backend — biometric consent is implicit in this public registration form
    formData.append("biometric_consent", "true");
    formData.append(
      "biometric_consent_text_version",
      eventInfo?.biometric_consent_text_version || ""
    );
    try {
      const res = await fetch(`${API_URL}/public/events/${eventId}/register`, {
        method: "POST",
        body: formData,
        signal: AbortSignal.timeout(120_000),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to register. Please try again.");
      }

      setSuccess(true);
    } catch (err: any) {
      setError(err?.name === "TimeoutError" ? "Registration timed out. Please try again." : err.message || "An unexpected error occurred.");
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
          Take a quick selfie so we can find your photos!
        </p>
      </header>

      {/* Form */}
      <main className="px-6 pt-8">
        <form onSubmit={handleSubmit} className="space-y-6">

          {/* Camera-only selfie capture */}
          <div className="flex flex-col items-center">
            <CameraCapture onCapture={setSelfie} allowUpload={false} />
            <p className="text-xs text-zinc-500 mt-3 text-center max-w-xs">
              Camera permission is used only to capture this selfie. Gallery uploads are disabled.
            </p>
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

            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <Input
                  label="Email Address"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setOtpSent(false);
                    setVerificationToken(null);
                  }}
                  required
                  placeholder="john@example.com"
                  disabled={!!verificationToken}
                />
              </div>
              {!verificationToken && (
                <Button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={!email || otpBusy}
                >
                  {otpBusy ? "Sending..." : otpSent ? "Resend" : "Send Code"}
                </Button>
              )}
            </div>

            {otpSent && !verificationToken && (
              <div className="flex gap-2 items-end mt-2 animate-in fade-in zoom-in duration-300">
                <div className="flex-1">
                  <Input
                    label="Enter OTP"
                    name="otp"
                    type="text"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    required
                    placeholder="123456"
                  />
                </div>
                <Button
                  type="button"
                  onClick={handleVerifyOtp}
                  disabled={!otp || otpBusy}
                >
                  Confirm
                </Button>
              </div>
            )}

            {verificationToken && (
              <p className="text-emerald-400 text-sm font-medium flex items-center gap-1">
                <HiOutlineCheckCircle className="w-5 h-5"/> Email Verified
              </p>
            )}

            <Input
              label="Phone Number"
              name="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              placeholder="+91 98765 43210"
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
            type="submit"
            variant="primary"
            disabled={submitting || !verificationToken}
            className="w-full h-12 text-base font-semibold mt-8 shadow-indigo-500/25"
          >
            {submitting ? "Registering..." : "Submit Registration"}
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
