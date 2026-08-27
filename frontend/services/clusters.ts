import api from "@/lib/api";
import { Photo } from "./photos";

export interface PhotoCluster {
  id: string;
  event_id: string;
  membership_hash: string;
  size: number;
  representative_photo_id?: string;
  mean_quality?: number;
  time_span_s?: number;
  params?: any;
}

export interface ClusterDetailResponse {
  cluster_id: string;
  photos: Photo[];
}

export async function runDeduplication(eventId: string): Promise<{ status: string; task_id?: string }> {
  const { data } = await api.post(`/events/${eventId}/clusters/run`);
  return data;
}

export async function getClusters(eventId: string): Promise<PhotoCluster[]> {
  const { data } = await api.get<PhotoCluster[]>(`/events/${eventId}/clusters`);
  return data;
}

export async function getClusterDetails(eventId: string, clusterId: string): Promise<ClusterDetailResponse> {
  const { data } = await api.get<ClusterDetailResponse>(`/events/${eventId}/clusters/${clusterId}`);
  return data;
}

export async function breakCluster(eventId: string, clusterId: string): Promise<void> {
  await api.post(`/events/${eventId}/clusters/${clusterId}/break`);
}

export async function excludePhoto(eventId: string, clusterId: string, photoId: string): Promise<void> {
  await api.post(`/events/${eventId}/clusters/${clusterId}/exclude?photo_id=${photoId}`);
}

export async function setRepresentative(eventId: string, clusterId: string, photoId: string): Promise<void> {
  await api.post(`/events/${eventId}/clusters/${clusterId}/representative?photo_id=${photoId}`);
}
