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
import api from "@/lib/api";
import type { User, LoginFormData, RegisterFormData } from "@/types";

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
    }
  }, []);

  // On mount: attempt to fetch user (interceptor handles silent refresh if needed)
  useEffect(() => {
    let active = true;
    const initAuth = async () => {
      try {
        console.log("AuthContext: Starting fetchUser...");
        await fetchUser();
        console.log("AuthContext: fetchUser completed.");
      } catch (err) {
        console.error("AuthContext: fetchUser threw:", err);
      } finally {
        if (active) {
          console.log("AuthContext: Setting isLoading to false");
          setIsLoading(false);
        }
      }
    };
    initAuth();

    const failsafe = setTimeout(() => {
      if (active) {
        console.warn("AuthContext: Failsafe triggered, setting isLoading to false!");
        setIsLoading(false);
      }
    }, 2000);

    return () => {
      active = false;
      clearTimeout(failsafe);
    };
  }, [fetchUser]);

  const login = useCallback(
    async (formData: LoginFormData) => {
      // FastAPI OAuth2PasswordRequestForm expects form-urlencoded with "username" field
      const params = new URLSearchParams();
      params.append("username", formData.email);
      params.append("password", formData.password);

      await api.post("/auth/login", params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      await fetchUser();
      router.push("/dashboard");
    },
    [fetchUser, router]
  );

  const register = useCallback(
    async (formData: RegisterFormData) => {
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
    try {
      await api.post("/auth/logout");
    } catch {
      // Ignore logout API errors
    } finally {
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
