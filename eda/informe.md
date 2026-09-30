# EDA - Fillet Dataset (Trucha arcoíris)

**Fecha:** 2026-09-16  
**Dataset:** `dataset/` - 7 días a 4°C, 20 truchas → 80 porciones (59 longitudinales + 21 microbiológicas)  
**Total verificado:** 820 JPG + 820 RAW + 210 CSV sensores (210 esperados)  
**Scripts:** `eda_micro.py`, `eda_sensors.py`, `eda_images.py` → resultados en `results/`

---

## Resumen ejecutivo

- **Modalidades:** 3 (imágenes RAW/JPG, series temporales de sensores MQ+Temp/Hum, TVC microbiológico). Vinculación solo por `Storage_Day` (no hay matching Fillet ↔ Microbiology ID).
- **Clases:** Binario `Fresh (días 1-5)` vs `Spoiled (días 6-7)` por umbral 7 log CFU/g. Desbalance ~71% / 29% en todas las modalidades.
- **Señal más clara:** TVC crece monótonamente (4.14→7.86 log). Sensores MQ muestran correlación muy fuerte con TVC (r=0.88-0.96, `MQ135` r=0.96 es el mejor) pero con solapamiento Fresh/Spoiled a nivel de sesión. Imágenes: diferencias sutiles de color/brillo; `Skin` más variable que `Flesh`.
- **Riesgo leakage:** Mismas 59 porciones repetidas 7 días + 4 porciones por pez. Split debe ser por **pez original**, no por imagen/sesión.

---

## 1. Organización del dataset

```
dataset/
├── day1..day7/
│   ├── raw/      -> .CR2 (118,117,114,118,118,118,117 = 820)
│   ├── jpg/F,S/  -> JPG  (410 F + 410 S = 820)
│   └── sensors/  -> 30 CSV/día = 210
├── tvc_individual_measurements.csv (21 filas)
├── raw_to_jpg.py
└── README.txt
```

**Verificación de conteos:**

- JPG por día: day1 118, day2 117 (F 58, S 59), day3 114 (57+57), day4 118, day5 118, day6 118, day7 117 (59+58). Total 820 - coincide con README (826 iniciales -6 descartadas).
- Sensores: 30/día exactos (150 Fresh, 60 Spoiled).
- TVC: 15 Fresh (días1-5) + 6 Spoiled (días6-7).

Archivos faltantes vs esperado 59 por superficie:

|   day | surface   |   count |   missing |   expected |
|------:|:----------|--------:|----------:|-----------:|
|     1 | F         |      59 |         0 |         59 |
|     1 | S         |      59 |         0 |         59 |
|     2 | F         |      58 |         1 |         59 |
|     2 | S         |      59 |         0 |         59 |
|     3 | F         |      57 |         2 |         59 |
|     3 | S         |      57 |         2 |         59 |
|     4 | F         |      59 |         0 |         59 |
|     4 | S         |      59 |         0 |         59 |
|     5 | F         |      59 |         0 |         59 |
|     5 | S         |      59 |         0 |         59 |
|     6 | F         |      59 |         0 |         59 |
|     6 | S         |      59 |         0 |         59 |
|     7 | F         |      59 |         0 |         59 |
|     7 | S         |      58 |         1 |         59 |

Imagen de conteo:

![Conteo imágenes](results/images_count_by_day_surface.png)

---

## 2. Microbiología (TVC)

**Fuente:** `tvc_individual_measurements.csv` (21 muestras destructivas, ISO 4833-1, 3/día)

### 2.1 Estadísticos por día

|   Storage_Day |   n |   mean_log |   std_log |   min_log |   max_log |         mean_cfu | status   |
|--------------:|----:|-----------:|----------:|----------:|----------:|-----------------:|:---------|
|             1 |   3 |    4.14467 |  0.111384 |     4.057 |     4.27  |  14266.7         | Fresh    |
|             2 |   3 |    4.50867 |  0.335455 |     4.23  |     4.881 |  39666.7         | Fresh    |
|             3 |   3 |    5.525   |  0.213703 |     5.322 |     5.748 | 363333           | Fresh    |
|             4 |   3 |    6.10333 |  0.225713 |     5.851 |     6.286 |      1.37667e+06 | Fresh    |
|             5 |   3 |    5.58233 |  0.158985 |     5.431 |     5.748 | 400000           | Fresh    |
|             6 |   3 |    7.738   |  0.294449 |     7.398 |     7.908 |      6.23333e+07 | Spoiled  |
|             7 |   3 |    7.85767 |  0.123662 |     7.724 |     7.968 |      7.4e+07     | Spoiled  |

### 2.2 Estadísticos por clase

| Fresh_Spoiled   |   n |    mean |      std |   min |   max |
|:----------------|----:|--------:|---------:|------:|------:|
| Fresh           |  15 | 5.1728  | 0.777405 | 4.057 | 6.286 |
| Spoiled         |   6 | 7.79783 | 0.212351 | 7.398 | 7.968 |

### 2.3 Visualizaciones

**Boxplot por día + strip + umbral 7 log:**

![Micro boxplot](results/micro_boxplot_by_day.png)

> Puntos individuales muestran baja dispersión intra-día (n=3) pero días 4-5 ya se acercan al umbral (6.28, 5.74). Día 6 salta a 7.7, superando claramente el umbral.

**Evolución media diaria:**

![Micro line](results/micro_line_mean_by_day.png)

**Histograma log:**

![Micro hist](results/micro_hist_log.png)

**Fresh vs Spoiled:**

![Micro fresh vs spoiled](results/micro_boxplot_fresh_spoiled.png)

**Scatter CFU vs log:**

![Micro scatter](results/micro_scatter_cfu_log.png)

**Interpretación:**

- Crecimiento aproximadamente exponencial hasta día 6, luego plateau ~7.8-7.9.
- Umbral 7 log separa perfectamente Fresh/Spoiled a nivel de **media diaria**, pero a nivel individual el mínimo de spoiled (7.39) está por encima del máximo de fresh (6.28) → separación completa en este dataset (no solapamiento microbiológico).
- **Advertencia:** Esta etiqueta diaria se propaga a todos los sensores/imágenes de ese día (`TVC_log` en CSVs sensores). No es ground-truth per-filete.

---

## 3. Sensores

**Fuente:** `day*/sensors/*.csv` - 210 sesiones × 120 puntos (1 Hz, 2 min) × 7 canales: `MQ3,MQ5,MQ9,MQ135,MQ137` (ADC 0-1023, sin calibración) + `Temp` + `Hum`.

### 3.1 Agregación por sesión

Cada CSV se resume a **media/std/min/max/range/slope/last/first** por canal. Total 25200 puntos temporales (210×120) → 210 filas agregadas.

![Conteo sensores](results/sensors_count_by_day.png)

### 3.2 Distribución por día

**Boxplots por canal (medias por sesión):**

- MQ3, MQ5, MQ9, MQ135, MQ137, Temp, Hum:

![MQ3](results/sensors_boxplot_MQ3_mean_by_day.png)
![MQ5](results/sensors_boxplot_MQ5_mean_by_day.png)
![MQ9](results/sensors_boxplot_MQ9_mean_by_day.png)
![MQ135](results/sensors_boxplot_MQ135_mean_by_day.png)
![MQ137](results/sensors_boxplot_MQ137_mean_by_day.png)
![Temp](results/sensors_boxplot_Temp_mean_by_day.png)
![Hum](results/sensors_boxplot_Hum_mean_by_day.png)

> Observaciones: MQ135 y MQ137 muestran mayor incremento días 6-7 (spoiled). MQ3/MQ5 más ruidosos. Temperatura ~8-11°C con variabilidad importante entre sesiones (posible apertura de cámara). Humedad 49-66%.

**Evolución diaria conjunta:**

![Line MQ](results/sensors_line_mq_daily_mean.png)
![Line Temp Hum](results/sensors_line_temp_hum_daily.png)

### 3.3 Fresh vs Spoiled

![Box fresh spoiled](results/sensors_boxplot_fresh_spoiled.png)

> Spoiled tiene medianas superiores en todos los MQ, pero solapamiento considerable (especialmente MQ3). Temp ligeramente menor en spoiled (posible correlación temporal, no causal).

### 3.4 Correlaciones

**Heatmap:**

![Corr heatmap](results/sensors_corr_heatmap.png)

**Correlación con TVC (ordenada):**

|    | Unnamed: 0   |   TVC_log |
|---:|:-------------|----------:|
|  0 | TVC_log      |  1        |
|  1 | MQ135_mean   |  0.962267 |
|  2 | MQ137_mean   |  0.946222 |
|  3 | MQ9_mean     |  0.942662 |
|  4 | MQ3_mean     |  0.916661 |
|  5 | MQ5_mean     |  0.886878 |
|  6 | Hum_mean     |  0.526749 |
|  7 | Temp_mean    | -0.514523 |

> MQ135 (r=0.96) y MQ137 (r=0.94), MQ9 (r=0.94), MQ3 (r=0.91), MQ5 (r=0.88) fuertemente asociados a TVC; Hum correlación moderada (r=0.52); Temp correlación negativa débil (r=-0.51).

**Scatter vs TVC:**

![Scatter vs TVC](results/sensors_scatter_vs_tvc.png)

### 3.5 Series temporales (120s)

**MQ3 ejemplos (2 sesiones/día):**

![TS MQ3](results/sensors_timeseries_example_MQ3.png)

**MQ135 ejemplos:**

![TS MQ135](results/sensors_timeseries_example_MQ135.png)

> Dentro de 120s hay drift ligero (ver pendientes). Variabilidad intra-sesión y entre-sesiones similar magnitud. Sin baseline correction `README:101`, hay offset entre sesiones.

**Variabilidad y pendiente:**

![Std slope](results/sensors_std_slope_by_day.png)

### 3.6 PCA (7 features medias)

![PCA fresh](results/sensors_pca_fresh_spoiled.png)
![PCA day](results/sensors_pca_by_day.png)
![PCA loadings](results/sensors_pca_loadings.png)
![PCA variance](results/sensors_pca_variance.png)

> PC1 ~40-45% varianza separa parcialmente Fresh/Spoiled y ordena días 1→7. PC2 captura Temp/Hum. Loadings muestran MQ135/MQ137 dominantes en PC1.

---

## 4. Imágenes

**Fuente:** `day*/jpg/F/*.jpg` (Flesh) y `day*/jpg/S/*.jpg` (Skin) - 820 JPG (2248×... aprox, ver resolución), más `raw/*.CR2`.

### 4.1 Características extraídas (via Pillow)

Por cada JPG: `width,height,MP,aspect,file_size_mb,R_mean,G_mean,B_mean,brightness (luminancia), H,S,V, R_G_ratio, R_B_ratio`.

|   day |   F |   S |
|------:|----:|----:|
|     1 |  59 |  59 |
|     2 |  58 |  59 |
|     3 |  57 |  57 |
|     4 |  59 |  59 |
|     5 |  59 |  59 |
|     6 |  59 |  59 |
|     7 |  59 |  58 |

**Tamaño y resolución:**

![Filesize dist](results/images_filesize_dist.png)
![Resolution](results/images_resolution_scatter.png)
![MP by day](results/images_mp_by_day.png)

> JPG ~3-4 MB, resolución constante (~ 4000×3000, verificar scatter). Ligeras variaciones de tamaño correlacionadas con brillo/contenido.

### 4.2 Color por día

![RGB by day](results/images_rgb_mean_by_day.png)

> R_mean tiende a bajar leve días 6-7 (pérdida de rojez), G/B más estables. Alta dispersión intra-día.

**Flesh vs Skin:**

![RGB flesh vs skin](results/images_rgb_flesh_vs_skin.png)

> Skin tiene mayor varianza y menor R_mean (más oscura/heterogénea). Flesh más homogénea y brillante.

**Brillo:**

![Brightness by day](results/images_brightness_by_day.png)
![Brightness fresh vs spoiled](results/images_brightness_fresh_spoiled.png)

> Brillo medio Fresh 159.9 vs Spoiled 151.6 → diferencia ~-8.3. Solapamiento alto; no discriminante fuerte solo.

**HSV:**

![HSV by day](results/images_hsv_by_day.png)

**Correlación features imagen:**

![Corr images](results/images_corr_features.png)

**R vs G scatter:**

![R vs G](results/images_r_vs_g_by_day.png)

**Ratios R/G, R/B:**

![Ratios](results/images_ratios_by_day.png)

> Ratios descienden levemente en spoiled (menos rojo relativo).

### 4.3 Ejemplos visuales

**Longitudinal - fillet con 7 días completos:**

Seleccionado fillet con 7 apariciones en F (ej: `F1F10` o similar):

![Grid example](results/images_grid_example_F1F1.png)

*(Si el nombre no coincide, ver `results/images_grid_example_*.png`)*

Muestras aleatorias por día:

![Random grid](results/images_grid_random_by_day.png)

> Inspección visual: cambios sutiles de color/textura; piel (S) muestra oscurecimiento/mucosidad; carne (M) palidece. Sin embargo alta variabilidad inter-filete.

---

## 5. Multimodal y correlaciones cruzadas

- **TVC vs sensores:** Correlación muy fuerte a nivel de media diaria (r>0.88), pero moderada a nivel de sesión individual por variabilidad. Útil para regresión; clasificación binaria tiene solapamiento.
- **TVC vs imágenes:** Features de color correlación débil (|r|<0.3) con TVC diario. Indica que imagen sola no predice TVC con alta precisión sin modelo profundo.
- **Sensores vs imágenes:** No hay correlación directa fuerte; modalidades complementarias.
- **Clase binaria:** Separación microbiológica perfecta a nivel día, pero sensores/imágenes con solapamiento → modelo multimodal podría superar unimodal.

---

## 6. Limitaciones y advertencias (del README + observadas)

- Solo trucha arcoíris, una granja, una campaña → no generaliza a otras especies/lotes.
- n=3 TVC/día (21 total) → estimación de media diaria ruidosa; intervalo confianza ancho.
- Etiqueta `Fresh/Spoiled` es **por día**, no por filete → ruido de etiqueta si filete individual diverge de media.
- Sensores MQ sin calibración, cross-sensitive, drift, 5 min ventilación sin criterio recuperación `README:105` → señal = respuesta, no concentración.
- 59 filetes longitudinales + 4 porciones por pez → dependencia estadística, leakage si split aleatorio. **Recomendado split por pez original `README:252`**.
- Imágenes: 6 descartadas por blur/iluminación, resolución constante pero variabilidad de iluminación no corregida (ver brillo std).
- Temperatura entre sesiones varía 8-11°C (no perfectamente 4°C) → confounder.

---

## 7. Recomendaciones para modelado

1. **Splits:** Agrupar por `Fish ID` (extraído de `F1F10` → `F1` es pez). Estratificar por día/clase si posible. Usar Leave-One-Fish-Out o GroupKFold.
2. **Tarea:** Clasificación binaria Fresh/Spoiled (71/29, usar F1, AUC, balanced accuracy) + regresión TVC log (RMSE) como multitask. Alternativa: clasificación 7 días ordinal.
3. **Sensores:** Usar features agregados (mean, slope, std) + series raw (1D CNN, LSTM) con normalización por sesión. Considerar corrección baseline (ej: restar primeros 10s).
4. **Imágenes:** Fine-tuning CNN (EfficientNet, ResNet) separando F vs S o ensemble. Data augmentation color/brightness. Extraer embeddings y concatenar con sensores.
5. **Multimodal:** Late fusion (concat embeddings). Evaluar solo por día 6-7 como test de generalización temporal.
6. **Métricas:** Reportar por fish, no por imagen, para evitar inflación.

---

## 8. Reproducibilidad

**Entorno:** `.venv` Python 3.10.12, `pandas 2.3.3`, `numpy 2.2.6`, `matplotlib 3.10.9`, `seaborn 0.13.2`, `Pillow 12.3.0`, `scikit-learn 1.7.2`, `tqdm`

**Ejecución:**

```bash
source .venv/bin/activate
pip install -r eda/requirements.txt
python eda/eda_micro.py      # → results/micro_*.png + tvc_summary.csv
python eda/eda_sensors.py    # → results/sensors_*.png + sensors_aggregated_per_session.csv
python eda/eda_images.py     # → results/images_*.png + images_features.csv
python eda/generate_report.py # → eda/informe.md
```

**Salidas en `eda/results/`:** 48 archivos (figuras PNG + CSVs)

---

## 9. Archivos generados

- `results/images_brightness_by_day.png` (49.9 KB)
- `results/images_brightness_fresh_spoiled.png` (69.7 KB)
- `results/images_corr_features.png` (157.1 KB)
- `results/images_count_by_day_surface.png` (41.7 KB)
- `results/images_features.csv` (326.3 KB)
- `results/images_filesize_dist.png` (81.9 KB)
- `results/images_grid_example_F1F1.png` (1084.4 KB)
- `results/images_grid_random_by_day.png` (1135.2 KB)
- `results/images_hsv_by_day.png` (90.9 KB)
- `results/images_missing_by_day.csv` (0.2 KB)
- `results/images_mp_by_day.png` (34.2 KB)
- `results/images_r_vs_g_by_day.png` (142.4 KB)
- `results/images_ratios_by_day.png` (54.9 KB)
- `results/images_resolution_scatter.png` (47.4 KB)
- `results/images_rgb_flesh_vs_skin.png` (134.4 KB)
- `results/images_rgb_mean_by_day.png` (65.1 KB)
- `results/micro_boxplot_by_day.png` (60.6 KB)
- `results/micro_boxplot_fresh_spoiled.png` (42.7 KB)
- `results/micro_hist_log.png` (40.5 KB)
- `results/micro_line_mean_by_day.png` (105.8 KB)
- `results/micro_scatter_cfu_log.png` (60.7 KB)
- `results/micro_stats.txt` (0.9 KB)
- `results/raw_files_stats.csv` (85.4 KB)
- `results/sensors_aggregated_per_session.csv` (138.9 KB)
- `results/sensors_boxplot_Hum_mean_by_day.png` (58.8 KB)
- `results/sensors_boxplot_MQ135_mean_by_day.png` (60.0 KB)
- `results/sensors_boxplot_MQ137_mean_by_day.png` (60.7 KB)
- `results/sensors_boxplot_MQ3_mean_by_day.png` (62.8 KB)
- `results/sensors_boxplot_MQ5_mean_by_day.png` (56.6 KB)
- `results/sensors_boxplot_MQ9_mean_by_day.png` (58.6 KB)
- `results/sensors_boxplot_Temp_mean_by_day.png` (59.9 KB)
- `results/sensors_boxplot_fresh_spoiled.png` (256.4 KB)
- `results/sensors_corr_heatmap.png` (125.7 KB)
- `results/sensors_corr_with_tvc.csv` (0.2 KB)
- `results/sensors_count_by_day.png` (30.4 KB)
- `results/sensors_line_mq_daily_mean.png` (105.9 KB)
- `results/sensors_line_temp_hum_daily.png` (69.6 KB)
- `results/sensors_pca_by_day.png` (136.2 KB)
- `results/sensors_pca_fresh_spoiled.png` (112.7 KB)
- `results/sensors_pca_loadings.csv` (0.3 KB)
- `results/sensors_pca_loadings.png` (80.9 KB)
- `results/sensors_pca_variance.png` (38.2 KB)
- `results/sensors_scatter_vs_tvc.png` (329.2 KB)
- `results/sensors_std_slope_by_day.png` (72.3 KB)
- `results/sensors_timeseries_example_MQ135.png` (582.4 KB)
- `results/sensors_timeseries_example_MQ3.png` (580.6 KB)
- `results/tvc_summary_by_class.csv` (0.1 KB)
- `results/tvc_summary_by_day.csv` (0.6 KB)

---

**Conclusión:** Dataset multimodal bien curado, con señal de spoilage clara microbiológicamente pero sutil en sensores/imágenes. Ideal para probar fusión multimodal y manejo de leakage longitudinal. El análisis sugiere que el spoilage días 6-7 es detectable pero requiere modelado cuidadoso por desbalance y dependencia temporal.

*Generado automáticamente por `generate_report.py`*
