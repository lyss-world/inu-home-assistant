# Inu for Home Assistant

A small account connector for completing a task by name and checking its result.
Requires an Inu account and a Home Assistant connection key. This is a custom
integration, not an official Home Assistant integration.

## Install

1. In HACS, open the menu > Custom repositories.
2. Add `https://github.com/lyss-world/inu-home-assistant` as **Integration**.
3. Download **Inu** and restart Home Assistant.
4. In Inu Settings > Devices & apps > Home Assistant, approve task completion
   and create a connection key with your current password.
5. In Home Assistant, choose Settings > Devices & services > Add integration
   > Inu, then paste the key.

Minimum Home Assistant 2025.1. Open the Inu device and enter a request in
**Message to Inu**, for example `task Wash to fluff abhaken`. Confirming the input
sends it immediately. **Response** shows the outcome. Automations use **Inu > Send
message** with the same Message field; no YAML or extra helpers.

Currently supports completing one task. It is not a general assistant connection.
Check result under Diagnostics reads an unconfirmed result without resending it.
If it remains unknown, review the task in Inu before choosing Mark reviewed.
Existing Complete task automations remain compatible. Update to1.0.2 in HACS and
restart Home Assistant: the old Complete task button is removed, and the existing
text entity becomes the message input without replacing its identity.

## Data and access

The connector sends your message and a request ID to `https://inuwithyou.com`
over HTTPS. Inu handles explicit completion commands directly; other phrasings
may be interpreted using its configured AI service. It reads
connection status and command results; it does not upload your Home Assistant
entity inventory, microphone, screen or PC activity. Home Assistant stores the
connection key in its configuration; keep configuration and backups private.
The connector does not need an open Inu browser or running Windows client.

To revoke access, choose Disconnect in Inu. Removing the HA entry alone does not
revoke the key. Never post keys, task text or private logs in public issues.

[Setup help](https://inuwithyou.com/help/home-assistant.html)


## Notifications

In Inu Settings, allow Home Assistant notifications when creating the connection key.
In a Home Assistant automation, select **Inu: Send notification** and enter the message.
The message stays in Inu notifications. A paired Windows app shows it when notifications
are allowed; it respects your profiles, lock state and notice interval.

**Inu: Send message** can complete one task: `task Wash to fluff abhaken`.
It also supports `notify: Open a window` with notification permission.
An action that is not confirmed reports an error instead of a successful automation.
