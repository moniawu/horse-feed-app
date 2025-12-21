import streamlit as st
import pandas as pd
import numpy as np
import os
import uuid

st.set_page_config(page_title="Horse Feed App", layout="wide")
st.title("🐴 Horse Feed – Aplikacja Żywieniowa dla Koni")

# ====== HASŁO ======
PASSWORD = "MonikaMistrz"

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Dostęp chroniony")
    pwd = st.text_input("Hasło dostępu", type="password")

    if pwd == PASSWORD:
        st.session_state.auth = True
       
    elif pwd:
        st.error("Nieprawidłowe hasło")

    st.stop()

    
@st.cache_data
def load_requirements(file_path):
    xls = pd.ExcelFile(file_path)
    data = {}
    for sheet in xls.sheet_names:
        if "kg" in sheet:
            weight = int("".join(filter(str.isdigit, sheet)))
            df = xls.parse(sheet)
            df.columns = df.iloc[0]
            df = df[2:].dropna(how="all").reset_index(drop=True)
            df.columns.name = None
            df = df.rename(columns=lambda x: str(x).strip() if pd.notna(x) else "")
            data[weight] = df
    return data

def interpolate(df1, df2, w1, w2, target_weight):
    df_interp = df1.copy()
    numeric_cols = df1.columns[1:]
    for col in numeric_cols:
        try:
            val1 = pd.to_numeric(df1[col], errors='coerce')
            val2 = pd.to_numeric(df2[col], errors='coerce')
            interp = val1 + (val2 - val1) * ((target_weight - w1) / (w2 - w1))
            df_interp[col] = interp.round(2)
        except:
            pass
    return df_interp

file_path = "konie wg wag wymagania zywieniowe.xlsx"
pasze_file = "pasze tresciwe i obetosciowe do aplikacji.xlsx"

if not os.path.exists(file_path) or not os.path.exists(pasze_file):
    st.error("❌ Brak plików danych Excel.")
    st.stop()

requirements = load_requirements(file_path)
available_weights = sorted(requirements.keys())
pasze_df = pd.read_excel(pasze_file, header=1)

category_map = {
    "Dorosły koń": ["Minimalne wymagania", "Średnie", "Podwyższone wymagania"],
    "Koń pracujący": ["Lekkie ćwiczenia", "Umiarkowane ćwiczenia", "Ciężkie ćwiczenia", "Bardzo ciężkie ćwiczenia"],
    "Ogier": ["Niekryjące", "kryjące"],
    "Klacz źrebna": ["< 5 miesięcy", "5 miesiąc", "6 miesiąc", "7 miesiąc", "8 miesiąc", "9 miesiąc", "10 miesiąc", "11 miesiąc"],
    "Klacz w laktacji": ["1 miesiąc", "2 miesiąc", "3 miesiąc", "4 miesiąc"],
    "Koń rosnący": [
        "4 miesiące", "6 miesięcy", "12 miesięcy", "18 miesięcy",
        "18 miesięcy - lekkie ćwiczenia", "18 miesięcy -umiarkowane ćwiczenia",
        "24 miesięcy", "24 miesięcy - lekkie ćwiczenia",
        "24  miesięcy -umiarkowane ćwiczenia", "24  miesięcy -ciężkie ćwiczenia",
        "24  miesięcy - bardzo ciężkie ćwiczenia"
    ]
}

with st.sidebar:
    st.header("📋 Dane konia")
    name = st.text_input("Imię konia")
    weight = st.number_input("Waga konia (kg)", min_value=200, max_value=1000, value=500)
    category_main = st.selectbox("Główna kategoria konia", list(category_map.keys()))
    subcategory = st.selectbox("Szczegółowa podkategoria", category_map[category_main])
    note = st.text_area("Uwagi / Problemy zdrowotne", key=f"uwagi_{uuid.uuid4()}")
    full_category = subcategory.strip()

# Interpolacja
lower = max([w for w in available_weights if w <= weight], default=available_weights[0])
upper = min([w for w in available_weights if w >= weight], default=available_weights[-1])

if lower == upper:
    interpolated_df = requirements[lower]
else:
    interpolated_df = interpolate(requirements[lower], requirements[upper], lower, upper, weight)

interpolated_df = interpolated_df[~interpolated_df.iloc[:, 0].str.lower().str.contains("waga|mleko|mkcal|digestible", na=False)]
match_row = interpolated_df[interpolated_df.iloc[:, 0].astype(str).str.strip() == full_category]

if not match_row.empty:
    match_row = match_row.T
    match_row.columns = match_row.iloc[0]
    match_row = match_row[1:]
    match_row = match_row.rename_axis("Składnik").reset_index()
    match_row = match_row.iloc[:, [0, 1]]  # wybieramy tylko dwie kolumny, by uniknąć błędu
    match_row.columns = ["Składnik", f"{full_category} ({weight} kg)"]

    match_row.loc[match_row["Składnik"].str.lower() == "waga", f"{full_category} ({weight} kg)"] = weight

    st.success(f"🔍 Znaleziono dane dla: **{full_category}** przy {weight} kg")
    st.subheader("📊 Zapotrzebowanie żywieniowe")
    st.dataframe(match_row.set_index("Składnik"))
else:
    st.warning(f"⚠️ Nie znaleziono danych dla: **{full_category}** przy {weight} kg")
    match_row = pd.DataFrame()  # pusta ramka, by uniknąć błędów dalej

# Pasze
st.subheader("🌾 Dieta konia – pasze")
feed_options = ["--- wybierz paszę ---"] + sorted(list(pasze_df["Nazwa paszy"].dropna().unique()))

if "feed_rows" not in st.session_state:
    st.session_state.feed_rows = [{"feed": "--- wybierz paszę ---", "kg": 0.0}]

if st.button("➕ Dodaj kolejną paszę"):
    st.session_state.feed_rows.append({"feed": "--- wybierz paszę ---", "kg": 0.0})

selected_feeds = []
for i, row in enumerate(st.session_state.feed_rows):
    cols = st.columns([4, 2])
    feed = cols[0].selectbox(f"Pasza {i+1}", feed_options, index=feed_options.index(row["feed"]), key=f"feed_{i}")
    kg = cols[1].number_input("Ilość (kg)", min_value=0.0, max_value=20.0, step=0.1, value=row["kg"], key=f"kg_{i}")
    if feed != "--- wybierz paszę ---" and kg > 0:
        selected_feeds.append((feed, kg))

# Składniki z diety
st.subheader("📦 Dieta – składniki")
total_nutrients = {}
if selected_feeds:
    diet_table = pd.DataFrame(selected_feeds, columns=["Nazwa paszy", "Ilość (kg)"])
    st.dataframe(diet_table)

    for feed_name, kg in selected_feeds:
        row = pasze_df[pasze_df["Nazwa paszy"] == feed_name]
        if not row.empty:
            for n in row.columns[2:]:
                try:
                    val = str(row.iloc[0][n])
                    val = float(val.replace(",", ".")) if val not in [None, "None", "nan"] else 0.0
                except:
                    val = 0.0
                val *= kg
                total_nutrients[n] = total_nutrients.get(n, 0.0) + val

    nutrients_series = pd.Series(total_nutrients).fillna(0).round(2)
    nutrients_df = nutrients_series.reset_index()
    nutrients_df.columns = ["Składnik", "Z diety (suma)"]
    st.dataframe(nutrients_df.set_index("Składnik"))

# Porównanie z zapotrzebowaniem
if not match_row.empty and total_nutrients:
    st.subheader("⚖️ Porównanie z zapotrzebowaniem")
    requirement_series = match_row.set_index("Składnik").iloc[:, 0]
    comparison = []

    for n in requirement_series.index:
        target = pd.to_numeric(requirement_series[n], errors="coerce")
        target = 0.0 if pd.isna(target) else target
        actual = total_nutrients.get(n, 0.0)
        diff = round(actual - target, 2)
        percent = round((actual / target) * 100, 1) if target else 0
        status = "✅" if 90 <= percent <= 110 else ("⚠️" if percent < 90 else "⬆️")
        comparison.append((n, actual, target, diff, f"{percent}%", status))

    result_df = pd.DataFrame(comparison, columns=["Składnik", "Spożycie", "Zapotrzebowanie", "Różnica", "% pokrycia", "Status"])
    st.dataframe(result_df.set_index("Składnik"))
