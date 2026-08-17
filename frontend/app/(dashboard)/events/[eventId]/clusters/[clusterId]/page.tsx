"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import api from "@/lib/api";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import Toast from "@/components/ui/Toast";
import Image from "next/image";

interface Photo {
  id: string;
  is_cluster_representative: boolean;
}

interface ClusterDetails {
  cluster_id: string;
  photos: Photo[];
}

export default function ClusterDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const eventId = params.eventId as string;
  const clusterId = params.clusterId as string;

  const [details, setDetails] = useState<ClusterDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetchDetails();
  }, [clusterId]);

  const fetchDetails = async () => {
    try {
      const { data } = await api.get<ClusterDetails>(`/events/${eventId}/clusters/${clusterId}`);
      setDetails(data);
    } catch {
      setError("Failed to load cluster details");
    } finally {
      setLoading(false);
    }
  };

  const excludePhoto = async (photoId: string) => {
    try {
      await api.post(`/events/${eventId}/clusters/${clusterId}/exclude?photo_id=${photoId}`);
      setSuccess("Photo excluded from cluster");
      fetchDetails();
    } catch {
      setError("Failed to exclude photo");
    }
  };

  const setRepresentative = async (photoId: string) => {
    try {
      await api.post(`/events/${eventId}/clusters/${clusterId}/representative?photo_id=${photoId}`);
      setSuccess("Representative updated");
      fetchDetails();
    } catch {
      setError("Failed to set representative");
    }
  };

  if (loading) {
    return <div className="flex justify-center py-20"><Spinner /></div>;
  }

  if (!details) {
    return <div className="text-center py-20 text-slate-400">Cluster not found</div>;
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Cluster Details</h1>
          <p className="text-slate-400 mt-1">{details.photos.length} similar photos</p>
        </div>
        <Button variant="secondary" onClick={() => router.push(`/events/${eventId}/clusters`)}>
          Back to Clusters
        </Button>
      </div>

      {error && <Toast message={error} type="error" onClose={() => setError("")} />}
      {success && <Toast message={success} type="success" onClose={() => setSuccess("")} />}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {details.photos.map((photo) => (
          <Card key={photo.id} className={`p-4 flex flex-col gap-3 ${photo.is_cluster_representative ? 'border-violet-500 border-2' : ''}`}>
            <div className="aspect-square relative rounded-md overflow-hidden bg-slate-800">
              <Image
                src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/photos/${photo.id}/thumb`}
                alt="Photo"
                fill
                className="object-cover"
                unoptimized
              />
            </div>
            
            <div className="flex gap-2 text-xs">
              {!photo.is_cluster_representative && (
                <Button 
                  variant="secondary" 
                  className="flex-1 px-2 py-1"
                  onClick={() => setRepresentative(photo.id)}
                >
                  Make Primary
                </Button>
              )}
              {photo.is_cluster_representative && (
                <div className="flex-1 px-2 py-1 bg-violet-500/20 text-violet-300 text-center rounded border border-violet-500/30">
                  Primary
                </div>
              )}
              <Button 
                variant="secondary" 
                className="flex-1 px-2 py-1 text-red-400 hover:text-red-300 hover:bg-red-900/20"
                onClick={() => excludePhoto(photo.id)}
              >
                Exclude
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
