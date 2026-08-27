"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import api from "@/lib/api";

type TaskType = "drive_import" | "clustering" | "quality_ranking";

export interface ActiveTask {
  id: string; // The batch_id or event_id depending on task
  type: TaskType;
  title: string;
  status: "pending" | "processing" | "completed" | "error";
  progress: number;
  total?: number;
  details?: string;
  eventId: string;
}

interface TaskContextType {
  tasks: ActiveTask[];
  addTask: (task: Omit<ActiveTask, "status" | "progress">) => void;
  removeTask: (id: string) => void;
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

export function TaskProvider({ children }: { children: React.ReactNode }) {
  const [tasks, setTasks] = useState<ActiveTask[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const savedTasks = localStorage.getItem("photo_distr_tasks");
      if (savedTasks) {
        setTasks(JSON.parse(savedTasks));
      }
    } catch (e) {
      console.error("Failed to parse tasks from localStorage", e);
    }
    setIsLoaded(true);
  }, []);

  // Save to localStorage when tasks change
  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem("photo_distr_tasks", JSON.stringify(tasks));
    }
  }, [tasks, isLoaded]);

  const addTask = useCallback((task: Omit<ActiveTask, "status" | "progress">) => {
    setTasks((prev) => {
      if (prev.find((t) => t.id === task.id)) return prev;
      return [...prev, { ...task, status: "processing", progress: 0 }];
    });
  }, []);

  const removeTask = useCallback((id: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Poll for task updates
  useEffect(() => {
    if (tasks.length === 0) return;

    const interval = setInterval(async () => {
      setTasks((prevTasks) => {
        const updatedTasks = [...prevTasks];
        let hasChanges = false;

        const updatePromises = updatedTasks.map(async (task, index) => {
          if (task.status === "completed" || task.status === "error") return;

          try {
            if (task.type === "drive_import") {
              const res = await api.get(`/uploads/batches/${task.id}`);
              const batch = res.data;
              const hasTotal = batch.total_files && batch.total_files > 0;
              const received = batch.received_files || 0;
              
              let progress = 0;
              if (hasTotal) {
                progress = Math.round((received / batch.total_files) * 100);
              }
              
              if (progress !== task.progress || batch.status !== task.status) {
                updatedTasks[index] = {
                  ...task,
                  progress,
                  status: batch.status === "completed" ? "completed" : "processing",
                  details: `${received} / ${batch.total_files || "?"} files`,
                };
                hasChanges = true;
              }
            } else if (task.type === "clustering" || task.type === "quality_ranking") {
              const res = await api.get(`/events/${task.eventId}/pipeline-status`);
              const pipeline = res.data;
              const total = pipeline.photos.pending + pipeline.photos.processing + pipeline.photos.processed + pipeline.photos.failed;
              const processed = pipeline.photos.processed;
              
              const progress = total > 0 ? Math.round((processed / total) * 100) : 0;
              
              if (progress !== task.progress) {
                updatedTasks[index] = {
                  ...task,
                  progress,
                  details: `${processed} / ${total} photos`,
                  status: (total > 0 && processed === total) ? "completed" : "processing",
                };
                hasChanges = true;
              }
            }
          } catch (e) {
            console.error("Task polling failed", e);
          }
        });

        Promise.all(updatePromises).then(() => {
          if (hasChanges) setTasks([...updatedTasks]);
        });
        
        return prevTasks; 
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [tasks.length]);

  return (
    <TaskContext.Provider value={{ tasks, addTask, removeTask }}>
      {children}
    </TaskContext.Provider>
  );
}

export function useTasks() {
  const context = useContext(TaskContext);
  if (context === undefined) {
    throw new Error("useTasks must be used within a TaskProvider");
  }
  return context;
}
