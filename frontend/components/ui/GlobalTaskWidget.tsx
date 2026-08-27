"use client";

import React from "react";
import { useTasks } from "@/contexts/TaskContext";
import { HiOutlineX, HiOutlineCheckCircle, HiOutlineRefresh } from "react-icons/hi";

export default function GlobalTaskWidget() {
  const { tasks, removeTask } = useTasks();

  if (tasks.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-80 max-w-[calc(100vw-2rem)]">
      {tasks.map((task) => (
        <div 
          key={task.id} 
          className="glass-panel rounded-lg p-4 animate-in slide-in-top relative overflow-hidden"
        >
          {/* Progress bar background */}
          <div 
            className="absolute left-0 bottom-0 h-1 bg-indigo-500 transition-all duration-500 ease-out" 
            style={{ width: `${task.progress}%` }} 
          />
          
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {task.status === "processing" || task.status === "pending" ? (
                <HiOutlineRefresh className="w-5 h-5 text-indigo-400 animate-spin" />
              ) : task.status === "completed" ? (
                <HiOutlineCheckCircle className="w-5 h-5 text-emerald-400" />
              ) : (
                <div className="w-5 h-5 rounded-full bg-red-500/20 border border-red-500 flex items-center justify-center text-xs text-red-500">!</div>
              )}
              
              <div>
                <p className="text-sm font-medium text-zinc-100">
                  {task.title}
                </p>
                <p className="text-xs text-zinc-400 mt-0.5 flex items-center gap-2">
                  <span>{task.progress}%</span>
                  {task.details && (
                    <>
                      <span className="w-1 h-1 rounded-full bg-zinc-700"></span>
                      <span>{task.details}</span>
                    </>
                  )}
                </p>
              </div>
            </div>

            {(task.status === "completed" || task.status === "error") && (
              <button 
                onClick={() => removeTask(task.id)}
                className="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
              >
                <HiOutlineX className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
