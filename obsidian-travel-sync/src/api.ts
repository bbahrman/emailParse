import { requestUrl } from "obsidian";
import {
	CognitoUserPool,
	CognitoUser,
	AuthenticationDetails,
	CognitoUserSession,
} from "amazon-cognito-identity-js";
import { TravelSyncSettings, TripNote, TripsListResponse } from "./types";

export class TravelApi {
	private session: CognitoUserSession | null = null;

	constructor(private settings: TravelSyncSettings) {}

	private async getToken(): Promise<string> {
		// Return cached token if still valid
		if (this.session && this.session.isValid()) {
			return this.session.getIdToken().getJwtToken();
		}

		// Authenticate with Cognito
		const pool = new CognitoUserPool({
			UserPoolId: this.settings.cognitoUserPoolId,
			ClientId: this.settings.cognitoClientId,
		});

		const user = new CognitoUser({
			Username: this.settings.cognitoEmail,
			Pool: pool,
		});

		const authDetails = new AuthenticationDetails({
			Username: this.settings.cognitoEmail,
			Password: this.settings.cognitoPassword,
		});

		this.session = await new Promise<CognitoUserSession>(
			(resolve, reject) => {
				user.authenticateUser(authDetails, {
					onSuccess: (session) => resolve(session),
					onFailure: (err) => reject(err),
					newPasswordRequired: () =>
						reject(new Error("Password change required")),
				});
			}
		);

		return this.session.getIdToken().getJwtToken();
	}

	private async get<T>(path: string): Promise<T> {
		const token = await this.getToken();
		const url = `${this.settings.apiUrl.replace(/\/$/, "")}${path}`;
		const response = await requestUrl({
			url,
			method: "GET",
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${token}`,
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
