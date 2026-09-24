"""
Route the CT6 board: hand-route the 230 V mains nets, autoroute everything else with Freerouting,
then restore rules and re-pour GND.

    set CT6_NO_ZONES=1 && "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/generate_kicad.py
    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/route_pcb.py <path-to-freerouting-1.9.0.jar>

Freerouting 1.9.0 runs on Java 17 (2.x needs Java 21).
"""
import os
import re
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "ct6-energy-monitor.kicad_pcb")
DSN = os.path.join(HERE, "kicad", "ct6-energy-monitor.dsn")
SES = os.path.join(HERE, "kicad", "ct6-energy-monitor.ses")
JAR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "freerouting-1.9.0.jar")

mm = pcbnew.FromMM
board = pcbnew.LoadBoard(PCB)
OX, OY = 50.0, 50.0   # same page offset as generate_kicad.py


FPS = {fp.GetReference(): fp for fp in board.GetFootprints()}


def pad_pos(ref, num):
    pad = next(p for p in FPS[ref].Pads() if p.GetNumber() == num)
    p = pad.GetPosition()
    return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY


def track(net, pts, layer=pcbnew.F_Cu, width=0.8):
    ni = board.FindNet(net)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(mm(x1 + OX), mm(y1 + OY)))
        t.SetEnd(pcbnew.VECTOR2I(mm(x2 + OX), mm(y2 + OY)))
        t.SetWidth(mm(width))
        t.SetLayer(layer)
        t.SetNet(ni)
        t.SetLocked(True)
        board.Add(t)


# ---- 1. read pad positions first (KiCad 10 SWIG wrappers break after board.Remove) ------
L1, N1 = pad_pos("J5", "1"), pad_pos("J5", "2")
F2a, F2b = pad_pos("F2", "1"), pad_pos("F2", "2")
RVa, RVb = pad_pos("RV1", "1"), pad_pos("RV1", "2")
R = {i: (pad_pos(f"R4{i}", "1"), pad_pos(f"R4{i}", "2")) for i in range(1, 5)}
T1a, T1b = pad_pos("T1", "1"), pad_pos("T1", "2")



# ---- 2. hand-route mains (230 V) nets, 0.8 mm, locked ---------------------------------------
track("AC_L", [L1, (L1[0], F2a[1] - 3), (F2a[0], F2a[1])])
track("AC_LF", [RVa, (RVa[0], F2b[1] - 2), F2b])
track("AC_LF", [F2b, (R[1][0][0] - 2.5, F2b[1]), (R[1][0][0], R[1][0][1] + 1.0), R[1][0]])
track("AC_M1", [R[1][1], R[2][0]])
track("AC_M2", [R[2][1], R[3][0]])
track("AC_M3", [R[3][1], R[4][0]])
track("AC_ZP", [R[4][1], (T1a[0] - 1.2, R[4][1][1]), T1a])
# neutral on the bottom layer, under the SMD resistor chain
track("AC_N", [N1, (RVb[0], N1[1]), RVb], layer=pcbnew.B_Cu)
track("AC_N", [RVb, (RVb[0] + 2, T1b[1]), T1b], layer=pcbnew.B_Cu)

# ---- 3. export DSN, then fence the (already fully routed) mains block with a keepout --------
assert pcbnew.ExportSpecctraDSN(board, DSN), "DSN export failed"
# board mm: mains copper reaches x=31.6 (T1 primary pads) and y=30.1 (F2 pads) -> + 6.5 mm margin.
# T1's secondary pads (x=40.5, low voltage) stay outside so the router can reach them.
MAINS_KEEPOUT = [(0.0, 0.0), (38.3, 0.0), (38.3, 36.8), (0.0, 36.8)]
dsn = open(DSN, encoding="utf-8").read()
# DSN units are um with the Y axis inverted - verify on J5 (placed at board 6,16 mm)
m = re.search(r"\(place J5 (-?[\d.]+) (-?[\d.]+)", dsn)
assert m and abs(float(m.group(1)) - 56000) < 1 and abs(float(m.group(2)) + 66000) < 1, m and m.group(0)
pts = " ".join(f"{(x + OX) * 1000:.0f} {-(y + OY) * 1000:.0f}" for x, y in MAINS_KEEPOUT + MAINS_KEEPOUT[:1])
keep = f"    (keepout \"mains\" (polygon signal 0 {pts}))\n"
dsn = dsn.replace("  (structure\n", "  (structure\n" + keep, 1)
open(DSN, "w", encoding="utf-8").write(dsn)

# ---- 4. Freerouting ------------------------------------------------------------------------
print("routing ...")
r = subprocess.run(["java", "-jar", JAR, "-de", DSN, "-do", SES, "-mp", "30"],
                   capture_output=True, text=True, timeout=1800)
print(r.stdout[-1500:], r.stderr[-1500:])
assert os.path.exists(SES), "Freerouting produced no .ses"
assert pcbnew.ImportSpecctraSES(board, SES), "SES import failed"

# ---- 5. restore rules, re-pour GND, save ----------------------------------------------------
sys.path.insert(0, HERE)
from generate_kicad import GND_POUR  # noqa: E402

for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet("GND"))
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in GND_POUR:
        ol.Append(mm(x + OX), mm(y + OY))
    board.Add(z)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("saved", PCB)
