#!/usr/bin/env python3
import subprocess, pathlib, sys
BASE = pathlib.Path(__file__).parent
VENV_PY = pathlib.Path("/home/ariel/Desktop/filletd_dataset/.venv/bin/python")
steps = ["eda_micro.py", "eda_sensors.py", "eda_images.py", "generate_report.py"]
for s in steps:
    print(f"\n=== Ejecutando {s} ===")
    ret = subprocess.run([str(VENV_PY), str(BASE / s)], cwd=str(BASE))
    if ret.returncode != 0:
        print(f"ERROR en {s} (exit {ret.returncode})")
        sys.exit(ret.returncode)
print("\n=== EDA COMPLETO ===")
print("Revisa eda/informe.md y eda/results/")
