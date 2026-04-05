"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { listTrips } from "@/lib/api";
import Link from "next/link";

export default function TripsPage() {
  return (
    <ProtectedRoute>
      <TripsContent />
    </ProtectedRoute>
  );
}

function TripsContent() {
  const [trips, setTrips] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listTrips()
      .then((data) => setTrips(data.trips))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Trips</h1>
        <Link
          href="/trips/new"
          className="bg-blue-600 text-white rounded px-4 py-2 text-sm hover:bg-blue-700"
        >
          New Trip
        </Link>
      </div>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : trips.length === 0 ? (
        <p className="text-gray-500">No trips found.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {trips.map((trip) => (
            <Link
              key={trip}
              href={`/trips/${encodeURIComponent(trip)}`}
              className="bg-white rounded-lg shadow p-5 hover:shadow-md transition-shadow"
            >
              <span className="text-lg font-medium">{trip}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
