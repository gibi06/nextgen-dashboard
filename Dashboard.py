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
        'Baseline 2025': ('Baseline', '2025'),
        'Baseline 2050': ('Baseline', '2050'),
        'Scenario 1 2025': ('100% SAF', '2025'),
        'Scenario 1 2050': ('100% SAF', '2050'),
        'Scenario 2 2025': ('Hybrid-Electric', '2025'),
        'Scenario 2 2050': ('Hybrid-Electric', '2050'),
        'Scenario 3 2025': ('Hydrogen', '2025'),
        'Scenario 3 2050': ('Hydrogen', '2050')
    }

    def get_col(df, keywords, exact=False):
        for c in df.columns:
            c_str = str(c).strip().lower()
            if exact:
                if c_str in keywords:
                    return c
            else:
                if any(k in c_str for k in keywords):
                    return c
        return df.columns[0]

    dfs = []
    for sheet, (scenario, year) in sheet_map.items():
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, skiprows=5)
            
            c_type = get_col(df, ['flight type'])
            c_cost = get_col(df, ['total cost', 'total costs'])
            rev_cols = [c for c in df.columns if 'revenue' in str(c).lower() or 'revenu' in str(c).lower()]
            c_rev = rev_cols[-1] if rev_cols else df.columns[0]
            c_co2 = get_col(df, ['total co2', 'co2 emmission'])
            c_nox = get_col(df, ['total nox'])
            c_sox = get_col(df, ['total sox'])
            c_freq = get_col(df, ['frequency', 'flights'])
            c_ticket = get_col(df, ['ticket'])
            c_seats = get_col(df, ['seat'])
            c_cargo = get_col(df, ['cargo'])
            
            temp = df[[c_type, c_cost, c_rev, c_co2, c_nox, c_sox, c_freq, c_ticket, c_seats, c_cargo]].dropna(subset=[c_type]).copy()
            freq_numeric = pd.to_numeric(temp[c_freq], errors='coerce').fillna(0)
            
            if scenario in ['Baseline', '100% SAF']:
                col_fuel = get_col(df, ['fuel'], exact=True)
                if col_fuel == df.columns[0]: col_fuel = get_col(df, ['total fuel', 'fuel '])
                temp['Liquid Fuel'] = pd.to_numeric(df[col_fuel], errors='coerce').fillna(0)
                temp['Electricity'] = 0
                temp['Hydrogen'] = 0
            elif scenario == 'Hybrid-Electric':
                hefa_col = get_col(df, ['fuel hefa', 'hefa'])
                elec_col = get_col(df, ['electric'])
                temp['Liquid Fuel'] = pd.to_numeric(df[hefa_col], errors='coerce').fillna(0)
                temp['Electricity'] = pd.to_numeric(df[elec_col], errors='coerce').fillna(0)
                temp['Hydrogen'] = 0
            elif scenario == 'Hydrogen':
                h2_col = get_col(df, ['hydrogen'], exact=True)
                if h2_col == df.columns[0]: h2_col = get_col(df, ['hydrogen'])
                temp['Liquid Fuel'] = 0
                temp['Electricity'] = 0
                temp['Hydrogen'] = pd.to_numeric(df[h2_col], errors='coerce').fillna(0)

            temp[c_cost] = pd.to_numeric(temp[c_cost], errors='coerce').fillna(0) * freq_numeric
            temp[c_rev] = pd.to_numeric(temp[c_rev], errors='coerce').fillna(0) * freq_numeric
            temp[c_co2] = pd.to_numeric(temp[c_co2], errors='coerce').fillna(0)
            temp[c_nox] = pd.to_numeric(temp[c_nox], errors='coerce').fillna(0)
            temp[c_sox] = pd.to_numeric(temp[c_sox], errors='coerce').fillna(0)
            temp['Ticket Price [€]'] = pd.to_numeric(temp[c_ticket], errors='coerce').fillna(0)
            temp['Seats'] = pd.to_numeric(temp[c_seats], errors='coerce').fillna(0)
            temp['Cargo (Tons)'] = pd.to_numeric(temp[c_cargo], errors='coerce').fillna(0)

            temp = temp[[c_type, c_cost, c_rev, c_co2, c_nox, c_sox, 'Ticket Price [€]', 'Seats', 'Cargo (Tons)', 'Liquid Fuel', 'Electricity', 'Hydrogen']]
            temp.columns = ['Flight Type', 'Total Costs [€]', 'Total Revenue [€]', 'CO2 Emissions [tons]', 'NOx Emissions [tons]', 'SOx Emissions [tons]', 'Ticket Price [€]', 'Seats', 'Cargo (Tons)', 'Liquid Fuel', 'Electricity', 'Hydrogen']
            temp['Scenario'] = scenario
            temp['Year'] = year
            dfs.append(temp)
        except Exception:
            continue
            
    if dfs:
        routes_df = pd.concat(dfs, ignore_index=True)
    else:
        st.error("Critical Error: No data could be processed. Please check the Excel file formatting.")
        st.stop()
    
    agg_df = routes_df.groupby(['Scenario', 'Year']).agg({
        'Total Costs [€]': 'sum', 'Total Revenue [€]': 'sum',
        'CO2 Emissions [tons]': 'sum', 'NOx Emissions [tons]': 'sum', 'SOx Emissions [tons]': 'sum'
    }).reset_index()
    agg_df['Profit Margin [%]'] = ((agg_df['Total Revenue [€]'] - agg_df['Total Costs [€]']) / agg_df['Total Revenue [€]']) * 100
    agg_df['Total Costs [Billion €]'] = agg_df['Total Costs [€]'] / 1e9
    agg_df['Total Revenue [Billion €]'] = agg_df['Total Revenue [€]'] / 1e9
    
    haul_df = routes_df.groupby(['Scenario', 'Year', 'Flight Type']).agg({
        'Total Costs [€]': 'sum', 'Total Revenue [€]': 'sum',
        'CO2 Emissions [tons]': 'sum', 'NOx Emissions [tons]': 'sum', 'SOx Emissions [tons]': 'sum',
        'Ticket Price [€]': 'mean', 'Seats': 'mean', 'Cargo (Tons)': 'mean',
        'Liquid Fuel': 'mean', 'Electricity': 'mean', 'Hydrogen': 'mean'
    }).reset_index()
    
    try:
        feasibility = pd.read_excel(file_path, sheet_name="feasibility")
        if "Unnamed" in str(feasibility.columns[0]):
            feasibility.rename(columns={feasibility.columns[0]: "Scenario"}, inplace=True)
    except:
        feasibility = pd.DataFrame({'Scenario': ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen'], 'Data': ['No data found']*4})
        
    return agg_df, haul_df, feasibility

agg_df, haul_df, feasibility = load_data()

def safe_val(df, scen, yr, col):
    val = df.loc[(df['Scenario'] == scen) & (df['Year'] == yr), col].values
    return val[0] if len(val) > 0 else 0

b_2025_co2 = safe_val(agg_df, 'Baseline', '2025', 'CO2 Emissions [tons]')
b_2025_nox = safe_val(agg_df, 'Baseline', '2025', 'NOx Emissions [tons]')
b_2025_sox = safe_val(agg_df, 'Baseline', '2025', 'SOx Emissions [tons]')
scenario_order = {'Scenario': ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen']}

# ----------------------------------------------------
# 3. DASHBOARD UI
# ----------------------------------------------------
st.title("🌍 NextGen Innovation Strategy Dashboard")
st.markdown("Prioritizing Environmental Impact (CO₂, NOx, SOx) & Financial Feasibility of 2050 Aviation Transition Strategies.")
st.divider()

st.subheader("Key Environmental Targets (2050 vs Current 2025 Baseline)")
cols = st.columns(4)
display_targets = [('Baseline', '2025', 'Current Operations (2025)'), ('100% SAF', '2050', '100% SAF Projection (2050)'), ('Hybrid-Electric', '2050', 'Hybrid Projection (2050)'), ('Hydrogen', '2050', 'Hydrogen Projection (2050)')]

for i, (scen, yr, label) in enumerate(display_targets):
    val = safe_val(agg_df, scen, yr, 'CO2 Emissions [tons]')
    delta_str = None if (scen == 'Baseline' and yr == '2025') or b_2025_co2 == 0 else f"{((val - b_2025_co2) / b_2025_co2)}
