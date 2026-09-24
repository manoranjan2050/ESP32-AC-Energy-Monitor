# CT6 Energy Monitor PCB (v0.1): ESP32-S3 DevKit + 6 CT + ZMPT101B

KiCad 10 project: [`kicad/ct6-energy-monitor.kicad_pro`](kicad/ct6-energy-monitor.kicad_pro)
Schematic PDF: [`renders/schematic.pdf`](renders/schematic.pdf) · 3D top view: [`renders/pcb_top.png`](renders/pcb_top.png) · BOM: [`bom.csv`](bom.csv)

> **Status: v0.1 fully routed. Not yet built or tested; do the breadboard test and the checklist below first.**
> ERC: 0 violations · DRC: 0 errors, **0 unconnected**, 0 creepage/clearance · schematic-to-PCB parity: 0 issues.
> Remaining DRC warnings are cosmetic only (silkscreen text overlaps, and the jack's edge marker moved off Edge.Cuts).

**Manufacturing files** (`fab/`):
- `ct6-gerbers-jlcpcb.zip`: Gerbers + drill, upload to JLCPCB as-is
- `ct6-bom.csv` and `ct6-cpl.csv`: BOM and pick-and-place (origin = bottom-left board corner)
- `ct6-kicad-project.zip`: the whole KiCad project

**EasyEDA:** EasyEDA Pro → *File → Import → KiCad*, then select `ct6-kicad-project.zip` (or the `.kicad_pro`).
The files are KiCad 10 format; if your EasyEDA version refuses them, order from the Gerber zip instead.
EasyEDA Standard only imports old KiCad 5 files.

Everything is generated from one netlist in [`generate_kicad.py`](generate_kicad.py), and routed by [`route_pcb.py`](route_pcb.py):
1. The 230 V nets are hand-routed as locked 0.8 mm tracks.
2. **Freerouting 1.9.0** autoroutes the rest, with the whole mains block (+6.5 mm) set as a keepout.
3. The GND pour is added last.

```bash
set CT6_NO_ZONES=1
"C:/Program Files/KiCad/10.0/bin/python.exe" hardware/generate_kicad.py
"C:/Program Files/KiCad/10.0/bin/python.exe" hardware/route_pcb.py path/to/freerouting-1.9.0.jar
```

⚠ Both scripts overwrite the `.kicad_pcb`. **If you edit the board by hand in KiCad, stop rerunning them.**

---

## Block diagram

```
 5V terminal / USB-C ─ polyfuse ─ SS34 ─► DevKit 5V ──► DevKit 3V3 ─ ferrite ─► +3V3A (analog)
                                                                               │
 +3V3A ─ 12k/10k ─► MCP6002-A buffer ─ 47R ─► VB = 1.50 V (10µF+100nF) ────────┼──► GPIO10 (bias monitor)
                                                                               │
 CT1..CT6 jack ─► [22R burden via mA/V jumper] ─ 1k ─┬─ 1k8 → VB              │
                                                      ├─ 100nF → GND           │
                                                      └─ BAT54S clamp ─► GPIO1,4,5,6,7,8
                                                                               │
 230V L/N ─ fuse 100mA ─ MOV ─ 4×220k ─► ZMPT101B ─► MCP6002-B TIA (2k7‖47nF) ─ 1k ─ BAT54S ─► GPIO9
```

## CT input channel (copied from KinCony KC868-M16v2, per channel)

| Part | Value | Purpose |
|---|---|---|
| J1n | 3.5 mm jack (SJ1-3523N) | **Tip = signal, Sleeve = VB**, Ring unused (SCT-013 wiring) |
| R1n1 | **22 Ω 0.1 %** | Burden for **mA-type** CTs (SCT-013-000 100 A/50 mA) |
| JP1n | 3-pin header | **1-2 = mA** (burden in, **ship with this fitted**); **2-3 = V** (burden out, for 1 V CTs such as SCT-013-030) |
| R1n2 / R1n3 | 1 kΩ / 1.8 kΩ 1 % | Attenuator: ×0.643 around VB. The 1 k limits current into the pin; the 1k8 holds an empty jack at VB |
| C1n | 100 nF | Anti-alias / noise filter, ~2.5 kHz |
| D1n | BAT54S | Clamps the ADC pin between GND and 3V3A |

**Headroom at the ADC pin** (1.50 V bias; S3 12 dB range is about 0 to 3.1 V):

| CT | At full scale | At the pin |
|---|---|---|
| SCT-013-000 + 22 Ω (jumper **mA**) | 100 A → 1.10 V RMS | ±1.00 V peak → 0.50 to 2.50 V ✅ |
| SCT-013-030 1 V (jumper **V**) | 30 A → 1.00 V RMS | ±0.91 V peak → 0.59 to 2.41 V ✅ |

Firmware scale (amps per RMS volt **measured at the pin**) = CT ratio ÷ 0.643:
- 100 A/50 mA + 22 Ω: 100 / 0.05 / 22 / 0.643 = **141.4 A/V**
- 30 A/1 V: 30 / 0.643 = **46.7 A/V**

Then fine-tune each channel's calibration factor against a clamp meter.

A **wrong jumper in one direction is safe**: a 1 V CT with the jumper on mA reads only **~25 % of the true value**, because its internal ~67 Ω burden ends up in parallel with the 22 Ω. It's obviously wrong, but harmless. **The dangerous case is an mA CT with the jumper on V.** In that state the CT runs open (the 0/4095 clipping from the breadboard test). That is why mA is the default and the 1k series resistor plus BAT54S protect the pin.

## Voltage channel (ZMPT101B, on board)

- **Primary:** 230 V → F2 100 mA T → 4 × 220 kΩ 1206 (880 kΩ, 57 V per resistor) → 0.26 mA. RV1 (275 VAC MOV) across L/N after the fuse.
- **Secondary:** into MCP6002-B used as a **transimpedance amplifier** with its + input at VB. Output = VB − 0.26 mA × 2.7 kΩ = **1.50 V ± 0.70 V RMS** (±1.0 V peak at 230 V, ±1.2 V at 270 V). 47 nF in parallel sets a ~1.25 kHz roll-off.
- Output goes through 1 kΩ + 100 nF + BAT54S to GPIO9. Calibrate volts in firmware; there's no trimmer.

## GPIO map (ESP32-S3, all ADC1)

| Signal | GPIO | DevKitC-1 pin |
|---|---|---|
| CT1 | GPIO1 | J3-4 (right header) |
| CT2 to CT6 | GPIO4, 5, 6, 7, 8 | J1-4..7, J1-12 (left header) |
| Voltage | GPIO9 | J1-15 |
| Bias monitor | GPIO10 | J1-16 |
| I2C OLED SDA / SCL | GPIO17 / GPIO18 | J1-10 / J1-11 |

Not used: GPIO0/3/45/46 (strapping), GPIO35 to 37 (octal PSRAM on N16R8), GPIO11 to 20 (ADC2, conflicts with Wi-Fi).

## PCB (120 × 90 mm, 2-layer)

- **Mains block** (top-left) is fenced by an **L-shaped 1.6 mm routed slot**. The slot's vertical leg runs **under the ZMPT101B** between primary and secondary pins (10 mm pin-to-pin).
- **Custom DRC rules** (`kicad/ct6-energy-monitor.kicad_dru`): **6.5 mm clearance and creepage** from any `AC_*` net to all low-voltage copper.
- **GND pour** on both layers covers the LV area only. It excludes the mains block and the **DevKit antenna area** (top-right; the DevKit's antenna end sits at the top board edge).
- CT jacks sit on the bottom edge. The DevKit's USB end points down into a clear area, so you can still plug in a USB cable for flashing.

## Before ordering (checklist)

1. **Measure your DevKit.** Header row spacing is set to **22.86 mm** (`DEVKIT_ROW_SPACING`), and the pin order is ESP32-S3-DevKitC-1. Your breadboard test showed the silkscreen didn't match the actual pin (the wire on "4" was GPIO1). **Check every pin used here with a meter or the pin-scan firmware.**
2. **ZMPT101B footprint:** 10.0 × 12.7 mm pin grid, cross-checked against two independent KiCad libraries. Check it against your part with calipers.
3. **Screw terminals J1/J5:** make sure the wire entry faces the board edge (rotate 180° in KiCad if not).
4. **Review the autorouted tracks** in KiCad. Autorouters are functional, not beautiful. The CT signal traces to the DevKit are long diagonals, which is fine at 50 Hz, but you may want to tidy them.
5. After any change, run DRC. It must show **0 unconnected items and 0 creepage errors**.
6. Mains safety: 230 V on a PCB needs an enclosure, a fuse, and no exposed metal. The ZMPT101B is the isolation barrier, so don't bypass it.

## Firmware

Not written yet. Extending `esphome/energy_monitor_test.yaml` to 6 CT + V gives:
- per-channel `ct_gpio`, CT type (mA/V), ratio and calibration
- interleaved V + I sampling for real power, PF and kWh

The on-board **attenuator (×0.643) must be included** in the scale; see the formulas above.
