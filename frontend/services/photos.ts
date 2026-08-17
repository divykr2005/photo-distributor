import api from "@/lib/api";

export interface PhotoFace {
  id: string;
  photo_id: string;
  event_id: string;
  bbox_x: number;
  bbox_y: number;
  bbox_w: number;
  bbox_h: number;
  det_score: number;
  quality_score?: number;
  is_matchable: boolean;
  quality_flags?: string[];
  crop_key?: string;
}

export interface Photo {
  id: string;
  event_id: string;
  batch_id?: string;
  original_filename: string;
  content_hash: string;
  mime_type: string;
  file_size: number;
  width?: number;
  height?: number;
  status: string;
  face_count: number;
  created_at: string;
  dup_cluster_id?: string;
  is_cluster_representative?: boolean;
  faces: PhotoFace[];
}

export interface PhotoListResponse {
  data: Photo[];
  next_cursor?: string;
  has_more: boolean;
}

export async function getEventPhotos(
  eventId: string,
  params?: { status?: string; face_count_zero?: boolean; group_duplicates?: boolean; cursor?: string; limit?: number }
): Promise<PhotoListResponse> {
  const { data } = await api.get<PhotoListResponse>(`/events/${eventId}/photos`, { params });
  return data;
}

export async function deletePhoto(photoId: string): Promise<void> {
  await api.delete(`/photos/${photoId}`);
}
