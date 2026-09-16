import { API_URL } from "@/lib/config";
import axios from "axios";

// -- Axios instance --

const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // Send cookies with every request
  timeout: 20_000,
});

// Helper to get cookie by name
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  if (match) return match[2];
  return null;
}

// Attach CSRF token to every request
api.interceptors.request.use((config) => {
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }

  const csrfToken = getCookie("csrf_token");
  if (csrfToken) {
    config.headers["X-CSRF-Token"] = csrfToken;
  }
  return config;
});

// On 401, attempt silent refresh exactly once
let isRefreshing = false;
let failedQueue: Array<{
  resolve: () => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve();
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => {
    console.log("api.ts: Intercepted successful response", response.config.url);
    return response;
  },
  async (error: any) => {
    const originalRequest = error.config as any;
    if (error.code === "ECONNABORTED") {
      error.userMessage = "The server took too long to respond. Please try again.";
    }
    console.log("api.ts: Intercepted error for", originalRequest?.url, error.response?.status);

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry &&
        !originalRequest.url?.includes("/auth/login") &&
        !originalRequest.url?.includes("/auth/refresh") &&
        !originalRequest.url?.includes("/auth/register")) {

      if (isRefreshing) {
        console.log("api.ts: Already refreshing, pushing to queue");
        // Queue subsequent 401s while a refresh is in-flight
        return new Promise<void>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => {
          console.log("api.ts: Retrying queued request", originalRequest.url);
          // CSRF token might have changed, re-fetch it
          const newCsrf = getCookie("csrf_token");
          if (newCsrf) {
            originalRequest.headers["X-CSRF-Token"] = newCsrf;
          }
          return api(originalRequest);
        });
      }

      console.log("api.ts: Starting refresh flow");
      originalRequest._retry = true;
      isRefreshing = true;

      try {
        console.log("api.ts: Calling /auth/refresh");
        // Call refresh endpoint - backend reads refresh_token cookie
        await axios.post(`${API_URL}/auth/refresh`, {}, { withCredentials: true });
        console.log("api.ts: /auth/refresh success");

        processQueue(null);

        const newCsrf = getCookie("csrf_token");
        if (newCsrf) {
          originalRequest.headers["X-CSRF-Token"] = newCsrf;
        }

        console.log("api.ts: Retrying original request");
        return api(originalRequest);
      } catch (refreshError) {
        console.log("api.ts: /auth/refresh failed", refreshError);
        processQueue(refreshError);

        // Redirect to login on refresh failure (client-side only) if not already on an auth page
        if (typeof window !== "undefined") {
          const path = window.location.pathname;
          if (!path.startsWith("/login") && !path.startsWith("/register")) {
            console.log("api.ts: Redirecting to /login");
            window.location.href = "/login";
          }
        }
        console.log("api.ts: Rejecting original promise with refreshError");
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
        console.log("api.ts: Refresh flow finally block completed");
      }
    }

    console.log("api.ts: Rejecting with original error");
    return Promise.reject(error);
  }
);

export default api;
