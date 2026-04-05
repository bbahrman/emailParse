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

		containerEl.createEl("h2", { text: "Travel Sync Settings" });

		new Setting(containerEl)
			.setName("API URL")
			.setDesc("The base URL of your travel booking API")
			.addText((text) =>
				text
					.setPlaceholder("https://xxx.execute-api.us-east-1.amazonaws.com")
					.setValue(this.plugin.settings.apiUrl)
					.onChange(async (value) => {
						this.plugin.settings.apiUrl = value;
						await this.plugin.saveSettings();
					})
			);

		containerEl.createEl("h3", { text: "Cognito Authentication" });

		new Setting(containerEl)
			.setName("User Pool ID")
			.setDesc("Cognito User Pool ID (e.g., us-east-1_xxxxxxxx)")
			.addText((text) =>
				text
					.setPlaceholder("us-east-1_xxxxxxxx")
					.setValue(this.plugin.settings.cognitoUserPoolId)
					.onChange(async (value) => {
						this.plugin.settings.cognitoUserPoolId = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("Client ID")
			.setDesc("Cognito App Client ID")
			.addText((text) =>
				text
					.setPlaceholder("xxxxxxxxxxxxxxxxxxxxxxxxxx")
					.setValue(this.plugin.settings.cognitoClientId)
					.onChange(async (value) => {
						this.plugin.settings.cognitoClientId = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("Email")
			.setDesc("Your login email")
			.addText((text) =>
				text
					.setPlaceholder("you@example.com")
					.setValue(this.plugin.settings.cognitoEmail)
					.onChange(async (value) => {
						this.plugin.settings.cognitoEmail = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("Password")
			.setDesc("Your login password")
			.addText((text) => {
				text.setPlaceholder("password")
					.setValue(this.plugin.settings.cognitoPassword)
					.onChange(async (value) => {
						this.plugin.settings.cognitoPassword = value;
						await this.plugin.saveSettings();
					});
				text.inputEl.type = "password";
			});

		containerEl.createEl("h3", { text: "Vault" });

		new Setting(containerEl)
			.setName("Trips folder")
			.setDesc("Vault folder where synced trip notes are created")
			.addText((text) =>
				text
					.setPlaceholder("path/to/trips")
					.setValue(this.plugin.settings.tripsFolder)
					.onChange(async (value) => {
						this.plugin.settings.tripsFolder = value;
						await this.plugin.saveSettings();
					})
			);

		containerEl.createEl("h3", { text: "Actions" });

		new Setting(containerEl)
			.setName("Sync now")
			.setDesc("Manually sync all trips from the API")
			.addButton((button) =>
				button
					.setButtonText("Sync Trips")
					.setCta()
					.onClick(async () => {
						button.setDisabled(true);
						button.setButtonText("Syncing...");
						try {
							await this.plugin.runSync();
							button.setButtonText("Done!");
							setTimeout(() => {
								button.setButtonText("Sync Trips");
								button.setDisabled(false);
							}, 2000);
						} catch {
							button.setButtonText("Failed");
							setTimeout(() => {
								button.setButtonText("Sync Trips");
								button.setDisabled(false);
							}, 2000);
						}
					})
			);
	}
}
