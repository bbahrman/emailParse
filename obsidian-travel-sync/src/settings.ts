import { App, PluginSettingTab, Setting } from "obsidian";
import TravelSyncPlugin from "../main";

export class TravelSyncSettingTab extends PluginSettingTab {
	plugin: TravelSyncPlugin;

	constructor(app: App, plugin: TravelSyncPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		new Setting(containerEl)
			.setName("API URL")
			.setDesc(
				"The base URL of your travel booking API (e.g., https://xxx.execute-api.us-east-1.amazonaws.com)"
			)
			.addText((text) =>
				text
					.setPlaceholder("https://your-api-url.com")
					.setValue(this.plugin.settings.apiUrl)
					.onChange(async (value) => {
						this.plugin.settings.apiUrl = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("API Key")
			.setDesc("API key for authenticating requests")
			.addText((text) => {
				text.setPlaceholder("your-api-key")
					.setValue(this.plugin.settings.apiKey)
					.onChange(async (value) => {
						this.plugin.settings.apiKey = value;
						await this.plugin.saveSettings();
					});
				text.inputEl.type = "password";
			});

		new Setting(containerEl)
			.setName("Trips folder")
			.setDesc(
				"Vault folder where synced trip notes are created. Subfolders per trip are used if they exist."
			)
			.addText((text) =>
				text
					.setPlaceholder("path/to/trips")
					.setValue(this.plugin.settings.tripsFolder)
					.onChange(async (value) => {
						this.plugin.settings.tripsFolder = value;
						await this.plugin.saveSettings();
					})
			);
	}
}
