"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { HiOutlineCamera, HiOutlineMail, HiOutlineLockClosed } from "react-icons/hi";
import { useAuth } from "@/contexts/AuthContext";
import { loginSchema, type LoginSchema } from "@/lib/validators";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Toast from "@/components/ui/Toast";
import GoogleLoginButton from "@/components/ui/GoogleLoginButton";

import { useSearchParams } from "next/navigation";
import { useEffect } from "react";

export default function LoginPage() {
  const { login } = useAuth();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const errorParam = searchParams.get("error");
    if (errorParam === "oauth_failed") {
      setError("Google Login failed. Please check your OAuth credentials.");
    } else if (errorParam === "oauth_missing_tokens") {
      setError("Google Login failed. Missing tokens.");
    }
  }, [searchParams]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginSchema>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginSchema) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await login(data);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Login failed. Please check your credentials.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="animate-in">
      {/* Logo */}
      <div className="text-center mb-8">
        <div className="inline-flex p-3 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-2xl shadow-violet-500/30 mb-4">
          <HiOutlineCamera className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-2xl font-bold text-white">Welcome back</h1>
        <p className="text-sm text-slate-400 mt-1">
          Sign in to your PhotoDistro account
        </p>
      </div>

      {/* Form card */}
      <div className="bg-slate-800/30 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-8 shadow-2xl shadow-black/30">
        {error && (
          <div className="mb-6">
            <Toast message={error} type="error" onClose={() => setError(null)} />
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div className="relative">
            <Input
              id="login-email"
              label="Email"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              error={errors.email?.message}
              {...register("email")}
            />
            <HiOutlineMail className="absolute right-3 top-9 w-5 h-5 text-slate-500 pointer-events-none" />
          </div>

          <div className="relative">
            <Input
              id="login-password"
              label="Password"
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              error={errors.password?.message}
              {...register("password")}
            />
            <HiOutlineLockClosed className="absolute right-3 top-9 w-5 h-5 text-slate-500 pointer-events-none" />
          </div>

          <Button
            type="submit"
            className="w-full"
            size="lg"
            isLoading={isSubmitting}
          >
            Sign In
          </Button>
        </form>

        <div className="mt-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-slate-700/50"></div>
          <span className="text-xs text-slate-500 font-medium">OR</span>
          <div className="h-px flex-1 bg-slate-700/50"></div>
        </div>

        <div className="mt-6">
          <GoogleLoginButton />
        </div>

        <p className="text-center text-sm text-slate-400 mt-6">
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="text-violet-400 hover:text-violet-300 font-medium transition-colors"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
