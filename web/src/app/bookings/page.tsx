"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { listBookings } from "@/lib/api";
import type { BookingResponse } from "@/lib/types";
import Link from "next/link";

export default function BookingsPage() {
  return (
    <ProtectedRoute>
      <BookingsContent />
    </ProtectedRoute>
  );
}

function BookingsContent() {
  const [bookings, setBookings] = useState<BookingResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  function fetchBookings() {
    setLoading(true);
    listBookings(startDate || undefined, endDate || undefined)
      .then((data) =>
        setBookings(
          data.bookings.sort((a, b) =>
            (a.check_in_date || "").localeCompare(b.check_in_date || "")
          )
        )
      )
      .catch((err) => console.error("Failed to fetch bookings:", err))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchBookings();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Bookings</h1>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="Start date"
        />
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="End date"
        />
        <button
          onClick={fetchBookings}
          className="bg-blue-600 text-white rounded px-4 py-2 text-sm hover:bg-blue-700"
        >
          Filter
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : bookings.length === 0 ? (
        <p className="text-gray-500">No bookings found.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {bookings.map((b) => (
            <Link
              key={b.confirmation}
              href={`/bookings/${encodeURIComponent(b.confirmation)}`}
              className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow space-y-1"
            >
              <div className="font-medium">
                {b.provider_name || "Unknown"}
              </div>
              <div className="text-sm text-gray-600">{b.city}</div>
              <div className="text-sm text-gray-500">
                {b.check_in_date} — {b.check_out_date}
              </div>
              <div className="text-xs text-gray-400">{b.confirmation}</div>
              {b.amount_total && (
                <div className="text-sm font-medium text-gray-700">
                  {b.amount_total}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
