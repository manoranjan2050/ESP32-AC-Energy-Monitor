"""
Generate the CT6 energy-monitor KiCad project (schematic + placed PCB) from ONE netlist.

Run with KiCad's bundled Python (it provides the `pcbnew` module):
    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/generate_kicad.py

Outputs into hardware/kicad/:
    ct6-energy-monitor.kicad_pro / .kicad_sch / .kicad_pcb / .kicad_dru
    ct6.pretty/ZMPT101B.kicad_mod, ct6.kicad_sym, fp-lib-table, sym-lib-table

The schematic connects every pin with a short wire + net label (no long wires), so the
netlist below is the single source of truth. The PCB is PLACED but NOT ROUTED.
"""
import copy
import json
import math
import os
import re
import uuid

KICAD = "C:/Program Files/KiCad/10.0/share/kicad"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "kicad")
NAME = "ct6-energy-monitor"
PROJECT_UUID_NS = uuid.UUID("6b1f3c1e-6a53-4a8e-9f0c-2c6d0e2f7a10")

# DevKit header spacing (centre-to-centre of the two 1x22 sockets).
# ESP32-S3-DevKitC-1 = 22.86 mm (0.9"). MEASURE YOUR BOARD before ordering.
DEVKIT_ROW_SPACING = 22.86


def uid(*parts):
    """Deterministic UUIDs so regenerating keeps KiCad links stable."""
    return str(uuid.uuid5(PROJECT_UUID_NS, "/".join(str(p) for p in parts)))


# ============================================================================
# S-expression helpers
# ============================================================================
class Q(str):
    """A quoted string atom."""


def parse(text):
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            node = stack.pop()
            stack[-1].append(node)
        elif t.startswith('"'):
            stack[-1].append(Q(t[1:-1].replace('\\"', '"').replace("\\\\", "\\")))
        else:
            stack[-1].append(t)
    return stack[0][0]


def dump(node, indent=0):
    if isinstance(node, list):
        if not any(isinstance(c, list) for c in node):
            return "(" + " ".join(dump(c) for c in node) + ")"
        pad = "\t" * (indent + 1)
        inner = []
        for c in node:
            inner.append(dump(c, indent + 1) if isinstance(c, list) else dump(c))
        head = []
        rest = []
        for c, s in zip(node, inner):
            (rest if (isinstance(c, list) or rest) else head).append(s)
        return "(" + " ".join(head) + "".join("\n" + pad + s for s in rest) + "\n" + "\t" * indent + ")"
    if isinstance(node, Q):
        return '"' + node.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(node, float):
        s = f"{node:.4f}".rstrip("0").rstrip(".")
        return s if s not in ("-0", "") else "0"
    return str(node)


def find(node, head):
    return [c for c in node if isinstance(c, list) and c and c[0] == head]


def first(node, head):
    r = find(node, head)
    return r[0] if r else None


# ============================================================================
# Symbol library access (with `extends` flattening)
# ============================================================================
_lib_cache = {}


def lib_symbols(lib):
    if lib not in _lib_cache:
        path = os.path.join(KICAD, "symbols", lib + ".kicad_sym")
        _lib_cache[lib] = {s[1]: s for s in find(parse(open(path, encoding="utf-8").read()), "symbol")}
    return _lib_cache[lib]


CUSTOM_SYMBOLS_TEXT = r'''
(kicad_symbol_lib (version 20241209) (generator "ct6_gen")
 (symbol "ZMPT101B" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
  (property "Reference" "T" (at 0 7.62 0) (effects (font (size 1.27 1.27))))
  (property "Value" "ZMPT101B" (at 0 -7.62 0) (effects (font (size 1.27 1.27))))
  (property "Footprint" "ct6:ZMPT101B" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
  (property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
  (property "Description" "ZMPT101B 2mA:2mA precision voltage transformer (1000:1000)" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
  (symbol "ZMPT101B_0_1"
   (rectangle (start -5.08 5.08) (end 5.08 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
   (polyline (pts (xy 0 4.572) (xy 0 -4.572)) (stroke (width 0.254) (type dash)) (fill (type none))))
  (symbol "ZMPT101B_1_1"
   (pin passive line (at -7.62 2.54 0) (length 2.54) (name "VA1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
   (pin passive line (at -7.62 -2.54 0) (length 2.54) (name "VA2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
   (pin passive line (at 7.62 -2.54 180) (length 2.54) (name "VB1" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
   (pin passive line (at 7.62 2.54 180) (length 2.54) (name "VB2" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27))))))))
'''
_lib_cache["ct6"] = {s[1]: s for s in find(parse(CUSTOM_SYMBOLS_TEXT), "symbol")}


def flat_symbol(lib, name):
    syms = lib_symbols(lib)
    sym = copy.deepcopy(syms[name])
    ext = first(sym, "extends")
    if ext:
        base = flat_symbol(lib, ext[1])
        base_name = ext[1]
        # override properties from derived symbol
        props = {p[1]: p for p in find(sym, "property")}
        out = [c for c in base if not (isinstance(c, list) and c and c[0] == "property" and c[1] in props)]
        # insert derived properties after head items
        idx = next(i for i, c in enumerate(out) if isinstance(c, list) and c[0] == "property") if any(
            isinstance(c, list) and c and c[0] == "property" for c in out) else 2
        out[idx:idx] = list(props.values())
        for c in out:
            if isinstance(c, list) and c and c[0] == "symbol" and c[1].startswith(base_name + "_"):
                c[1] = Q(name + c[1][len(base_name):])
        out[1] = Q(name)
        sym = out
    return sym


def embedded_symbol(lib_id):
    lib, name = lib_id.split(":")
    sym = flat_symbol(lib, name)
    sym[1] = Q(lib_id)
    return sym


def symbol_pins(lib_id):
    """-> {unit: [(number, x, y, angle, type)]} ; unit 0 = common to all units."""
    lib, name = lib_id.split(":")
    sym = flat_symbol(lib, name)
    units = {}
    for sub in find(sym, "symbol"):
        m = re.match(r".*_(\d+)_(\d+)$", sub[1])
        u, style = int(m.group(1)), int(m.group(2))
        if style > 1:
            continue
        for p in find(sub, "pin"):
            at = first(p, "at")
            num = first(p, "number")[1]
            units.setdefault(u, []).append((str(num), float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, p[1]))
    return units


# ============================================================================
# The netlist  (single source of truth for schematic AND pcb)
# ============================================================================
FP_R = "Resistor_SMD:R_0805_2012Metric"
FP_R_HV = "Resistor_SMD:R_1206_3216Metric"
FP_C = "Capacitor_SMD:C_0805_2012Metric"
FP_C_BIG = "Capacitor_SMD:C_1206_3216Metric"

parts = []   # dicts: ref, lib_id, value, fp, pins{num: net}, sch(x,y), pcb(x,y,rot), note


def part(ref, lib_id, value, fp, pins, sch, pcb=None, rot=0, mpn="", note=""):
    parts.append(dict(ref=ref, lib_id=lib_id, value=value, fp=fp, pins=pins, sch=sch,
                      pcb=pcb, rot=rot, mpn=mpn, note=note))


# ---------------------------------------------------------------- power (5 V in)
part("J1", "Connector_Generic:Conn_01x02", "5V IN",
     "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
     {"1": "VIN_RAW", "2": "GND"}, (30, 50), (6, 62, 90), mpn="KF128-5.08-2P")
part("J2", "Connector:USB_C_Receptacle_PowerOnly_6P", "USB-C 5V (power only)",
     "Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal",
     {"A9": "VIN_RAW", "B9": "VIN_RAW", "A12": "GND", "B12": "GND", "A5": "CC1", "B5": "CC2", "SH": "GND"},
     (30, 90), (5, 45, 90), mpn="TYPE-C-6P")
part("R1", "Device:R", "5.1k", FP_R, {"1": "CC1", "2": "GND"}, (60, 85), (14, 40, 0))
part("R2", "Device:R", "5.1k", FP_R, {"1": "CC2", "2": "GND"}, (68, 85), (14, 50, 0))
part("F1", "Device:Polyfuse", "500mA hold", "Fuse:Fuse_1206_3216Metric",
     {"1": "VIN_RAW", "2": "VIN_F"}, (85, 50), (16, 58, 90), mpn="SMD1206P050TF")
part("D1", "Device:D_Schottky", "SS34", "Diode_SMD:D_SMA", {"2": "VIN_F", "1": "+5V"},
     (105, 50), (22, 58, 90), mpn="SS34")
part("C1", "Device:C", "22uF 16V", FP_C_BIG, {"1": "+5V", "2": "GND"}, (125, 55), (27, 58, 90))
part("FB1", "Device:FerriteBead_Small", "600R@100MHz", "Inductor_SMD:L_0805_2012Metric",
     {"1": "+3V3", "2": "+3V3A"}, (85, 110), (74, 30, 0), mpn="BLM21PG601")
part("C2", "Device:C", "10uF", FP_C, {"1": "+3V3A", "2": "GND"}, (105, 115), (74, 34, 0))
part("C3", "Device:C", "100nF", FP_C, {"1": "+3V3A", "2": "GND"}, (115, 115), (78, 34, 0))

# ---------------------------------------------------------------- bias (≈1.50 V, buffered)
part("R3", "Device:R", "12k 1%", FP_R, {"1": "+3V3A", "2": "VB_DIV"}, (160, 45), (58, 30, 90))
part("R4", "Device:R", "10k 1%", FP_R, {"1": "VB_DIV", "2": "GND"}, (160, 65), (58, 34, 90))
part("C4", "Device:C", "100nF", FP_C, {"1": "VB_DIV", "2": "GND"}, (170, 65), (58, 38, 90))
part("U1", "Amplifier_Operational:MCP6002-xSN", "MCP6002-E/SN", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
     {"3": "VB_DIV", "2": "VB_OUT", "1": "VB_OUT",          # A = bias buffer (unity gain)
      "5": "VB", "6": "ZS_A", "7": "V_OUT",                 # B = ZMPT transimpedance amp
      "8": "+3V3A", "4": "GND"},
     (180, 100), (66, 38, 0), mpn="MCP6002T-E/SN")
part("C5", "Device:C", "100nF", FP_C, {"1": "+3V3A", "2": "GND"}, (270, 100), (66, 32, 0))
part("R5", "Device:R", "47R", FP_R, {"1": "VB_OUT", "2": "VB"}, (225, 45), (72, 41, 0),
     note="isolates op-amp output from the 10uF bias capacitor")
part("C6", "Device:C", "10uF", FP_C, {"1": "VB", "2": "GND"}, (245, 55), (76, 41, 90))
part("C7", "Device:C", "100nF", FP_C, {"1": "VB", "2": "GND"}, (255, 55), (79, 41, 90))
part("R6", "Device:R", "1k", FP_R, {"1": "VB", "2": "VB_MON"}, (270, 45), (82, 41, 0))

# ---------------------------------------------------------------- 6 × CT channels
CT_GPIO = {1: "GPIO1", 2: "GPIO4", 3: "GPIO5", 4: "GPIO6", 5: "GPIO7", 6: "GPIO8"}
JACK_PITCH = 16.0
for n in range(1, 7):
    sx = 25 + (n - 1) * 62          # schematic block origin
    sy = 175
    px = 12 + (n - 1) * JACK_PITCH  # pcb column centre
    sig, ma, adc = f"CT{n}_SIG", f"CT{n}_MA", f"CT{n}_ADC"
    part(f"J1{n}", "Connector_Audio:AudioJack3", f"CT{n}",
         "Connector_Audio:Jack_3.5mm_CUI_SJ1-3523N_Horizontal",
         {"S": "VB", "T": sig, "R": None}, (sx, sy), (px, 82, 0), mpn="SJ1-3523N / PJ-3523")
    part(f"R1{n}1", "Device:R", "22R 0.1%", FP_R, {"1": sig, "2": ma}, (sx + 18, sy - 8), (px - 4, 68, 90),
         mpn="0805 22R 0.1% 25ppm", note="CT burden (mA-type CT only)")
    part(f"JP1{n}", "Connector_Generic:Conn_01x03", "mA|V", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
         {"1": "VB", "2": ma, "3": None}, (sx + 18, sy + 12), (px - 4, 61, 0),
         note="shunt 1-2 = mA CT (burden in, DEFAULT) ; 2-3 = 1V CT (burden out)")
    part(f"R1{n}2", "Device:R", "1k 1%", FP_R, {"1": sig, "2": adc}, (sx + 30, sy - 8), (px + 1, 68, 90))
    part(f"R1{n}3", "Device:R", "1k8 1%", FP_R, {"1": adc, "2": "VB"}, (sx + 38, sy + 8), (px + 4, 68, 90))
    part(f"C1{n}", "Device:C", "100nF", FP_C, {"1": adc, "2": "GND"}, (sx + 46, sy + 8), (px + 7, 68, 90))
    part(f"D1{n}", "Diode:BAT54S", "BAT54S", "Package_TO_SOT_SMD:SOT-23",
         {"1": "GND", "2": "+3V3A", "3": adc}, (sx + 30, sy + 22), (px + 3, 61, 0))

# ---------------------------------------------------------------- mains voltage sensing (ZMPT101B)
part("J5", "Connector_Generic:Conn_01x02", "230V AC (L,N)",
     "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
     {"1": "AC_L", "2": "AC_N"}, (30, 245), (6, 12, 90), mpn="KF128-5.08-2P 300V")
part("F2", "Device:Fuse", "100mA T 250V", "Fuse:Fuse_Littelfuse_395Series",
     {"1": "AC_L", "2": "AC_LF"}, (60, 240), (18, 8, 0), mpn="Littelfuse 39211000440 (TR5)")
part("RV1", "Device:Varistor", "275VAC 7mm", "Varistor:RV_Disc_D7mm_W4.2mm_P5mm",
     {"1": "AC_LF", "2": "AC_N"}, (80, 255), (18, 20, 0), mpn="7D431K")
for i, (a, b) in enumerate([("AC_LF", "AC_M1"), ("AC_M1", "AC_M2"), ("AC_M2", "AC_M3"), ("AC_M3", "AC_ZP")], 1):
    part(f"R4{i}", "Device:R", "220k 1% 1206", FP_R_HV, {"1": a, "2": b}, (95 + i * 14, 240),
         (27 + (i - 1) * 4.5, 8, 90), mpn="1206 220k 1% (200V)",
         note="4 x 220k = 880k -> 0.26 mA at 230 V")
part("T1", "ct6:ZMPT101B", "ZMPT101B", "ct6:ZMPT101B",
     {"1": "AC_ZP", "2": "AC_N", "3": "VB", "4": "ZS_A"}, (175, 250), (36, 22, 0), mpn="ZMPT101B")
part("R47", "Device:R", "2k7 1%", FP_R, {"1": "ZS_A", "2": "V_OUT"}, (215, 240), (60, 44, 0),
     note="transimpedance gain: 0.26 mA x 2.7k = 0.70 V RMS at 230 V")
part("C41", "Device:C", "47nF", FP_C, {"1": "ZS_A", "2": "V_OUT"}, (215, 262), (60, 47, 0))
part("R48", "Device:R", "1k", FP_R, {"1": "V_OUT", "2": "V_ADC"}, (240, 240), (66, 47, 0))
part("C42", "Device:C", "100nF", FP_C, {"1": "V_ADC", "2": "GND"}, (255, 250), (70, 47, 90))
part("D41", "Diode:BAT54S", "BAT54S", "Package_TO_SOT_SMD:SOT-23",
     {"1": "GND", "2": "+3V3A", "3": "V_ADC"}, (285, 255), (74, 47, 0))

# ---------------------------------------------------------------- ESP32-S3-DevKitC-1 sockets
# Verify against YOUR DevKit silkscreen/pinout before ordering!
DEVKIT_LEFT = ["+3V3", "+3V3", None, "CT2_ADC", "CT3_ADC", "CT4_ADC", "CT5_ADC", None, None, "I2C_SDA",
               "I2C_SCL", "CT6_ADC", None, None, "V_ADC", "VB_MON", None, None, None, None, "+5V", "GND"]
#               3V3  3V3  RST GPIO4 GPIO5 GPIO6 GPIO7 GPIO15 GPIO16 GPIO17 GPIO18 GPIO8 GPIO3 GPIO46 GPIO9 GPIO10 11 12 13 14 5V GND
DEVKIT_RIGHT = ["GND", None, None, "CT1_ADC", None, None, None, None, None, None, None, None, None, None,
                None, None, None, None, None, None, "GND", "GND"]
#               GND TX RX GPIO1 GPIO2 42 41 40 39 38 37 36 35 0 45 48 47 21 20 19 GND GND
part("J3", "Connector_Generic:Conn_01x22", "DevKit J1 (3V3..GND)", "Connector_PinSocket_2.54mm:PinSocket_1x22_P2.54mm_Vertical",
     {str(i + 1): n for i, n in enumerate(DEVKIT_LEFT)}, (330, 60), (88, 30, 270))
part("J4", "Connector_Generic:Conn_01x22", "DevKit J3 (GND..GND)", "Connector_PinSocket_2.54mm:PinSocket_1x22_P2.54mm_Vertical",
     {str(i + 1): n for i, n in enumerate(DEVKIT_RIGHT)}, (380, 60), (88, 30 + DEVKIT_ROW_SPACING, 270))

# ---------------------------------------------------------------- OLED / I2C header
part("J6", "Connector_Generic:Conn_01x04", "I2C OLED", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
     {"1": "GND", "2": "+3V3", "3": "I2C_SCL", "4": "I2C_SDA"}, (300, 130), (112, 64, 0))

# ---------------------------------------------------------------- mounting holes
for i, (x, y) in enumerate([(3.5, 3.5), (116.5, 3.5), (3.5, 86.5), (116.5, 86.5)], 1):
    part(f"H{i}", "Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {},
         (450 + i * 15, 60), (x, y, 0))

# ---------------------------------------------------------------- PCB floor plan (x right, y down, mm from top-left)
# Mains block x<35.5 / y<33 is fenced by an L-shaped slot; the slot runs under the ZMPT101B between
# its primary (x=30.5) and secondary (x=40.5) pins. DevKit on the right, antenna at the top edge.
JACK_PITCH = 14.0
JACK_Y = 90.0 - 4.5            # SJ1-3523N "PCB edge" line is 4.5 mm in front of its origin
PLACE = {
    # mains
    "J5": (6, 16, 90), "F2": (9, 29, 0), "RV1": (14, 19, 0),
    "R41": (23, 25, 90), "R42": (23, 20, 90), "R43": (23, 15, 90), "R44": (23, 10, 90),
    "T1": (35.5, 16, 0),
    # ZMPT transimpedance amp + bias (LV, right of the slot)
    "R47": (47, 12, 90), "C41": (50, 12, 90), "U1": (56, 20, 0), "C5": (56, 15, 0),
    "R48": (62, 20, 90), "C42": (65, 20, 90), "D41": (68.5, 20, 0),
    "R3": (48, 20, 90), "R4": (48, 25, 90), "C4": (51, 25, 90),
    "R5": (62, 26, 0), "C6": (56, 27, 0), "C7": (56, 30, 0), "R6": (62, 30, 0),
    "FB1": (70, 26, 0), "C2": (70, 29, 0), "C3": (70, 32, 0),
    # 5 V input
    "J2": (3.5, 44, 270), "R1": (11, 41, 90), "R2": (11, 46, 90),
    "J1": (6, 58, 90), "F1": (17, 52, 90), "D1": (22, 52, 90), "C1": (27, 52, 90),
    # DevKit sockets (pin 1 = top / antenna end)
    "J3": (84, 5, 0), "J4": (84 + DEVKIT_ROW_SPACING, 5, 0),
    "J6": (114, 66, 0),
    "H1": (3.5, 3.5, 0), "H2": (116.5, 3.5, 0), "H3": (116.5, 86.5, 0), "H4": (95, 86.5, 0),
}
for n in range(1, 7):
    cx = 8 + (n - 1) * JACK_PITCH
    PLACE.update({f"J1{n}": (cx, JACK_Y, 0), f"JP1{n}": (cx - 4.5, 63, 0), f"R1{n}1": (cx - 1, 64, 90),
                  f"R1{n}2": (cx + 1.5, 64, 90), f"R1{n}3": (cx + 4, 64, 90), f"C1{n}": (cx + 1.5, 70, 90),
                  f"D1{n}": (cx + 4.5, 71, 0)})
for p in parts:
    p["pcb"] = PLACE[p["ref"]]

# PWR_FLAGs (schematic only)
PWR_FLAG_NETS = ["GND", "+3V3", "+3V3A", "+5V", "VIN_RAW", "AC_L", "AC_N"]

BOARD_W, BOARD_H = 120.0, 90.0
# GND pour outline: whole board minus the mains block and the DevKit antenna area
GND_POUR = [(38.0, 0.5), (80.0, 0.5), (80.0, 16.0), (112.0, 16.0), (112.0, 0.5),
            (BOARD_W - 0.5, 0.5), (BOARD_W - 0.5, BOARD_H - 0.5), (0.5, BOARD_H - 0.5),
            (0.5, 36.0), (38.0, 36.0)]


# ============================================================================
# Schematic writer
# ============================================================================
def snap(v, g=1.27):
    return round(round(v / g) * g, 4)


def write_schematic():
    root = uid("root")
    items = []
    used = {}
    for p in parts:
        used[p["lib_id"]] = True
    used["power:PWR_FLAG"] = True

    def label(net, x, y, angle, key):
        just = {0: "left", 180: "right", 90: "left", 270: "right"}[angle]
        items.append(["global_label", Q(net), ["shape", "passive"], ["at", x, y, angle], ["fields_autoplaced", "yes"],
                      ["effects", ["font", ["size", 1.27, 1.27]], ["justify"] + just.split()[:1]],
                      ["uuid", Q(uid("lbl", key))],
                      ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", x, y, 0], ["hide", "yes"],
                       ["effects", ["font", ["size", 1.27, 1.27]]]]])

    def wire(x1, y1, x2, y2, key):
        items.append(["wire", ["pts", ["xy", x1, y1], ["xy", x2, y2]], ["stroke", ["width", 0], ["type", "default"]],
                      ["uuid", Q(uid("w", key))]])

    def noconn(x, y, key):
        items.append(["no_connect", ["at", x, y], ["uuid", Q(uid("nc", key))]])

    def place(ref, lib_id, value, fp, pins, X, Y, unit, key):
        units = symbol_pins(lib_id)
        pinlist = units.get(0, []) + units.get(unit, [])
        props = [
            ["property", Q("Reference"), Q(ref), ["at", X + 2.54, Y - 5.08, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "left"]]],
            ["property", Q("Value"), Q(value), ["at", X + 2.54, Y + 5.08, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "left"]]],
            ["property", Q("Footprint"), Q(fp or ""), ["at", X, Y, 0], ["hide", "yes"], ["effects", ["font", ["size", 1.27, 1.27]]]],
            ["property", Q("Datasheet"), Q(""), ["at", X, Y, 0], ["hide", "yes"], ["effects", ["font", ["size", 1.27, 1.27]]]],
        ]
        sym = ["symbol", ["lib_id", Q(lib_id)], ["at", X, Y, 0], ["unit", unit],
               ["exclude_from_sim", "no"], ["in_bom", "no" if lib_id.startswith(("power:", "Mechanical:")) else "yes"],
               ["on_board", "no" if lib_id.startswith("power:") else "yes"], ["dnp", "no"],
               ["uuid", Q(uid("sym", key))]] + props
        for num, *_ in pinlist:
            sym.append(["pin", Q(num), ["uuid", Q(uid("pin", key, num))]])
        sym.append(["instances", ["project", Q(NAME), ["path", Q("/" + root), ["reference", Q(ref)], ["unit", unit]]]])
        items.append(sym)
        for num, px, py, ang, ptype in pinlist:
            x0, y0 = X + px, Y - py
            dx, dy = -math.cos(math.radians(ang)), math.sin(math.radians(ang))
            dx, dy = round(dx), round(dy)
            net = pins.get(num, "__missing__")
            if net == "__missing__" or net is None:
                if ptype != "no_connect":
                    noconn(x0, y0, f"{key}.{num}")
                continue
            x1, y1 = round(x0 + dx * 2.54, 4), round(y0 + dy * 2.54, 4)
            wire(x0, y0, x1, y1, f"{key}.{num}")
            angle = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
            label(net, x1, y1, angle, f"{key}.{num}")
        return sym

    for p in parts:
        X, Y = snap(p["sch"][0], 2.54), snap(p["sch"][1], 2.54)
        units = sorted(u for u in symbol_pins(p["lib_id"]) if u > 0) or [1]
        for k, u in enumerate(units):
            place(p["ref"], p["lib_id"], p["value"], p["fp"], p["pins"], X + k * 33.02, Y, u, f"{p['ref']}.{u}")
        p["sch_uuid"] = uid("sym", f"{p['ref']}.{units[0]}")

    for i, net in enumerate(PWR_FLAG_NETS):
        X, Y = snap(300 + i * 12.7, 2.54), snap(170 - 25, 2.54)
        place(f"#FLG{i + 1:02d}", "power:PWR_FLAG", "PWR_FLAG", "", {"1": net}, X, Y, 1, f"FLG{i}")

    notes = [
        (20, 30, "POWER IN: 5 V from terminal J1 or USB-C J2 (power only)"),
        (150, 30, "BIAS: 1.50 V buffered mid-point shared by all CT channels (MCP6002 unit A)"),
        (20, 155, "CT CHANNELS x6 (KinCony KC868-M16v2 style): JP = mA (1-2, default, 22R burden in) or V (2-3, 1 V CTs)."
                  "  Route each burden's VB end straight to its jack sleeve."),
        (20, 225, "!! MAINS 230 V SECTION - keep >= 6.5 mm creepage to everything else (see .kicad_dru) !!"),
        (310, 30, "ESP32-S3-DevKitC-1 (N16R8) sockets - VERIFY PINOUT of your DevKit"),
    ]
    for i, (x, y, t) in enumerate(notes):
        items.append(["text", Q(t), ["exclude_from_sim", "no"], ["at", x, y, 0],
                      ["effects", ["font", ["size", 2, 2], ["bold", "yes"]], ["justify", "left", "bottom"]],
                      ["uuid", Q(uid("note", i))]])

    sch = ["kicad_sch", ["version", 20250114], ["generator", Q("eeschema")], ["generator_version", Q("9.0")],
           ["uuid", Q(root)], ["paper", Q("A2")],
           ["title_block", ["title", Q("CT6 Energy Monitor - ESP32-S3 + 6 CT + ZMPT101B")], ["date", Q("2026-09-24")],
            ["rev", Q("0.1")], ["company", Q("ElectroIoT")],
            ["comment", 1, Q("Generated by hardware/generate_kicad.py - edit the script, not this file")]],
           ["lib_symbols"] + [embedded_symbol(l) for l in sorted(used)]]
    sch += items
    sch.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
    open(os.path.join(OUT, NAME + ".kicad_sch"), "w", encoding="utf-8").write(dump(sch) + "\n")


# ============================================================================
# Library / project files
# ============================================================================
ZMPT_FP = """(footprint "ZMPT101B"
	(version 20241229)
	(generator "ct6_gen")
	(layer "F.Cu")
	(descr "ZMPT101B 2mA:2mA voltage transformer. Pin grid 10.0 x 12.7 mm, cross-checked with two independent KiCad libraries. VERIFY with your part.")
	(property "Reference" "REF**" (at 0 -10 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
	(property "Value" "ZMPT101B" (at 0 10 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
	(attr through_hole)
	(fp_rect (start -9.6 -8.35) (end 9.6 8.35) (stroke (width 0.1) (type default)) (fill no) (layer "F.Fab"))
	(fp_rect (start -9.72 -8.47) (end 9.72 8.47) (stroke (width 0.12) (type default)) (fill no) (layer "F.SilkS"))
	(fp_rect (start -10 -8.75) (end 10 8.75) (stroke (width 0.05) (type default)) (fill no) (layer "F.CrtYd"))
	(fp_text user "PRIMARY 230V" (at -5 0 90) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
	(fp_text user "SEC" (at 5 0 90) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
	(pad "1" thru_hole rect (at -5 -6.35) (size 2.2 2.2) (drill 1.2) (layers "*.Cu" "*.Mask"))
	(pad "2" thru_hole circle (at -5 6.35) (size 2.2 2.2) (drill 1.2) (layers "*.Cu" "*.Mask"))
	(pad "3" thru_hole circle (at 5 6.35) (size 2.2 2.2) (drill 1.2) (layers "*.Cu" "*.Mask"))
	(pad "4" thru_hole circle (at 5 -6.35) (size 2.2 2.2) (drill 1.2) (layers "*.Cu" "*.Mask"))
)
"""

DRU = """(version 1)
# Mains (230 V) nets are named AC_*. Keep them away from all low-voltage copper.
(rule "mains_to_lv_clearance"
	(condition "A.hasNetclass('Mains') && !B.hasNetclass('Mains')")
	(constraint clearance (min 6.5mm)))
(rule "mains_to_lv_creepage"
	(condition "A.hasNetclass('Mains') && !B.hasNetclass('Mains')")
	(constraint creepage (min 6.5mm)))
(rule "mains_hole_clearance"
	(condition "A.hasNetclass('Mains')")
	(constraint hole_clearance (min 1.0mm)))
"""


def write_project_files():
    os.makedirs(os.path.join(OUT, "ct6.pretty"), exist_ok=True)
    open(os.path.join(OUT, "ct6.pretty", "ZMPT101B.kicad_mod"), "w", encoding="utf-8").write(ZMPT_FP)
    open(os.path.join(OUT, "ct6.kicad_sym"), "w", encoding="utf-8").write(CUSTOM_SYMBOLS_TEXT.strip() + "\n")
    open(os.path.join(OUT, "fp-lib-table"), "w").write(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "ct6")(type "KiCad")(uri "${KIPRJMOD}/ct6.pretty")(options "")(descr "CT6 project footprints"))\n)\n')
    open(os.path.join(OUT, "sym-lib-table"), "w").write(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "ct6")(type "KiCad")(uri "${KIPRJMOD}/ct6.kicad_sym")(options "")(descr "CT6 project symbols"))\n)\n')
    open(os.path.join(OUT, NAME + ".kicad_dru"), "w").write(DRU)
    pro = {
        "meta": {"filename": NAME + ".kicad_pro", "version": 3},
        "board": {"design_settings": {"defaults": {}, "rules": {"min_clearance": 0.2, "min_track_width": 0.2}}},
        "net_settings": {
            "classes": [
                {"name": "Default", "clearance": 0.2, "track_width": 0.3, "via_diameter": 0.6, "via_drill": 0.3,
                 "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "wire_width": 6, "bus_width": 12, "line_style": 0, "schematic_color": "rgba(0, 0, 0, 0.000)",
                 "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647},
                {"name": "Power", "clearance": 0.25, "track_width": 0.8, "via_diameter": 0.8, "via_drill": 0.4,
                 "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "wire_width": 6, "bus_width": 12, "line_style": 0, "schematic_color": "rgba(0, 0, 0, 0.000)",
                 "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 1},
                {"name": "Mains", "clearance": 1.5, "track_width": 0.8, "via_diameter": 1.2, "via_drill": 0.6,
                 "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "wire_width": 6, "bus_width": 12, "line_style": 0, "schematic_color": "rgba(200, 0, 0, 1.000)",
                 "pcb_color": "rgba(200, 0, 0, 1.000)", "priority": 0},
            ],
            "meta": {"version": 4},
            "netclass_patterns": [
                {"netclass": "Mains", "pattern": "AC_*"},
                {"netclass": "Power", "pattern": "+5V"}, {"netclass": "Power", "pattern": "VIN_*"},
                {"netclass": "Power", "pattern": "GND"},
            ],
        },
    }
    json.dump(pro, open(os.path.join(OUT, NAME + ".kicad_pro"), "w"), indent=2)


# ============================================================================
# PCB writer (pcbnew API)
# ============================================================================
def schematic_nc_nets():
    """(ref, pad) -> 'unconnected-(...)' net names, read from KiCad's own netlist export."""
    import subprocess, tempfile
    cli = os.path.join(os.path.dirname(KICAD), "..", "bin", "kicad-cli.exe")
    tmp = os.path.join(tempfile.gettempdir(), "ct6_nc.net")
    subprocess.run([os.path.normpath(cli), "sch", "export", "netlist", "--format", "kicadsexpr", "-o", tmp,
                    os.path.join(OUT, NAME + ".kicad_sch")], check=True, capture_output=True)
    out = {}
    for n in find(first(parse(open(tmp, encoding="utf-8").read()), "nets"), "net"):
        name = first(n, "name")[1]
        if name.startswith("unconnected-"):
            for nd in find(n, "node"):
                out[(first(nd, "ref")[1], first(nd, "pin")[1])] = name
    return out


def write_pcb():
    import pcbnew
    nc_nets = schematic_nc_nets()
    mm = pcbnew.FromMM
    V = lambda x, y: pcbnew.VECTOR2I(mm(x + OX), mm(y + OY))
    OX, OY = 50.0, 50.0

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    # fab origin = bottom-left board corner (JLCPCB-friendly CPL coordinates)
    board.GetDesignSettings().SetAuxOrigin(V(0, BOARD_H))
    board.GetDesignSettings().SetGridOrigin(V(0, BOARD_H))
    nets = {}

    def net(name):
        if name not in nets:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
            nets[name] = ni
        return nets[name]

    for p in parts:
        lib, fpname = p["fp"].split(":")
        libpath = os.path.join(OUT, "ct6.pretty") if lib == "ct6" else os.path.join(KICAD, "footprints", lib + ".pretty")
        fp = pcbnew.FootprintLoad(libpath, fpname)
        if fp is None:
            raise SystemExit(f"footprint not found: {p['fp']}")
        fp.SetFPID(pcbnew.LIB_ID(lib, fpname))
        fp.SetReference(p["ref"])
        fp.SetValue(p["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + p["sch_uuid"]))
        x, y, rot = p["pcb"]
        fp.SetPosition(V(x, y))
        fp.SetOrientationDegrees(rot)
        for item in list(fp.GraphicalItems()):
            if item.GetLayer() == pcbnew.Edge_Cuts:   # jack footprints carry a "PCB edge" marker
                item.SetLayer(pcbnew.Dwgs_User)
        fp.SetExcludedFromBOM(p["lib_id"].startswith("Mechanical:"))
        for pad in fp.Pads():
            n = p["pins"].get(pad.GetNumber()) or nc_nets.get((p["ref"], pad.GetNumber()))
            if n:
                pad.SetNet(net(n))
        board.Add(fp)

    # Board outline
    def seg(x1, y1, x2, y2, layer=pcbnew.Edge_Cuts, w=0.1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(x1, y1))
        s.SetEnd(V(x2, y2))
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        board.Add(s)

    for a, b in [((0, 0), (BOARD_W, 0)), ((BOARD_W, 0), (BOARD_W, BOARD_H)),
                 ((BOARD_W, BOARD_H), (0, BOARD_H)), ((0, BOARD_H), (0, 0))]:
        seg(*a, *b)

    # L-shaped isolation slot (1.6 mm) fencing the mains block; its vertical leg runs under the ZMPT101B
    L = [(34.7, 2.0), (36.3, 2.0), (36.3, 33.8), (2.0, 33.8), (2.0, 32.2), (34.7, 32.2)]
    for i in range(len(L)):
        seg(*L[i], *L[(i + 1) % len(L)])

    # Silkscreen warnings
    def text(t, x, y, size=1.5, layer=pcbnew.F_SilkS):
        tx = pcbnew.PCB_TEXT(board)
        tx.SetText(t)
        tx.SetPosition(V(x, y))
        tx.SetLayer(layer)
        tx.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        tx.SetTextThickness(mm(size * 0.15))
        board.Add(tx)

    text("DANGER 230V AC", 19, 3.5, 1.3)
    text("L N", 3.0, 21.5, 1.0)
    text("CT6 ENERGY MONITOR v0.1", 57, 5, 1.3)
    text("ESP32-S3-DevKitC-1  (antenna ^, USB v)", 95.4, 62, 0.9)
    text("5V", 1.5, 51, 1.0)
    for n in range(1, 7):
        cx = 8 + (n - 1) * JACK_PITCH
        text(f"CT{n}", cx, 75.5, 1.1)
        text("mA", cx - 7.2, 63, 0.8)
        text("V", cx - 7.2, 68.1, 0.8)

    # GND pour on both layers, low-voltage area only (mains area + slots excluded).
    # route_pcb.py sets CT6_NO_ZONES=1 and pours after autorouting instead.
    for layer in (() if os.environ.get("CT6_NO_ZONES") else (pcbnew.F_Cu, pcbnew.B_Cu)):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net("GND"))
        z.SetLocalClearance(mm(0.3))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        ol = z.Outline()
        ol.NewOutline()
        for (x, y) in GND_POUR:
            ol.Append(mm(x + OX), mm(y + OY))
        board.Add(z)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.SetFileName(os.path.join(OUT, NAME + ".kicad_pcb"))
    pcbnew.SaveBoard(os.path.join(OUT, NAME + ".kicad_pcb"), board)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write_project_files()
    write_schematic()
    try:
        write_pcb()
        print("PCB written")
    except ImportError:
        print("pcbnew not available - run with KiCad's python.exe to also generate the PCB")
    print("parts:", len(parts), "nets:", len({n for p in parts for n in p["pins"].values() if n}))
