// ── Types mirroring the FastAPI backend schemas ──

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ── Events ──

export interface Event {
  id: string;
  title: string;
  description: string | null;
  location: string | null;
  date: string;
  status: "draft" | "active" | "completed" | "cancelled";
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface EventFormData {
  title: string;
  description?: string;
  location?: string;
  date: string;
}

// ── Dashboard ──

export interface DashboardStats {
  total_events: number;
  total_guests: number;
  registered_today: number;
}

// ── Form data types ──

export interface LoginFormData {
  email: string;
  password: string;
}

export interface RegisterFormData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

// ── Dashboard stat card ──

export interface StatCard {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  color: string;
}

