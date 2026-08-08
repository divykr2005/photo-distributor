"use client";

import { useAuth } from "@/contexts/AuthContext";
import { HiOutlineCamera, HiOutlineLogout } from "react-icons/hi";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className="h-16 border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="h-full px-6 flex items-center justify-between">
        {/* Logo / Brand */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/20">
            <HiOutlineCamera className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">
              PhotoDistro
            </h1>
            <p className="text-[10px] text-slate-500 -mt-0.5 font-medium uppercase tracking-widest">
              AI Event Photos
            </p>
          </div>
        </div>

        {/* User section */}
        <div className="flex items-center gap-4">
          {user && (
            <div className="hidden sm:flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center text-sm font-bold text-white shadow-lg shadow-violet-500/20">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-slate-200">
                  {user.name}
                </p>
                <p className="text-xs text-slate-500">{user.email}</p>
              </div>
            </div>
          )}
          <button
            onClick={logout}
            className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800/50 transition-all duration-200 cursor-pointer"
            title="Logout"
          >
            <HiOutlineLogout className="w-5 h-5" />
          </button>
        </div>
      </div>
    </nav>
  );
}
