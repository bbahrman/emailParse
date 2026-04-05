"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { listCities, createCity } from "@/lib/api";
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
  const [showForm, setShowForm] = useState(false);
  const [cityName, setCityName] = useState("");
  const [country, setCountry] = useState("");
  const [state, setState] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  function fetchCities() {
    setLoading(true);
    listCities()
      .then((data) => setCities(data.cities))
      .catch((err) => console.error("Failed to fetch cities:", err))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchCities();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError("");
    try {
      await createCity({
        city_name: cityName,
        country,
        state: state || undefined,
      });
      setCityName("");
      setCountry("");
      setState("");
      setShowForm(false);
      fetchCities();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create city");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Cities</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white rounded px-4 py-2 text-sm hover:bg-blue-700"
        >
          {showForm ? "Cancel" : "Add City"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="bg-white rounded-lg shadow p-5 space-y-4"
        >
          <h2 className="text-lg font-semibold">New City</h2>
          {error && (
            <div className="bg-red-50 text-red-700 text-sm rounded p-3">
              {error}
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                City Name
              </label>
              <input
                type="text"
                value={cityName}
                onChange={(e) => setCityName(e.target.value)}
                required
                placeholder="London"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Country</label>
              <input
                type="text"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                required
                placeholder="UK"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                State / Province
              </label>
              <input
                type="text"
                value={state}
                onChange={(e) => setState(e.target.value)}
                placeholder="Optional"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={creating}
            className="bg-blue-600 text-white rounded px-6 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create City"}
          </button>
          <p className="text-xs text-gray-400">
            The city will be auto-geocoded for coordinates.
          </p>
        </form>
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : cities.length === 0 ? (
        <p className="text-gray-500">No cities yet. Add one above.</p>
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
                  {city.visits.length} visit
                  {city.visits.length !== 1 ? "s" : ""}
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
