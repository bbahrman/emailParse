export interface TripNote {
	trip_name: string;
	filename: string;
	content: string;
}

export interface TripsListResponse {
	trips: string[];
	count: number;
}

export interface TravelSyncSettings {
	apiUrl: string;
	apiKey: string;
	tripsFolder: string;
}

export const DEFAULT_SETTINGS: TravelSyncSettings = {
	apiUrl: "",
	apiKey: "",
	tripsFolder: "Decimal System/10-19 Life admin/15 Travel, events, & entertainment 🎒/15.52 Active Trips",
};
