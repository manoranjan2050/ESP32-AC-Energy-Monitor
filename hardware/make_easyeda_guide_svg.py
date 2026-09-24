"""
Generate renders/easyeda_connection_guide.svg from the SAME netlist as the KiCad project
(generate_kicad.py), so the EasyEDA drawing guide can never drift from the verified design.

    python hardware/make_easyeda_guide_svg.py
"""
import os
import sys
from collections import defaultdict
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_kicad as g  # noqa: E402  (only builds the parts list on import)

OUT = os.path.join(HERE, "renders", "easyeda_connection_guide.svg")
P = {p["ref"]: p for p in g.parts}

# Friendly pin names for the parts where the pin number alone is not obvious
PIN_NAMES = {
    "U1": {"1": "OUT A", "2": "−IN A", "3": "+IN A", "4": "V− (GND)", "5": "+IN B", "6": "−IN B", "7": "OUT B", "8": "V+"},
    "BAT54S": {"1": "A (to GND)", "2": "K (to 3V3A)", "3": "COM"},
    "J2": {"A9": "VBUS", "B9": "VBUS", "A12": "GND", "B12": "GND", "A5": "CC1", "B5": "CC2", "SH": "Shield"},
    "D1": {"1": "K (cathode, band)", "2": "A (anode)"},
    "T1": {"1": "VA1 primary", "2": "VA2 primary", "3": "VB1 secondary", "4": "VB2 secondary"},
    "JACK": {"T": "Tip", "S": "Sleeve", "R": "Ring (unused)"},
    "JP": {"1": "mA side", "2": "middle", "3": "V side"},
    "J3": dict(zip([str(i) for i in range(1, 23)],
                   ["3V3", "3V3", "RST/EN", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO15", "GPIO16", "GPIO17",
                    "GPIO18", "GPIO8", "GPIO3", "GPIO46", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14",
                    "5V", "GND"])),
    "J4": dict(zip([str(i) for i in range(1, 23)],
                   ["GND", "TX (43)", "RX (44)", "GPIO1", "GPIO2", "GPIO42", "GPIO41", "GPIO40", "GPIO39", "GPIO38",
                    "GPIO37", "GPIO36", "GPIO35", "GPIO0", "GPIO45", "GPIO48", "GPIO47", "GPIO21", "GPIO20", "GPIO19",
                    "GND", "GND"])),
    "J6": {"1": "GND", "2": "VCC", "3": "SCL", "4": "SDA"},
    "J1": {"1": "+5V in", "2": "GND"},
    "J5": {"1": "L (live)", "2": "N (neutral)"},
}


def pin_name(ref, num):
    if ref in PIN_NAMES:
        return PIN_NAMES[ref].get(num, "")
    lib = P[ref]["lib_id"]
    if lib.endswith("BAT54S"):
        return PIN_NAMES["BAT54S"].get(num, "")
    if lib.endswith("AudioJack3"):
        return PIN_NAMES["JACK"].get(num, "")
    if ref.startswith("JP"):
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
    if net in ("V_OUT", "V_ADC", "ZS_A"):
        return "#7b2cbf"
    return "#4a5a6a"


FP_NICK = {
    "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal": "Screw terminal 2P 5.08mm",
    "USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal": "USB-C 6P power-only",
    "Jack_3.5mm_CUI_SJ1-3523N_Horizontal": "3.5mm jack SJ1-3523N (PJ-3523)",
    "PinSocket_1x22_P2.54mm_Vertical": "Female header 1x22 2.54mm",
    "PinHeader_1x03_P2.54mm_Vertical": "Pin header 1x03 2.54mm",
    "PinHeader_1x04_P2.54mm_Vertical": "Pin header 1x04 2.54mm",
    "SOIC-8_3.9x4.9mm_P1.27mm": "SOIC-8",
    "Fuse_Littelfuse_395Series": "TR5 fuse (395 series)",
    "RV_Disc_D7mm_W4.2mm_P5mm": "MOV disc 7mm P5",
    "MountingHole_3.2mm_M3": "M3 hole 3.2mm",
}


def fp_short(fp):
    name = fp.split(":")[1]
    return FP_NICK.get(name, name.replace("_2012Metric", "").replace("_3216Metric", ""))


s = []
add = s.append


def text(x, y, t, size=13, c="#1b2733", w="400", anchor="start", italic=False):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{c}" font-weight="{w}" text-anchor="{anchor}"'
        + (' font-style="italic"' if italic else "") + f'>{escape(str(t))}</text>')


CARD_W, ROW = 300, 19


def card(x, y, ref):
    p = P[ref]
    pins = sorted(p["pins"].items(), key=lambda kv: (len(kv[0]), kv[0]))
    h = 46 + ROW * max(1, len(pins)) + 8
    mains = any(n and n.startswith("AC_") for n in p["pins"].values())
    add(f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{h}" rx="8" fill="{"#fff1f0" if mains else "#f7f9fb"}" '
        f'stroke="{"#c0392b" if mains else "#b8c4d0"}" stroke-width="1.5"/>')
    text(x + 12, y + 20, f"{ref}  ·  {p['value']}", 14.5, "#1b2733", "700")
    sub = fp_short(p["fp"]) + (f"  ·  {p['mpn']}" if p["mpn"] else "")
    text(x + 12, y + 37, sub if len(sub) <= 50 else sub[:48] + "…", 11, "#5b6b7b")
    if not pins:
        text(x + 12, y + 58, "no electrical pins", 12, "#5b6b7b", italic=True)
    for k, (num, net) in enumerate(pins):
        yy = y + 58 + k * ROW
        nm = pin_name(ref, num)
        text(x + 12, yy, f"pin {num}", 12, "#3d4b59", "600")
        if nm:
            text(x + 62, yy, nm, 11.5, "#5b6b7b")
        c = net_color(net)
        add(f'<rect x="{x + 168}" y="{yy - 13}" width="{CARD_W - 180}" height="17" rx="8" fill="{c}"/>')
        text(x + 168 + (CARD_W - 180) / 2, yy, net if net else "no connect", 11.5, "#ffffff", "700", "middle")
    return h


def section(y, title, refs, note=None, cols=5, x0=30):
    text(x0, y, title, 20, "#1b2733", "700")
    y += 12
    if note:
        text(x0, y + 12, note, 13, "#8a4b00", italic=True)
        y += 22
    col_y = [y + 8] * cols
    for i, ref in enumerate(refs):
        c = col_y.index(min(col_y))
        h = card(x0 + c * (CARD_W + 16), col_y[c], ref)
        col_y[c] += h + 12
    return max(col_y) + 30


W = 30 + 5 * (CARD_W + 16) + 14
add("__HEADER__")
text(30, 44, "CT6 Energy Monitor v0.1: EasyEDA connection guide (every part, every pin, every net)", 26, "#1b2733", "700")
text(30, 70, "Generated from the verified KiCad netlist (ERC 0 · DRC 0). In EasyEDA: place each part, then put a Net Label "
             "with the EXACT coloured name on each pin. Same name = connected.", 14, "#4a5a6a")
text(30, 90, "Pins marked \"no connect\" stay empty. Power nets: use EasyEDA net labels (not power symbols) so the names "
             "match exactly: +5V, +3V3, +3V3A, GND, VB.", 14, "#4a5a6a")

y = 130
# legend
lg = [("#d62828", "Power (+5V, +3V3, +3V3A, VIN)"), ("#222222", "GND"), ("#1d6fd6", "Bias VB (≈1.5 V)"),
      ("#2a9d3f", "CT tip side"), ("#e07b00", "CT → ADC"), ("#7b2cbf", "Voltage signal"),
      ("#b3261e", "230 V MAINS (AC_*)"), ("#4a5a6a", "Other")]
add(f'<rect x="30" y="{y - 22}" width="{W - 60}" height="36" rx="8" fill="#ffffff" stroke="#b8c4d0"/>')
lx = 46
for c, t in lg:
    add(f'<rect x="{lx}" y="{y - 12}" width="26" height="14" rx="7" fill="{c}"/>')
    text(lx + 32, y, t, 12.5)
    lx += 40 + len(t) * 7.2
y += 50

y = section(y, "1 · Power input (5 V terminal or USB-C, power only)",
            ["J1", "J2", "R1", "R2", "F1", "D1", "C1", "FB1", "C2", "C3"],
            "+3V3 comes from the DevKit's own 3V3 pin; FB1 makes the clean analog rail +3V3A.")
y = section(y, "2 · Bias VB ≈ 1.50 V (MCP6002 unit A) + op-amp decoupling",
            ["R3", "R4", "C4", "U1", "C5", "R5", "C6", "C7", "R6"],
            "U1 is one MCP6002 chip: unit A = bias buffer, unit B = voltage amplifier (section 3). R5 47Ω isolates the op-amp from C6.")
y = section(y, "3 · Mains voltage sensing ⚠ 230 V: keep ≥ 6.5 mm from all other copper, slot under T1",
            ["J5", "F2", "RV1", "R41", "R42", "R43", "R44", "T1", "R47", "C41", "R48", "C42", "D41"],
            "AC_* nets are LIVE. T1 (ZMPT101B) is the isolation barrier: primary pins 1-2 mains, secondary pins 3-4 low voltage.")
y = section(y, "4 · CT channel (CT1 shown; CT2–CT6 are identical, see table below)",
            ["J11", "R111", "JP11", "R112", "R113", "C11", "D11"],
            "JP jumper: shunt on pins 1-2 = mA CT (100A/50mA, burden IN, default); pins 2-3 = 1 V CT (30A/1V, burden OUT).")

# channel table
cols = ["Channel", "Jack", "Burden 22Ω", "Jumper", "1k", "1.8k", "100nF", "BAT54S", "Tip net", "Burden net", "ADC net", "GPIO"]
cw = [90, 70, 110, 80, 70, 70, 80, 90, 110, 110, 110, 90]
tx = 30
add(f'<rect x="30" y="{y - 20}" width="{sum(cw) + 20}" height="{30 + 6 * 26}" rx="8" fill="#f7f9fb" stroke="#b8c4d0"/>')
xx = tx + 10
for c, w in zip(cols, cw):
    text(xx, y, c, 13, "#1b2733", "700")
    xx += w
for n in range(1, 7):
    yy = y + n * 26
    vals = [f"CT{n}", f"J1{n}", f"R1{n}1", f"JP1{n}", f"R1{n}2", f"R1{n}3", f"C1{n}", f"D1{n}",
            f"CT{n}_SIG", f"CT{n}_MA", f"CT{n}_ADC", g.CT_GPIO[n]]
    xx = tx + 10
    for k, (v, w) in enumerate(zip(vals, cw)):
        text(xx, yy, v, 13, net_color(v) if k >= 8 and k < 11 else "#1b2733", "700" if k in (0, 11) else "400")
        xx += w
y += 6 * 26 + 50

y = section(y, "5 · ESP32-S3-DevKitC-1 sockets + I²C header",
            ["J3", "J4", "J6"],
            "Two 1×22 female headers, rows 22.86 mm apart (MEASURE your DevKit). Pin 1 = antenna end. Unused pins: no connect.",
            cols=3)
y = section(y, "6 · Mounting holes", ["H1", "H2", "H3", "H4"], "M3 holes, no copper. H1 is inside the mains area: plastic screw.")

# full net list
nets = defaultdict(list)
for p in g.parts:
    for num, net in p["pins"].items():
        if net:
            nets[net].append(f"{p['ref']}.{num}")
text(30, y, "7 · Full net list (check every net in EasyEDA's Design Manager against this)", 20, "#1b2733", "700")
y += 20
order = sorted(nets, key=lambda n: (not n.startswith("AC_"), n))
cols3 = 2
colw = (W - 60) / cols3
rows = []
for n in order:
    members = ", ".join(sorted(nets[n], key=lambda r: (len(r), r)))
    # wrap long member lists
    line, lines = "", []
    for part in members.split(", "):
        if len(line) + len(part) > 88:
            lines.append(line.rstrip(", "))
            line = ""
        line += part + ", "
    lines.append(line.rstrip(", "))
    rows.append((n, lines))
half = (len(rows) + 1) // 2
for c in range(cols3):
    yy = y + 14
    for n, lines in rows[c * half:(c + 1) * half]:
        cx = 30 + c * colw
        add(f'<rect x="{cx}" y="{yy - 13}" width="104" height="17" rx="8" fill="{net_color(n)}"/>')
        text(cx + 52, yy, n, 11.5, "#ffffff", "700", "middle")
        for k, ln in enumerate(lines):
            text(cx + 114, yy + k * 17, ln, 12, "#1b2733")
        yy += 17 * len(lines) + 7
    if c == 0:
        end0 = yy
y = max(end0, yy) + 30

text(30, y, "Order check before sending to JLCPCB: DevKit row spacing & pinout · ZMPT101B pin grid 10.0 × 12.7 mm · "
            "screw-terminal wire entry · 6.5 mm mains creepage + slot · run EasyEDA DRC.", 13.5, "#a33b00", "700")
y += 30

H = int(y)
s[s.index("__HEADER__")] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
                            f'font-family="Segoe UI, Arial, sans-serif"><rect width="{W}" height="{H}" fill="#ffffff"/>')
add("</svg>")
open(OUT, "w", encoding="utf-8").write("\n".join(s) + "\n")
print("wrote", OUT, W, "x", H, "|", len(g.parts), "parts,", len(nets), "nets")
