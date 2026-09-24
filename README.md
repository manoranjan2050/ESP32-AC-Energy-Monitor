# ESP32-S3 AC Energy Monitor (6 CT + voltage), ESPHome / Home Assistant

An open-source, DIY mains energy monitor built on an **ESP32-S3 DevKit**:
- up to **6 SCT-013 current transformers (CTs)**, each channel works with **100A/50mA** or **30A/1V** CTs
- one **ZMPT101B** voltage sensor
- **ESPHome** firmware, visible in **Home Assistant**

> **⚠ Not a certified energy meter.** The ESP32 ADC is noisy and non-linear. Don't use this for
> billing or protection. The board has a **230 V section**, so build and test it only if you're
> competent with mains wiring.

---

## Project status (2026-09-24)

| Part | Status |
|---|---|
| Stage-1 test firmware (1 CT, true RMS, calibration in HA) | ✅ Working (`esphome/energy_monitor_test.yaml`) |
| CT input circuit (bias + 1k/1.8k + 104 + burden) | ✅ **Proven on a breadboard** with both CT types (results below) |
| Custom PCB v0.1 (KiCad): 6 CT + on-board ZMPT101B | ✅ Designed and **fully routed**. ERC 0, DRC 0 errors, schematic ↔ PCB parity 0. **Not built yet** |
| On-board ZMPT101B + MCP6002 voltage stage | ⚠ Designed, **not tested yet** |
| 6-channel + voltage firmware (real power, PF, kWh) | ⏳ Next step (after the PCB) |

### Breadboard test results (CT channel = same values as the PCB)

| CT | Load | Reading | Notes |
|---|---|---|---|
| 30A/1V | CT unclamped | ~0.08 A | Noise floor |
| 30A/1V | Light + fan | **0.33 A** | ≈ 75 W |
| 30A/1V | Water heater | **12.66 A** | Clean sine (pp/rms 2.86), no clipping |
| 100A/50mA + 24 Ω burden | Induction cooker | **4.6 A** | Stable, no clipping |

---

## Repository map

```
esphome/
  energy_monitor_test.yaml      Stage-1 test firmware (1 CT on GPIO1)
  secrets.example.yaml          Copy to secrets.yaml (git-ignored) and fill in Wi-Fi/keys
docs/wiring.md                  Stage-1 breadboard wiring checks
hardware/
  README.md                     PCB design notes, calculations, before-ordering checklist
  kicad/                        KiCad 10 project (schematic + routed PCB + ZMPT101B footprint + DRC rules)
  fab/                          Manufacturing files: Gerbers zip, BOM, pick-and-place, KiCad zip
  renders/                      Diagrams (SVG), PCB images, schematic PDF
  generate_kicad.py             Builds schematic + PCB from ONE netlist (source of truth)
  route_pcb.py                  Hand-routes mains, autoroutes the rest with Freerouting
  make_*_svg.py                 Regenerate the SVG diagrams from the same netlist
```

---

## Files you'll use

### KiCad (schematic + PCB)

| File | What it is |
|---|---|
| [`hardware/kicad/ct6-energy-monitor.kicad_pro`](hardware/kicad/ct6-energy-monitor.kicad_pro) | **Open this in KiCad 10** (free, kicad.org). The schematic and PCB open together |
| [`hardware/kicad/ct6-energy-monitor.kicad_sch`](hardware/kicad/ct6-energy-monitor.kicad_sch) | Schematic: 81 parts, 42 nets |
| [`hardware/kicad/ct6-energy-monitor.kicad_pcb`](hardware/kicad/ct6-energy-monitor.kicad_pcb) | Routed 2-layer PCB, 120 × 90 mm |
| [`hardware/fab/ct6-kicad-project.zip`](hardware/fab/ct6-kicad-project.zip) | The whole KiCad project in one zip |
| [`hardware/renders/schematic.pdf`](hardware/renders/schematic.pdf) | Schematic as a PDF, for viewing and printing |

### EasyEDA

- **EasyEDA Pro:** *File → Import → KiCad*, then pick `ct6-energy-monitor.kicad_pro` or `ct6-kicad-project.zip`.
  The files are **KiCad 10 format**, and EasyEDA's importer may only accept older KiCad versions (**not tested**).
- **EasyEDA Standard:** only imports old KiCad 5 files, so it won't work.
- **If the import fails**, you have three options:
  1. **Order straight from the Gerbers** (below). The board is already routed, so no EasyEDA is needed.
  2. **Redraw in EasyEDA** using [`easyeda_connection_guide.svg`](hardware/renders/easyeda_connection_guide.svg).
     It shows every part, every pin and its net name. Place the parts, put a **Net Label** with the exact
     name on each pin, then check the nets against the list in section 7 of that SVG.
  3. Ask for a **KiCad 6-format copy** of the schematic, which EasyEDA Pro is more likely to accept.

### Ordering (JLCPCB)

| File | Use |
|---|---|
| [`hardware/fab/ct6-gerbers-jlcpcb.zip`](hardware/fab/ct6-gerbers-jlcpcb.zip) | Upload as-is: Gerbers + drill, 2 layers |
| [`hardware/fab/ct6-bom.csv`](hardware/fab/ct6-bom.csv) | Bill of materials |
| [`hardware/fab/ct6-cpl.csv`](hardware/fab/ct6-cpl.csv) | Pick-and-place, origin = bottom-left board corner |

### Diagrams (SVG, open in any browser)

| Diagram | Shows |
|---|---|
| [`pcb_full_connection.svg`](hardware/renders/pcb_full_connection.svg) | **The complete PCB circuit**: every R, C, diode, jumper, op-amp pin and GPIO |
| [`easyeda_connection_guide.svg`](hardware/renders/easyeda_connection_guide.svg) | Every part as a card: pin → net name. Use it for EasyEDA redraws and checks |
| [`final_6ct_voltage_connection.svg`](hardware/renders/final_6ct_voltage_connection.svg) | Breadboard version: 6 CT + ready-made ZMPT101B module |
| [`breadboard_connection.svg`](hardware/renders/breadboard_connection.svg) | Breadboard test of one CT channel (the proven circuit) |
| [`pcb_top.png`](hardware/renders/pcb_top.png), [`pcb_copper.png`](hardware/renders/pcb_copper.png) | PCB 3D render and copper view |

---

## How the circuit works

### GPIO map (ESP32-S3, ADC1 only)

| Signal | GPIO | DevKit socket pin |
|---|---|---|
| CT1 | GPIO1 | J4-4 |
| CT2 · CT3 · CT4 · CT5 | GPIO4 · 5 · 6 · 7 | J3-4 · 5 · 6 · 7 |
| CT6 | GPIO8 | J3-12 |
| Voltage (ZMPT101B) | GPIO9 | J3-15 |
| Bias monitor | GPIO10 | J3-16 |
| I²C OLED SDA / SCL | GPIO17 / GPIO18 | J3-10 / J3-11 |
| 5V in / 3V3 / GND | — | J3-21 / J3-1,2 / J3-22, J4-1,21,22 |

Avoid GPIO0/3/45/46 (strapping), GPIO35–37 (octal PSRAM on N16R8) and GPIO11–20 (ADC2, conflicts with Wi-Fi).
**Measure your DevKit before ordering.** On the test board the silkscreen "4" was really GPIO1.

### One CT channel (×6, identical)

```
CT sleeve ─────────────────────────────────────── VB (bias ≈ 1.5 V)
CT tip ──┬── 1 kΩ ──┬── ADC node ──► GPIO
         │          ├── 1.8 kΩ ──► VB
       22 Ω         ├── 100 nF (104) ──► GND
     (burden,       └── BAT54S clamp (to GND and +3V3A)
   via jumper JP)
```

- **1 kΩ + 1.8 kΩ** scale the signal to **×0.643** around the bias. This gives headroom for 100 A, and the 1 kΩ limits current into the pin.
- **100 nF** filters noise (~2.5 kHz).
- **BAT54S** clamps the pin between 0 and 3.3 V. See "Diodes" below.

### Jumpers JP11…JP16 (one per CT)

| CT type | Shunt position | Burden | Home Assistant settings |
|---|---|---|---|
| **100A/50mA** (SCT-013-000) | **1-2 (mA), default** | IN | Burden **22** (or 24) · Secondary **0.05** · Primary **100** · Calibration **1.555** |
| **30A/1V** (SCT-013-030) | **2-3 (V)** | OUT | Burden **1** · Secondary **1** · Primary **30** · Calibration **1.555** |

- **1.555** undoes the ×0.643 divider. Fine-tune each channel: `Cal = 1.555 × (clamp-meter A ÷ reading A)`.
- **A 1V CT with the shunt on mA** reads ~25 % of the true value. That's safe, just obviously wrong.
- **⚠ A 100A CT with the shunt on V runs OPEN.** The reading clips to 0/4095 and can damage the CT or the pin. **Unclamp immediately.**
- Ship boards with every shunt on **1-2**.

### Diodes (D…)

| Designator | Part | Job |
|---|---|---|
| **D1** | SS34 Schottky | Power input: reverse-polarity protection, and stops USB 5V back-feeding your 5V supply |
| **D11 … D16** | BAT54S | ADC clamps for **CT1 … CT6** (D1**n** = CT**n**, so **D16 = CT6 → GPIO8**) |
| **D41** | BAT54S | ADC clamp for the voltage channel (GPIO9) |

A **BAT54S** is two Schottky diodes in series in one SOT-23:
- **pin 1 = GND side**
- **pin 2 = +3V3A side**
- **pin 3 = ADC node**

It does nothing while the signal is between 0 and 3.3 V. If a fault pushes the pin outside that range (for example a CT without its burden), it clamps the pin. The 1 kΩ in front limits the current. The clamps were optional on the breadboard; **fit them on the PCB.**

### Parts naming (per CT channel n = 1…6)

`J1n` jack · `R1n1` 22 Ω burden · `JP1n` mA/V jumper · `R1n2` 1 kΩ · `R1n3` 1.8 kΩ · `C1n` 100 nF · `D1n` BAT54S

### Resistor colour codes (4-band)

| Value | Bands |
|---|---|
| 10 kΩ | brown · black · orange |
| 1 kΩ | brown · black · red |
| 1.8 kΩ | brown · grey · red |
| 22 Ω | red · red · black |
| 24 Ω | red · yellow · black |
| 18 Ω | brown · grey · black (⚠ not 18 kΩ = brown · grey · orange) |

A ceramic cap marked **104** = 100 nF; **103** = 10 nF; **473** = 47 nF.

---

## Working on another PC

```bash
git clone https://github.com/manoranjan2050/ESP32-AC-Energy-Monitor.git
```

- **PCB:** install KiCad 10 and open `hardware/kicad/ct6-energy-monitor.kicad_pro`.
- **Firmware:** copy `esphome/secrets.example.yaml` to `esphome/secrets.yaml` (git-ignored) and fill in your Wi-Fi and keys.
- **Regenerate** (optional; this overwrites the KiCad files, so **don't** run it after editing the board by hand):

  ```bash
  "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/generate_kicad.py
  ```

## Before ordering the PCB

1. Measure the **DevKit header row spacing** (22.86 mm) and check every pin used.
2. Check the **ZMPT101B pin grid**: 10.0 × 12.7 mm, with calipers.
3. **Screw terminals:** the wire entry faces the board edge.
4. Keep the **6.5 mm mains creepage** and the **slot under T1**.
5. **First power-up without mains and without CTs.** Expect +3V3A ≈ 3.3 V, VB ≈ 1.50 V, and every CTn_ADC / V_ADC ≈ 1.50 V.

Full details are in [`hardware/README.md`](hardware/README.md).

---

## Next steps

1. Order and build PCB v0.1, then test it: the CT channels first, then the on-board voltage stage (untested so far).
2. **6-channel + voltage ESPHome firmware:**
   - per-channel CT type, ratio and calibration
   - V + I sampled together for **real power, power factor, frequency and kWh**
   - Home Assistant **Energy dashboard** support

---

# Stage-1 test firmware guide (1 CT, breadboard)

> The sections below document the **first single-CT test**. Its bias circuit (10k/10k) and direct CT
> wiring were the starting point. The **final, proven channel circuit** adds the 1 kΩ / 1.8 kΩ / 104
> network shown above: use [`breadboard_connection.svg`](hardware/renders/breadboard_connection.svg) and set
> **Calibration 1.555**.

- Board: **ESP32-S3** (QFN56 rev v0.2, 16 MB flash, 8 MB PSRAM, native USB)
- ESPHome: **2026.8.2**, esp-idf framework
- Firmware: [`esphome/energy_monitor_test.yaml`](esphome/energy_monitor_test.yaml)
- Wiring checks: [`docs/wiring.md`](docs/wiring.md)


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

## Original roadmap (written before the 1-channel test)

The 1-channel test has since passed, and the 6-CT PCB is designed. See **Project status** and **Next steps** at the top of this README.

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
