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

## Which battery sensor should I use?

Any sensor that shows the car's **traction battery level in %** works. Below is a starting list of common car integrations. Entity names depend on what you named the car and on the integration version – look for the entity with the name in the table, or search in **Developer tools → States** for `battery` / `soc` / `charge` with unit `%`.

✅ = verified with this integration · 🔎 = not verified yet, what to look for. Please [open an issue](https://github.com/mirhagen/ha-tibber-ev-soc-sync/issues) or a pull request with corrections and additions.

### Cars

| Brand | Home Assistant integration | Battery level (%) | Plugged in (optional) | |
|---|---|---|---|---|
| **Kia, Hyundai, Genesis** | [Kia Uvo / Hyundai Bluelink](https://github.com/Hyundai-Kia-Connect/kia_uvo) (HACS) | **EV Battery Level** – `sensor.<car>_ev_battery_level` | **EV Battery Plug** – `binary_sensor.<car>_ev_battery_plug` | ✅ |
| Tesla | [Tesla Fleet](https://www.home-assistant.io/integrations/tesla_fleet/), [Teslemetry](https://www.home-assistant.io/integrations/teslemetry/), [Tessie](https://www.home-assistant.io/integrations/tessie/) | *Battery level* | *Charge cable* | 🔎 |
| Volvo | [Volvo](https://www.home-assistant.io/integrations/volvo/) | *Battery charge level* | *Charging connection status* | 🔎 |
| Polestar | [Polestar API](https://github.com/pypolestar/polestar_api) (HACS) | *Battery charge level* | *Charging connection status* | 🔎 |
| Volkswagen ID | [Volkswagen We Connect ID](https://github.com/mitch-dc/volkswagen_we_connect_id) (HACS) | *State of charge* / *Battery level* | *Plug connection state* | 🔎 |
| Škoda | [MySkoda](https://github.com/skodaconnect/homeassistant-myskoda) (HACS) | *Battery percentage* | *Charger connected* | 🔎 |
| Renault, Dacia | [Renault](https://www.home-assistant.io/integrations/renault/) | *Battery* | *Plug state* (`unplugged` = not plugged in) | 🔎 |
| Mercedes-Benz | [Mercedes-Benz](https://github.com/ReneNulschDE/mbapi2020) (HACS) | *State of charge* | *Charging active* / plug status | 🔎 |
| BMW, Mini | [BMW Connected Drive](https://www.home-assistant.io/integrations/bmw_connected_drive/) | *Remaining battery percent* | *Charging plug connected* | 🔎 |
| Nissan | [Nissan Leaf](https://www.home-assistant.io/integrations/nissan_leaf/) | *Charge* | *Plug status* | 🔎 |
| Any car | [evcc](https://github.com/marq24/ha-evcc) (HACS) or an OBD-II dongle (e.g. WiCAN) | the vehicle's *SoC* | – | 🔎 |

> [!IMPORTANT]
> Choose the **traction (high-voltage) battery**, not the 12 V battery. Kia/Hyundai has both: *EV Battery Level* is correct, *Car Battery Level* is the 12 V battery.

### Chargers (for "plugged in")

The charger's status is often the most reliable "plugged in" signal, because it changes the moment the cable is connected.

| Charger | Integration | Sensor | "Not plugged in" state | |
|---|---|---|---|---|
| **Easee** | [Easee EV Charger](https://github.com/nordicopen/easee_hass) (HACS) | `sensor.<charger>_status` | `disconnected` | ✅ |
| Zaptec | [Zaptec](https://github.com/custom-components/zaptec) (HACS) | Charger operation mode | `disconnected` | 🔎 |
| Wallbox | [Wallbox](https://www.home-assistant.io/integrations/wallbox/) | Status description | `Disconnected`, `Ready` | 🔎 |
| go-e | via [MQTT](https://www.home-assistant.io/integrations/mqtt/) or a go-e integration from HACS | Car state | `Idle` | 🔎 |

If the car's integration has a binary "plugged in" sensor, you can use that instead – then the "not plugged in" states are not needed.

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

**Inställning:** Inställningar → Enheter och tjänster → Lägg till integration → *Tibber EV SoC Sync* → logga in med Tibber-kontot → välj bilen → välj batterisensorn och gärna laddboxens status. Se [listan över batterisensorer](#which-battery-sensor-should-i-use) – för Kia/Hyundai är det **EV Battery Level** (inte *Car Battery Level*, som är 12 V-batteriet), och för Easee laddboxens *Status* med `disconnected`. Vid inkoppling skickas bilens batterinivå till Tibber; medan den sitter i skickas den igen när nivån ändrats med minst 5 procentenheter. Det finns en knapp *Synka nu* och tjänsten `tibber_ev_soc_sync.sync`.

## License

MIT
