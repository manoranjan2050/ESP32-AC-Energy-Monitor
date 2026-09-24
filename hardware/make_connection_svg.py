"""Generate renders/final_6ct_voltage_connection.svg: the breadboard-proven wiring for 6 CTs + ZMPT101B."""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders", "final_6ct_voltage_connection.svg")
W, H = 1600, 1212
RED, BLK, BLU, GRN, ORG = "#d62828", "#222222", "#1d6fd6", "#2a9d3f", "#e07b00"
TXT, SUB = "#1b2733", "#3d4b59"
Y33, YB, YG = 110, 250, 560          # 3V3 rail, BIAS bus, GND rail
CT_GPIO = ["GPIO1", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO8"]

s = []
def add(x): s.append(x)
def line(x1, y1, x2, y2, c, w=4, dash=None):
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{w}"'
        + (f' stroke-dasharray="{dash}"' if dash else "") + ' stroke-linecap="round"/>')
def poly(pts, c, w=4):
    add(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" stroke="{c}" stroke-width="{w}" fill="none" stroke-linejoin="round"/>')
def dot(x, y, c, r=6):
    add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"/>')
def text(x, y, t, size=14, c=TXT, weight="400", anchor="start", italic=False):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{c}" font-weight="{weight}" text-anchor="{anchor}"'
        + (' font-style="italic"' if italic else "") + f'>{t}</text>')
def res_v(x, y1, y2, fill="#f3e2b3", stroke="#6b5518", dash=None):
    add(f'<rect x="{x - 8}" y="{y1}" width="16" height="{y2 - y1}" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="2"'
        + (f' stroke-dasharray="{dash}"' if dash else "") + '/>')
def res_h(x1, x2, y):
    add(f'<rect x="{x1}" y="{y - 8}" width="{x2 - x1}" height="16" rx="3" fill="#f3e2b3" stroke="#6b5518" stroke-width="2"/>')
def cap_v(x, y):  # plates at y and y+10
    line(x - 16, y, x + 16, y, TXT, 4)
    line(x - 16, y + 10, x + 16, y + 10, TXT, 4)
def pill(x, y, t, c=ORG, w=78):
    add(f'<rect x="{x}" y="{y - 13}" width="{w}" height="26" rx="13" fill="{c}"/>')
    text(x + w / 2, y + 5, t, 13, "#ffffff", "700", "middle")

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Segoe UI, Arial, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(30, 42, "CT6 energy monitor: final wiring, 6 CT + ZMPT101B voltage (breadboard-proven values)", 26, TXT, "700")
text(30, 68, "One shared BIAS feeds all 6 CT channels. Each channel is identical: fit the 24 Ω burden only when that channel uses a 100A/50mA CT.", 15, "#4a5a6a")

# ---------------- rails ----------------
poly([(40, Y33), (1360, Y33), (1360, 130), (1380, 130)], RED)
text(44, Y33 - 10, "3V3 rail", 15, RED, "600")
poly([(40, YG), (1360, YG), (1360, 540), (1380, 540)], BLK)
text(44, YG + 24, "GND rail", 15, TXT, "600")
line(120, YB, 1340, YB, BLU)
text(1250, YB - 12, "BIAS bus ≈ 1.65 V", 14, BLU, "700")

# ---------------- bias block ----------------
line(120, Y33, 120, 140, RED); res_v(120, 140, 210); line(120, 210, 120, YB, BLU)
text(134, 180, "R1 10k", 14, TXT, "600")
line(120, YB, 120, 300, BLU); res_v(120, 300, 370); line(120, 370, 120, YG, BLK)
text(134, 340, "R2 10k", 14, TXT, "600")
dot(120, YB, BLU, 7)
poly([(120, YB), (45, YB), (45, 420)], BLU); cap_v(45, 420); line(45, 430, 45, YG, BLK)
text(68, 446, "C1", 14, TXT, "600"); text(68, 464, "100µF", 14, TXT, "600")
text(68, 482, "+ up", 11.5, SUB)
dot(45, YB, BLU)

# ---------------- 6 CT channels ----------------
for i in range(6):
    cx = 270 + i * 190
    n = i + 1
    # jack
    add(f'<rect x="{cx - 58}" y="380" width="48" height="60" rx="8" fill="#e9eef5" stroke="#5b6b7b" stroke-width="2"/>')
    text(cx - 34, 406, f"CT{n}", 14, TXT, "700", "middle")
    text(cx - 34, 424, "jack", 11, SUB, anchor="middle")
    dot(cx - 10, 400, GRN)
    text(cx - 6, 418, "T", 11, GRN, "700")
    # sleeve up to bias bus
    dot(cx - 34, 380, BLU)
    line(cx - 34, 380, cx - 34, YB, BLU)
    dot(cx - 34, YB, BLU)
    text(cx - 30, 374, "S", 11, BLU, "700")
    # tip node + burden (optional)
    line(cx - 10, 400, cx + 8, 400, GRN)
    dot(cx, 400, GRN)
    line(cx, 400, cx, 360, GRN)
    res_v(cx, 300, 360, "#ffd6d6", "#b01e1e", "5,3")
    poly([(cx, 300), (cx, 282), (cx - 34, 282)], BLU)
    dot(cx - 34, 282, BLU)
    text(cx + 12, 322, "R_B", 13, "#b01e1e", "700")
    text(cx + 12, 338, "24 Ω", 12, "#b01e1e")
    text(cx + 12, 353, "100A", 11, "#8a4b00", italic=True)
    # R3 1k
    res_h(cx + 8, cx + 48, 400)
    text(cx + 14, 388, "1k", 12, TXT, "600")
    line(cx + 48, 400, cx + 60, 400, ORG)
    # ADC node
    dot(cx + 60, 400, ORG, 7)
    # R4 1k8 up to bias
    line(cx + 60, 400, cx + 60, 360, ORG); res_v(cx + 60, 290, 360); line(cx + 60, 290, cx + 60, YB, BLU)
    dot(cx + 60, YB, BLU)
    text(cx + 72, 318, "1.8k", 12, TXT, "600")
    # 104 to GND
    poly([(cx + 60, 400), (cx + 110, 400), (cx + 110, 490)], ORG); cap_v(cx + 110, 490); line(cx + 110, 500, cx + 110, YG, BLK)
    dot(cx + 110, 400, ORG)
    text(cx + 130, 500, "104", 12, TXT, "600")
    # output to GPIO
    line(cx + 60, 400, cx + 60, 440, ORG)
    pill(cx + 22, 455, "→ " + CT_GPIO[i], ORG, 78)

# ---------------- ESP32 ----------------
add('<rect x="1380" y="90" width="190" height="480" rx="12" fill="#20303f" stroke="#0d161f" stroke-width="2"/>')
text(1398, 122, "ESP32-S3", 17, "#ffffff", "700"); text(1398, 142, "DevKit N16R8", 13, "#b9c7d4")
dot(1380, 130, RED, 7); text(1398, 170, "3V3", 15, "#ff8a8a", "700")
rows = [("GPIO1", "CT1"), ("GPIO4", "CT2"), ("GPIO5", "CT3"), ("GPIO6", "CT4"), ("GPIO7", "CT5"),
        ("GPIO8", "CT6"), ("GPIO9", "Voltage"), ("GPIO10", "Bias mon.*")]
for k, (g, what) in enumerate(rows):
    y = 205 + k * 36
    dot(1380, y, ORG if what != "Voltage" else "#7b2cbf", 7)
    text(1398, y + 5, g, 15, "#ffc07a" if what != "Voltage" else "#d7b4ff", "700")
    text(1470, y + 5, what, 13, "#b9c7d4")
dot(1380, 540, "#aaaaaa", 7); text(1398, 545, "GND", 15, "#dddddd", "700")

# ---------------- voltage sensor ----------------
text(30, 632, "VOLTAGE: ZMPT101B module (ready-made blue board)", 18, TXT, "700")
add('<rect x="40" y="660" width="120" height="110" rx="10" fill="#fff0f0" stroke="#c0392b" stroke-width="2.5"/>')
text(100, 690, "230 V AC", 15, "#c0392b", "700", "middle")
text(100, 712, "from MCB", 12, SUB, anchor="middle")
text(100, 740, "via 100mA fuse", 12, SUB, anchor="middle")
line(160, 690, 230, 690, "#8b4513", 5); text(190, 682, "L", 14, "#8b4513", "700")
line(160, 740, 230, 740, "#1f3a93", 5); text(190, 760, "N", 14, "#1f3a93", "700")
add('<rect x="230" y="650" width="230" height="130" rx="10" fill="#dbe9ff" stroke="#1d4f91" stroke-width="2"/>')
text(345, 690, "ZMPT101B", 17, "#1d4f91", "700", "middle")
text(345, 710, "module", 13, SUB, anchor="middle")
text(345, 738, "trim pot: GPIO9 ≈ 1.5–2 Vpp", 11.5, SUB, anchor="middle")
text(345, 756, "(check with firmware)", 11.5, SUB, anchor="middle")
for y, lbl in [(670, "VCC"), (715, "OUT"), (760, "GND")]:
    dot(460, y, "#1d4f91"); text(452, y + 5, lbl, 12, "#1d4f91", "700", "end")
line(460, 670, 520, 670, RED); pill(520, 670, "5V (VIN)", RED, 80)
line(460, 760, 520, 760, BLK); pill(520, 760, "GND", BLK, 70)
line(460, 715, 610, 715, "#7b2cbf"); res_h(610, 650, 715); text(612, 703, "10k", 12, TXT, "600")
line(650, 715, 800, 715, "#7b2cbf"); dot(690, 715, "#7b2cbf", 7); dot(745, 715, "#7b2cbf", 7)
pill(800, 715, "→ GPIO9", "#7b2cbf", 76)
# 22k to GND
line(690, 715, 690, 728, "#7b2cbf"); res_v(690, 728, 768); line(690, 768, 690, 788, BLK)
text(680, 754, "22k", 12, TXT, "600", "end")
# 103 to GND
line(745, 715, 745, 750, "#7b2cbf"); cap_v(745, 750); line(745, 760, 745, 788, BLK)
text(767, 760, "103", 12, TXT, "600")
line(690, 788, 745, 788, BLK); line(745, 788, 800, 788, BLK); pill(800, 788, "GND", BLK, 60)
add('<rect x="880" y="650" width="690" height="140" rx="10" fill="#fff6f0" stroke="#e0a070" stroke-width="1.5"/>')
text(898, 676, "ZMPT101B notes", 15, "#a33b00", "700")
text(898, 700, "• Power the module from 5 V (DevKit 5V/VIN). Its LM358 cannot swing high enough on 3.3 V.", 13, TXT)
text(898, 721, "• 10k/22k scales OUT (≈2.5 V centre) to ≈1.7 V at GPIO9. Check GPIO9 with a meter: DC ≈ 1.7 V, never > 3.3 V.", 13, TXT)
text(898, 742, "• Mains L/N go ONLY into the module's screw terminal, through a 100 mA fuse. Never on the breadboard.", 13, TXT)
text(898, 763, "• The CT6 PCB replaces this module with its own on-board ZMPT101B circuit (same GPIO9).", 13, TXT)

# ---------------- legend ----------------
add('<rect x="30" y="826" width="1540" height="44" rx="8" fill="#f7f9fb" stroke="#b8c4d0" stroke-width="1.5"/>')
lx = 50
for c, t in [(RED, "3V3 / 5V"), (BLK, "GND"), (BLU, "BIAS / CT sleeve"), (GRN, "CT tip"), (ORG, "CT to ADC"),
             ("#7b2cbf", "Voltage signal"), ("#8b4513", "Mains L"), ("#1f3a93", "Mains N")]:
    line(lx, 848, lx + 36, 848, c, 5); text(lx + 44, 853, t, 13.5, TXT); lx += 180
text(1480, 853, "● = joint", 13, SUB)

# ---------------- tables ----------------
def box(x, y, w, h, title, lines, fill="#f7f9fb", stroke="#b8c4d0", tcol=TXT):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    text(x + 16, y + 28, title, 15, tcol, "700")
    for k, (t, sz, c, wt) in enumerate(lines):
        text(x + 16, y + 54 + k * 21, t, sz, c, wt)

box(30, 888, 520, 308, "Home Assistant settings per CT type", [
    ("100A/50mA CT (SCT-013-000) + 24 Ω R_B:", 13.5, TXT, "700"),
    ("  Burden 24 · Secondary 0.05 · Primary 100 · Cal 1.555", 13.5, TXT, "400"),
    ("30A/1V CT (SCT-013-030), NO R_B:", 13.5, TXT, "700"),
    ("  Burden 1 · Secondary 1 · Primary 30 · Cal 1.555", 13.5, TXT, "400"),
    ("", 8, TXT, "400"),
    ("1.555 undoes the 1k/1.8k divider (×0.643).", 12.5, SUB, "400"),
    ("Fine-tune: Cal = 1.555 × (clamp-meter A ÷ reading A).", 12.5, SUB, "400"),
    ("Tested: 30A CT 12.66 A (water heater), 0.33 A (light+fan);", 12.5, SUB, "400"),
    ("100A CT + 24 Ω 4.6 A (induction cooker).", 12.5, SUB, "400"),
    ("", 8, TXT, "400"),
    ("* GPIO10 bias monitor is optional: BIAS → 1k → GPIO10.", 12.5, SUB, "400"),
    ("Current firmware reads CT1 only; 6-ch + voltage firmware is next.", 12.5, "#a33b00", "600"),
])
box(565, 888, 480, 308, "Parts for the full build", [
    ("Shared bias: R1, R2 10 kΩ ×2 · C1 100 µF ×1", 13.5, TXT, "400"),
    ("Per CT channel (×6):", 13.5, TXT, "700"),
    ("  1 kΩ ×6 (brown-black-red)", 13.5, TXT, "400"),
    ("  1.8 kΩ ×6 (brown-grey-red)", 13.5, TXT, "400"),
    ("  104 ceramic ×6", 13.5, TXT, "400"),
    ("  24 Ω ×1 per 100A CT (red-yellow-black)", 13.5, TXT, "400"),
    ("  3.5 mm jack ×6 (tip + sleeve used)", 13.5, TXT, "400"),
    ("Voltage: ZMPT101B module ×1 · 10 kΩ · 22 kΩ · 103 ×1", 13.5, TXT, "400"),
    ("Optional: BAT54S ×7 clamps (ADC node → GND/3V3)", 13.5, SUB, "400"),
    ("", 8, TXT, "400"),
    ("Tip = signal, Sleeve = BIAS, Ring = not used.", 12.5, SUB, "400"),
    ("Keep each R_B's legs right at its own jack.", 12.5, SUB, "400"),
])
box(1060, 888, 510, 308, "Check before clamping (every channel)", [
    ("1. Meter Ω tip↔sleeve, CT plugged, unclamped:", 13.5, TXT, "700"),
    ("   100A CT + 24 Ω → ≈15–24 Ω · 30A/1V CT → ≈60–70 Ω", 13, TXT, "400"),
    ("2. Unclamped: Bias ≈1.6 V, RMS few mV, Clipped 0", 13.5, TXT, "400"),
    ("3. Clamp ONE wire (live only), small load first", 13.5, TXT, "400"),
    ("4. Min/Max hit 0/4095 or Clipped > 0", 13.5, "#b01e1e", "700"),
    ("   → unclamp immediately (burden missing)", 13.5, "#b01e1e", "400"),
    ("", 8, TXT, "400"),
    ("Never run a 100A/50mA CT without its 24 Ω burden.", 12.5, SUB, "400"),
    ("No 230 V wiring on the breadboard.", 12.5, SUB, "400"),
    ("ADC1 pins only; avoid GPIO3 and GPIO11–20.", 12.5, SUB, "400"),
], "#fff6f0", "#e0a070", "#a33b00")

add("</svg>")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(s) + "\n")
print("wrote", OUT)
