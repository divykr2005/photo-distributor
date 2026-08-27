"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import api from "@/lib/api";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";
import Image from "next/image";

interface PhotoCluster {
  id: string;
  event_id: string;
  representative_photo_id: string | null;
  size: number;
}

export default function ReviewClustersPage() {
  const router = useRouter();
  const params = useParams();
  const eventId = params.eventId as string;

  const [clusters, setClusters] = useState<PhotoCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetchClusters();
  }, [eventId]);

  const fetchClusters = async () => {
    try {
      const { data } = await api.get<PhotoCluster[]>(`/events/${eventId}/clusters`);
      setClusters(data.filter(c => c.size > 1));
    } catch {
      setError("Failed to load clusters");
    } finally {
      setLoading(false);
    }
  };

  const breakCluster = async (clusterId: string) => {
    try {
      await api.post(`/events/${eventId}/clusters/${clusterId}/break`);
      setSuccess("Cluster broken");
      fetchClusters();
    } catch {
      setError("Failed to break cluster");
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Review Duplicates</h1>
          <p className="text-slate-400 mt-1">Review grouped similar photos and separate them if needed.</p>
        </div>
        <Button variant="secondary" onClick={() => router.push(`/events/${eventId}`)}>
          Back to Event
        </Button>
      </div>

      {error && <Toast message={error} type="error" onClose={() => setError("")} />}
      {success && <Toast message={success} type="success" onClose={() => setSuccess("")} />}

      {clusters.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-slate-400">No duplicate clusters found.</p>
          <Button className="mt-4" onClick={fetchClusters}>Refresh</Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {clusters.map((cluster) => (
            <Card key={cluster.id} className="flex flex-col">
              <div className="p-4 border-b border-slate-700 flex justify-between items-center">
                <span className="font-medium text-white">{cluster.size} Photos</span>
                <Button 
                  variant="secondary" 
                  onClick={() => breakCluster(cluster.id)}
                  className="text-xs px-2 py-1 text-red-400 hover:text-red-300 border-red-900/30 hover:bg-red-900/20"
                >
                  Break
                </Button>
              </div>
              <div className="p-4 flex-1">
                {cluster.representative_photo_id ? (
                  <div className="aspect-square relative rounded-md overflow-hidden bg-slate-800">
                    <Image
                      src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/photos/${cluster.representative_photo_id}/thumb`}
                      alt="Representative"
                      fill
                      className="object-cover"
                      unoptimized
                    />
                  </div>
                ) : (
                  <div className="aspect-square bg-slate-800 rounded-md flex items-center justify-center text-slate-500">
                    No image
                  </div>
                )}
              </div>
              <div className="p-4 pt-0">
                <Button 
                  className="w-full"
                  onClick={() => router.push(`/events/${eventId}/clusters/${cluster.id}`)}
                >
                  Review Details
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
