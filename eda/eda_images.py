#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDA Imágenes - features de color, tamaños, ejemplos visuales
"""
import pathlib, re, os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
from tqdm import tqdm

BASE = pathlib.Path(__file__).parent
DATASET = pathlib.Path("/home/ariel/Desktop/filletd_dataset/dataset")
RESULTS = BASE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 150

# Recolectar JPGs
jpg_files = sorted(DATASET.glob("day*/jpg/*/*.jpg"))
print(f"[IMAGES] JPGs encontrados: {len(jpg_files)}")  # esperado 820
raw_files = sorted(DATASET.glob("day*/raw/*.CR2"))
print(f"[IMAGES] RAWs encontrados: {len(raw_files)}")

# Extraer metadata y features
records = []
# Para ahorrar tiempo, podriamos procesar todos; 820 es manejable
for f in tqdm(jpg_files, desc="Procesando JPGs"):
    try:
        # day del path
        day = int(re.search(r"day(\d)", str(f)).group(1))
        surface = f.parent.name  # F o S
        stem = f.stem  # ej 20260509F1F10M
        # fillet id: extraer F... parte
        # Formato: 20260509F1F10M -> fillet = F1F10
        m = re.search(r"(\d{8})(F\d+F\d+)([MS])", stem)
        if m:
            date_str = m.group(1)
            fillet_id = m.group(2)
            surf_code = m.group(3)  # M o S
            # Mapear M->F (flesh), S->S (skin) según README? Pero carpeta F/S ya indica
            # Usaremos carpeta como surface ground truth
        else:
            date_str = stem[:8]
            fillet_id = stem[8:-1]
            surf_code = stem[-1]
        # file size
        fsize = f.stat().st_size
        # image features via PIL
        with Image.open(f) as im:
            w, h = im.size
            mode = im.mode
            # Convert to RGB if needed
            if im.mode != 'RGB':
                im = im.convert('RGB')
            arr = np.array(im)
            # arr shape HxWx3
            r_mean = arr[:,:,0].mean()
            g_mean = arr[:,:,1].mean()
            b_mean = arr[:,:,2].mean()
            r_std = arr[:,:,0].std()
            g_std = arr[:,:,1].std()
            b_std = arr[:,:,2].std()
            # brightness: luminance Rec 709
            lum = (0.2126*arr[:,:,0] + 0.7152*arr[:,:,1] + 0.0722*arr[:,:,2]).mean()
            lum_std = (0.2126*arr[:,:,0] + 0.7152*arr[:,:,1] + 0.0722*arr[:,:,2]).std()
            # HSV via colorsys aprox o PIL convert
            # Usaremos numpy simple: convertir a HSV mediante matplotlib.colors
            # Más rápido: usar PIL convert to HSV
            hsv_im = im.convert('HSV')
            hsv_arr = np.array(hsv_im)
            h_mean = hsv_arr[:,:,0].mean() * 360/255  # 0-360
            s_mean = hsv_arr[:,:,1].mean() * 100/255  # 0-100
            v_mean = hsv_arr[:,:,2].mean() * 100/255
            # Histograma rojo verde comparacion
            # Ratio R/G, R/B
            rg_ratio = r_mean / (g_mean+1e-6)
            rb_ratio = r_mean / (b_mean+1e-6)
        fresh = 'Fresh' if day<=5 else 'Spoiled'
        records.append({
            "path": str(f),
            "day": day,
            "surface_folder": surface,
            "surf_code": surf_code,
            "fillet_id": fillet_id,
            "date_str": date_str,
            "file_size_bytes": fsize,
            "file_size_mb": fsize/1024/1024,
            "width": w,
            "height": h,
            "mp": w*h/1e6,
            "aspect": w/h if h!=0 else 0,
            "R_mean": r_mean,
            "G_mean": g_mean,
            "B_mean": b_mean,
            "R_std": r_std,
            "G_std": g_std,
            "B_std": b_std,
            "brightness": lum,
            "brightness_std": lum_std,
            "H_mean": h_mean,
            "S_mean": s_mean,
            "V_mean": v_mean,
            "R_G_ratio": rg_ratio,
            "R_B_ratio": rb_ratio,
            "fresh_spoiled": fresh
        })
    except Exception as e:
        print(f"Error {f}: {e}")

df = pd.DataFrame(records)
df.to_csv(RESULTS / "images_features.csv", index=False)
print(df.head())
print(df.describe(include='all').T)
print(df['surface_folder'].value_counts())
print(df['day'].value_counts().sort_index())
print(df.groupby(['day','surface_folder']).size())

# También guardar raw stats
raw_records=[]
for f in raw_files:
    day = int(re.search(r"day(\d)", str(f)).group(1))
    raw_records.append({"path":str(f),"day":day,"size_mb":f.stat().st_size/1024/1024, "stem":f.stem})
raw_df=pd.DataFrame(raw_records)
raw_df.to_csv(RESULTS / "raw_files_stats.csv", index=False)
print(raw_df.groupby('day').size())
print(raw_df.describe())

# --- PLOTS ---

# Plot 1: Conteo por día y superficie
fig, ax = plt.subplots(figsize=(10,4))
counts = df.groupby(['day','surface_folder']).size().unstack(fill_value=0)
counts.plot(kind='bar', ax=ax, color=['#FF7043','#4DB6AC'])
ax.set_title('Conteo de imágenes JPG por día y superficie (F=Flesh, S=Skin)')
ax.set_xlabel('Día')
ax.set_ylabel('N imágenes')
ax.legend(title='Superficie')
for c in ax.containers:
    ax.bar_label(c, fontsize=9)
plt.tight_layout()
plt.savefig(RESULTS / "images_count_by_day_surface.png")
plt.close()

# Plot 2: File size distribution
fig, axes = plt.subplots(1,2, figsize=(12,4))
sns.histplot(df['file_size_mb'], bins=30, kde=True, color='#607D8B', ax=axes[0])
axes[0].set_title('Distribución tamaño JPG (MB)')
axes[0].set_xlabel('MB')
sns.boxplot(data=df, x='day', y='file_size_mb', hue='surface_folder', palette={'F':'#FF7043','S':'#4DB6AC'}, ax=axes[1])
axes[1].set_title('Tamaño JPG por día y superficie')
plt.tight_layout()
plt.savefig(RESULTS / "images_filesize_dist.png")
plt.close()

# Plot 3: Resolución
fig, ax = plt.subplots(figsize=(8,4))
# Scatter width vs height coloreado por day
sns.scatterplot(data=df, x='width', y='height', hue='day', palette='viridis', alpha=0.6, ax=ax, s=30, edgecolor='black', linewidth=0.2)
ax.set_title(f'Resolución imágenes JPG (n={len(df)}) width vs height')
plt.tight_layout()
plt.savefig(RESULTS / "images_resolution_scatter.png")
plt.close()
# Boxplot MP por day
fig, ax = plt.subplots(figsize=(10,4))
sns.boxplot(data=df, x='day', y='mp', hue='surface_folder', palette={'F':'#FF7043','S':'#4DB6AC'}, ax=ax)
ax.set_title('Megapíxeles por día')
plt.tight_layout()
plt.savefig(RESULTS / "images_mp_by_day.png")
plt.close()

# Plot 4: RGB means por día (líneas)
fig, axes = plt.subplots(1,3, figsize=(15,4), sharey=True)
for i, col in enumerate(['R_mean','G_mean','B_mean']):
    ax = axes[i]
    means = df.groupby('day')[col].mean()
    stds = df.groupby('day')[col].std()
    ax.errorbar(means.index, means.values, yerr=stds.values, marker='o', capsize=4, color='#1976D2')
    ax.set_title(col)
    ax.set_xlabel('Día')
    ax.set_xticks(range(1,8))
    ax.axvspan(0.5,5.5,color='green',alpha=0.07)
    ax.axvspan(5.5,7.5,color='red',alpha=0.07)
    ax.grid(True, alpha=0.3)
plt.suptitle('Evolución media RGB por día (todas superficies)')
plt.tight_layout()
plt.savefig(RESULTS / "images_rgb_mean_by_day.png")
plt.close()

# Plot 5: RGB por superficie F vs S
fig, axes = plt.subplots(1,3, figsize=(15,5))
for i, col in enumerate(['R_mean','G_mean','B_mean']):
    ax = axes[i]
    sns.boxplot(data=df, x='surface_folder', y=col, order=['F','S'], palette={'F':'#FF7043','S':'#4DB6AC'}, ax=ax)
    sns.stripplot(data=df, x='surface_folder', y=col, order=['F','S'], color='black', alpha=0.2, size=2, ax=ax, jitter=True)
    ax.set_title(col)
fig.suptitle('Comparación color Flesh (F) vs Skin (S)')
plt.tight_layout()
plt.savefig(RESULTS / "images_rgb_flesh_vs_skin.png")
plt.close()

# Plot 6: Brightness por día
fig, ax = plt.subplots(figsize=(10,4))
sns.boxplot(data=df, x='day', y='brightness', hue='surface_folder', palette={'F':'#FF7043','S':'#4DB6AC'}, ax=ax)
# overlay mean
means = df.groupby('day')['brightness'].mean()
ax.plot(means.index-1, means.values, color='black', marker='o', linestyle='--', label='media global')
ax.set_title('Brillo (luminancia) por día y superficie')
ax.legend()
plt.tight_layout()
plt.savefig(RESULTS / "images_brightness_by_day.png")
plt.close()

# Brightness fresh vs spoiled
fig, ax = plt.subplots(figsize=(6,4))
sns.boxplot(data=df, x='fresh_spoiled', y='brightness', order=['Fresh','Spoiled'], palette={'Fresh':'#4CAF50','Spoiled':'#F44336'}, ax=ax)
sns.stripplot(data=df, x='fresh_spoiled', y='brightness', order=['Fresh','Spoiled'], color='black', alpha=0.3, size=3, ax=ax, jitter=True)
ax.set_title('Brillo Fresh vs Spoiled')
plt.tight_layout()
plt.savefig(RESULTS / "images_brightness_fresh_spoiled.png")
plt.close()

# Plot 7: HSV por día
fig, axes = plt.subplots(1,3, figsize=(15,4))
for i, col in enumerate(['H_mean','S_mean','V_mean']):
    ax = axes[i]
    means = df.groupby('day')[col].mean()
    ax.plot(means.index, means.values, marker='o', color='#00796B')
    ax.set_title(col)
    ax.set_xlabel('Día')
    ax.set_xticks(range(1,8))
    ax.grid(True, alpha=0.3)
    # boxplot overlay?
plt.suptitle('HSV medios por día')
plt.tight_layout()
plt.savefig(RESULTS / "images_hsv_by_day.png")
plt.close()

# Plot 8: Correlation heatmap de features de imagen
feat_cols = ['R_mean','G_mean','B_mean','brightness','H_mean','S_mean','V_mean','R_G_ratio','R_B_ratio','file_size_mb']
corr = df[feat_cols].corr()
fig, ax = plt.subplots(figsize=(10,8))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax, annot_kws={"size":8})
ax.set_title('Correlación entre features de imagen')
plt.tight_layout()
plt.savefig(RESULTS / "images_corr_features.png")
plt.close()

# Plot 9: Image features vs brightness scatter coloured by day
fig, ax = plt.subplots(figsize=(8,6))
sns.scatterplot(data=df, x='R_mean', y='G_mean', hue='day', palette='viridis', alpha=0.6, ax=ax, s=40, edgecolor='black', linewidth=0.2)
ax.set_title('R_mean vs G_mean coloreado por día')
plt.tight_layout()
plt.savefig(RESULTS / "images_r_vs_g_by_day.png")
plt.close()

# Plot 10: Grid de ejemplos - elegir un fillet longitudinal que aparezca todos los días
# Buscar fillets que tengan 7 apariciones para F y S
from collections import Counter
# Contar fillet_id por day para F y S
# Intentar encontrar un fillet con 7 días en F
fillet_counts = df[df['surface_folder']=='F'].groupby('fillet_id')['day'].nunique()
full_f = fillet_counts[fillet_counts==7].index.tolist()
print(f"Fillets con 7 días en F: {full_f[:5]} {len(full_f)}")
fillet_counts_s = df[df['surface_folder']=='S'].groupby('fillet_id')['day'].nunique()
full_s = fillet_counts_s[fillet_counts_s==7].index.tolist()
print(f"Fillets con 7 días en S: {full_s[:5]} {len(full_s)}")

# Elegir uno
example_fillet = full_f[0] if full_f else df['fillet_id'].iloc[0]
print(f"Ejemplo fillet: {example_fillet}")

# Crear grid 2x7 (F y S)
fig, axes = plt.subplots(2,7, figsize=(16,5))
fig.suptitle(f'Ejemplo longitudinal - Fillet {example_fillet} (F=Flesh arriba, S=Skin abajo) - 7 días', fontsize=12)
for day in range(1,8):
    for row, surf in enumerate(['F','S']):
        ax = axes[row, day-1]
        # buscar imagen de ese fillet, day, surface
        cand = df[(df['fillet_id']==example_fillet) & (df['day']==day) & (df['surface_folder']==surf)]
        if not cand.empty:
            path = cand.iloc[0]['path']
            try:
                im = Image.open(path)
                im.thumbnail((400,400))
                ax.imshow(im)
                ax.set_title(f'Day{day} {surf}', fontsize=9)
            except Exception as e:
                ax.text(0.5,0.5, str(e), ha='center')
        else:
            ax.text(0.5,0.5, 'No image', ha='center')
            ax.set_title(f'Day{day} {surf} missing', fontsize=8)
        ax.axis('off')
plt.tight_layout()
plt.savefig(RESULTS / f"images_grid_example_{example_fillet}.png")
plt.close()

# Grid adicional: 1 imagen aleatoria por día (misma estética)
import random
random.seed(0)
fig, axes = plt.subplots(2,7, figsize=(16,5))
fig.suptitle('Muestras aleatorias por día - Flesh (arriba) y Skin (abajo)', fontsize=12)
for day in range(1,8):
    for row, surf in enumerate(['F','S']):
        ax = axes[row, day-1]
        subset = df[(df['day']==day) & (df['surface_folder']==surf)]
        if not subset.empty:
            sample = subset.sample(1, random_state=day*10+row).iloc[0]
            path = sample['path']
            try:
                im = Image.open(path)
                im.thumbnail((400,400))
                ax.imshow(im)
                ax.set_title(f'D{day} {sample["fillet_id"]}', fontsize=7)
            except:
                pass
        ax.axis('off')
plt.tight_layout()
plt.savefig(RESULTS / "images_grid_random_by_day.png")
plt.close()

# Plot 11: R/G ratio y R/B ratio por día (indicadores de enrojecimiento)
fig, axes = plt.subplots(1,2, figsize=(12,4))
for i, col in enumerate(['R_G_ratio','R_B_ratio']):
    ax = axes[i]
    sns.boxplot(data=df, x='day', y=col, hue='surface_folder', palette={'F':'#FF7043','S':'#4DB6AC'}, ax=ax)
    ax.set_title(col)
plt.tight_layout()
plt.savefig(RESULTS / "images_ratios_by_day.png")
plt.close()

# Stats para informe
fresh_bri = df[df['fresh_spoiled']=='Fresh']['brightness'].mean()
spoiled_bri = df[df['fresh_spoiled']=='Spoiled']['brightness'].mean()
print(f"Brightness Fresh {fresh_bri:.2f} vs Spoiled {spoiled_bri:.2f} diff {spoiled_bri-fresh_bri:.2f}")

# Guardar missing analysis
missing = []
for day in range(1,8):
    for surf in ['F','S']:
        count = len(df[(df['day']==day) & (df['surface_folder']==surf)])
        expected = 59
        missing.append({"day":day, "surface":surf, "count":count, "missing":expected-count, "expected":expected})
missing_df = pd.DataFrame(missing)
missing_df.to_csv(RESULTS / "images_missing_by_day.csv", index=False)
print(missing_df)

print(f"[IMAGES] Done. Features: {df.shape}")
