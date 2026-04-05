"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { listTrips, listBookings } from "@/lib/api";
import type { BookingResponse } from "@/lib/types";
import Link from "next/link";

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}

function Dashboard() {
  const [trips, setTrips] = useState<string[]>([]);
  const [bookings, setBookings] = useState<BookingResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([listTrips(), listBookings()]).then(([t, b]) => {
      setTrips(t.trips);
      setBookings(
        b.bookings.sort(
          (a, b) =>
            (a.check_in_date || "").localeCompare(b.check_in_date || "")
        )
      );
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-gray-500">Loading...</p>;
  }

  // Split bookings into upcoming and past
  const today = new Date().toISOString().split("T")[0];
  const upcoming = bookings.filter(
    (b) => (b.check_in_date || "") >= today
  );
  const recent = bookings
    .filter((b) => (b.check_in_date || "") < today)
    .slice(-5)
    .reverse();

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label="Trips" value={trips.length} href="/trips" />
        <StatCard label="Upcoming" value={upcoming.length} href="/bookings" />
        <StatCard label="Total Bookings" value={bookings.length} href="/bookings" />
      </div>

      {/* Upcoming bookings */}
      {upcoming.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Upcoming Bookings</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcoming.map((b) => (
              <BookingCard key={b.confirmation} booking={b} />
            ))}
          </div>
        </section>
      )}

      {/* Recent past bookings */}
      {recent.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Recent Bookings</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recent.map((b) => (
              <BookingCard key={b.confirmation} booking={b} />
            ))}
          </div>
        </section>
      )}

      {/* Trips */}
      {trips.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Trips</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {trips.map((t) => (
              <Link
                key={t}
                href={`/trips/${encodeURIComponent(t)}`}
                className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow"
              >
                <span className="font-medium">{t}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  href,
}: {
  label: string;
  value: number;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow"
    >
      <div className="text-2xl font-bold text-blue-600">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </Link>
  );
}

function BookingCard({ booking }: { booking: BookingResponse }) {
  return (
    <Link
      href={`/bookings/${encodeURIComponent(booking.confirmation)}`}
      className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow space-y-1"
    >
      <div className="font-medium">
        {booking.provider_name || "Unknown Hotel"}
      </div>
      <div className="text-sm text-gray-600">{booking.city || ""}</div>
      <div className="text-sm text-gray-500">
        {booking.check_in_date || "?"} — {booking.check_out_date || "?"}
      </div>
      {booking.amount_total && (
        <div className="text-sm text-gray-500">{booking.amount_total}</div>
      )}
    </Link>
  );
}
