import { getIdToken } from "./auth";
import type {
  BookingResponse,
  BookingUpdateRequest,
  BookingsListResponse,
  CitiesListResponse,
  CityResponse,
  CreateTripRequest,
  TripPreviewResponse,
  TripResponse,
  TripsListResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getIdToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// Trips
export const listTrips = () => apiFetch<TripsListResponse>("/trips/");
export const getTrip = (name: string) =>
  apiFetch<TripResponse>(`/trips/${encodeURIComponent(name)}`);
export const previewTrip = (data: CreateTripRequest) =>
  apiFetch<TripPreviewResponse>("/trips/preview", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const createTrip = (data: CreateTripRequest) =>
  apiFetch<TripResponse>("/trips/create", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const autoAssignDates = (tripName: string) =>
  apiFetch<TripResponse>(
    `/trips/${encodeURIComponent(tripName)}/auto-assign`,
    { method: "POST" }
  );

// Cities
export const listCities = (trip?: string) =>
  apiFetch<CitiesListResponse>(
    trip ? `/cities/?trip=${encodeURIComponent(trip)}` : "/cities/"
  );
export const getCity = (id: string) =>
  apiFetch<CityResponse>(`/cities/${encodeURIComponent(id)}`);
export const updateCity = (
  id: string,
  params: { city_name?: string; country?: string; state?: string }
) => {
  const qs = new URLSearchParams();
  if (params.city_name) qs.set("city_name", params.city_name);
  if (params.country) qs.set("country", params.country);
  if (params.state !== undefined) qs.set("state", params.state);
  return apiFetch<CityResponse>(
    `/cities/${encodeURIComponent(id)}?${qs.toString()}`,
    { method: "PUT" }
  );
};

export const createCity = (params: {
  city_name: string;
  country: string;
  state?: string;
}) => {
  const qs = new URLSearchParams();
  qs.set("city_name", params.city_name);
  qs.set("country", params.country);
  if (params.state) qs.set("state", params.state);
  return apiFetch<CityResponse>(`/cities/?${qs.toString()}`, {
    method: "POST",
  });
};
export const addVisit = (
  cityId: string,
  params: { start_date?: string; end_date?: string; trip: string }
) => {
  const qs = new URLSearchParams();
  if (params.start_date) qs.set("start_date", params.start_date);
  if (params.end_date) qs.set("end_date", params.end_date);
  qs.set("trip", params.trip);
  return apiFetch<CityResponse>(
    `/cities/${encodeURIComponent(cityId)}/visits?${qs.toString()}`,
    { method: "POST" }
  );
};
export const updateVisit = (
  cityId: string,
  visitIndex: number,
  params: { start_date?: string; end_date?: string; trip?: string }
) => {
  const qs = new URLSearchParams();
  qs.set("visit_index", visitIndex.toString());
  if (params.start_date !== undefined) qs.set("start_date", params.start_date);
  if (params.end_date !== undefined) qs.set("end_date", params.end_date);
  if (params.trip !== undefined) qs.set("trip", params.trip);
  return apiFetch<CityResponse>(
    `/cities/${encodeURIComponent(cityId)}/visits?${qs.toString()}`,
    { method: "PUT" }
  );
};

// Bookings
export const listBookings = (startDate?: string, endDate?: string) => {
  const qs = new URLSearchParams();
  if (startDate) qs.set("start_date", startDate);
  if (endDate) qs.set("end_date", endDate);
  const query = qs.toString();
  return apiFetch<BookingsListResponse>(
    `/bookings/${query ? `?${query}` : ""}`
  );
};
export const getBooking = (confirmation: string) =>
  apiFetch<BookingResponse>(
    `/bookings/${encodeURIComponent(confirmation)}`
  );
export const updateBooking = (
  confirmation: string,
  data: BookingUpdateRequest
) =>
  apiFetch<BookingResponse>(
    `/bookings/${encodeURIComponent(confirmation)}`,
    { method: "PUT", body: JSON.stringify(data) }
  );
