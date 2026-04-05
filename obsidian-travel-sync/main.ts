import { Plugin } from "obsidian";
import { TravelSyncSettings, DEFAULT_SETTINGS } from "./src/types";
import { TravelSyncSettingTab } from "./src/settings";
import { TravelSync } from "./src/sync";

export default class TravelSyncPlugin extends Plugin {
	settings: TravelSyncSettings = DEFAULT_SETTINGS;

	async onload() {
		await this.loadSettings();

		this.addSettingTab(new TravelSyncSettingTab(this.app, this));

		this.addCommand({
			id: "sync-trips",
			name: "Sync Trips",
			callback: () => this.runSync(),
		});

		// Auto-sync on load after the vault and metadata cache are ready
		this.app.workspace.onLayoutReady(() => {
			if (this.settings.apiUrl) {
				this.runSync();
			}
		});
	}

	async runSync() {
		const sync = new TravelSync(this.app, this.settings);
		await sync.syncTrips();
	}

	async loadSettings() {
		this.settings = Object.assign(
			{},
			DEFAULT_SETTINGS,
			await this.loadData()
		);
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}
}
