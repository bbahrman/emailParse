"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { getCity, updateCity, addVisit, updateVisit } from "@/lib/api";
import type { CityResponse, VisitResponse } from "@/lib/types";

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

  // Add visit form
  const [showAddVisit, setShowAddVisit] = useState(false);
  const [newStartDate, setNewStartDate] = useState("");
  const [newEndDate, setNewEndDate] = useState("");
  const [newTrip, setNewTrip] = useState("");
  const [addingVisit, setAddingVisit] = useState(false);

  // Edit visit — now tracked by index
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editStartDate, setEditStartDate] = useState("");
  const [editEndDate, setEditEndDate] = useState("");
  const [editTrip, setEditTrip] = useState("");
  const [savingVisit, setSavingVisit] = useState(false);

  function loadCity() {
    if (!cityId) return;
    getCity(decodeURIComponent(cityId))
      .then((c) => {
        setCity(c);
        setCityName(c.city_name);
        setCountry(c.country);
        setState(c.state || "");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadCity();
  }, [cityId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSaveCity(e: React.FormEvent) {
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

  async function handleAddVisit(e: React.FormEvent) {
    e.preventDefault();
    if (!cityId) return;
    setAddingVisit(true);
    setMessage("");
    try {
      const updated = await addVisit(decodeURIComponent(cityId), {
        start_date: newStartDate || undefined,
        end_date: newEndDate || undefined,
        trip: newTrip,
      });
      setCity(updated);
      setNewStartDate("");
      setNewEndDate("");
      setNewTrip("");
      setShowAddVisit(false);
      setMessage("Visit added");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to add visit");
    } finally {
      setAddingVisit(false);
    }
  }

  function startEditVisit(index: number, visit: VisitResponse) {
    setEditingIndex(index);
    setEditStartDate(visit.start_date || "");
    setEditEndDate(visit.end_date || "");
    setEditTrip(visit.trip);
  }

  async function handleSaveVisit(index: number) {
    if (!cityId) return;
    setSavingVisit(true);
    setMessage("");
    try {
      const updated = await updateVisit(
        decodeURIComponent(cityId),
        index,
        {
          start_date: editStartDate,
          end_date: editEndDate,
          trip: editTrip,
        }
      );
      setCity(updated);
      setEditingIndex(null);
      setMessage("Visit updated");
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Failed to update visit"
      );
    } finally {
      setSavingVisit(false);
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

      {message && (
        <div
          className={`text-sm rounded p-3 ${
            message.includes("fail") || message.includes("Failed")
              ? "bg-red-50 text-red-700"
              : "bg-green-50 text-green-700"
          }`}
        >
          {message}
        </div>
      )}

      {/* City details form */}
      <form onSubmit={handleSaveCity} className="space-y-4">
        <h2 className="text-lg font-semibold">City Details</h2>
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
        <button
          type="submit"
          disabled={saving}
          className="bg-blue-600 text-white rounded px-6 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save City"}
        </button>
      </form>

      {/* Visits section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Visits</h2>
          <button
            onClick={() => setShowAddVisit(!showAddVisit)}
            className="text-sm text-blue-600 hover:underline"
          >
            {showAddVisit ? "Cancel" : "Add Visit"}
          </button>
        </div>

        {/* Add visit form */}
        {showAddVisit && (
          <form
            onSubmit={handleAddVisit}
            className="bg-blue-50 rounded-lg p-4 space-y-3"
          >
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">
                  Start Date
                </label>
                <input
                  type="date"
                  value={newStartDate}
                  onChange={(e) => setNewStartDate(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">
                  End Date
                </label>
                <input
                  type="date"
                  value={newEndDate}
                  onChange={(e) => setNewEndDate(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">
                  Trip Name
                </label>
                <input
                  type="text"
                  value={newTrip}
                  onChange={(e) => setNewTrip(e.target.value)}
                  required
                  placeholder="e.g. London Weekend"
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={addingVisit}
              className="bg-blue-600 text-white rounded px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {addingVisit ? "Adding..." : "Add Visit"}
            </button>
          </form>
        )}

        {/* Visit list */}
        {!city.visits || city.visits.length === 0 ? (
          <p className="text-sm text-gray-500">
            No visits yet. Add one to link this city to a trip.
          </p>
        ) : (
          <div className="space-y-2">
            {city.visits.map((visit, index) => (
              <div
                key={index}
                className="bg-gray-50 rounded-lg p-4 space-y-3"
              >
                {editingIndex === index ? (
                  /* Edit mode */
                  <div className="space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs font-medium mb-1">
                          Start Date
                        </label>
                        <input
                          type="date"
                          value={editStartDate}
                          onChange={(e) => setEditStartDate(e.target.value)}
                          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium mb-1">
                          End Date
                        </label>
                        <input
                          type="date"
                          value={editEndDate}
                          onChange={(e) => setEditEndDate(e.target.value)}
                          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium mb-1">
                          Trip Name
                        </label>
                        <input
                          type="text"
                          value={editTrip}
                          onChange={(e) => setEditTrip(e.target.value)}
                          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSaveVisit(index)}
                        disabled={savingVisit}
                        className="bg-blue-600 text-white rounded px-4 py-1.5 text-sm hover:bg-blue-700 disabled:opacity-50"
                      >
                        {savingVisit ? "Saving..." : "Save"}
                      </button>
                      <button
                        onClick={() => setEditingIndex(null)}
                        className="text-sm text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  /* Display mode */
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="text-sm font-medium">{visit.trip}</div>
                      <div className="text-xs text-gray-500">
                        {visit.start_date && visit.end_date
                          ? `${visit.start_date} — ${visit.end_date}`
                          : visit.start_date || visit.end_date || "No dates set"}
                      </div>
                    </div>
                    <button
                      onClick={() => startEditVisit(index, visit)}
                      className="text-sm text-blue-600 hover:underline"
                    >
                      Edit
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
