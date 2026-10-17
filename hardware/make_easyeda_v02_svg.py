"""
CT6 Energy Monitor v0.2 (EasyEDA build): ESP32-S3-WROOM-1U-N16R8 module on the board instead of the DevKit
sockets, plus a plug-in ZMPT101B module backup selected by jumper JP2.

Generates renders/easyeda_v02_wroom1u_guide.svg: every part, every pin, every net. The CT channels, bias and
on-board voltage stage are taken unchanged from the v0.1 netlist in generate_kicad.py.

    python hardware/make_easyeda_v02_svg.py
"""
import copy
import os
import sys
from collections import defaultdict
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "renders", "easyeda_v02_wroom1u_guide.svg")

# ------------------------------------------------------------------ v0.2 netlist (shared with the KiCad schematic)
from netlist_v02 import MOD_PINS, P, parts  # noqa: E402

PIN_NAMES = {
    "U1": {"1": "OUT A", "2": "−IN A", "3": "+IN A", "4": "V− (GND)", "5": "+IN B", "6": "−IN B", "7": "OUT B", "8": "V+"},
    "BAT54S": {"1": "A (to GND)", "2": "K (to 3V3A)", "3": "COM"},
    "J2": {"A4": "VBUS", "B4": "VBUS", "A9": "VBUS", "B9": "VBUS", "A1": "GND", "B1": "GND", "A12": "GND",
           "B12": "GND", "SH": "Shield", "A5": "CC1", "B5": "CC2", "A6": "D+", "B6": "D+", "A7": "D−", "B7": "D−",
           "A8": "SBU1", "B8": "SBU2"},
    "U4": {"1": "I/O1", "6": "I/O1", "3": "I/O2", "4": "I/O2", "5": "VBUS", "2": "GND"},
    "U3": {"3": "VIN", "2": "VOUT (+tab)", "1": "GND/ADJ"},
    "D1": {"1": "K (cathode, band)", "2": "A (anode)"},
    "T1": {"1": "VA1 primary", "2": "VA2 primary", "3": "VB1 secondary", "4": "VB2 secondary"},
    "JACK": {"T": "Tip", "S": "Sleeve", "R": "Ring (unused)"},
    "JP": {"1": "mA side", "2": "middle", "3": "V side"},
    "JP2": {"1": "on-board", "2": "→ GPIO9", "3": "module"},
    "J6": {"1": "GND", "2": "VCC", "3": "SCL", "4": "SDA"},
    "J1": {"1": "+5V in", "2": "GND"}, "J5": {"1": "L (live)", "2": "N (neutral)"},
    "J7": {"1": "TX (out)", "2": "RX (in)", "3": "GND"}, "J8": {"1": "VCC", "2": "OUT", "3": "GND"},
    "SW1": {"1": "EN side", "2": "GND side"}, "SW2": {"1": "IO0 side", "2": "GND side"},
}


def pin_name(ref, num):
    if ref in PIN_NAMES:
        return PIN_NAMES[ref].get(num, "")
    lib = P[ref].get("lib_id", "")
    if lib.endswith("BAT54S"):
        return PIN_NAMES["BAT54S"].get(num, "")
    if lib.endswith("AudioJack3"):
        return PIN_NAMES["JACK"].get(num, "")
    if ref.startswith("JP1"):
        return PIN_NAMES["JP"].get(num, "")
    return ""


def net_color(net):
    if net is None:
        return "#9aa5b1"
    if net.startswith("AC_"):
        return "#b3261e"
    if net == "GND":
        return "#222222"
    if net in ("+5V", "VIN_RAW", "VIN_F", "+3V3", "+3V3A"):
        return "#d62828"
    if net.startswith("VB"):
        return "#1d6fd6"
    if net.endswith("_ADC") and net.startswith("CT"):
        return "#e07b00"
    if net.startswith("CT"):
        return "#2a9d3f"
    if net in ("V_OUT", "V_ADC", "ZS_A", "V_ONB", "V_MOD", "ZM_OUT"):
        return "#7b2cbf"
    if net.startswith("USB_"):
        return "#0f8b8d"
    return "#4a5a6a"


FP_NICK = {
    "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal": "Screw terminal 2P 5.08mm",
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": "USB-C 16P",
    "Jack_3.5mm_CUI_SJ1-3523N_Horizontal": "3.5mm jack SJ1-3523N (PJ-3523)",
    "PinHeader_1x03_P2.54mm_Vertical": "Pin header 1x03 2.54mm",
    "PinHeader_1x04_P2.54mm_Vertical": "Pin header 1x04 2.54mm",
    "SOIC-8_3.9x4.9mm_P1.27mm": "SOIC-8", "SOT-23-6": "SOT-23-6", "SOT-223-3_TabPin2": "SOT-223",
    "Fuse_Littelfuse_395Series": "TR5 fuse (395 series)", "RV_Disc_D7mm_W4.2mm_P5mm": "MOV disc 7mm P5",
    "MountingHole_3.2mm_M3": "M3 hole 3.2mm", "ESP32-S3-WROOM-1U": "Module 19.2x18mm",
    "SW_SPST_TL3342": "Tactile switch SMD",
}


def fp_short(fp):
    name = fp.split(":")[1]
    return FP_NICK.get(name, name.replace("_2012Metric", "").replace("_3216Metric", ""))


# ------------------------------------------------------------------ drawing
s = []
emit = s.append


def text(x, y, t, size=13, c="#1b2733", w="400", anchor="start", italic=False):
    emit(f'<text x="{x}" y="{y}" font-size="{size}" fill="{c}" font-weight="{w}" text-anchor="{anchor}"'
         + (' font-style="italic"' if italic else "") + f'>{escape(str(t))}</text>')


def rect(x, y, w, h, fill, stroke, rx=8, sw=1.5):
    emit(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def tag(x, y, w, net):
    c = net_color(net)
    rect(x, y - 13, w, 17, c, c, 8, 1)
    text(x + w / 2, y, net if net else "no connect", 11.5, "#ffffff", "700", "middle")


CARD_W, ROW = 300, 19


def card(x, y, ref):
    p = P[ref]
    pins = sorted(p["pins"].items(), key=lambda kv: (len(kv[0]), kv[0]))
    h = 46 + ROW * max(1, len(pins)) + 8
    mains = any(n and n.startswith("AC_") for n in p["pins"].values())
    new = ref in NEW
    fill = "#fff1f0" if mains else ("#eefaf3" if new else "#f7f9fb")
    stroke = "#c0392b" if mains else ("#2a9d3f" if new else "#b8c4d0")
    rect(x, y, CARD_W, h, fill, stroke)
    text(x + 12, y + 20, f"{ref}  ·  {p['value']}" + ("   NEW" if new else ""), 14.5, "#1b2733", "700")
    sub = fp_short(p["fp"]) + (f"  ·  {p['mpn']}" if p.get("mpn") else "")
    text(x + 12, y + 37, sub if len(sub) <= 50 else sub[:48] + "…", 11, "#5b6b7b")
    if not pins:
        text(x + 12, y + 58, "no electrical pins", 12, "#5b6b7b", italic=True)
    for k, (num, net) in enumerate(pins):
        yy = y + 58 + k * ROW
        nm = pin_name(ref, num)
        text(x + 12, yy, f"pin {num}", 12, "#3d4b59", "600")
        if nm:
            text(x + 62, yy, nm, 11.5, "#5b6b7b")
        tag(x + 168, yy, CARD_W - 180, net)
    return h


def section(y, title, refs, note=None, cols=5, x0=30, color="#1b2733"):
    text(x0, y, title, 20, color, "700")
    y += 12
    if note:
        for ln in note.split("\n"):
            text(x0, y + 12, ln, 13, "#8a4b00", italic=True)
            y += 20
        y += 2
    col_y = [y + 8] * cols
    for ref in refs:
        c = col_y.index(min(col_y))
        h = card(x0 + c * (CARD_W + 16), col_y[c], ref)
        col_y[c] += h + 12
    return max(col_y) + 30


NEW = {"J2", "U4", "U3", "C50", "C51", "U2", "C52", "C53", "R50", "C54", "SW1", "R51", "SW2", "J7",
       "J8", "R52", "R53", "C55", "JP2"}
W = 30 + 5 * (CARD_W + 16) + 14
emit("__HEADER__")
text(30, 44, "CT6 Energy Monitor v0.2 (EasyEDA): ESP32-S3-WROOM-1U-N16R8 on board + ZMPT101B module backup", 25, "#1b2733", "700")
text(30, 70, "Every part, every pin, every net. In EasyEDA: place each part (LCSC numbers given), then put a Net Label with the "
             "EXACT coloured name on each pin. Same name = connected. Green cards = NEW in v0.2.", 14, "#4a5a6a")
text(30, 90, "CT channels, bias and the on-board ZMPT stage are unchanged from v0.1 (CT circuit proven on breadboard). "
             "Power nets: use net labels, not power symbols: +5V, +3V3, +3V3A, GND, VB.", 14, "#4a5a6a")

# what changed box
y = 112
rect(30, y, W - 60, 128, "#fffaf0", "#e0a070")
text(46, y + 26, "What changed from v0.1 (DevKit) → v0.2 (module on board)", 15, "#a33b00", "700")
for k, ln in enumerate([
    "• REMOVED: DevKit sockets J3/J4 and the power-only USB-C.   • ADDED: U2 ESP32-S3-WROOM-1U-N16R8 (U.FL → external 2.4 GHz IPEX antenna, better from inside a metal DB box).",
    "• ADDED: U3 AMS1117-3.3 regulator (+5V → +3V3), J2 USB-C 16P WITH data (D+ → IO20, D− → IO19, native USB for flashing/logs), U4 USBLC6-2SC6 ESD.",
    "• ADDED: EN reset (R50 10k + C54 1µF + SW1 RESET), BOOT (R51 10k + SW2 on IO0), J7 UART header, module decoupling C52/C53 next to module pin 2. KiCad schematic: hardware/kicad_v02/.",
    "• ADDED: J8 ZMPT101B module header (+5V/OUT/GND) → R52 10k / R53 22k / C55 10nF → V_MOD, and JP2 selects GPIO9 source: 1-2 on-board stage, 2-3 module.",
    "• Unchanged GPIO map: CT1 IO1 · CT2-CT5 IO4-IO7 · CT6 IO8 · Voltage IO9 · Bias monitor IO10 · OLED SDA IO17 / SCL IO18.",
]):
    text(46, y + 50 + k * 17, ln, 12.5, "#1b2733")
y += 160

lg = [("#d62828", "Power"), ("#222222", "GND"), ("#1d6fd6", "Bias VB"), ("#2a9d3f", "CT tip side"),
      ("#e07b00", "CT → ADC"), ("#7b2cbf", "Voltage signal"), ("#0f8b8d", "USB data"), ("#b3261e", "230 V MAINS"),
      ("#4a5a6a", "Control / other"), ("#9aa5b1", "no connect")]
rect(30, y - 22, W - 60, 36, "#ffffff", "#b8c4d0")
lx = 46
for c, t in lg:
    rect(lx, y - 12, 26, 14, c, c, 7, 1)
    text(lx + 32, y, t, 12.5)
    lx += 48 + len(t) * 7.2
y += 50

# ---- module pin table
text(30, y, "1 · U2 ESP32-S3-WROOM-1U-N16R8 (LCSC C3013946): all 41 pins", 20, "#1b2733", "700")
y += 12
text(30, y + 12, "Connect by PIN NAME (IO1, IO4 …) as shown on the LCSC/EasyEDA symbol; pin numbers are per the WROOM-1/1U "
                 "datasheet and match KiCad 10's official ESP32-S3-WROOM-1 symbol. Pin 41 = big bottom GND pad (solder it).", 13, "#8a4b00", italic=True)
y += 30
cols, per = 3, 14
colw = (W - 60) / cols
rect(30, y - 6, W - 60, per * 22 + 18, "#f7f9fb", "#b8c4d0")
for k, (pin, nm, net) in enumerate(MOD_PINS):
    c, r = divmod(k, per)
    x = 46 + c * colw
    yy = y + 14 + r * 22
    text(x, yy, f"pin {pin}", 12, "#3d4b59", "600")
    text(x + 58, yy, nm, 12.5, "#1b2733", "700")
    tag(x + 175, yy, 180, net)
y += per * 22 + 50

y = section(y, "2 · Power: 5 V in (screw terminal or USB-C) → +5V → AMS1117 → +3V3 → FB1 → +3V3A",
            ["J1", "J2", "R1", "R2", "U4", "F1", "D1", "C1", "U3", "C50", "C51", "FB1", "C2", "C3"],
            "USB-C now carries data: D+ (A6/B6) → IO20, D− (A7/B7) → IO19 through U4 ESD. CC1/CC2 5.1k → GND (R1/R2).\n"
            "Put C50 at U3 input and C51 at U3 output. +3V3 feeds the module and J6; FB1 makes the clean analog rail +3V3A.")
y = section(y, "3 · Module support: decoupling, EN/RESET, BOOT, UART header, OLED",
            ["C52", "C53", "R50", "C54", "SW1", "R51", "SW2", "J7", "J6"],
            "C52 + C53 as close as possible to module pin 2 (3V3). Flash: hold BOOT, tap RESET, release BOOT (first time only).\n"
            "J7: connect a USB-UART with TX↔RX crossed if native USB ever fails. 4-pin tactile switches: the two pins on each side are joined.")
y = section(y, "4 · Bias VB ≈ 1.50 V (MCP6002 unit A) + op-amp decoupling (unchanged)",
            ["R3", "R4", "C4", "U1", "C5", "R5", "C6", "C7", "R6"],
            "U1 = one MCP6002: unit A (pins 1-2-3) bias buffer, unit B (pins 5-6-7) on-board voltage amplifier.")
y = section(y, "5 · Mains voltage, on-board ZMPT101B ⚠ 230 V (unchanged, except R48 now → V_ONB → JP2)",
            ["J5", "F2", "RV1", "R41", "R42", "R43", "R44", "T1", "R47", "C41", "R48", "C42", "D41", "JP2"],
            "AC_* nets are LIVE: keep ≥ 6.5 mm from all other copper + slot under T1 between primary and secondary.\n"
            "JP2 shunt 1-2 = on-board stage (default) · 2-3 = plug-in module (section 6). C42 + D41 protect GPIO9 in both cases.",
            color="#b01e1e")
y = section(y, "6 · ZMPT101B plug-in module backup (blue module on J8)",
            ["J8", "R52", "R53", "C55"],
            "Module VCC = +5V (its LM358 needs 5 V). 10k/22k scales its ≈2.5 V-centred output to ≈1.7 V. Set JP2 to 2-3 to use it.\n"
            "Mains L/N go ONLY into the module's own screw terminal. Before connecting, check V_MOD with a meter: ≈1.7 V DC, never > 3.3 V.")
y = section(y, "7 · CT channel (CT1 shown; CT2–CT6 identical, table below) — PROVEN on breadboard",
            ["J11", "R111", "JP11", "R112", "R113", "C11", "D11"],
            "JP1n: shunt 1-2 = mA CT (100A/50mA, 22Ω burden IN, default) · 2-3 = 1 V CT (30A/1V, burden OUT). 24Ω burden also OK (set HA Burden 24).")

cols_ = ["Channel", "Jack", "Burden 22Ω", "Jumper", "1k", "1.8k", "100nF", "BAT54S", "Tip net", "Burden net", "ADC net", "Module pin"]
cw = [90, 70, 110, 80, 70, 70, 80, 90, 110, 110, 110, 120]
rect(30, y - 20, sum(cw) + 20, 30 + 6 * 26, "#f7f9fb", "#b8c4d0")
xx = 40
for c, w in zip(cols_, cw):
    text(xx, y, c, 13, "#1b2733", "700")
    xx += w
mod_pin = {"CT1_ADC": "IO1 (39)", "CT2_ADC": "IO4 (4)", "CT3_ADC": "IO5 (5)", "CT4_ADC": "IO6 (6)",
           "CT5_ADC": "IO7 (7)", "CT6_ADC": "IO8 (12)"}
for n in range(1, 7):
    yy = y + n * 26
    vals = [f"CT{n}", f"J1{n}", f"R1{n}1", f"JP1{n}", f"R1{n}2", f"R1{n}3", f"C1{n}", f"D1{n}",
            f"CT{n}_SIG", f"CT{n}_MA", f"CT{n}_ADC", mod_pin[f"CT{n}_ADC"]]
    xx = 40
    for k, (v, w) in enumerate(zip(vals, cw)):
        text(xx, yy, v, 13, net_color(v) if 8 <= k <= 10 else "#1b2733", "700" if k in (0, 11) else "400")
        xx += w
y += 6 * 26 + 50

y = section(y, "8 · Mounting holes", ["H1", "H2", "H3", "H4"], "M3, no copper. A hole inside the mains area needs a plastic screw.")

# ---- full net list
nets = defaultdict(list)
for p in parts:
    for num, net in p["pins"].items():
        if net:
            nets[net].append(f"{p['ref']}.{num}")
text(30, y, "9 · Full net list (check every net in EasyEDA's Design Manager against this)", 20, "#1b2733", "700")
y += 20
order = sorted(nets, key=lambda n: (not n.startswith("AC_"), n))
rows = []
for n in order:
    members = sorted(nets[n], key=lambda r: (len(r), r))
    line, lines = "", []
    for m in members:
        if len(line) + len(m) > 86:
            lines.append(line.rstrip(", "))
            line = ""
        line += m + ", "
    lines.append(line.rstrip(", "))
    rows.append((n, lines))
half = (len(rows) + 1) // 2
colw = (W - 60) / 2
ends = []
for c in range(2):
    yy = y + 14
    for n, lines in rows[c * half:(c + 1) * half]:
        cx = 30 + c * colw
        tag(cx, yy, 104, n)
        for k, ln in enumerate(lines):
            text(cx + 114, yy + k * 17, ln, 12, "#1b2733")
        yy += 17 * len(lines) + 7
    ends.append(yy)
y = max(ends) + 30
text(30, y, f"Totals: {len(parts)} parts, {len(nets)} nets. Before ordering: ZMPT101B pin grid 10.0 × 12.7 mm · screw-terminal wire "
            "entry · 6.5 mm mains creepage + slot · module antenna U.FL reachable · run EasyEDA DRC.", 13.5, "#a33b00", "700")
y += 26
text(30, y, "Not yet tested in hardware: v0.2 power/USB/module circuit, on-board ZMPT stage, ZMPT module path. "
            "The CT channel circuit IS tested (30A CT 0.33 A / 12.66 A, 100A CT + 24Ω 4.6 A).", 13, "#4a5a6a", italic=True)
y += 30

H = int(y)
s[s.index("__HEADER__")] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
                            f'font-family="Segoe UI, Arial, sans-serif"><rect width="{W}" height="{H}" fill="#ffffff"/>')
emit("</svg>")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(s) + "\n")
print("wrote", OUT, W, "x", H, "|", len(parts), "parts,", len(nets), "nets")
# sanity: every net must have ≥2 pins
single = [n for n, m in nets.items() if len(m) < 2]
print("single-pin nets:", single)
