"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";

export function useAuthImage(src: string | undefined | null) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    if (!src) {
      setObjectUrl(null);
      setLoading(false);
      setError(false);
      return;
    }

    let active = true;
    let createdUrl: string | null = null;
    setLoading(true);
    setError(false);

    api
      .get(src, { responseType: "arraybuffer" })
      .then((res) => {
        const contentType = res.headers["content-type"];
        const mime = typeof contentType === "string" ? contentType : "image/jpeg";
        const blob = new Blob([res.data], { type: mime });
        createdUrl = URL.createObjectURL(blob);
        setObjectUrl(createdUrl);
        setLoading(false);
      })
      .catch((err) => {
        if (!active) return;
        console.error("Failed to load authenticated image:", err);
        setError(true);
        setLoading(false);
      });

    return () => {
      active = false;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [src]);

  return { objectUrl, loading, error };
}
