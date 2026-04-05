export interface BookingResponse {
  confirmation: string;
  booking_type?: string | null;
  guest_name?: string | null;
  provider_name?: string | null;
  departure_city?: string | null;
  arrival_city?: string | null;
  check_in_date?: string | null;
  check_out_date?: string | null;
  check_in_time?: string | null;
  check_out_time?: string | null;
  early_check_in_time?: string | null;
  early_check_in_cost?: string | null;
  breakfast_included?: boolean | null;
  cancellation_terms?: string | null;
  street_address?: string | null;
  city?: string | null;
  postal_code?: string | null;
  booking_date?: string | null;
  what3words?: string | null;
  website?: string | null;
  amount_paid?: string | null;
  amount_total?: string | null;
  room_type?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  source_key?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface BookingUpdateRequest {
  booking_type?: string;
  guest_name?: string;
  provider_name?: string;
  departure_city?: string;
  arrival_city?: string;
  check_in_date?: string;
  check_out_date?: string;
  check_in_time?: string;
  check_out_time?: string;
  early_check_in_time?: string;
  early_check_in_cost?: string;
  breakfast_included?: boolean;
  cancellation_terms?: string;
  street_address?: string;
  city?: string;
  postal_code?: string;
  booking_date?: string;
  what3words?: string;
  website?: string;
  amount_paid?: string;
  amount_total?: string;
  room_type?: string;
}

export interface BookingsListResponse {
  bookings: BookingResponse[];
  count: number;
}

export interface VisitResponse {
  start_date?: string | null;
  end_date?: string | null;
  trip: string;
}

export interface CityResponse {
  city_id: string;
  city_name: string;
  country: string;
  state?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  location_name?: string | null;
  visits?: VisitResponse[];
}

export interface CitiesListResponse {
  cities: CityResponse[];
  count: number;
}

export interface TripResponse {
  trip_name: string;
  cities: CityResponse[];
  bookings: BookingResponse[];
}

export interface TripsListResponse {
  trips: string[];
  count: number;
}

export interface TripCityInput {
  city_name: string;
  country: string;
  state?: string;
  start_date?: string;
  end_date?: string;
}

export interface CreateTripRequest {
  trip_name: string;
  cities: TripCityInput[];
}

export interface TripCitySuggestion {
  city_name: string;
  country: string;
  state?: string | null;
  city_id?: string | null;
  city_exists: boolean;
  suggested_start_date?: string | null;
  suggested_end_date?: string | null;
  matched_bookings: BookingResponse[];
}

export interface TripPreviewResponse {
  trip_name: string;
  cities: TripCitySuggestion[];
}
