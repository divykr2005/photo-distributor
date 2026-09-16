import api from "@/lib/api";
import { Photo } from "./photos";

export interface PhotoCluster {
  id: string;
  event_id: string;
  membership_hash: string;
  size: number;
  representative_photo_id: string | null;
  mean_quality?: number;
  time_span_s?: number;
  params?: any;
}

export interface ClusterDetailResponse {
  cluster_id: string;
  photos: Photo[];
}

export interface PaginatedClusters {
  data: PhotoCluster[];
  total: number;
  page: number;
  page_size: number;
}

export async function runDeduplication(eventId: string): Promise<{ status: string; task_id?: string }> {
  const { data } = await api.post(`/events/${eventId}/clusters/run`);
  return data;
}

export async function getClustersPage(
  eventId: string,
  page = 1,
  pageSize = 24,
): Promise<PaginatedClusters> {
  const { data } = await api.get<PaginatedClusters>(`/events/${eventId}/clusters`, {
    params: { page, page_size: pageSize, min_size: 2 },
  });
  return data;
}

export async function getClusters(eventId: string): Promise<PhotoCluster[]> {
  const first = await getClustersPage(eventId, 1, 200);
  const clusters = [...first.data];
  const pages = Math.ceil(first.total / first.page_size);
  for (let page = 2; page <= pages; page += 1) {
    const next = await getClustersPage(eventId, page, first.page_size);
    clusters.push(...next.data);
  }
  return clusters;
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
