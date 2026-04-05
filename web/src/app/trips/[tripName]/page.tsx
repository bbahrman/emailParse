"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { getTrip } from "@/lib/api";
import type { TripResponse } from "@/lib/types";
import Link from "next/link";

export default function TripDetailPage() {
  return (
    <ProtectedRoute>
      <TripDetail />
    </ProtectedRoute>
  );
}

function TripDetail() {
  const { tripName } = useParams<{ tripName: string }>();
  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!tripName) return;
    getTrip(decodeURIComponent(tripName))
      .then(setTrip)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [tripName]);

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!trip) return <p className="text-gray-500">Trip not found.</p>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">{trip.trip_name}</h1>

      {/* Cities */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Cities</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {trip.cities.map((city) => (
            <Link
              key={city.city_id}
              href={`/cities/${encodeURIComponent(city.city_id)}`}
              className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow space-y-1"
            >
              <div className="font-medium">
                {city.city_name}, {city.country}
              </div>
              {city.visits?.map((v, i) => (
                <div key={i} className="text-sm text-gray-500">
                  {v.start_date} — {v.end_date}
                </div>
              ))}
              {city.location_name && (
                <div className="text-xs text-gray-400 truncate">
                  {city.location_name}
                </div>
              )}
            </Link>
          ))}
        </div>
      </section>

      {/* Bookings */}
      {trip.bookings.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Bookings</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {trip.bookings.map((b) => (
              <Link
                key={b.confirmation}
                href={`/bookings/${encodeURIComponent(b.confirmation)}`}
                className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow space-y-1"
              >
                <div className="font-medium">{b.provider_name}</div>
                <div className="text-sm text-gray-600">{b.city}</div>
                <div className="text-sm text-gray-500">
                  {b.check_in_date} — {b.check_out_date}
                </div>
                {b.amount_total && (
                  <div className="text-sm text-gray-500">
                    {b.amount_total}
                  </div>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
