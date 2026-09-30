#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDA Microbiología - TVC
Genera: stats, plots, tablas para tvc_individual_measurements.csv
"""
import pathlib, sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

BASE = pathlib.Path(__file__).parent
DATASET = pathlib.Path("/home/ariel/Desktop/filletd_dataset/dataset")
RESULTS = BASE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.dpi'] = 150

CSV = DATASET / "tvc_individual_measurements.csv"
print(f"[MICRO] Leyendo {CSV}")
df = pd.read_csv(CSV, encoding='utf-8-sig')
# Normalizar columnas por si BOM raro
df.columns = [c.strip() for c in df.columns]
print(df.head())
print(df.info())
print(df.describe(include='all'))

# Asegurar tipos
df['Storage_Day'] = df['Storage_Day'].astype(int)
df['TVC_log10_CFU_g'] = pd.to_numeric(df['TVC_log10_CFU_g'], errors='coerce')
df['Fresh_Spoiled'] = df['Storage_Day'].apply(lambda x: 'Fresh' if x <=5 else 'Spoiled')
df['Label'] = df['Fresh_Spoiled']

# Resumen por día
summary = df.groupby('Storage_Day').agg(
    n=('TVC_log10_CFU_g','count'),
    mean_log=('TVC_log10_CFU_g','mean'),
    std_log=('TVC_log10_CFU_g','std'),
    min_log=('TVC_log10_CFU_g','min'),
    max_log=('TVC_log10_CFU_g','max'),
    mean_cfu=('TVC_CFU_g','mean'),
).reset_index()
summary['status'] = summary['Storage_Day'].apply(lambda x: 'Fresh' if x<=5 else 'Spoiled')
summary.to_csv(RESULTS / "tvc_summary_by_day.csv", index=False)
print(summary)

# Global stats
overall = df.groupby('Fresh_Spoiled').agg(
    n=('TVC_log10_CFU_g','count'),
    mean=('TVC_log10_CFU_g','mean'),
    std=('TVC_log10_CFU_g','std'),
    min=('TVC_log10_CFU_g','min'),
    max=('TVC_log10_CFU_g','max'),
)
overall.to_csv(RESULTS / "tvc_summary_by_class.csv")
print(overall)

# Plot 1: Boxplot + strip por día con threshold
fig, ax = plt.subplots(figsize=(10,5))
sns.boxplot(data=df, x='Storage_Day', y='TVC_log10_CFU_g', hue='Fresh_Spoiled', dodge=False, ax=ax, palette={'Fresh':'#4CAF50','Spoiled':'#F44336'})
sns.stripplot(data=df, x='Storage_Day', y='TVC_log10_CFU_g', color='black', size=8, alpha=0.8, ax=ax, jitter=True)
ax.axhline(7.0, color='red', linestyle='--', linewidth=2, label='Umbral 7 log CFU/g')
ax.set_title('TVC log10 CFU/g por día de almacenamiento (n=3/día)')
ax.set_xlabel('Día de almacenamiento')
ax.set_ylabel('TVC log10 CFU/g')
ax.legend()
plt.tight_layout()
plt.savefig(RESULTS / "micro_boxplot_by_day.png")
plt.close()

# Plot 2: Línea media diaria + intervalo min-max y threshold
fig, ax = plt.subplots(figsize=(10,5))
ax.plot(summary['Storage_Day'], summary['mean_log'], marker='o', linewidth=2.5, color='#1976D2', label='Media diaria')
ax.fill_between(summary['Storage_Day'], summary['min_log'], summary['max_log'], alpha=0.2, color='#1976D2', label='Rango min-max')
# Error bars std
ax.errorbar(summary['Storage_Day'], summary['mean_log'], yerr=summary['std_log'], fmt='none', ecolor='gray', capsize=4)
ax.axhline(7.0, color='red', linestyle='--', linewidth=2, label='Umbral 7.0')
# Shade fresh/spoiled
ax.axvspan(0.5, 5.5, color='green', alpha=0.08, label='Fresh (1-5)')
ax.axvspan(5.5, 7.5, color='red', alpha=0.08, label='Spoiled (6-7)')
ax.set_xticks(range(1,8))
ax.set_xlabel('Día de almacenamiento')
ax.set_ylabel('TVC log10 CFU/g')
ax.set_title('Evolución de TVC - media diaria con umbral Fresh/Spoiled')
ax.legend(loc='upper left')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(RESULTS / "micro_line_mean_by_day.png")
plt.close()

# Plot 3: Histograma log TVC
fig, ax = plt.subplots(figsize=(8,4))
sns.histplot(df['TVC_log10_CFU_g'], bins=12, kde=True, color='#607D8B', ax=ax)
ax.axvline(7.0, color='red', linestyle='--', label='Umbral')
ax.set_title('Distribución de TVC log10 (21 muestras)')
ax.set_xlabel('TVC log10 CFU/g')
ax.legend()
plt.tight_layout()
plt.savefig(RESULTS / "micro_hist_log.png")
plt.close()

# Plot 4: Boxplot binario Fresh vs Spoiled
fig, ax = plt.subplots(figsize=(6,5))
sns.boxplot(data=df, x='Fresh_Spoiled', y='TVC_log10_CFU_g', order=['Fresh','Spoiled'], palette={'Fresh':'#4CAF50','Spoiled':'#F44336'}, ax=ax)
sns.stripplot(data=df, x='Fresh_Spoiled', y='TVC_log10_CFU_g', order=['Fresh','Spoiled'], color='black', size=8, ax=ax, jitter=True)
ax.axhline(7.0, color='red', linestyle='--')
ax.set_title('TVC Fresh vs Spoiled (15 vs 6 muestras)')
plt.tight_layout()
plt.savefig(RESULTS / "micro_boxplot_fresh_spoiled.png")
plt.close()

# Plot 5: CFU vs log scatter
fig, ax = plt.subplots(figsize=(8,5))
sns.scatterplot(data=df, x='TVC_CFU_g', y='TVC_log10_CFU_g', hue='Fresh_Spoiled', style='Storage_Day', s=120, palette={'Fresh':'#4CAF50','Spoiled':'#F44336'}, ax=ax)
ax.set_xscale('log')
ax.set_title('TVC CFU/g (log scale) vs log10')
ax.set_xlabel('TVC CFU/g (log scale)')
plt.tight_layout()
plt.savefig(RESULTS / "micro_scatter_cfu_log.png")
plt.close()

# Tabla resumen para MD
summary_md = summary.to_markdown(index=False)

with open(RESULTS / "micro_stats.txt", "w") as f:
    f.write(f"TOTAL MUESTRAS: {len(df)}\n")
    f.write(f"Fresh (1-5): {(df['Fresh_Spoiled']=='Fresh').sum()}  Spoiled (6-7): {(df['Fresh_Spoiled']=='Spoiled').sum()}\n")
    f.write("\nSUMMARY BY DAY:\n")
    f.write(summary.to_string(index=False))
    f.write("\n\nOVERALL BY CLASS:\n")
    f.write(overall.to_string())

print(f"[MICRO] Done. Figuras guardadas en {RESULTS}")
