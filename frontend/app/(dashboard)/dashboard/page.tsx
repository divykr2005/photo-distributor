"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  HiOutlineCalendar,
  HiOutlineUserGroup,
  HiOutlineUserAdd,
} from "react-icons/hi";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import type { DashboardStats } from "@/types";
import Card from "@/components/ui/Card";

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    total_events: 0,
    total_guests: 0,
    registered_today: 0,
  });

  useEffect(() => {
    api
      .get<DashboardStats>("/dashboard/stats")
      .then(({ data }) => setStats(data))
      .catch(() => {}); // silently fail, cards show 0
  }, []);

  const statCards = [
    {
      title: "Total Events",
      value: stats.total_events,
      icon: <HiOutlineCalendar className="w-6 h-6" />,
      description: "Events created",
      gradient: "from-violet-500 to-indigo-500",
      shadow: "shadow-violet-500/20",
    },
    {
      title: "Total Guests",
      value: stats.total_guests,
      icon: <HiOutlineUserGroup className="w-6 h-6" />,
      description: "Guests registered",
      gradient: "from-cyan-500 to-blue-500",
      shadow: "shadow-cyan-500/20",
    },
    {
      title: "Registered Today",
      value: stats.registered_today,
      icon: <HiOutlineUserAdd className="w-6 h-6" />,
      description: "New guests today",
      gradient: "from-emerald-500 to-teal-500",
      shadow: "shadow-emerald-500/20",
    },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">
          Welcome back, {user?.name?.split(" ")[0] || "Organizer"} 👋
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Here&apos;s an overview of your event platform
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {statCards.map((stat) => (
          <Card key={stat.title} gradient className="group hover:scale-[1.02] transition-transform duration-300">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">
                  {stat.title}
                </p>
                <p className="text-3xl font-bold text-white mt-2">
                  {stat.value}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {stat.description}
                </p>
              </div>
              <div
                className={`p-3 rounded-xl bg-gradient-to-br ${stat.gradient} shadow-lg ${stat.shadow} text-white`}
              >
                {stat.icon}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card gradient>
          <div className="text-center py-8">
            <div className="inline-flex p-4 rounded-2xl bg-slate-700/30 mb-4">
              <HiOutlineCalendar className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-semibold text-white">
              {stats.total_events > 0 ? "Manage Events" : "Create Your First Event"}
            </h3>
            <p className="text-sm text-slate-400 mt-2 max-w-sm mx-auto">
              {stats.total_events > 0
                ? `You have ${stats.total_events} event${stats.total_events > 1 ? "s" : ""}. Manage them or create a new one.`
                : "Start by creating an event. You'll then be able to register guests and distribute photos automatically."}
            </p>
            <Link
              href={stats.total_events > 0 ? "/events" : "/events/new"}
              className="inline-block mt-4"
            >
              <button className="px-5 py-2.5 rounded-xl text-sm font-medium bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 transition-all shadow-lg shadow-violet-500/25 cursor-pointer">
                {stats.total_events > 0 ? "View Events" : "Create Event"}
              </button>
            </Link>
          </div>
        </Card>

        <Card gradient>
          <div className="text-center py-8">
            <div className="inline-flex p-4 rounded-2xl bg-slate-700/30 mb-4">
              <HiOutlineUserGroup className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-semibold text-white">
              Register Guests
            </h3>
            <p className="text-sm text-slate-400 mt-2 max-w-sm mx-auto">
              Capture guest faces via webcam or upload photos. AI will generate
              embeddings for automatic photo matching.
            </p>
            <button
              className="mt-4 px-5 py-2.5 rounded-xl text-sm font-medium bg-gradient-to-r from-cyan-600 to-blue-600 text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-lg shadow-cyan-500/25 cursor-pointer disabled:opacity-50"
              disabled
            >
              Coming Soon
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}

