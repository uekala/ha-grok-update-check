# Update check with Grok for Home Assistant

Is it safe to install that update yet? This blueprint asks **Grok (xAI)** to search **X, GitHub, Reddit and the Home Assistant forum** for problems reported with the exact version that just showed up, and sends you the verdict before you hit *Install*.

```
Update: Home Assistant Core 2026.11.1
Recommendation: Wait
- Several users report Matter devices unavailable after the update.
- Fix is already merged for 2026.11.2.
```

[![Open your Home Assistant instance and show the blueprint import dialog with this blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fuekala%2Fha-grok-update-check%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgrok_update_check.yaml)

## How it works

1. An update entity you watch switches to *update available*.
2. After a configurable wait (default 4 h, so first reports can appear), Grok runs a live search for that version.
3. You get a push notification: **Install / Wait / Caution** plus up to three concrete issues. Tapping it opens the updates page.
4. The full answer with sources is saved as a Home Assistant notification.

Run the automation manually to check **all pending updates** from your list right away (see [Dashboard button](#dashboard-button)).

## Requirements

- Home Assistant **2026.7** or newer
- [xAI Grok Conversation](https://github.com/braytonstafford/grok_conversation) from HACS, set up with an xAI API key that has credits
- Home Assistant Companion app on your phone

## Setup

1. Import the blueprint with the button above.
2. Create an automation from it and fill in the inputs:

| Input | What it does |
|---|---|
| Updates to watch | Update entities to check. Core, OS, key add-ons and HACS integrations are the best fit. Skip device firmware and dashboard cards. |
| Wait before checking | Hours an update must be available before the check (0–48, default 4). |
| Grok integration | Your xAI Grok Conversation entry. |
| Live search | Full (web + X), web only or X only. |
| Your setup | Optional description (e.g. "HA Green, Zigbee via ZHA, Matter over Thread"), so Grok focuses on what matters to you. |
| Answer language | e.g. English, German, Español. |
| Phone | Device with the Companion app. |
| Also save as notification | Keeps the full answer with sources in HA. |
| Texts (collapsed) | The two fixed messages ("nothing pending", "check failed"), so you can translate them. |

### Dashboard button

A tile that runs the check for every pending update on tap:

```yaml
type: tile
entity: automation.update_check_with_grok   # your automation's entity ID
name: Grok update check
icon: mdi:robot-outline
tap_action:
  action: perform-action
  perform_action: automation.trigger
  target:
    entity_id: automation.update_check_with_grok
  data:
    skip_condition: true
  confirmation:
    text: Run the Grok update check for all pending updates?
```

## Good to know

- **Cost:** each check uses live search. In testing, one check took about 20k prompt tokens. The integration's `estimated_cost` sensor shows what you actually spend.
- **Privacy:** sent to xAI are the component name, both version numbers, the release notes link and your optional setup description. No entity states.
- **Timing:** installing the update before the wait is over skips the check. A Home Assistant restart during the wait does too, because HA resets `for:` timers on restart.
- **Known issue in the integration (v1.11.1):** with *Send user name* enabled, requests from users without a linked person entity fail. Turn that option off until it is fixed upstream.
- Grok can be wrong. Treat the verdict as a hint and read the release notes for anything critical.

## License

[MIT](LICENSE). Unofficial; not affiliated with xAI or Home Assistant.
