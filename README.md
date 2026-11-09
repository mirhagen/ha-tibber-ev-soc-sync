# Tibber EV SoC Sync

[![Validate](https://github.com/mirhagen/ha-tibber-ev-soc-sync/actions/workflows/validate.yml/badge.svg)](https://github.com/mirhagen/ha-tibber-ev-soc-sync/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)

Keep **Tibber's battery level for your electric car** up to date from Home Assistant – for cars that Tibber has no direct integration with (shown as *"&lt;brand&gt; offline"* in the Tibber app).

Tibber Smart Charging plans charging from the battery level. For an offline car, Tibber only knows the level you last typed into the app, so it may plan too many (or too few) cheap hours. This integration sends the real level from your car's own Home Assistant integration (Kia, Hyundai, VW, Tesla, …) to Tibber – automatically when the cable is plugged in.

> [!WARNING]
> This integration uses Tibber's **unofficial app API** (`app.tibber.com`) – the same one the Tibber app uses. Tibber's public API cannot set the battery level. Tibber may change the app API at any time, which would stop the sync until the integration is updated. It is not affiliated with or supported by Tibber.

*Svenska: se [längre ned](#svenska).*

## What it does

- **When the car is plugged in** (charger status or a binary sensor): optionally asks the car's integration for a fresh value, waits, and sends the battery level to Tibber – right when Tibber plans the charging.
- **While plugged in**: sends again when the level has changed by at least *N* percentage points.
- **Sync now** button and a `tibber_ev_soc_sync.sync` action for your own automations (optionally with an explicit level).
- Sensors for *Battery level in Tibber*, *Last successful sync* and *Sync status* (with the latest error as an attribute).
- If Tibber stops accepting the login, Home Assistant asks you to log in again (repair/re-authentication).

## Requirements

- A Tibber account with the car added in the Tibber app as a vehicle without integration.
- A sensor in Home Assistant with the car's battery level in percent.
- Recommended: a sensor that shows when the charging cable is plugged in, e.g. the status sensor of your charger (Easee, Zaptec, Wallbox …) or a binary sensor from the car.

## Installation

### HACS (recommended)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/mirhagen/ha-tibber-ev-soc-sync` with type **Integration**.
2. Find **Tibber EV SoC Sync** in HACS and download it.
3. Restart Home Assistant.

### Manual

Copy `custom_components/tibber_ev_soc_sync` to `config/custom_components/` and restart Home Assistant.

## Setup

**Settings → Devices & services → Add integration → Tibber EV SoC Sync**

1. **Log in** with the e-mail and password you use in the Tibber app.
2. **Choose the vehicle** – the integration lists the vehicles on your account.
3. **Choose sensors and behaviour:**

| Option | Meaning | Default |
|---|---|---|
| Battery level sensor | The car's battery level in % | – |
| Plugged-in sensor | Charger status or binary sensor. Plugging in triggers a sync | – (optional) |
| States meaning "not plugged in" | For non-binary sensors, e.g. `disconnected` for Easee | `disconnected`, `unplugged`, `not_connected`, `off` |
| Only sync while plugged in | Level changes are only sent while plugged in | on |
| Sync again when the level has changed by | Percentage points | 5 |
| When plugged in, refresh the battery sensor and wait | Seconds, 0 = send immediately | 60 |

All options except the login can be changed later under **Configure**.

### Tip: wake the car for a fresher value

Some car integrations only return cached data. You can force a refresh yourself and then sync, for example with Kia/Hyundai:

```yaml
automation:
  - alias: Fresh battery level to Tibber when plugged in
    triggers:
      - trigger: state
        entity_id: sensor.charger_status
        from: disconnected
    actions:
      - action: kia_uvo.force_update
      - delay: {minutes: 2}
      - action: tibber_ev_soc_sync.sync
        data:
          config_entry_id: YOUR_CONFIG_ENTRY_ID
```

(Then set *refresh and wait* to 0 in the integration's options to avoid a double sync.)

## Known limitations

- Tibber shows *"Last updated: X days ago"* even after a successful sync. The battery level itself is updated; the timestamp appears to be set only when you save in the app.
- One car per integration entry. Add the integration again for more cars.
- The integration logs in for every sync (syncs are rare). Your password is stored in Home Assistant's config entry like for other cloud integrations.

## Troubleshooting

Look at the **Sync status** sensor and its `last_error` attribute, or download diagnostics from the integration (e-mail and password are redacted).

---

## Svenska

Håller **Tibbers batterinivå för elbilen** uppdaterad från Home Assistant, för bilar som Tibber saknar direktintegration med (heter *"&lt;märke&gt; offline"* i Tibber-appen). Tibbers smartladdning planerar efter batterinivån – med rätt nivå laddar den bara de billigaste timmar som faktiskt behövs.

> [!WARNING]
> Integrationen använder Tibbers **inofficiella app-API**. Tibber kan ändra det när som helst, och då slutar synken fungera tills integrationen uppdaterats. Den är inte kopplad till eller supportad av Tibber.

**Installation:** HACS → ⋮ → *Anpassade arkiv* → `https://github.com/mirhagen/ha-tibber-ev-soc-sync` (typ *Integration*) → ladda ned → starta om.

**Inställning:** Inställningar → Enheter och tjänster → Lägg till integration → *Tibber EV SoC Sync* → logga in med Tibber-kontot → välj bilen → välj batterisensorn och gärna laddboxens status. Vid inkoppling skickas bilens batterinivå till Tibber; medan den sitter i skickas den igen när nivån ändrats med minst 5 procentenheter. Det finns en knapp *Synka nu* och tjänsten `tibber_ev_soc_sync.sync`.

## License

MIT
