"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { createTrip } from "@/lib/api";
import type { TripCityInput } from "@/lib/types";

export default function NewTripPage() {
  return (
    <ProtectedRoute>
      <NewTrip />
    </ProtectedRoute>
  );
}

function NewTrip() {
  const router = useRouter();
  const [tripName, setTripName] = useState("");
  const [cities, setCities] = useState<TripCityInput[]>([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  // Add city inputs
  const [cityName, setCityName] = useState("");
  const [country, setCountry] = useState("");
  const [state, setState] = useState("");

  function addCity() {
    if (!cityName || !country) return;
    setCities([
      ...cities,
      { city_name: cityName, country, state: state || undefined },
    ]);
    setCityName("");
    setCountry("");
    setState("");
  }

  function removeCity(index: number) {
    setCities(cities.filter((_, i) => i !== index));
  }

  async function handleCreate() {
    if (!tripName || cities.length === 0) return;
    setCreating(true);
    setError("");
    try {
      await createTrip({ trip_name: tripName, cities });
      router.push(`/trips/${encodeURIComponent(tripName)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Creation failed");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <button
        onClick={() => router.back()}
        className="text-sm text-blue-600 hover:underline"
      >
        Back
      </button>
      <h1 className="text-2xl font-bold">New Trip</h1>

      {error && (
        <div className="bg-red-50 text-red-700 text-sm rounded p-3">
          {error}
        </div>
      )}

      {/* Trip name */}
      <div>
        <label className="block text-sm font-medium mb-1">Trip Name</label>
        <input
          type="text"
          value={tripName}
          onChange={(e) => setTripName(e.target.value)}
          placeholder="e.g. London Weekend"
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Cities */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Cities</h2>

        {cities.length > 0 && (
          <div className="space-y-2">
            {cities.map((c, i) => (
              <div
                key={i}
                className="flex items-center justify-between bg-gray-50 rounded px-4 py-3"
              >
                <span className="text-sm">
                  {c.city_name}, {c.country}
                  {c.state ? `, ${c.state}` : ""}
                </span>
                <button
                  onClick={() => removeCity(i)}
                  className="text-sm text-red-500 hover:text-red-700"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">
                City Name
              </label>
              <input
                type="text"
                value={cityName}
                onChange={(e) => setCityName(e.target.value)}
                placeholder="London"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addCity();
                  }
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Country</label>
              <input
                type="text"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                placeholder="UK"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addCity();
                  }
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">
                State (optional)
              </label>
              <input
                type="text"
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addCity();
                  }
                }}
              />
            </div>
          </div>
          <button
            onClick={addCity}
            disabled={!cityName || !country}
            className="text-sm text-blue-600 hover:underline disabled:text-gray-400 disabled:no-underline"
          >
            + Add city
          </button>
        </div>
      </section>

      {/* Create */}
      <div className="space-y-2">
        <button
          onClick={handleCreate}
          disabled={creating || !tripName || cities.length === 0}
          className="w-full bg-blue-600 text-white rounded py-2.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {creating ? "Creating trip..." : "Create Trip"}
        </button>
        <p className="text-xs text-gray-400 text-center">
          Cities will be geocoded automatically. Dates can be auto-assigned from
          bookings on the trip detail page.
        </p>
      </div>
    </div>
  );
}
