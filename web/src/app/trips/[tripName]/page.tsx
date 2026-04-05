"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { getTrip, autoAssignDates, createTrip } from "@/lib/api";
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
  const decodedName = tripName ? decodeURIComponent(tripName) : "";
  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Add city form
  const [showAddCity, setShowAddCity] = useState(false);
  const [cityName, setCityName] = useState("");
  const [country, setCountry] = useState("");
  const [state, setState] = useState("");
  const [addingCity, setAddingCity] = useState(false);

  function loadTrip() {
    if (!decodedName) return;
    setLoading(true);
    getTrip(decodedName)
      .then(setTrip)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadTrip();
  }, [tripName]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAutoAssign() {
    setAssigning(true);
    setMessage("");
    try {
      const updated = await autoAssignDates(decodedName);
      setTrip(updated);
      setMessage("Dates auto-assigned from matching bookings");
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Auto-assign failed"
      );
    } finally {
      setAssigning(false);
    }
  }

  async function handleAddCity(e: React.FormEvent) {
    e.preventDefault();
    if (!cityName || !country) return;
    setAddingCity(true);
    setMessage("");
    try {
      const updated = await createTrip({
        trip_name: decodedName,
        cities: [{ city_name: cityName, country, state: state || undefined }],
      });
      setTrip(updated);
      setCityName("");
      setCountry("");
      setState("");
      setShowAddCity(false);
      setMessage("City added to trip");
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Failed to add city"
      );
    } finally {
      setAddingCity(false);
    }
  }

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!trip) return <p className="text-gray-500">Trip not found.</p>;

  const citiesMissingDates = trip.cities.filter((c) =>
    c.visits?.some(
      (v) =>
        v.trip === trip.trip_name && (!v.start_date || !v.end_date)
    )
  );

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{trip.trip_name}</h1>
        <div className="flex gap-2">
          {citiesMissingDates.length > 0 && (
            <button
              onClick={handleAutoAssign}
              disabled={assigning}
              className="bg-blue-600 text-white rounded px-4 py-2 text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {assigning ? "Assigning..." : "Auto-Assign Dates"}
            </button>
          )}
        </div>
      </div>

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

      {citiesMissingDates.length > 0 && (
        <div className="bg-amber-50 text-amber-800 text-sm rounded p-3">
          {citiesMissingDates.length} cit
          {citiesMissingDates.length === 1 ? "y is" : "ies are"} missing
          dates. Click &ldquo;Auto-Assign Dates&rdquo; to match from bookings, or edit
          dates on each city page.
        </div>
      )}

      {/* Cities */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Cities</h2>
          <button
            onClick={() => setShowAddCity(!showAddCity)}
            className="text-sm text-blue-600 hover:underline"
          >
            {showAddCity ? "Cancel" : "Add City"}
          </button>
        </div>

        {showAddCity && (
          <form
            onSubmit={handleAddCity}
            className="bg-blue-50 rounded-lg p-4 space-y-3 mb-4"
          >
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">
                  City Name
                </label>
                <input
                  type="text"
                  value={cityName}
                  onChange={(e) => setCityName(e.target.value)}
                  required
                  placeholder="Budapest"
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">
                  Country
                </label>
                <input
                  type="text"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  required
                  placeholder="Hungary"
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={addingCity}
              className="bg-blue-600 text-white rounded px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {addingCity ? "Adding..." : "Add City to Trip"}
            </button>
          </form>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {trip.cities.map((city) => {
            const tripVisit = city.visits?.find(
              (v) => v.trip === trip.trip_name
            );
            const hasDates = tripVisit?.start_date && tripVisit?.end_date;

            return (
              <Link
                key={city.city_id}
                href={`/cities/${encodeURIComponent(city.city_id)}`}
                className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    {city.city_name}, {city.country}
                  </span>
                  {!hasDates && (
                    <span className="text-xs bg-amber-100 text-amber-700 rounded px-1.5 py-0.5">
                      no dates
                    </span>
                  )}
                </div>
                {hasDates && (
                  <div className="text-sm text-gray-500">
                    {tripVisit.start_date} — {tripVisit.end_date}
                  </div>
                )}
                {city.location_name && (
                  <div className="text-xs text-gray-400 truncate">
                    {city.location_name}
                  </div>
                )}
              </Link>
            );
          })}
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

      {trip.bookings.length === 0 && citiesMissingDates.length === 0 && (
        <p className="text-sm text-gray-500">
          No bookings matched for this trip&apos;s date range.
        </p>
      )}
    </div>
  );
}
