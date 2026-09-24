# Breadboard wiring: single SCT-013-000 channel on the ESP32-S3

| From | To | Notes |
|---|---|---|
| ESP32-S3 **3V3** | R1 (10 k), top end | |
| R1 bottom end | **BIAS** row | |
| **BIAS** row | R2 (10 k), top end | |
| R2 bottom end | ESP32-S3 **GND** | |
| **BIAS** row | 10 µF capacitor (+) | Optional but recommended; (−) to GND |
| **BIAS** row | CT lead A (jack **sleeve**) | |
| CT lead B (jack **tip**) | **ADC** row | |
| 22 Ω burden | between **BIAS** row and **ADC** row | directly across the CT leads |
| **ADC** row | ESP32-S3 **GPIO1** | or any ADC1 pin GPIO1..10 (not GPIO3); set `ct_gpio` to match |

Checks before you clamp anything (USB power only):

1. Multimeter DC V from BIAS to GND should read about 1.65 V.
2. Measure the resistance across the CT jack with the CT plugged in. It should read about 15 to 22 Ω
   (the 22 Ω burden in parallel with the CT winding's DC resistance). If it reads open-circuit, the burden isn't connected. **Do not clamp.**
3. In HA, **CT Bias Voltage** should match your meter to within about 20 mV, and **CT AC RMS** should be low.

Only after those checks, clamp the CT around **one** insulated conductor.
