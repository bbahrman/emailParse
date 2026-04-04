import { App, Notice, TFile, TFolder, normalizePath } from "obsidian";
import { TravelApi } from "./api";
import { TravelSyncSettings } from "./types";

const FRONTMATTER_TYPE = "travel-sync";

export class TravelSync {
	private api: TravelApi;

	constructor(
		private app: App,
		private settings: TravelSyncSettings
	) {
		this.api = new TravelApi(settings);
	}

	async syncTrips(): Promise<void> {
		if (!this.settings.apiUrl) {
			new Notice("Travel Sync: API URL not configured. Check plugin settings.");
			return;
		}

		try {
			// 1. Get all trips from API
			const apiTrips = await this.api.listTrips();

			// 2. Find existing synced files in the trips folder
			const existingSyncedTrips = await this.getExistingSyncedTrips();

			// 3. Determine which trips to sync:
			//    - All trips from the API (current/future will be there)
			//    - Plus any trip that has an existing synced file
			const tripsToSync = new Set<string>([
				...apiTrips,
				...existingSyncedTrips.keys(),
			]);

			if (tripsToSync.size === 0) {
				new Notice("Travel Sync: No trips to sync.");
				return;
			}

			let synced = 0;
			let errors = 0;

			for (const tripName of tripsToSync) {
				try {
					const tripNote = await this.api.getTripNote(tripName);
					await this.writeTripNote(
						tripName,
						tripNote.filename,
						tripNote.content,
						existingSyncedTrips.get(tripName)
					);
					synced++;
				} catch (e) {
					// Trip might not have cities yet — skip silently if 404
					const msg = e instanceof Error ? e.message : String(e);
					if (!msg.includes("404")) {
						console.error(
							`Travel Sync: Error syncing trip "${tripName}":`,
							e
						);
						errors++;
					}
				}
			}

			const parts = [`Synced ${synced} trip${synced !== 1 ? "s" : ""}`];
			if (errors > 0) {
				parts.push(`${errors} error${errors !== 1 ? "s" : ""}`);
			}
			new Notice(`Travel Sync: ${parts.join(", ")}`);
		} catch (e) {
			console.error("Travel Sync: Error during sync:", e);
			new Notice(
				"Travel Sync: Failed to connect to API. Check your settings."
			);
		}
	}

	/**
	 * Scan the trips folder for existing files with `type: travel-sync` frontmatter.
	 * Returns a map of trip name -> file path.
	 */
	private async getExistingSyncedTrips(): Promise<Map<string, string>> {
		const result = new Map<string, string>();
		const folderPath = normalizePath(this.settings.tripsFolder);
		const folder = this.app.vault.getAbstractFileByPath(folderPath);

		if (!folder || !(folder instanceof TFolder)) {
			return result;
		}

		const files = this.getAllMarkdownFiles(folder);

		for (const file of files) {
			const cache = this.app.metadataCache.getFileCache(file);
			if (cache?.frontmatter?.type === FRONTMATTER_TYPE && cache.frontmatter.trip) {
				result.set(cache.frontmatter.trip, file.path);
			}
		}

		return result;
	}

	private getAllMarkdownFiles(folder: TFolder): TFile[] {
		const files: TFile[] = [];
		for (const child of folder.children) {
			if (child instanceof TFile && child.extension === "md") {
				files.push(child);
			} else if (child instanceof TFolder) {
				files.push(...this.getAllMarkdownFiles(child));
			}
		}
		return files;
	}

	/**
	 * Write a trip note to the vault. If an existing synced file exists, overwrite it.
	 * Otherwise create in the trips folder (inside a trip subfolder if one exists).
	 */
	private async writeTripNote(
		tripName: string,
		filename: string,
		content: string,
		existingPath?: string
	): Promise<void> {
		if (existingPath) {
			// Overwrite existing synced file
			const file = this.app.vault.getAbstractFileByPath(existingPath);
			if (file instanceof TFile) {
				await this.app.vault.modify(file, content);
				return;
			}
		}

		// Create new file — look for a trip subfolder first
		const basePath = normalizePath(this.settings.tripsFolder);

		// Check if there's already a subfolder that matches this trip name
		const baseFolder = this.app.vault.getAbstractFileByPath(basePath);
		let targetFolder = basePath;

		if (baseFolder instanceof TFolder) {
			for (const child of baseFolder.children) {
				if (
					child instanceof TFolder &&
					child.name.toLowerCase().includes(tripName.toLowerCase())
				) {
					targetFolder = child.path;
					break;
				}
			}
		}

		const filePath = normalizePath(`${targetFolder}/${filename}`);

		// Ensure parent folder exists
		const parentPath = filePath.substring(0, filePath.lastIndexOf("/"));
		if (
			parentPath &&
			!this.app.vault.getAbstractFileByPath(parentPath)
		) {
			await this.app.vault.createFolder(parentPath);
		}

		await this.app.vault.create(filePath, content);
	}
}
