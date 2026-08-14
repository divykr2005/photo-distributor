import api from "@/lib/api";

export interface UploadBatch {
  id: string;
  event_id: string;
  created_by: string;
  total_files: number;
  received_files: number;
  duplicate_files: number;
  rejected_files: number;
  processed_files: number;
  failed_files: number;
  faces_found: number;
  matches_created: number;
  status: string;
  created_at: string;
  completed_at?: string;
}

export async function createUploadBatch(eventId: string, totalFiles: number): Promise<UploadBatch> {
  const { data } = await api.post<UploadBatch>(`/events/${eventId}/upload-batches`, {
    total_files: totalFiles,
  });
  return data;
}

export async function getUploadBatch(batchId: string): Promise<UploadBatch> {
  const { data } = await api.get<UploadBatch>(`/upload-batches/${batchId}`);
  return data;
}

export async function uploadSinglePhoto(
  eventId: string,
  file: File,
  batchId?: string,
  onProgress?: (progress: number) => void
): Promise<{ photo_id: string; duplicate: boolean }> {
  const formData = new FormData();
  formData.append("file", file);
  if (batchId) {
    formData.append("batch_id", batchId);
  }

  const { data } = await api.post<{ photo_id: string; duplicate: boolean }>(
    `/events/${eventId}/photos`,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
    }
  );
  return data;
}
