import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------------------------------
# 1. SETUP & HIGH-QUALITY EXPORT
# ----------------------------------------------------
st.set_page_config(page_title="NextGen Strategy Dashboard", page_icon="🌍", layout="wide")

dl_config = {
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'NextGen_Chart_Export',
        'scale': 3 
    }
}

# ----------------------------------------------------
# 2. BULLETPROOF DATA LOADING
# ----------------------------------------------------
@st.cache_data
def load_data():
    file_path = "Cost Calculation Scenarios.xlsx"
    sheet_map = {
        'Baseline 2025': ('Baseline', '2025'), 'Baseline 2050': ('Baseline', '2050'),
        'Scenario 1 2025': ('100% SAF', '2025'), 'Scenario 1 2050': ('100% SAF', '2050'),
        'Scenario 2 2025': ('Hybrid-Electric', '2025'), 'Scenario 2 2050': ('Hybrid-Electric', '2050'),
        'Scenario 3 2025': ('Hydrogen', '2025'), 'Scenario 3 2050': ('Hydrogen', '2050')
    }

    def extract_series(df, keywords, exact=False):
        for c in df.columns:
            c_str = str(c).strip().lower()
            match = False
            if exact and c_str in keywords: match = True
            elif not exact and any(k in c_str for k in keywords): match = True
            if match:
                val = df[c]
                return val.iloc[:, 0] if isinstance(val, pd.DataFrame) else val
        return pd.Series([0]*len(df), index=df.index)

    dfs = []
    for sheet, (scenario, year) in sheet_map.items():
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, skiprows=5)
            temp = pd.DataFrame()
            
            # Extract
            freq = pd.to_numeric(extract_series(df, ['frequency', 'flights']), errors='coerce').fillna(0)
            temp['Total Costs [€]'] = pd.to_numeric(extract_series(df, ['total cost', 'total costs']), errors='coerce').fillna(0) * freq
            
            # Revenue logic
            rev_series = pd.Series([0]*len(df), index=df.index)
            for c in reversed(df.columns):
                if 'revenue' in str(c).lower():
                    rev_series = df[c].iloc[:, 0] if isinstance(df[c], pd.DataFrame) else df[c]
                    break
            temp['Total Revenue [€]'] = pd.to_numeric(rev_series, errors='coerce').fillna(0) * freq
            
            temp['CO2 Emissions [tons]'] = pd.to_numeric(extract_series(df, ['total co2']), errors='coerce').fillna(0)
            temp['Ticket Price [€]'] = pd.to_numeric(extract_series(df, ['ticket']), errors='coerce').fillna(0)
            temp['Seats'] = pd.to_numeric(extract_series(df, ['seat']), errors='coerce').fillna(0)
            temp['Cargo (Tons)'] = pd.to_numeric(extract_series(df, ['cargo']), errors='coerce').fillna(0)
            
            # Energy logic
            if scenario in ['Baseline', '100% SAF']:
                fuel = extract_series(df, ['fuel'], exact=True)
                temp['Liquid Fuel'] = pd.to_numeric(fuel, errors='coerce').fillna(0)
            elif scenario == 'Hybrid-Electric':
                temp['Liquid Fuel'] = pd.to_numeric(extract_series(df, ['hefa']), errors='coerce').fillna(0)
                temp['Electricity'] = pd.to_numeric(extract_series(df, ['electric']), errors='coerce').fillna(0)
            elif scenario == 'Hydrogen':
                temp['Hydrogen'] = pd.to_numeric(extract_series(df, ['hydrogen']), errors='coerce').fillna(0)

            temp['Scenario'], temp['Year'] = scenario, year
            dfs.append(temp)
        except Exception: continue
            
    return pd.concat(dfs, ignore_index=True)

df = load_data()
agg_df = df.groupby(['Scenario', 'Year']).agg({'Total Costs [€]': 'sum', 'Total Revenue [€]': 'sum', 'CO2 Emissions [tons]': 'sum'}).reset_index()
agg_df['Total Costs [Billion €]'] = agg_df['Total Costs [€]'] / 1e9
agg_df['Total Revenue [Billion €]'] = agg_df['Total Revenue [€]'] / 1e9

# ----------------------------------------------------
# 3. DASHBOARD UI
# ----------------------------------------------------
st.title("🌍 NextGen Innovation Strategy Dashboard")

st.subheader("📊 Executive Summary: 2050 Projections")
df_2050 = agg_df[agg_df['Year'] == '2050'].copy()

col1, col2 = st.columns(2)

with col1:
    # Safe Max Calculation
    max_co2 = df_2050['CO2 Emissions [tons]'].max()
    fig = px.bar(df_2050, x='Scenario', y='CO2 Emissions [tons]', title="CO₂ Emissions", color='Scenario')
    fig.update_layout(yaxis=dict(range=[0, (max_co2 * 1.25) if pd.notna(max_co2) else 1000]))
    st.plotly_chart(fig, use_container_width=True, config=dl_config)

with col2:
    melted = df_2050.melt(id_vars=['Scenario'], value_vars=['Total Costs [Billion €]', 'Total Revenue [Billion €]'])
    max_fin = melted['value'].max()
    fig = px.bar(melted, x='Scenario', y='value', color='variable', barmode='group', title="Costs vs Revenue")
    fig.update_layout(yaxis=dict(range=[0, (max_fin * 1.25) if pd.notna(max_fin) else 1]))
    st.plotly_chart(fig, use_container_width=True, config=dl_config)

# --- TRANSPARENCY SECTION (Bottom) ---
st.info("""
**📚 Data Transparency & Sources:**
All KPIs are calculated using **`Cost Calculation Scenarios.xlsx`**. 
* Financials: Calculated from flight frequencies, ticket prices, and cost breakdowns.
* Emissions: Based on 2050 CO₂ penalty (€500/ton) and standard fuel emission factors.
""")
