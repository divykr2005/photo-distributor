import { API_URL } from "@/lib/config";
import axios from "axios";

// -- Axios instance --

const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // Send cookies with every request
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
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only intercept 401s, skip if this is already a retry or a refresh/login call
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes("/auth/login") ||
      originalRequest.url?.includes("/auth/refresh") ||
      originalRequest.url?.includes("/auth/register")
    ) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Queue subsequent 401s while a refresh is in-flight
      return new Promise<void>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(() => {
        // CSRF token might have changed, re-fetch it
        const newCsrf = getCookie("csrf_token");
        if (newCsrf) {
          originalRequest.headers["X-CSRF-Token"] = newCsrf;
        }
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // Call refresh endpoint - backend reads refresh_token cookie
      await axios.post(`${API_URL}/auth/refresh`, {}, { withCredentials: true });

      processQueue(null);

      // Re-fetch the CSRF token from the new cookie
      const newCsrf = getCookie("csrf_token");
      if (newCsrf) {
        originalRequest.headers["X-CSRF-Token"] = newCsrf;
      }
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError);
      
      // Redirect to login on refresh failure (client-side only)
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;
