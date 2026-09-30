#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDA Sensores - series temporales MQ + Temp/Humidity
"""
import pathlib, re, glob
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

BASE = pathlib.Path(__file__).parent
DATASET = pathlib.Path("/home/ariel/Desktop/filletd_dataset/dataset")
RESULTS = BASE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 150

SENSOR_COLS = ["MQ3","MQ5","MQ9","MQ135","MQ137","Temperature(°C)","Humidity(%)"]
# Normalizados sin unidades para heatmap
SHORT_COLS = {"MQ3":"MQ3","MQ5":"MQ5","MQ9":"MQ9","MQ135":"MQ135","MQ137":"MQ137","Temperature(°C)":"Temp","Humidity(%)":"Hum"}

# Encontrar todos los CSVs
all_files = sorted(DATASET.glob("day*/sensors/*.csv"))
print(f"[SENSORS] Encontrados {len(all_files)} archivos")
# Debe ser 210
days_map = {}
for p in all_files:
    m = re.search(r"day(\d)", str(p))
    day = int(m.group(1)) if m else -1
    days_map[str(p)] = day

# Leer cada sesión y agregar
records = []
all_series = []  # para analisis temporal largo
for f in all_files:
    # extraer day del path, y fillet id del nombre
    day = int(re.search(r"day(\d)", str(f)).group(1))
    fillet = f.stem  # ej 20260509F1F1
    # intentar extraer Fish/Fillet
    try:
        df = pd.read_csv(f, encoding='utf-8-sig')
        # limpiar columnas
        df.columns = [c.strip() for c in df.columns]
        # Renombrar TVC column que tiene espacio y paréntesis raro
        # Buscar columna TVC
        tvc_col = [c for c in df.columns if 'TVC' in c][0]
        label_col = [c for c in df.columns if 'Label' in c][0]
        # Verificar 120 filas
        n_rows = len(df)
        # Calcular stats por canal
        rec = {"file": str(f), "day": day, "fillet_id": fillet, "n_rows": n_rows, "label": df[label_col].iloc[0], "TVC_log": df[tvc_col].iloc[0]}
        for col in SENSOR_COLS:
            if col not in df.columns:
                # fallback sin simbolos
                alt = [c for c in df.columns if col[:3] in c]
                col_actual = alt[0] if alt else col
            else:
                col_actual = col
            vals = pd.to_numeric(df[col_actual], errors='coerce')
            rec[f"{SHORT_COLS[col]}_mean"] = vals.mean()
            rec[f"{SHORT_COLS[col]}_std"] = vals.std()
            rec[f"{SHORT_COLS[col]}_min"] = vals.min()
            rec[f"{SHORT_COLS[col]}_max"] = vals.max()
            rec[f"{SHORT_COLS[col]}_range"] = vals.max()-vals.min()
            rec[f"{SHORT_COLS[col]}_last"] = vals.iloc[-1]
            rec[f"{SHORT_COLS[col]}_first"] = vals.iloc[0]
            # slope via linear regression (tiempo 0..n-1)
            x = np.arange(len(vals))
            slope = np.polyfit(x, vals, 1)[0] if len(vals)>1 else 0
            rec[f"{SHORT_COLS[col]}_slope"] = slope
        records.append(rec)
        # para series largas, guardar con tiempo
        df['_day'] = day
        df['_fillet'] = fillet
        df['_time'] = np.arange(len(df))
        df['_file'] = str(f)
        all_series.append(df)
    except Exception as e:
        print(f"Error leyendo {f}: {e}")

agg = pd.DataFrame(records)
agg['fresh_spoiled'] = agg['day'].apply(lambda x: 'Fresh' if x<=5 else 'Spoiled')
agg['day_str'] = agg['day'].astype(str)
print(agg.head())
print(agg.describe().T)
print(f"Agg shape {agg.shape}")

# Guardar agregado
agg.to_csv(RESULTS / "sensors_aggregated_per_session.csv", index=False)

# Verificar balance
print(agg['day'].value_counts().sort_index())
print(agg['fresh_spoiled'].value_counts())
print(agg['label'].value_counts())

# --- PLOTS ---

# Plot 1: Conteo por día
fig, ax = plt.subplots(figsize=(8,4))
counts = agg['day'].value_counts().sort_index()
sns.barplot(x=counts.index, y=counts.values, ax=ax, color='#2196F3')
ax.set_title('Sesiones de sensores por día (30/día esperado)')
ax.set_xlabel('Día')
ax.set_ylabel('N sesiones')
for i, v in enumerate(counts.values):
    ax.text(i, v+0.5, str(v), ha='center', fontweight='bold')
plt.tight_layout()
plt.savefig(RESULTS / "sensors_count_by_day.png")
plt.close()

# Plot 2: Boxplots por canal por día (5 MQ + Temp/Hum)
mq_cols_mean = ["MQ3_mean","MQ5_mean","MQ9_mean","MQ135_mean","MQ137_mean"]
for col in mq_cols_mean + ["Temp_mean","Hum_mean"]:
    fig, ax = plt.subplots(figsize=(10,4))
    # Boxplot by day
    sns.boxplot(data=agg, x='day', y=col, hue='fresh_spoiled', dodge=False, palette={'Fresh':'#4CAF50','Spoiled':'#F44336'}, ax=ax)
    # Overlay mean line
    means = agg.groupby('day')[col].mean()
    ax.plot(means.index-1, means.values, color='black', marker='o', linewidth=1.5, label='media diaria')
    ax.set_title(f'{col} - distribución por día (media por sesión, n=30/día)')
    ax.set_xlabel('Día')
    ax.legend()
    plt.tight_layout()
    plt.savefig(RESULTS / f"sensors_boxplot_{col}_by_day.png")
    plt.close()

# Plot 3: Líneas de evolución diaria (todos MQ juntos)
fig, ax = plt.subplots(figsize=(10,5))
means_mq = agg.groupby('day')[mq_cols_mean].mean()
for col in mq_cols_mean:
    ax.plot(means_mq.index, means_mq[col], marker='o', label=col)
ax.axvspan(0.5,5.5,color='green',alpha=0.07)
ax.axvspan(5.5,7.5,color='red',alpha=0.07)
ax.set_xticks(range(1,8))
ax.set_xlabel('Día')
ax.set_ylabel('Valor ADC medio (0-1023)')
ax.set_title('Evolución de media diaria por sensor MQ')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(RESULTS / "sensors_line_mq_daily_mean.png")
plt.close()

# Temp/Humidity line
fig, ax1 = plt.subplots(figsize=(10,4))
means_th = agg.groupby('day')[["Temp_mean","Hum_mean"]].mean()
ax1.plot(means_th.index, means_th["Temp_mean"], marker='o', color='orange', label='Temp °C')
ax1.set_ylabel('Temp °C', color='orange')
ax1.tick_params(axis='y', labelcolor='orange')
ax2 = ax1.twinx()
ax2.plot(means_th.index, means_th["Hum_mean"], marker='s', color='steelblue', label='Hum %')
ax2.set_ylabel('Hum %', color='steelblue')
ax2.tick_params(axis='y', labelcolor='steelblue')
ax1.set_xticks(range(1,8))
ax1.set_xlabel('Día')
ax1.set_title('Temperatura y Humedad - media diaria')
ax1.grid(True, alpha=0.3)
fig.tight_layout()
plt.savefig(RESULTS / "sensors_line_temp_hum_daily.png")
plt.close()

# Plot 4: Fresh vs Spoiled boxplot binario para cada sensor mean
fig, axes = plt.subplots(2,4, figsize=(16,8))
axes = axes.flatten()
cols = mq_cols_mean + ["Temp_mean","Hum_mean","TVC_log"]
for i, col in enumerate(cols):
    ax = axes[i]
    sns.boxplot(data=agg, x='fresh_spoiled', y=col, order=['Fresh','Spoiled'], palette={'Fresh':'#4CAF50','Spoiled':'#F44336'}, ax=ax)
    sns.stripplot(data=agg, x='fresh_spoiled', y=col, order=['Fresh','Spoiled'], color='black', alpha=0.4, size=3, ax=ax, jitter=True)
    ax.set_title(col)
    ax.set_xlabel('')
    if i>=4:
        ax.set_xlabel('Clase')
plt.suptitle('Comparación Fresh (n=150) vs Spoiled (n=60) - medias por sesión', fontsize=14)
plt.tight_layout()
plt.savefig(RESULTS / "sensors_boxplot_fresh_spoiled.png")
plt.close()
# close unused subplot
if len(cols) < len(axes):
    for j in range(len(cols), len(axes)):
        fig.delaxes(axes[j])

# Plot 5: Correlación entre sensores (mean)
corr_cols = mq_cols_mean + ["Temp_mean","Hum_mean","TVC_log"]
corr = agg[corr_cols].corr()
fig, ax = plt.subplots(figsize=(9,7))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True, ax=ax, annot_kws={"size":9})
ax.set_title('Matriz de correlación (medias por sesión, n=210)')
plt.tight_layout()
plt.savefig(RESULTS / "sensors_corr_heatmap.png")
plt.close()

# Plot 6: Correlación con TVC (scatter)
fig, axes = plt.subplots(2,3, figsize=(15,8))
axes=axes.flatten()
for i, col in enumerate(mq_cols_mean + ["Temp_mean"]):
    ax=axes[i]
    sns.scatterplot(data=agg, x='TVC_log', y=col, hue='day', palette='viridis', ax=ax, alpha=0.7, edgecolor='black', linewidth=0.3)
    # regression line
    sns.regplot(data=agg, x='TVC_log', y=col, scatter=False, color='red', ax=ax, line_kws={'lw':1.5})
    # corr value
    r = agg['TVC_log'].corr(agg[col])
    ax.set_title(f'{col} vs TVC (r={r:.2f})')
    ax.legend(title='Día', bbox_to_anchor=(1.05,1), loc='upper left', fontsize=7)
plt.suptitle('Relación Sensor (media) vs TVC log (media diaria)', fontsize=13)
plt.tight_layout()
plt.savefig(RESULTS / "sensors_scatter_vs_tvc.png")
plt.close()
if len(mq_cols_mean+["Temp_mean"]) < len(axes):
    for j in range(len(mq_cols_mean)+1, len(axes)):
        fig.delaxes(axes[j])

# Plot 7: Ejemplo series temporales (120 puntos) - elegir 2 fillets por día y plotear MQ3 y MQ137
# Tomar todos los files, agrupar por day, sample 2
import random
random.seed(42)
fig, axes = plt.subplots(7,1, figsize=(14,16), sharex=True)
concatenated = pd.concat(all_series, ignore_index=True) if all_series else pd.DataFrame()
for day in range(1,8):
    ax = axes[day-1]
    day_files = [f for f in all_files if f"day{day}" in str(f)]
    # sample 2 files
    sample = random.sample(day_files, min(2, len(day_files)))
    for sf in sample:
        df = pd.read_csv(sf, encoding='utf-8-sig')
        df.columns = [c.strip() for c in df.columns]
        # encontrar MQ3 col
        mq3 = [c for c in df.columns if 'MQ3' in c][0]
        ax.plot(pd.to_numeric(df[mq3], errors='coerce').values, alpha=0.7, label=f"{sf.stem}")
    ax.set_ylabel(f'Day{day}\nMQ3 ADC')
    ax.legend(fontsize=6, loc='upper right')
    ax.grid(True, alpha=0.2)
axes[-1].set_xlabel('Tiempo (s, 0-119, 1Hz)')
fig.suptitle('Ejemplos de series temporales MQ3 - 2 sesiones por día (120 puntos cada una)', fontsize=13)
plt.tight_layout()
plt.savefig(RESULTS / "sensors_timeseries_example_MQ3.png")
plt.close()

# Similar for MQ135
fig, axes = plt.subplots(7,1, figsize=(14,16), sharex=True)
for day in range(1,8):
    ax = axes[day-1]
    day_files = [f for f in all_files if f"day{day}" in str(f)]
    sample = random.sample(day_files, min(2, len(day_files)))
    for sf in sample:
        df = pd.read_csv(sf, encoding='utf-8-sig')
        df.columns = [c.strip() for c in df.columns]
        mq = [c for c in df.columns if 'MQ135' in c][0]
        ax.plot(pd.to_numeric(df[mq], errors='coerce').values, alpha=0.7, label=f"{sf.stem}")
    ax.set_ylabel(f'Day{day}\nMQ135')
    ax.legend(fontsize=6, loc='upper right')
    ax.grid(True, alpha=0.2)
axes[-1].set_xlabel('Tiempo (s)')
fig.suptitle('Ejemplos series temporales MQ135 - 2 sesiones por día', fontsize=13)
plt.tight_layout()
plt.savefig(RESULTS / "sensors_timeseries_example_MQ135.png")
plt.close()

# Plot 8: PCA sobre medias MQ + Temp/Hum
features = mq_cols_mean + ["Temp_mean","Hum_mean"]
X = agg[features].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)
agg_pca = agg.copy()
agg_pca['PC1'] = X_pca[:,0]
agg_pca['PC2'] = X_pca[:,1]

fig, ax = plt.subplots(figsize=(8,6))
# by fresh/spoiled
sns.scatterplot(data=agg_pca, x='PC1', y='PC2', hue='fresh_spoiled', style='day', palette={'Fresh':'#4CAF50','Spoiled':'#F44336'}, s=80, alpha=0.8, edgecolor='black', linewidth=0.5, ax=ax)
ax.set_title(f'PCA sensores (medias) - PC1 {pca.explained_variance_ratio_[0]:.1%}, PC2 {pca.explained_variance_ratio_[1]:.1%}')
ax.legend(bbox_to_anchor=(1.05,1), loc='upper left')
plt.tight_layout()
plt.savefig(RESULTS / "sensors_pca_fresh_spoiled.png")
plt.close()

# PCA by day
fig, ax = plt.subplots(figsize=(8,6))
sns.scatterplot(data=agg_pca, x='PC1', y='PC2', hue='day', palette='viridis', s=80, alpha=0.8, edgecolor='black', linewidth=0.5, ax=ax)
ax.set_title(f'PCA sensores coloreado por día (n=210)')
plt.tight_layout()
plt.savefig(RESULTS / "sensors_pca_by_day.png")
plt.close()

# Loadings
loadings = pd.DataFrame(pca.components_.T, index=features, columns=['PC1','PC2'])
loadings.to_csv(RESULTS / "sensors_pca_loadings.csv")
# Plot loadings
fig, ax = plt.subplots(figsize=(8,6))
for i, feat in enumerate(features):
    ax.arrow(0,0, loadings.loc[feat,'PC1']*3, loadings.loc[feat,'PC2']*3, color='r', alpha=0.8, head_width=0.05)
    ax.text(loadings.loc[feat,'PC1']*3.2, loadings.loc[feat,'PC2']*3.2, feat, fontsize=10, ha='center', va='center', color='darkred')
# also plot points
ax.scatter(X_pca[:,0], X_pca[:,1], alpha=0.15, color='gray')
ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})')
ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})')
ax.set_title('PCA Loadings - sensores')
ax.grid(True, alpha=0.3)
ax.set_xlim(-4,4)
ax.set_ylim(-4,4)
plt.tight_layout()
plt.savefig(RESULTS / "sensors_pca_loadings.png")
plt.close()

# Varianza explicada
fig, ax = plt.subplots(figsize=(6,4))
pca_full = PCA().fit(X_scaled)
ax.bar(range(1,len(pca_full.explained_variance_ratio_)+1), pca_full.explained_variance_ratio_, color='#2196F3')
ax.plot(range(1,len(pca_full.explained_variance_ratio_)+1), np.cumsum(pca_full.explained_variance_ratio_), marker='o', color='red', label='acumulada')
ax.set_xlabel('Componente')
ax.set_ylabel('Varianza explicada')
ax.set_title('PCA varianza explicada (7 features)')
ax.legend()
plt.tight_layout()
plt.savefig(RESULTS / "sensors_pca_variance.png")
plt.close()

# Estadísticos por day para TVC correlation
corr_with_tvc = agg[corr_cols].corr()['TVC_log'].sort_values(ascending=False)
corr_with_tvc.to_csv(RESULTS / "sensors_corr_with_tvc.csv")

# Distribucion de std y slope (variabilidad intra-sesión)
fig, axes = plt.subplots(1,2, figsize=(12,4))
# std
std_cols = [c for c in agg.columns if '_std' in c]
mean_std_by_day = agg.groupby('day')[std_cols].mean()
mean_std_by_day.columns = [c.replace('_std','') for c in mean_std_by_day.columns]
mean_std_by_day.plot(kind='bar', ax=axes[0])
axes[0].set_title('Variabilidad intra-sesión (std medio) por día')
axes[0].set_xlabel('Día')
axes[0].legend(fontsize=8)
# slope
slope_cols = [c for c in agg.columns if '_slope' in c]
mean_slope_by_day = agg.groupby('day')[slope_cols].mean()
mean_slope_by_day.columns = [c.replace('_slope','') for c in mean_slope_by_day.columns]
mean_slope_by_day.plot(kind='bar', ax=axes[1])
axes[1].set_title('Pendiente media por sesión (drift 120s) por día')
axes[1].set_xlabel('Día')
plt.tight_layout()
plt.savefig(RESULTS / "sensors_std_slope_by_day.png")
plt.close()

print(f"[SENSORS] Done. {len(agg)} sesiones agregadas")
print(agg['day'].value_counts().sort_index().to_string())
print(corr_with_tvc)
