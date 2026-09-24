# ESP32 AC Energy Monitor: Stage 1 (single SCT-013-000 signal test)

> **⚠ This is test and calibration firmware, not a certified energy meter.**
> It checks that the CT signal reaches the ESP32 correctly. The "estimated
> current" entities are a theoretical conversion that is off by default. The
> ESP32 ADC is noisy and non-linear, so don't use these numbers for billing
> or protection.

- Board: **ESP32-S3** (QFN56 rev v0.2, 16 MB flash, 8 MB PSRAM, native USB), detected on COM5
- ESPHome: **2026.8.2**, esp-idf framework
- Firmware: [`esphome/energy_monitor_test.yaml`](esphome/energy_monitor_test.yaml)
- Wiring detail: [`docs/wiring.md`](docs/wiring.md)
- **Custom PCB (6 CT + ZMPT101B, KiCad):** [`hardware/README.md`](hardware/README.md)

---

## 1. Hardware wiring (overview)

```
                     ESP32-S3 3V3
                          │
                         10k
                          │
             ┌────────────┼──────────── BIAS node (~1.65 V)
             │            │                 │
             │           10k            [10 µF, optional
             │            │              but recommended]
             │           GND                │
             │                             GND
   SCT-013-000
   ┌───────────┐
   │ lead A ───┼──────────┬──────── BIAS node
   │           │         22 Ω   (burden, directly across the CT leads)
   │ lead B ───┼──────────┴──────── ESP32-S3 GPIO1 (ADC1_CH0)
   └───────────┘
```

The CT drives an AC voltage across the 22 Ω burden. Because one end of the
burden sits on the 1.65 V bias node, the ADC pin sees **1.65 V ± the AC signal**.

## 2. ESP32 ADC pin configuration

Set the pin in the `substitutions:` block. Give the GPIO **number only**:

```yaml
ct_gpio: "1"     # GPIO1 = ADC1 channel 0 (check the pin electrically; header labels can be misleading)
```

On the ESP32-S3 use an **ADC1 pin, GPIO1 to GPIO10**. Skip GPIO3 (it's a strapping pin).
Don't use ADC2 (GPIO11 to GPIO20), because Wi-Fi uses ADC2.

- Attenuation is **12 dB**. On the S3 that gives about 0 to 3.1 V of usable range.
- Every sample is converted with ESP-IDF's **eFuse curve-fitting calibration**,
  so the ADC is not treated as linear. The diagnostic entity
  **CT ADC Calibration** shows which scheme is active. If it says
  `UNCALIBRATED`, the linear 3.3 V/4095 fallback is in use and the voltages are rough.

## 3. The 22 Ω burden resistor

The SCT-013-000 is a **current-output CT** (100 A : 50 mA) and has **no internal burden**.
The 22 Ω resistor turns its current into a voltage:

| Primary current | Secondary current | Burden RMS | Burden peak | ADC swing (around 1.65 V) |
|---|---|---|---|---|
| 1 A     | 0.5 mA  | 11 mV   | 15.6 mV | ±0.016 V |
| 4.35 A (1 kW) | 2.17 mA | 47.9 mV | 67.7 mV | ±0.068 V |
| 10 A    | 5 mA    | 110 mV  | 156 mV  | ±0.156 V |
| 50 A    | 25 mA   | 550 mV  | 778 mV  | ±0.78 V |
| ~90 A   | 45 mA   | 990 mV  | 1.40 V  | about the S3 ADC limit |
| 100 A   | 50 mA   | 1.10 V  | 1.556 V | **clips** (0.09 to 3.21 V) |

With 22 Ω the usable range is about 0 to 90 A. The **CT Clipped Samples** entity counts samples at the ADC rails.

## 4. The 2 × 10 k bias circuit

The two 10 k resistors from 3V3 to GND make a mid-rail point (~1.65 V), so the AC
signal swings around it instead of going below 0 V. Put a
**10 µF to 100 µF capacitor from the bias node to GND**. Without it the bias node
picks up ripple and noise, which shows up as a higher no-load RMS. The firmware
measures the real bias every window (**CT Bias Voltage**), so it doesn't need to be exactly 1.65 V.

## 5. SCT-013-000 connection

The 3.5 mm jack uses **tip** and **sleeve** for the two secondary leads. The ring is
normally unused. Polarity doesn't matter for RMS. Use a 3.5 mm breakout, or cut
the plug and solder the leads. **Fit the burden before clamping the CT on anything.**

## 6. Flashing the ESP32-S3

**Option A: ESPHome Builder (Home Assistant add-on)**
1. ESPHome Builder → **Secrets** (top-right). Add the lines from
   `esphome/secrets.yaml` (not in git; copy `esphome/secrets.example.yaml` and fill in your values) (`wifi_ssid`, `wifi_password`, `ct_test_api_key`,
   `ct_test_ota_password`, `ct_test_ap_password`).
2. **+ New device** → *Continue* → *Skip* the wizard, or create any device and then
   **Edit** it. Replace the whole YAML with `energy_monitor_test.yaml` and save.
3. **Install** → *Plug into this computer* (Chrome/Edge Web Serial), or
   *Manual download* → *Factory format* and flash with web.esphome.io.
4. Later updates can go over the air: **Install → Wirelessly**.

**Option B: ESPHome CLI on this PC**
```bash
cd "D:/My Project/ElectroIoT/ESP32-AC-Energy-Monitor/esphome"
```
```bash
python -m esphome run energy_monitor_test.yaml --device COM5
```
If the S3 won't enter download mode, hold **BOOT**, tap **RST**, then release BOOT.

## 7. Adding it to Home Assistant

The device uses the ESPHome native API, so HA should discover it automatically
(**Settings → Devices & services → Discovered: CT Energy Test → Configure**). When
asked for the encryption key, enter the `ct_test_api_key` value. If it isn't
discovered, add the **ESPHome** integration manually with host `ct-energy-test.local`
(or its IP address) and port `6053`.

Entities (all published together every **5 s**, one window each):

| Entity | Meaning |
|---|---|
| CT Raw ADC | Last raw 12-bit sample in the window |
| CT ADC Voltage | Last sample converted to volts (calibrated) |
| CT Bias Voltage | Mean of the window, which is the DC bias the RMS is taken around |
| CT Minimum / CT Maximum | Lowest and highest raw counts in the window |
| CT Peak-to-Peak | Calibrated V(max) − V(min) |
| CT AC RMS | **True RMS of the AC part across the burden** (bias removed; 400 samples over 10 cycles) |
| CT Secondary / Primary Current (estimated) | Only while **CT Current Estimate Enabled** is on |
| CT Burden Resistance, CT Rated Primary/Secondary Current, CT Calibration Factor | Editable config numbers, kept across reboots |
| CT Clipped Samples, CT Actual Sample Rate, CT ADC Calibration | Diagnostics |

The current estimate is:
```
secondary_A = CT_AC_RMS / burden_resistance
primary_A   = secondary_A × (ct_primary_current / ct_secondary_current) × calibration_factor
```

## 8. Expected values with NO load (CT unclamped or on a dead cable)

| Entity | Expected |
|---|---|
| CT Bias Voltage | ~1.60 to 1.70 V (depends on the 3V3 rail and resistor tolerance) |
| CT Raw ADC / Min / Max | Around the bias count, roughly 1900 to 2300, with Min and Max only a few dozen counts apart |
| CT Peak-to-Peak | Small, about 10 to 60 mV (ADC noise) |
| CT AC RMS | **Low, about 1 to 10 mV** (noise floor) |
| CT Clipped Samples | 0 |
| CT Actual Sample Rate | ~2000 Hz |

Note your no-load RMS. It is the noise floor. As a rough guide, 5 mV of noise
equals about 0.45 A of "phantom" primary current.

## 9. What changes when you clamp a live conductor

Clamp **one** insulated conductor (live **or** neutral), not the whole cable. If
you clamp live and neutral together, their currents cancel and you read about 0.

With a **1000 W resistive load** (~4.35 A at 230 V):

| Entity | Load off | Load on (theory) |
|---|---|---|
| CT Bias Voltage | ~1.65 V | **Unchanged** (~1.65 V) |
| CT Min / Max | ±a few counts | Spread out by roughly ±85 counts |
| CT Peak-to-Peak | ~0.03 V | **~0.14 V** |
| CT AC RMS | ~0.005 V | **~0.048 V** |
| Primary Current (est., if enabled) | ~0.2 to 0.5 A (noise) | **~4.3 A** |

The HA history graph for **CT AC RMS** should step up when the load turns on and
drop when it turns off. To calibrate, compare against a trusted clamp meter and set
`CT Calibration Factor = meter_amps / estimated_amps`. Tip: pass the conductor
through the CT **5 times** (5 turns), so 4.35 A reads like 21.7 A. That gives a much
better signal-to-noise ratio for calibration (divide by 5 afterwards).

## 10. Safety warnings

- **Mains voltage (230 V AC) can kill.** Only clamp an insulated conductor.
  Never open or modify live wiring on a breadboard setup. If you're unsure, have a
  licensed electrician install the CT.
- **Never leave the SCT-013-000 secondary open-circuit while it's clamped on a
  loaded conductor.** A current-output CT with no burden can produce dangerously
  high voltages and damage itself. Keep the 22 Ω burden fitted whenever the CT is
  plugged in or clamped.
- **Never connect the CT directly to the ESP32 without the burden and bias.** The
  ADC pin must stay between 0 V and 3.3 V. A loose bias wire leaves the pin
  swinging below 0 V, which can damage the GPIO.
- The burden must match the current range. 22 Ω clips above ~90 A. For higher
  currents use a smaller burden (for example 18 Ω).
- The ESP32 is powered from USB and is **not isolated from anything except through
  the CT's own insulation**. Keep the breadboard away from the mains side.
- This firmware is not a certified meter. Don't use it for billing, protection, or
  safety decisions.

---

## Roadmap (not implemented yet, pending a successful 1-channel test)

```
ESP32-S3
├── CT1 … CT8   (ADC1 GPIO1..10; per-channel burden + calibration)
└── ZMPT101B    (voltage)
```
Planned: RMS voltage, RMS current per CT, real/apparent power, power factor,
frequency, kWh with the HA Energy dashboard, per-channel calibration, MQTT option, and OTA.
Eight CTs plus a ZMPT101B is 9 analog inputs, which fits in ADC1's 10 pins on the S3. Real power needs
V and I sampled nearly at the same time, so the stage-2 design will use interleaved sampling (or an external
ADC such as the ADS1115/ADS131M08).
