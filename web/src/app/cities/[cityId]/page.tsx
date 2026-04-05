"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { getCity, updateCity } from "@/lib/api";
import type { CityResponse } from "@/lib/types";

export default function CityEditPage() {
  return (
    <ProtectedRoute>
      <CityEdit />
    </ProtectedRoute>
  );
}

function CityEdit() {
  const { cityId } = useParams<{ cityId: string }>();
  const router = useRouter();
  const [city, setCity] = useState<CityResponse | null>(null);
  const [cityName, setCityName] = useState("");
  const [country, setCountry] = useState("");
  const [state, setState] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!cityId) return;
    getCity(decodeURIComponent(cityId))
      .then((c) => {
        setCity(c);
        setCityName(c.city_name);
        setCountry(c.country);
        setState(c.state || "");
      })
      .finally(() => setLoading(false));
  }, [cityId]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!cityId) return;
    setSaving(true);
    setMessage("");
    try {
      const updated = await updateCity(decodeURIComponent(cityId), {
        city_name: cityName,
        country,
        state,
      });
      setCity(updated);
      setMessage("Saved");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (!city) return <p className="text-gray-500">City not found.</p>;

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <button
        onClick={() => router.back()}
        className="text-sm text-blue-600 hover:underline"
      >
        Back
      </button>
      <h1 className="text-2xl font-bold">
        {city.city_name}, {city.country}
      </h1>

      {city.location_name && (
        <p className="text-sm text-gray-500">{city.location_name}</p>
      )}
      {city.latitude && city.longitude && (
        <p className="text-xs text-gray-400">
          {city.latitude}, {city.longitude}
        </p>
      )}

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">City Name</label>
          <input
            type="text"
            value={cityName}
            onChange={(e) => setCityName(e.target.value)}
            required
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
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={saving}
            className="bg-blue-600 text-white rounded px-6 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
          {message && (
            <span
              className={`text-sm ${
                message === "Saved" ? "text-green-600" : "text-red-600"
              }`}
            >
              {message}
            </span>
          )}
        </div>
      </form>

      {/* Visits */}
      {city.visits && city.visits.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Visits</h2>
          <div className="space-y-2">
            {city.visits.map((v, i) => (
              <div
                key={i}
                className="bg-gray-50 rounded p-3 flex justify-between items-center"
              >
                <div>
                  <div className="text-sm font-medium">{v.trip}</div>
                  <div className="text-xs text-gray-500">
                    {v.start_date} — {v.end_date}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
