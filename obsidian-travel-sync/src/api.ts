import { requestUrl } from "obsidian";
import { TravelSyncSettings, TripNote, TripsListResponse } from "./types";

export class TravelApi {
	constructor(private settings: TravelSyncSettings) {}

	private async get<T>(path: string): Promise<T> {
		const url = `${this.settings.apiUrl.replace(/\/$/, "")}${path}`;
		const response = await requestUrl({
			url,
			method: "GET",
			headers: {
				"Content-Type": "application/json",
				...(this.settings.apiKey
					? { Authorization: `Bearer ${this.settings.apiKey}` }
					: {}),
			},
		});

		if (response.status !== 200) {
			throw new Error(
				`API request failed: ${response.status} ${response.text}`
			);
		}

		return response.json as T;
	}

	async listTrips(): Promise<string[]> {
		const data = await this.get<TripsListResponse>("/trips/");
		return data.trips;
	}

	async getTripNote(tripName: string): Promise<TripNote> {
		return this.get<TripNote>(
			`/export/obsidian/trip-note/${encodeURIComponent(tripName)}`
		);
	}
}
