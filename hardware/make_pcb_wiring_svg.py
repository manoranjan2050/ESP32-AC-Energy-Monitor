"""
Generate renders/pcb_full_connection.svg: the complete CT6 PCB circuit drawn as a wired diagram
(every R, C, diode, jumper, op-amp pin and GPIO), with the same designators and values as the
KiCad netlist in generate_kicad.py.

    python hardware/make_pcb_wiring_svg.py
"""
import os
import sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_kicad as g  # noqa: E402

OUT = os.path.join(HERE, "renders", "pcb_full_connection.svg")
V = {p["ref"]: p["value"] for p in g.parts}          # values straight from the netlist

W, H = 1900, 1640
RED, BLK, BLU, GRN, ORG, PUR = "#d62828", "#222222", "#1d6fd6", "#2a9d3f", "#e07b00", "#7b2cbf"
MAINS_L, MAINS_N, TXT, SUB, WARN = "#8b4513", "#1f3a93", "#1b2733", "#4a5a6a", "#b01e1e"
Y3A, YVB = 470, 520                                  # +3V3A and VB buses across the CT area

s = []
add = s.append


def text(x, y, t, size=12, c=TXT, w="400", anchor="start", italic=False):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{c}" font-weight="{w}" text-anchor="{anchor}"'
        + (' font-style="italic"' if italic else "") + f'>{escape(str(t))}</text>')


def line(x1, y1, x2, y2, c=TXT, w=3):
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>')


def poly(pts, c=TXT, w=3):
    add(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" stroke="{c}" stroke-width="{w}" '
        f'fill="none" stroke-linejoin="round" stroke-linecap="round"/>')


def dot(x, y, c=TXT, r=5):
    add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"/>')


def rect(x, y, w, h, fill, stroke, sw=2, rx=4, dash=None):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'
        + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")


def gnd(x, y, c=BLK):
    line(x, y, x, y + 10, c)
    line(x - 11, y + 10, x + 11, y + 10, c, 3)
    line(x - 7, y + 15, x + 7, y + 15, c, 2.5)
    line(x - 3, y + 20, x + 3, y + 20, c, 2)


def res_v(x, y1, y2, fill="#f3e2b3", stroke="#6b5518", dash=None):
    rect(x - 7, y1, 14, y2 - y1, fill, stroke, 2, 3, dash)


def res_h(x1, x2, y, fill="#f3e2b3", stroke="#6b5518"):
    rect(x1, y - 7, x2 - x1, 14, fill, stroke, 2, 3)


def cap_v(x, y, c=TXT):          # vertical wire, plates at y and y+9
    line(x - 13, y, x + 13, y, c, 3.5)
    line(x - 13, y + 9, x + 13, y + 9, c, 3.5)


def cap_h(x, y, c=TXT):          # horizontal wire, plates at x and x+9
    line(x, y - 13, x, y + 13, c, 3.5)
    line(x + 9, y - 13, x + 9, y + 13, c, 3.5)


def diode_up(x, ytop, ybot, c=TXT):   # anode at bottom, cathode (bar) at top
    add(f'<polygon points="{x - 8},{ybot} {x + 8},{ybot} {x},{ytop}" fill="{c}"/>')
    line(x - 9, ytop, x + 9, ytop, c, 3)


def diode_right(x1, x2, y, c=TXT):    # anode left, cathode right
    add(f'<polygon points="{x1},{y - 8} {x1},{y + 8} {x2},{y}" fill="{c}"/>')
    line(x2, y - 9, x2, y + 9, c, 3)


def pill(x, y, t, c, w=None, anchor="start"):
    w = w or (len(t) * 7.4 + 18)
    x0 = x - w if anchor == "end" else x
    rect(x0, y - 11, w, 22, c, c, 1, 11)
    text(x0 + w / 2, y + 4.5, t, 11.5, "#ffffff", "700", "middle")
    return x0, x0 + w


def opamp(x, y, label, pins):
    """Triangle with − input at (x, y-20), + input at (x, y+20), output at (x+80, y)."""
    add(f'<polygon points="{x},{y - 40} {x},{y + 40} {x + 80},{y}" fill="#eef3fa" stroke="{TXT}" stroke-width="2.5"/>')
    text(x + 8, y - 15, "−", 18, TXT, "700")
    text(x + 8, y + 27, "+", 18, TXT, "700")
    text(x + 26, y + 5, label, 11, SUB, "700")
    text(x - 4, y - 25, pins[0], 10.5, SUB, anchor="end")
    text(x - 4, y + 36, pins[1], 10.5, SUB, anchor="end")
    text(x + 84, y + 20, pins[2], 10.5, SUB)


def section_title(x, y, t, c=TXT):
    text(x, y, t, 17, c, "700")


# ============================================================ header
add("__HEADER__")
text(30, 40, "CT6 Energy Monitor PCB v0.1: full circuit connection diagram", 27, TXT, "700")
text(30, 66, "Every resistor, capacitor, diode, jumper and GPIO, with the same designators and values as the KiCad "
             "netlist / Gerbers in hardware/fab. ⏚ = GND. Wires that cross without a dot are NOT connected.", 14, SUB)

# ============================================================ 1. POWER INPUT
section_title(30, 100, "1 · Power input")
rect(40, 125, 76, 115, "#e9eef5", "#5b6b7b", 2, 8)
text(78, 145, "J2", 13, TXT, "700", "middle"); text(78, 160, "USB-C", 11, SUB, anchor="middle")
text(78, 173, "power only", 10, SUB, anchor="middle")
for y, t in [(185, "VBUS"), (205, "CC1"), (222, "CC2"), (236, "GND")]:
    text(112, y + 4, t, 10, SUB, anchor="end")
# VBUS -> VIN_RAW
poly([(116, 185), (200, 185)], RED); dot(116, 185, RED, 4)
# CC1 -> R1 5.1k -> GND (x=175) ; CC2 -> R2 5.1k -> GND (x=150); no crossings
poly([(116, 205), (175, 205), (175, 250)], "#4a5a6a"); res_v(175, 250, 290); gnd(175, 290)
text(185, 272, f"R1 {V['R1']}", 11, TXT, "600")
poly([(116, 222), (150, 222), (150, 250)], "#4a5a6a"); res_v(150, 250, 290); gnd(150, 290)
text(140, 272, f"R2 {V['R2']}", 11, TXT, "600", "end")
poly([(116, 236), (130, 236), (130, 320)], BLK); gnd(130, 320)
rect(40, 330, 76, 70, "#e9eef5", "#5b6b7b", 2, 8)
text(78, 352, "J1", 13, TXT, "700", "middle"); text(78, 367, "5V screw", 11, SUB, anchor="middle")
text(112, 383, "+5V", 10, SUB, anchor="end"); text(112, 397, "GND", 10, SUB, anchor="end")
poly([(116, 380), (200, 380), (200, 185)], RED); dot(200, 185, RED)
poly([(116, 394), (170, 394), (170, 410)], BLK); gnd(170, 410)
text(122, 176, "VIN_RAW", 10.5, RED, "700")
# F1, D1
line(200, 185, 240, 185, RED); rect(240, 176, 50, 18, "#ffe8a3", "#8a6d00", 2, 3); line(240, 185, 290, 185, "#8a6d00", 1.5)
text(265, 170, f"F1 {V['F1']}", 11, TXT, "600", "middle"); text(265, 208, "PTC", 10, SUB, anchor="middle")
line(290, 185, 325, 185, RED); diode_right(325, 350, 185)
text(338, 170, f"D1 {V['D1']}", 11, TXT, "600", "middle")
line(350, 185, 420, 185, RED); dot(400, 185, RED)
text(372, 208, "+5V", 11, RED, "700")
line(400, 185, 400, 230, RED); cap_v(400, 230); gnd(400, 239)
text(418, 240, f"C1 {V['C1']}", 11, TXT, "600")
pill(420, 185, "→ DevKit 5V (J3-21)", RED)
# DevKit 3V3 -> FB1 -> +3V3A
pill(250, 300, "DevKit 3V3 (J3-1,2) →", RED)
line(410, 300, 440, 300, RED); rect(440, 292, 44, 16, "#555", "#222", 1.5, 3)
text(462, 285, f"FB1 {V['FB1']}", 11, TXT, "600", "middle")
line(484, 300, 560, 300, RED); dot(510, 300, RED); dot(545, 300, RED)
text(583, 330, "+3V3A", 11, RED, "700")
line(510, 300, 510, 340, RED); cap_v(510, 340); gnd(510, 349); text(480, 385, f"C2 {V['C2']}", 10.5, TXT, "600")
line(545, 300, 545, 340, RED); cap_v(545, 340); gnd(545, 349); text(538, 400, f"C3 {V['C3']}", 10.5, TXT, "600")
poly([(560, 300), (575, 300), (575, Y3A)], RED); dot(575, Y3A, RED)

# ============================================================ 2. BIAS
section_title(620, 100, "2 · Bias VB ≈ 1.50 V (MCP6002 U1 unit A)")
pill(640, 132, "+3V3A", RED, anchor="start")
line(660, 143, 660, 160, RED); res_v(660, 160, 210); text(672, 190, f"R3 {V['R3']}", 11, TXT, "600")
line(660, 210, 660, 255, BLU); dot(660, 255, BLU)
line(660, 255, 660, 290, BLU); res_v(660, 290, 340); gnd(660, 340); text(650, 320, f"R4 {V['R4']}", 11, TXT, "600", "end")
poly([(660, 255), (705, 255), (705, 290)], BLU); cap_v(705, 290); gnd(705, 299); text(716, 305, f"C4 {V['C4']}", 11, TXT, "600")
text(605, 250, "VB_DIV", 10.5, BLU, "700")
line(705, 255, 780, 255, BLU)
opamp(780, 235, "U1A", ("pin 2", "pin 3", "pin 1"))
poly([(860, 235), (880, 235), (880, 180), (760, 180), (760, 215), (780, 215)], BLU)
dot(880, 235, BLU)
line(880, 235, 905, 235, BLU); res_h(905, 950, 235); text(927, 222, f"R5 {V['R5']}", 11, TXT, "600", "middle")
line(950, 235, 1080, 235, BLU); dot(985, 235, BLU); dot(1025, 235, BLU); dot(1065, 235, BLU)
line(985, 235, 985, 275, BLU); cap_v(985, 275); gnd(985, 284); text(968, 320, f"C6 {V['C6']}", 10.5, TXT, "600")
line(1025, 235, 1025, 275, BLU); cap_v(1025, 275); gnd(1025, 284); text(1016, 335, f"C7 {V['C7']}", 10.5, TXT, "600")
text(1000, 226, "VB", 13, BLU, "700")
poly([(1065, 235), (1065, 180), (1090, 180)], BLU); res_h(1090, 1135, 180); text(1112, 167, f"R6 {V['R6']}", 11, TXT, "600", "middle")
line(1135, 180, 1150, 180, BLU); pill(1150, 180, "→ GPIO10 (bias monitor)", BLU)
line(1065, 235, 1065, YVB, BLU); dot(1065, YVB, BLU)
# U1 power
pill(784, 340, "+3V3A", RED, 52)
text(830, 352, "U1 pin 8 (V+)", 11, SUB); text(830, 400, "U1 pin 4 (V−) → ⏚", 11, SUB)
line(810, 351, 810, 366, RED); cap_v(810, 366); gnd(810, 375); text(796, 400, f"C5 {V['C5']}", 10.5, TXT, "600", "end")
text(620, 440, "U1 = one MCP6002 (SOIC-8): unit A pins 1-2-3 = bias buffer · unit B pins 5-6-7 = voltage amp (section 4)",
     11.5, SUB, italic=True)

# ============================================================ buses
line(40, Y3A, 1400, Y3A, RED); text(44, Y3A - 8, "+3V3A bus (from FB1)", 12, RED, "700")
line(40, YVB, 1400, YVB, BLU); text(44, YVB - 8, "VB bus ≈ 1.50 V (from R5)", 12, BLU, "700")

# ============================================================ 3. CT CHANNELS
section_title(30, 560, "3 · CT channels ×6 (all identical)")
text(330, 560, "JP shunt on 1-2 = mA CT (100A/50mA, burden IN, DEFAULT) · shunt on 2-3 = 1 V CT (30A/1V, burden OUT)",
     12.5, "#8a4b00", "600", italic=True)
for i in range(6):
    n = i + 1
    cx = 95 + i * 225
    gp = g.CT_GPIO[n]
    # jack
    rect(cx - 62, 650, 50, 60, "#e9eef5", "#5b6b7b", 2, 8)
    text(cx - 37, 675, f"CT{n}", 13, TXT, "700", "middle")
    text(cx - 37, 691, f"J1{n}", 10.5, SUB, anchor="middle")
    text(cx - 37, 704, "3.5mm", 9.5, SUB, anchor="middle")
    # sleeve -> VB bus
    dot(cx - 37, 650, BLU, 4); line(cx - 37, 650, cx - 37, YVB, BLU); dot(cx - 37, YVB, BLU)
    text(cx - 33, 646, "S", 10, BLU, "700")
    # tip
    dot(cx - 12, 675, GRN, 4); text(cx - 10, 694, "T", 10, GRN, "700")
    line(cx - 12, 675, cx + 22, 675, GRN); dot(cx + 5, 675, GRN)
    # burden up to jumper pin 2
    line(cx + 5, 675, cx + 5, 655, GRN)
    res_v(cx + 5, 610, 655, "#ffd6d6", WARN)
    text(cx - 60, 616, f"R1{n}1", 10.5, WARN, "700"); text(cx - 60, 629, "22Ω 0.1%", 10, WARN)
    poly([(cx + 5, 610), (cx + 5, 594), (cx + 40, 594)], GRN)
    # jumper JP1n (pin1 top = VB, pin2 = burden, pin3 = open)
    for k, py in enumerate([576, 594, 612]):
        rect(cx + 35, py - 6, 12, 12, "#ffffff", TXT, 1.5, 2)
        text(cx + 51, py + 4, str(k + 1), 9.5, SUB)
    rect(cx + 32, 568, 18, 34, "none", "#111", 2.5, 5)          # shunt on 1-2 (default)
    line(cx + 41, 570, cx + 41, YVB, BLU); dot(cx + 41, YVB, BLU)
    text(cx + 22, 632, f"JP1{n}", 10.5, TXT, "700")
    text(cx + 57, 580, "mA", 9.5, "#8a4b00", "700"); text(cx + 57, 616, "V", 9.5, "#8a4b00", "700")
    # R 1k
    res_h(cx + 22, cx + 58, 675); text(cx + 40, 700, f"R1{n}2 1k", 10, TXT, "600", "middle")
    line(cx + 58, 675, cx + 110, 675, ORG); dot(cx + 88, 675, ORG, 6)
    # R 1k8 up to VB
    line(cx + 88, 675, cx + 88, 655, ORG); res_v(cx + 88, 610, 655)
    line(cx + 88, 610, cx + 88, YVB, BLU); dot(cx + 88, YVB, BLU)
    text(cx + 99, 636, f"R1{n}3", 10, TXT, "700"); text(cx + 99, 648, "1k8", 10, TXT)
    # C 100n to GND
    line(cx + 88, 675, cx + 88, 740, ORG); cap_v(cx + 88, 740); gnd(cx + 88, 749)
    text(cx + 72, 752, f"C1{n} 100n", 10, TXT, "600", "end")
    # BAT54S
    dot(cx + 110, 675, ORG, 4)
    line(cx + 130, 675, cx + 130, 650, ORG); diode_up(cx + 130, 620, 650)
    line(cx + 130, 620, cx + 130, Y3A, RED); dot(cx + 130, Y3A, RED)
    line(cx + 130, 675, cx + 130, 705, ORG); diode_up(cx + 130, 705, 735)
    line(cx + 130, 735, cx + 130, 745); gnd(cx + 130, 745)
    line(cx + 110, 675, cx + 130, 675, ORG); dot(cx + 130, 675, ORG, 4)
    text(cx + 118, 787, f"D1{n} BAT54S", 10, TXT, "700")
    # output
    line(cx + 110, 675, cx + 110, 815, ORG)
    pill(cx + 65, 828, f"→ {gp}", ORG, 90)

# ============================================================ 4. MAINS VOLTAGE
yM = 900
section_title(30, yM, "4 · Mains voltage sensing (on-board ZMPT101B) + U1 unit B", WARN)
rect(30, yM + 15, 590, 200, "#fff1f0", "#e6a39c", 1.5, 10, "6,4")
text(40, yM + 205, "⚠ 230 V AREA: 6.5 mm clearance + slot under T1. Never touch when powered.", 11.5, WARN, "700")
rect(45, yM + 45, 62, 110, "#e9eef5", "#5b6b7b", 2, 8)
text(76, yM + 70, "J5", 13, TXT, "700", "middle"); text(76, yM + 86, "230V", 10, SUB, anchor="middle")
text(103, yM + 104, "L", 11, MAINS_L, "700", "end"); text(103, yM + 146, "N", 11, MAINS_N, "700", "end")
yl, yn = yM + 100, yM + 142
line(107, yl, 150, yl, MAINS_L, 3.5); rect(150, yl - 9, 52, 18, "#ffe8a3", "#8a6d00", 2, 3); line(150, yl, 202, yl, "#8a6d00", 1.5)
text(176, yl - 15, f"F2 {V['F2']}", 10.5, TXT, "600", "middle")
line(202, yl, 520, yl, MAINS_L, 3.5); dot(230, yl, MAINS_L)
line(107, yn, 575, yn, MAINS_N, 3.5); dot(230, yn, MAINS_N)
rect(221, yl + 8, 18, yn - yl - 16, "#cfe8cf", "#3b6e3b", 2, 3); line(221, yn - 10, 239, yl + 10, "#3b6e3b", 1.5)
text(245, yl + 26, "RV1", 10.5, TXT, "700"); text(245, yl + 38, "275VAC MOV", 9.5, SUB)
for k in range(4):
    x1 = 290 + k * 60
    res_h(x1, x1 + 40, yl, "#fde0dc", WARN)
    text(x1 + 20, yl - 13, f"R4{k + 1}", 10.5, WARN, "700", "middle")
    text(x1 + 20, yl + 22, "220k", 10, TXT, anchor="middle")
line(290, yl, 290, yl)
text(410, yl + 38, "4 × 220k 1% 1206 (≥200 V)", 10, SUB, anchor="middle")
# T1
rect(575, yM + 60, 110, 110, "#dbe9ff", "#1d4f91", 2.5, 8)
line(630, yM + 66, 630, yM + 164, WARN, 2); text(630, yM + 180, "isolation", 9.5, WARN, anchor="middle")
text(630, yM + 54, "T1", 13, "#1d4f91", "700", "middle"); text(630, yM + 190, "ZMPT101B", 10.5, "#1d4f91", "700", "middle")
line(520, yl, 575, yl, MAINS_L, 3.5)
text(585, yl + 4, "1", 10, SUB); text(585, yn + 4, "2", 10, SUB)
text(674, yl + 4, "4", 10, SUB); text(674, yn + 4, "3", 10, SUB)
# secondary
yA, yP = yl, yn
line(685, yP, 745, yP, BLU); pill(745, yP, "VB", BLU, 40)
line(685, yA, 820, yA, PUR); dot(790, yA, PUR)
text(700, yA - 6, "ZS_A", 10.5, PUR, "700")
# op-amp B: − at (840, yA), + at (840, yA+40)
opamp(840, yA + 20, "U1B", ("pin 6", "pin 5", "pin 7"))
line(820, yA, 840, yA, PUR)
poly([(840, yA + 40), (812, yA + 40), (812, yA + 72)], BLU); pill(793, yA + 84, "VB", BLU, 38)
# feedback R47 || C41
poly([(790, yA), (790, yA - 45), (840, yA - 45)], PUR); res_h(840, 890, yA - 45)
text(865, yA - 55, f"R47 {V['R47']}", 10.5, TXT, "600", "middle")
poly([(890, yA - 45), (945, yA - 45), (945, yA + 20)], PUR)
poly([(790, yA - 45), (790, yA - 80), (860, yA - 80)], PUR); cap_h(860, yA - 80); line(869, yA - 80, 945, yA - 80, PUR)
line(945, yA - 80, 945, yA - 45, PUR); dot(945, yA - 45, PUR); dot(790, yA - 45, PUR)
text(866, yA - 98, f"C41 {V['C41']}", 10.5, TXT, "600", "middle")
line(920, yA + 20, 960, yA + 20, PUR); dot(945, yA + 20, PUR)
text(952, yA + 48, "V_OUT", 10.5, PUR, "700")
res_h(960, 1005, yA + 20); text(982, yA + 8, f"R48 {V['R48']}", 10.5, TXT, "600", "middle")
line(1005, yA + 20, 1100, yA + 20, PUR); dot(1030, yA + 20, PUR, 6); dot(1065, yA + 20, PUR, 4)
line(1030, yA + 20, 1030, yA + 60, PUR); cap_v(1030, yA + 60); gnd(1030, yA + 69)
text(990, yA + 108, f"C42 {V['C42']}", 10, TXT, "600")
line(1065, yA + 20, 1065, yA - 5); diode_up(1065, yA - 35, yA - 5); line(1065, yA - 35, 1065, yA - 55, RED)
pill(1040, yA - 66, "+3V3A", RED, 52)
line(1065, yA + 20, 1065, yA + 45); diode_up(1065, yA + 45, yA + 75); gnd(1065, yA + 75)
text(1077, yA - 12, "D41", 10, TXT, "700"); text(1077, yA, "BAT54S", 9.5, SUB)
pill(1100, yA + 20, "→ GPIO9 (V_ADC)", PUR)
text(700, yM + 235, "T1 primary 0.26 mA at 230 V → U1B transimpedance (R47 2k7) → ≈0.70 V RMS around VB → R48/C42 filter → GPIO9",
     11.5, SUB, italic=True)

# ============================================================ 5. OLED header
section_title(1250, yM + 10, "5 · I²C OLED header J6")
rect(1260, yM + 30, 70, 110, "#e9eef5", "#5b6b7b", 2, 8)
text(1295, yM + 50, "J6", 13, TXT, "700", "middle")
for k, (pin, net, c) in enumerate([("1 GND", "⏚ GND", BLK), ("2 VCC", "+3V3 (DevKit)", RED),
                                    ("3 SCL", "→ GPIO18", "#4a5a6a"), ("4 SDA", "→ GPIO17", "#4a5a6a")]):
    y = yM + 72 + k * 20
    text(1325, y + 4, pin, 10, SUB, anchor="end")
    line(1330, y, 1350, y, c); pill(1350, y, net, c)

# ============================================================ ESP32 DevKit
rect(1480, 90, 390, 800, "#20303f", "#0d161f", 2, 14)
text(1500, 124, "ESP32-S3-DevKitC-1 (N16R8)", 17, "#ffffff", "700")
text(1500, 144, "plugs into sockets J3 (left header) + J4 (right header)", 11.5, "#b9c7d4")
rows = [("J3-1, J3-2", "3V3", "+3V3 → FB1 / J6", RED), ("J3-21", "5V", "+5V ← D1", RED),
        ("J3-22, J4-1/21/22", "GND", "⏚ GND", "#aaaaaa"),
        ("J4-4", "GPIO1", "CT1_ADC", ORG), ("J3-4", "GPIO4", "CT2_ADC", ORG), ("J3-5", "GPIO5", "CT3_ADC", ORG),
        ("J3-6", "GPIO6", "CT4_ADC", ORG), ("J3-7", "GPIO7", "CT5_ADC", ORG), ("J3-12", "GPIO8", "CT6_ADC", ORG),
        ("J3-15", "GPIO9", "V_ADC (voltage)", PUR), ("J3-16", "GPIO10", "VB_MON (bias)", BLU),
        ("J3-10", "GPIO17", "I2C_SDA → J6-4", "#8ea1b5"), ("J3-11", "GPIO18", "I2C_SCL → J6-3", "#8ea1b5")]
text(1500, 178, "Socket pin", 11.5, "#b9c7d4", "700"); text(1630, 178, "GPIO", 11.5, "#b9c7d4", "700")
text(1710, 178, "Net / use", 11.5, "#b9c7d4", "700")
for k, (sp, gpio, net, c) in enumerate(rows):
    y = 206 + k * 34
    add(f'<circle cx="1488" cy="{y - 4}" r="6" fill="{c}"/>')
    text(1500, y, sp, 12, "#dbe4ec")
    text(1630, y, gpio, 13, "#ffffff", "700")
    text(1710, y, net, 12, c if c not in ("#aaaaaa",) else "#dddddd", "700")
text(1500, 666, "All other socket pins: no connect.", 11.5, "#b9c7d4")
text(1500, 686, "Avoid: GPIO0/3/45/46 (strapping), GPIO35-37", 11.5, "#b9c7d4")
text(1500, 704, "(octal PSRAM), GPIO11-20 (ADC2 / Wi-Fi).", 11.5, "#b9c7d4")
text(1500, 734, "Header rows 22.86 mm apart. MEASURE", 11.5, "#ffc07a", "700")
text(1500, 752, "your DevKit and verify each pin before", 11.5, "#ffc07a", "700")
text(1500, 770, "ordering (your board's silkscreen \"4\"", 11.5, "#ffc07a", "700")
text(1500, 788, "was really GPIO1).", 11.5, "#ffc07a", "700")
text(1500, 822, "Antenna end = pin 1 end → board top edge,", 11.5, "#b9c7d4")
text(1500, 840, "no copper under it.", 11.5, "#b9c7d4")

# ============================================================ 6. tables
yT = 1165


def table(x, y, w, h, title, rows_, tc=TXT, fill="#f7f9fb", stroke="#b8c4d0"):
    rect(x, y, w, h, fill, stroke, 1.5, 10)
    text(x + 16, y + 28, title, 15, tc, "700")
    for k, (t, sz, c, wt) in enumerate(rows_):
        text(x + 16, y + 54 + k * 20, t, sz, c, wt)


table(30, yT, 600, 455, "Parts: values (all from the KiCad BOM)", [
    ("Resistors", 13, TXT, "700"),
    ("R1, R2: 5.1k (USB-C CC pull-downs)", 12.5, TXT, "400"),
    ("R3: 12k 1% · R4: 10k 1% (bias divider)", 12.5, TXT, "400"),
    ("R5: 47Ω (op-amp isolation) · R6: 1k (bias monitor)", 12.5, TXT, "400"),
    ("R111…R161: 22Ω 0.1% burden ×6 (24Ω also works: set HA Burden 24)", 12.5, TXT, "400"),
    ("R112…R162: 1k 1% ×6 · R113…R163: 1k8 1% ×6", 12.5, TXT, "400"),
    ("R41–R44: 220k 1% 1206 ×4 (mains) · R47: 2k7 1% · R48: 1k", 12.5, TXT, "400"),
    ("Capacitors", 13, TXT, "700"),
    ("C1: 22µF 16V 1206 · C2, C6: 10µF 0805", 12.5, TXT, "400"),
    ("C3, C4, C5, C7, C42, C11…C16: 100nF (104) ×11", 12.5, TXT, "400"),
    ("C41: 47nF (473)", 12.5, TXT, "400"),
    ("Semiconductors / others", 13, TXT, "700"),
    ("U1: MCP6002 SOIC-8 · D1: SS34 · D11…D16, D41: BAT54S ×7", 12.5, TXT, "400"),
    ("F1: 500mA PTC 1206 · F2: 100mA T 250V TR5 · RV1: 275VAC 7mm MOV", 12.5, TXT, "400"),
    ("FB1: 600Ω ferrite 0805 · T1: ZMPT101B", 12.5, TXT, "400"),
    ("J1, J5: 2P 5.08mm screw terminal · J2: USB-C 6P power-only", 12.5, TXT, "400"),
    ("J3, J4: 1×22 female header · J6: 1×4 pin header", 12.5, TXT, "400"),
    ("J11…J16: 3.5mm jack SJ1-3523N · JP11…JP16: 1×3 header + shunt", 12.5, TXT, "400"),
    ("H1–H4: M3 holes (H1 in mains area → plastic screw)", 12.5, TXT, "400"),
    ("Total: 81 parts, 42 nets", 12.5, SUB, "700"),
])
table(650, yT, 600, 455, "Jumpers JP11…JP16 & Home Assistant settings", [
    ("Shunt position per CT channel", 13, TXT, "700"),
    ("100A/50mA CT (SCT-013-000): shunt on 1-2 (mA), burden IN", 12.5, TXT, "400"),
    ("   HA: Burden 22 (or 24) · Secondary 0.05 · Primary 100 · Cal 1.555", 12.5, TXT, "400"),
    ("30A/1V CT (SCT-013-030): shunt on 2-3 (V), burden OUT", 12.5, TXT, "400"),
    ("   HA: Burden 1 · Secondary 1 · Primary 30 · Cal 1.555", 12.5, TXT, "400"),
    ("", 8, TXT, "400"),
    ("Why 1.555: the 1k/1k8 divider passes ×0.643 of the CT signal.", 12, SUB, "400"),
    ("Fine-tune per channel: Cal = 1.555 × (clamp-meter A ÷ reading A).", 12, SUB, "400"),
    ("", 8, TXT, "400"),
    ("Wrong jumper?", 13, TXT, "700"),
    ("1V CT with shunt on mA → reads ~25 % of true (safe, obviously wrong)", 12, TXT, "400"),
    ("mA CT with shunt on V → CT runs OPEN → 0/4095 clipping", 12, WARN, "700"),
    ("   → unclamp immediately. Ship boards with shunts on 1-2 (mA).", 12, WARN, "400"),
    ("", 8, TXT, "400"),
    ("Tested on the breadboard (same CT channel values)", 13, TXT, "700"),
    ("30A CT: 0.33 A light+fan · 12.66 A water heater (clean sine)", 12, SUB, "400"),
    ("100A CT + 24Ω: 4.6 A induction cooker, no clipping", 12, SUB, "400"),
    ("Not yet tested: on-board ZMPT101B + MCP6002 voltage stage", 12, "#a33b00", "700"),
])
table(1270, yT, 600, 455, "Before ordering / first power-up", [
    ("1. Measure DevKit row spacing (22.86 mm) + every used pin", 12.5, TXT, "400"),
    ("2. ZMPT101B pin grid 10.0 × 12.7 mm (calipers)", 12.5, TXT, "400"),
    ("3. Screw terminals: wire entry towards board edge", 12.5, TXT, "400"),
    ("4. 6.5 mm mains creepage + slot under T1 kept", 12.5, TXT, "400"),
    ("5. First power-up WITHOUT mains and WITHOUT CTs:", 12.5, TXT, "700"),
    ("   +5V ≈ 4.7 V after D1 · +3V3A ≈ 3.3 V · VB ≈ 1.50 V", 12.5, TXT, "400"),
    ("   each CTn_ADC ≈ 1.50 V · V_ADC ≈ 1.50 V", 12.5, TXT, "400"),
    ("6. Then one CT at a time, small load first, Clipped = 0", 12.5, TXT, "400"),
    ("7. Mains last: fuse fitted, enclosure closed", 12.5, WARN, "700"),
    ("", 8, TXT, "400"),
    ("Files", 13, TXT, "700"),
    ("KiCad: hardware/kicad/ct6-energy-monitor.kicad_pro", 12, SUB, "400"),
    ("Gerbers/BOM/CPL: hardware/fab/", 12, SUB, "400"),
    ("EasyEDA pin-by-pin guide: renders/easyeda_connection_guide.svg", 12, SUB, "400"),
    ("This diagram: renders/pcb_full_connection.svg", 12, SUB, "400"),
], "#a33b00", "#fff6f0", "#e0a070")

s[s.index("__HEADER__")] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
                            f'font-family="Segoe UI, Arial, sans-serif"><rect width="{W}" height="{H}" fill="#ffffff"/>')
add("</svg>")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(s) + "\n")
print("wrote", OUT)
