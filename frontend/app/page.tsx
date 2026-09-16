"use client";

import { useEffect } from "react";
import Spinner from "@/components/ui/Spinner";
import { navigateWithinOrigin } from "@/lib/navigation";

export default function Home() {
  useEffect(() => {
    navigateWithinOrigin("/dashboard", true);
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a]">
      <Spinner />
    </div>
  );
}
