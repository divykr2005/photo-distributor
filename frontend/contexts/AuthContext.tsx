"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import api, { setTokens, clearTokens, getRefreshToken } from "@/lib/api";
import type { User, TokenResponse, LoginFormData, RegisterFormData } from "@/types";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (data: LoginFormData) => Promise<void>;
  register: (data: RegisterFormData) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const fetchUser = useCallback(async () => {
    try {
      const { data } = await api.get<User>("/auth/me");
      setUser(data);
    } catch {
      setUser(null);
      clearTokens();
    }
  }, []);

  // On mount: attempt silent refresh if we have a refresh token in memory
  useEffect(() => {
    const tryRefresh = async () => {
      const rt = getRefreshToken();
      if (rt) {
        try {
          const { data } = await api.post<TokenResponse>("/auth/refresh", {
            refresh_token: rt,
          });
          setTokens(data);
          await fetchUser();
        } catch {
          clearTokens();
          setUser(null);
        }
      }
      setIsLoading(false);
    };
    tryRefresh();
  }, [fetchUser]);

  const login = useCallback(
    async (formData: LoginFormData) => {
      // FastAPI OAuth2PasswordRequestForm expects form-urlencoded with "username" field
      const params = new URLSearchParams();
      params.append("username", formData.email);
      params.append("password", formData.password);

      const { data } = await api.post<TokenResponse>("/auth/login", params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      setTokens(data);
      await fetchUser();
      router.push("/dashboard");
    },
    [fetchUser, router]
  );

  const register = useCallback(
    async (formData: RegisterFormData) => {
      // Register the user
      await api.post("/auth/register", {
        name: formData.name,
        email: formData.email,
        password: formData.password,
      });

      // Auto-login after successful registration
      await login({ email: formData.email, password: formData.password });
    },
    [login]
  );

  const logout = useCallback(async () => {
    const rt = getRefreshToken();
    try {
      if (rt) {
        await api.post("/auth/logout", { refresh_token: rt });
      }
    } catch {
      // Ignore logout API errors — we clear tokens regardless
    } finally {
      clearTokens();
      setUser(null);
      router.push("/login");
    }
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
