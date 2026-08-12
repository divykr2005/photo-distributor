import api from "@/lib/api";
import { Photo } from "./photos";

export interface CandidateItem {
  guest_id: string;
  guest_name?: string;
  score: number;
  rank: number;
}

export interface Match {
  id: string;
  event_id: string;
  guest_id: string;
  photo_id: string;
  photo_face_id: string;
  similarity: number;
  threshold_used: number;
  decision: "auto_confirmed" | "review" | "rejected";
  status: "active" | "rejected_by_organizer" | "manually_added";
  second_guest_id?: string;
  second_similarity?: number;
  margin?: number;
  review_reason?: string;
  top_candidates?: CandidateItem[];
  matched_at: string;
}

export async function getEventMatches(
  eventId: string,
  params?: { decision?: string; status?: string; guest_id?: string; skip?: number; limit?: number }
): Promise<Match[]> {
  const { data } = await api.get<Match[]>(`/events/${eventId}/matches`, { params });
  return data;
}

export async function updateMatchAction(matchId: string, action: "confirm" | "reject"): Promise<Match> {
  const { data } = await api.patch<Match>(`/matches/${matchId}`, { action });
  return data;
}

export async function manualAssignMatch(photoFaceId: string, guestId: string): Promise<Match> {
  const { data } = await api.post<Match>(`/matches`, { photo_face_id: photoFaceId, guest_id: guestId });
  return data;
}

export async function getGuestPhotos(guestId: string): Promise<Photo[]> {
  const { data } = await api.get<Photo[]>(`/guests/${guestId}/photos`);
  return data;
}

export async function getPipelineStatus(eventId: string): Promise<any> {
  const { data } = await api.get(`/events/${eventId}/pipeline-status`);
  return data;
}

export async function triggerMatchRun(eventId: string, force: boolean = false): Promise<any> {
  const { data } = await api.post(`/events/${eventId}/match-runs`, { force });
  return data;
}
