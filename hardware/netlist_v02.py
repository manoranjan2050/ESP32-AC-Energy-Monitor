"""
CT6 Energy Monitor v0.2 netlist: the single source of truth for BOTH the v0.2 KiCad schematic
(generate_kicad_v02.py) and the v0.2 EasyEDA guide (make_easyeda_v02_svg.py).

v0.2 = v0.1 (generate_kicad.py) minus the DevKit sockets J3/J4 and the power-only USB-C, plus an
ESP32-S3-WROOM-1U-N16R8 module with its support circuit and a plug-in ZMPT101B module backup.
Pin numbers of the new parts were checked against KiCad 10.0.6's official symbols.
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_kicad as g  # noqa: E402  (only builds the v0.1 parts list on import)

parts = [copy.deepcopy(p) for p in g.parts if p["ref"] not in ("J3", "J4", "J2")]
P = {p["ref"]: p for p in parts}
P["R48"]["pins"]["2"] = "V_ONB"            # on-board stage now goes to JP2, not straight to GPIO9

# move v0.1 schematic positions that sat where the DevKit sockets were
P["J6"]["sch"] = (300, 130)
for i in range(1, 5):
    P[f"H{i}"]["sch"] = (520 + i * 15, 300)


def add(ref, lib_id, value, fp, pins, sch, mpn=""):
    p = dict(ref=ref, lib_id=lib_id, value=value, fp=fp, pins=pins, sch=sch, pcb=None, rot=0, mpn=mpn, note="")
    parts.append(p)
    P[ref] = p


R0805, C0805, C1206 = "Resistor_SMD:R_0805_2012Metric", "Capacitor_SMD:C_0805_2012Metric", "Capacitor_SMD:C_1206_3216Metric"
HDR3 = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"

# ---- USB-C with data (native USB on IO19/IO20) + ESD
add("J2", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C 16P (data)", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    {"A4": "VIN_RAW", "B4": "VIN_RAW", "A9": "VIN_RAW", "B9": "VIN_RAW",
     "A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND",
     "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
     "A8": None, "B8": None}, (30, 120), "HRO TYPE-C-31-M-12 (LCSC C165948)")
add("U4", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
    {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "5": "VIN_RAW", "2": "GND"},
    (95, 140), "USB ESD (LCSC C7519)")
# ---- 3.3 V regulator (the module needs its own 3V3; the DevKit used to provide it)
add("U3", "Regulator_Linear:AMS1117-3.3", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    {"3": "+5V", "2": "+3V3", "1": "GND"}, (150, 85), "LDO 1 A (LCSC C6186), tab = pin 2 = OUT")
add("C50", "Device:C", "10uF", C0805, {"1": "+5V", "2": "GND"}, (135, 95), "LDO input")
add("C51", "Device:C", "22uF", C1206, {"1": "+3V3", "2": "GND"}, (170, 95), "LDO output")
# ---- ESP32-S3 module (pinout = KiCad RF_Module:ESP32-S3-WROOM-1, identical for WROOM-1U)
MOD_PINS = [  # (pin, name, net)
    ("1", "GND", "GND"), ("2", "3V3", "+3V3"), ("3", "EN", "EN"), ("4", "IO4", "CT2_ADC"),
    ("5", "IO5", "CT3_ADC"), ("6", "IO6", "CT4_ADC"), ("7", "IO7", "CT5_ADC"), ("8", "IO15", None),
    ("9", "IO16", None), ("10", "IO17", "I2C_SDA"), ("11", "IO18", "I2C_SCL"), ("12", "IO8", "CT6_ADC"),
    ("13", "IO19 / USB_D-", "USB_DN"), ("14", "IO20 / USB_D+", "USB_DP"), ("15", "IO3", None), ("16", "IO46", None),
    ("17", "IO9", "V_ADC"), ("18", "IO10", "VB_MON"), ("19", "IO11", None), ("20", "IO12", None),
    ("21", "IO13", None), ("22", "IO14", None), ("23", "IO21", None), ("24", "IO47", None),
    ("25", "IO48", None), ("26", "IO45", None), ("27", "IO0", "IO0_BOOT"), ("28", "IO35", None),
    ("29", "IO36", None), ("30", "IO37", None), ("31", "IO38", None), ("32", "IO39", None),
    ("33", "IO40", None), ("34", "IO41", None), ("35", "IO42", None), ("36", "RXD0", "U0RXD"),
    ("37", "TXD0", "U0TXD"), ("38", "IO2", None), ("39", "IO1", "CT1_ADC"), ("40", "GND", "GND"),
    ("41", "GND (pad)", "GND"),
]
add("U2", "RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1U-N16R8", "RF_Module:ESP32-S3-WROOM-1U",
    {p: n for p, _, n in MOD_PINS}, (430, 95), "LCSC C3013946, U.FL antenna")
add("C52", "Device:C", "10uF", C0805, {"1": "+3V3", "2": "GND"}, (500, 45), "at module pin 2")
add("C53", "Device:C", "100nF", C0805, {"1": "+3V3", "2": "GND"}, (512, 45), "at module pin 2")
add("R50", "Device:R", "10k", R0805, {"1": "+3V3", "2": "EN"}, (530, 45), "EN pull-up")
add("C54", "Device:C", "1uF", C0805, {"1": "EN", "2": "GND"}, (545, 45), "EN delay")
add("SW1", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_TL3342", {"1": "EN", "2": "GND"},
    (515, 80), "tactile SMD (LCSC C318884)")
add("R51", "Device:R", "10k", R0805, {"1": "+3V3", "2": "IO0_BOOT"}, (545, 80), "IO0 pull-up")
add("SW2", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_TL3342", {"1": "IO0_BOOT", "2": "GND"},
    (515, 110), "tactile SMD (LCSC C318884)")
add("J7", "Connector_Generic:Conn_01x03", "UART debug", HDR3, {"1": "U0TXD", "2": "U0RXD", "3": "GND"},
    (520, 140), "optional recovery header")
# ---- ZMPT101B plug-in module backup + GPIO9 source selector
add("J8", "Connector_Generic:Conn_01x03", "ZMPT101B module", HDR3, {"1": "+5V", "2": "ZM_OUT", "3": "GND"},
    (330, 240), "blue module: VCC / OUT / GND")
add("R52", "Device:R", "10k 1%", R0805, {"1": "ZM_OUT", "2": "V_MOD"}, (355, 235), "module divider top")
add("R53", "Device:R", "22k 1%", R0805, {"1": "V_MOD", "2": "GND"}, (370, 250), "module divider bottom")
add("C55", "Device:C", "10nF", C0805, {"1": "V_MOD", "2": "GND"}, (382, 250), "103")
add("JP2", "Connector_Generic:Conn_01x03", "V source", HDR3, {"1": "V_ONB", "2": "V_ADC", "3": "V_MOD"},
    (310, 270), "1-2 on-board ZMPT · 2-3 plug-in module")

# PWR_FLAGs: +3V3 is driven by U3's power-output pin now, so it gets no flag
PWR_FLAG_NETS = ["GND", "+3V3A", "+5V", "VIN_RAW", "AC_L", "AC_N"]
