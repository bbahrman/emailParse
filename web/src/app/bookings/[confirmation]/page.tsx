"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { getBooking, updateBooking } from "@/lib/api";
import type { BookingResponse, BookingUpdateRequest } from "@/lib/types";

const FIELDS: { key: keyof BookingUpdateRequest; label: string; type?: string }[] = [
  { key: "guest_name", label: "Guest Name" },
  { key: "provider_name", label: "Provider" },
  { key: "departure_city", label: "Departure City" },
  { key: "arrival_city", label: "Arrival City" },
  { key: "departure_station", label: "Departure Station" },
  { key: "arrival_station", label: "Arrival Station" },
  { key: "route_number", label: "Route / Flight Number" },
  { key: "seat_class", label: "Seat Class" },
  { key: "seat_number", label: "Seat Number" },
  { key: "check_in_date", label: "Check-in / Departure Date", type: "date" },
  { key: "check_out_date", label: "Check-out / Arrival Date", type: "date" },
  { key: "check_in_time", label: "Check-in / Departure Time" },
  { key: "check_out_time", label: "Check-out / Arrival Time" },
  { key: "street_address", label: "Address" },
  { key: "city", label: "City" },
  { key: "postal_code", label: "Postal Code" },
  { key: "room_type", label: "Room Type" },
  { key: "amount_paid", label: "Amount Paid" },
  { key: "amount_total", label: "Amount Total" },
  { key: "website", label: "Website" },
  { key: "cancellation_terms", label: "Cancellation Terms" },
  { key: "early_check_in_time", label: "Early Check-in Time" },
  { key: "early_check_in_cost", label: "Early Check-in Cost" },
];

export default function BookingEditPage() {
  return (
    <ProtectedRoute>
      <BookingEdit />
    </ProtectedRoute>
  );
}

function BookingEdit() {
  const { confirmation } = useParams<{ confirmation: string }>();
  const router = useRouter();
  const [booking, setBooking] = useState<BookingResponse | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [bookingType, setBookingType] = useState("hotel");
  const [breakfastIncluded, setBreakfastIncluded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!confirmation) return;
    getBooking(decodeURIComponent(confirmation))
      .then((b) => {
        setBooking(b);
        const f: Record<string, string> = {};
        for (const { key } of FIELDS) {
          f[key] = (b[key as keyof BookingResponse] as string) || "";
        }
        setForm(f);
        setBookingType(b.booking_type || "hotel");
        setBreakfastIncluded(b.breakfast_included || false);
      })
      .finally(() => setLoading(false));
  }, [confirmation]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!confirmation) return;
    setSaving(true);
    setMessage("");
    try {
      const updates: BookingUpdateRequest = { booking_type: bookingType, breakfast_included: breakfastIncluded };
      for (const { key } of FIELDS) {
        const val = form[key];
        if (val !== undefined && val !== "") {
          (updates as Record<string, string>)[key] = val;
        }
      }
      await updateBooking(decodeURIComponent(confirmation), updates);
      setMessage("Saved");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (!booking) return <p className="text-gray-500">Booking not found.</p>;

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <button
        onClick={() => router.back()}
        className="text-sm text-blue-600 hover:underline"
      >
        Back
      </button>
      <h1 className="text-2xl font-bold">{booking.confirmation}</h1>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Booking Type</label>
          <select
            value={bookingType}
            onChange={(e) => setBookingType(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="hotel">Hotel</option>
            <option value="train">Train</option>
            <option value="flight">Flight</option>
            <option value="car">Car Rental</option>
            <option value="tour">Tour</option>
            <option value="other">Other</option>
          </select>
        </div>

        {FIELDS.map(({ key, label, type }) => (
          <div key={key}>
            <label className="block text-sm font-medium mb-1">{label}</label>
            <input
              type={type || "text"}
              value={form[key] || ""}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, [key]: e.target.value }))
              }
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        ))}

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="breakfast"
            checked={breakfastIncluded}
            onChange={(e) => setBreakfastIncluded(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="breakfast" className="text-sm font-medium">
            Breakfast Included
          </label>
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
    </div>
  );
}
