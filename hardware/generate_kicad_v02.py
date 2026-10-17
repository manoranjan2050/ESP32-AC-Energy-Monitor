"""
Generate the CT6 v0.2 KiCad SCHEMATIC (ESP32-S3-WROOM-1U module on board + ZMPT101B module backup)
from netlist_v02.py, reusing the proven schematic writer in generate_kicad.py.

Schematic only (the v0.2 PCB is laid out in EasyEDA). Output: hardware/kicad_v02/

    python hardware/generate_kicad_v02.py          (plain Python is enough; no pcbnew needed)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_kicad as g  # noqa: E402
import netlist_v02 as n  # noqa: E402

g.parts = n.parts
g.PWR_FLAG_NETS = n.PWR_FLAG_NETS
g.NAME = "ct6-energy-monitor-v02"
g.OUT = os.path.join(HERE, "kicad_v02")

os.makedirs(g.OUT, exist_ok=True)
g.write_project_files()
g.write_schematic()

sch_path = os.path.join(g.OUT, g.NAME + ".kicad_sch")
sch = open(sch_path, encoding="utf-8").read()
sch = (sch.replace('(rev "0.1")', '(rev "0.2")')
          .replace("CT6 Energy Monitor - ESP32-S3 + 6 CT + ZMPT101B",
                   "CT6 Energy Monitor v0.2 - ESP32-S3-WROOM-1U + 6 CT + ZMPT101B")
          .replace("ESP32-S3-DevKitC-1 (N16R8) sockets - VERIFY PINOUT of your DevKit",
                   "U2 ESP32-S3-WROOM-1U-N16R8 module (U.FL antenna) + LDO, USB-C data, RESET/BOOT, UART")
          .replace("POWER IN: 5 V from terminal J1 or USB-C J2 (power only)",
                   "POWER IN: 5 V from terminal J1 or USB-C J2 (data: D+ IO20, D- IO19) -> AMS1117 -> +3V3"))
open(sch_path, "w", encoding="utf-8").write(sch)
print("wrote", sch_path, "|", len(n.parts), "parts")
