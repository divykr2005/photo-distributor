"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  HiOutlineCalendar,
  HiOutlineUserGroup,
  HiOutlineUserAdd,
  HiOutlineLightningBolt,
} from "react-icons/hi";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import type { DashboardStats } from "@/types";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

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
      gradient: "from-indigo-500 to-indigo-600",
      shadow: "shadow-indigo-500/20",
    },
    {
      title: "Total Guests",
      value: stats.total_guests,
      icon: <HiOutlineUserGroup className="w-6 h-6" />,
      description: "Guests registered",
      gradient: "from-zinc-400 to-zinc-500",
      shadow: "shadow-zinc-500/20",
    },
    {
      title: "Registered Today",
      value: stats.registered_today,
      icon: <HiOutlineUserAdd className="w-6 h-6" />,
      description: "New guests today",
      gradient: "from-emerald-500 to-emerald-600",
      shadow: "shadow-emerald-500/20",
    },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-white tracking-tight">
            Welcome back, {user?.name?.split(" ")[0] || "Organizer"}
          </h1>
          <p className="text-base text-zinc-400 mt-2">
            Here's an overview of your event platform
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/events/new">
            <Button variant="primary" className="gap-2">
              <HiOutlineLightningBolt className="w-5 h-5" />
              Quick Add Event
            </Button>
          </Link>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        {statCards.map((stat) => (
          <Card key={stat.title} gradient className="group hover:scale-[1.02] transition-transform duration-300">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-zinc-400">
                  {stat.title}
                </p>
                <p className="text-3xl font-bold text-white mt-2 tracking-tight">
                  {stat.value}
                </p>
                <p className="text-xs text-zinc-500 mt-1">
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
            <div className="inline-flex p-4 rounded-2xl bg-zinc-800/50 mb-5 border border-zinc-700/50">
              <HiOutlineCalendar className="w-8 h-8 text-zinc-400" />
            </div>
            <h3 className="text-xl font-medium text-white tracking-tight">
              {stats.total_events > 0 ? "Manage Events" : "Create Your First Event"}
            </h3>
            <p className="text-sm text-zinc-400 mt-3 max-w-sm mx-auto leading-relaxed">
              {stats.total_events > 0
                ? `You have ${stats.total_events} event${stats.total_events > 1 ? "s" : ""}. Manage them or create a new one.`
                : "Start by creating an event. You'll then be able to register guests and distribute photos automatically."}
            </p>
            <div className="mt-6">
              <Link href={stats.total_events > 0 ? "/events" : "/events/new"}>
                <Button variant="primary">
                  {stats.total_events > 0 ? "View Events" : "Create Event"}
                </Button>
              </Link>
            </div>
          </div>
        </Card>

        <Card gradient>
          <div className="text-center py-8">
            <div className="inline-flex p-4 rounded-2xl bg-zinc-800/50 mb-5 border border-zinc-700/50">
              <HiOutlineUserGroup className="w-8 h-8 text-zinc-400" />
            </div>
            <h3 className="text-xl font-medium text-white tracking-tight">
              Register Guests
            </h3>
            <p className="text-sm text-zinc-400 mt-3 max-w-sm mx-auto leading-relaxed">
              Capture guest faces via webcam or upload photos. AI will generate
              embeddings for automatic photo matching.
            </p>
            <div className="flex items-center justify-center gap-3 mt-6">
              <Link href="/guests/new">
                <Button variant="secondary">
                  Register Guest
                </Button>
              </Link>
              <Link href="/guests">
                <Button variant="ghost">
                  View All
                </Button>
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

