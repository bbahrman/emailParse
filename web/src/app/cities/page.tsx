"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { listCities } from "@/lib/api";
import type { CityResponse } from "@/lib/types";
import Link from "next/link";

export default function CitiesPage() {
  return (
    <ProtectedRoute>
      <CitiesContent />
    </ProtectedRoute>
  );
}

function CitiesContent() {
  const [cities, setCities] = useState<CityResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listCities()
      .then((data) => setCities(data.cities))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Cities</h1>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : cities.length === 0 ? (
        <p className="text-gray-500">No cities found.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cities.map((city) => (
            <Link
              key={city.city_id}
              href={`/cities/${encodeURIComponent(city.city_id)}`}
              className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow space-y-1"
            >
              <div className="font-medium">
                {city.city_name}, {city.country}
              </div>
              {city.state && (
                <div className="text-sm text-gray-500">{city.state}</div>
              )}
              {city.visits && city.visits.length > 0 && (
                <div className="text-sm text-gray-500">
                  {city.visits.length} visit{city.visits.length !== 1 ? "s" : ""}
                </div>
              )}
              {city.location_name && (
                <div className="text-xs text-gray-400 truncate">
                  {city.location_name}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
