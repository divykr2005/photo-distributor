"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  HiOutlineCamera,
  HiOutlineUser,
  HiOutlineMail,
  HiOutlineLockClosed,
} from "react-icons/hi";
import { useAuth } from "@/contexts/AuthContext";
import { registerSchema, type RegisterSchema } from "@/lib/validators";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Toast from "@/components/ui/Toast";
import GoogleLoginButton from "@/components/ui/GoogleLoginButton";

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterSchema>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterSchema) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await registerUser(data);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Registration failed. Please try again.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="animate-in">
      {/* Logo */}
      <div className="text-center mb-8">
        <div className="inline-flex p-3 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 shadow-xl shadow-indigo-500/10 mb-4">
          <HiOutlineCamera className="w-8 h-8 text-indigo-400" />
        </div>
        <h1 className="text-2xl font-bold text-zinc-100">Create your account</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Get started with PhotoDistro
        </p>
      </div>

      {/* Form card */}
      <div className="glass-panel rounded-2xl p-8 shadow-2xl">
        {error && (
          <div className="mb-6">
            <Toast message={error} type="error" onClose={() => setError(null)} />
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div className="relative">
            <Input
              id="register-name"
              label="Full Name"
              type="text"
              placeholder="John Doe"
              autoComplete="name"
              error={errors.name?.message}
              {...register("name")}
            />
            <HiOutlineUser className="absolute right-3 top-9 w-5 h-5 text-zinc-500 pointer-events-none" />
          </div>

          <div className="relative">
            <Input
              id="register-email"
              label="Email"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              error={errors.email?.message}
              {...register("email")}
            />
            <HiOutlineMail className="absolute right-3 top-9 w-5 h-5 text-zinc-500 pointer-events-none" />
          </div>

          <div className="relative">
            <Input
              id="register-password"
              label="Password"
              type="password"
              placeholder="••••••••"
              autoComplete="new-password"
              error={errors.password?.message}
              {...register("password")}
            />
            <HiOutlineLockClosed className="absolute right-3 top-9 w-5 h-5 text-zinc-500 pointer-events-none" />
          </div>

          <div className="relative">
            <Input
              id="register-confirm-password"
              label="Confirm Password"
              type="password"
              placeholder="••••••••"
              autoComplete="new-password"
              error={errors.confirmPassword?.message}
              {...register("confirmPassword")}
            />
            <HiOutlineLockClosed className="absolute right-3 top-9 w-5 h-5 text-zinc-500 pointer-events-none" />
          </div>

          <Button
            type="submit"
            className="w-full"
            size="lg"
            isLoading={isSubmitting}
          >
            Create Account
          </Button>
        </form>

        <div className="mt-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-zinc-800"></div>
          <span className="text-xs text-zinc-500 font-medium">OR</span>
          <div className="h-px flex-1 bg-zinc-800"></div>
        </div>

        <div className="mt-6">
          <GoogleLoginButton />
        </div>

        <p className="text-center text-sm text-zinc-400 mt-6">
          Already have an account?{" "}
          <Link
            href="/login"
            className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
