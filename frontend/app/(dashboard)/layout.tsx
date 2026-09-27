"use client";

export const runtime = "edge";

import { useEffect } from "react";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import Spinner from "@/components/ui/Spinner";
import { navigateWithinOrigin } from "@/lib/navigation";
import { TaskProvider } from "@/contexts/TaskContext";
import GlobalTaskWidget from "@/components/ui/GlobalTaskWidget";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <TaskProvider>
        <GlobalTaskWidget />
        <DashboardContent>{children}</DashboardContent>
      </TaskProvider>
    </AuthProvider>
  );
}

function DashboardContent({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigateWithinOrigin("/login", true);
    }
  }, [isAuthenticated, isLoading]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a]">
        <Spinner />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0e1a]">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="p-6 lg:p-8 max-w-7xl mx-auto animate-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
