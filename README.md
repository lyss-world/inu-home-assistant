# Inu for Home Assistant

Complete one Inu task by its full name or send a notification to your Inu inbox.
This HACS integration needs an Inu account and a connection key.

## Set up

1. Add `https://github.com/lyss-world/inu-home-assistant` to HACS as an **Integration**.
2. Download **Inu** and restart Home Assistant.
3. In Inu Settings → Integrations → Home Assistant, create a connection key with the permissions you want.
4. In Home Assistant, choose **Settings → Devices & services → Add integration → Inu** and paste the key.

## Use

- **Inu device → Complete task:** Enter the full task name, such as `Wash to fluff`.
- **Inu device → Send notification:** Enter a message for the Inu inbox.
- **Automation → Inu → Complete task:** Fill in **Task name**. To reuse the result, set the response variable to `inu_result` and use `{{ inu_result.feedback }}`.
- **Last result** shows the latest outcome. Inu checks a missing confirmation automatically.

Update through HACS and restart Home Assistant. Existing connection keys and automation action IDs work with the update.

## Data and access

Inu receives your text and a request ID over HTTPS. Exact completion and plain notifications need no model. Optional free-form commands may use the AI provider you configured in Inu. The integration reads connection status and action confirmations. A paired PC and its optional MQTT sensors work separately. Keep your key and HA backups private. To revoke the key, choose **Disconnect** in Inu.

[Setup help](https://inuwithyou.com/help/home-assistant.html)
