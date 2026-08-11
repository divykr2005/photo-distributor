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

// ── Guests ──

export interface Guest {
  id: string;
  event_id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
  gender: string | null;
  notes: string | null;
  image_path: string | null;
  embedding_status: "pending" | "success" | "failed";
  consent_given_at: string | null;
  created_at: string;
  updated_at: string;
  expires_at: string;
}

export interface GuestFormData {
  event_id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email?: string;
  gender?: string;
  notes?: string;
}

export interface PaginatedGuests {
  data: Guest[];
  total: number;
  page: number;
  page_size: number;
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

