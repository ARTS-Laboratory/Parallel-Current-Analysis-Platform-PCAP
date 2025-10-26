# -*- coding: utf-8 -*-
"""
Created on Thu Oct  2 23:04:45 2025

@author: Malichi Flemming II
"""

import os
import csv
import time
import random
from datetime import datetime

# Output CSV file
CSV_FILE = os.path.join(os.path.dirname(__file__), "battery_cycle_data.csv")
print('🔧 Battery simulation started', flush=True)

# Battery parameters
capacity_ah = 3.0
voltage_max = 4.2
voltage_min = 2.5
current_charge = 3.0
current_discharge = -3.0
cccv_threshold = 4.1

# Initialize state for 3 batteries
batteries = []
for i in range(3):
    batteries.append({
        "voltage": voltage_min,
        "soc": 0.0,
        "mode": "charge",
        "cycle": 1
    })

# Create CSV header
header = ["Timestamp"]
for i in range(3):
    prefix = f"Cell_{i+1}"
    header += [
        f"Cycle_{i+1}", f"Mode_{i+1}", f"Voltage_{i+1}", f"Current_{i+1}",
        f"SOC_{i+1}", f"Strain_{i+1}", f"Temp_{i+1}"
    ]

with open(CSV_FILE, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(header)

try:
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp]

        for i, cell in enumerate(batteries):
            # Charging logic
            if cell["mode"] == "charge":
                if cell["voltage"] < cccv_threshold:
                    cell["voltage"] += 0.01
                    current = current_charge
                else:
                    cell["voltage"] += 0.002
                    current = max(0.3, current_charge * (1 - (cell["voltage"] - cccv_threshold) / (voltage_max - cccv_threshold)))

                cell["soc"] = min(1.0, cell["soc"] + 0.005)

                if cell["voltage"] >= voltage_max:
                    cell["voltage"] = voltage_max
                    cell["mode"] = "discharge"
                    print(f"🔄 Cell {i+1} switching to discharge (Cycle {cell['cycle']})")

            elif cell["mode"] == "discharge":
                cell["voltage"] -= 0.01
                current = current_discharge
                cell["soc"] = max(0.0, cell["soc"] - 0.005)

                if cell["voltage"] <= voltage_min:
                    cell["voltage"] = voltage_min
                    cell["mode"] = "charge"
                    cell["cycle"] += 1
                    print(f"🔄 Cell {i+1} starting new charge cycle ({cell['cycle']})")

            # Add noise
            cell["voltage"] += random.uniform(-0.005, 0.005)

            # Simulate strain and temperature
            strain = round(random.uniform(0.1, 0.5), 3)
            temperature = round(25 + 20 * cell["soc"] + random.uniform(-2, 2), 2)

            # Append to row
            row += [
                cell["cycle"], cell["mode"],
                round(cell["voltage"], 3), round(current, 2),
                round(cell["soc"] * 100, 1), strain, temperature
            ]

        # Write row to CSV
        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(row)

        time.sleep(1)

except KeyboardInterrupt:
    print("🛑 Simulation interrupted. Cleaning up...")