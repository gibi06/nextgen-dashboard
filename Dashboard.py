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
                if col_fuel == df.columns[0]: 
                    col_fuel = get_col(df, ['total fuel', 'fuel '])
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
                if h2_col == df.columns[0]:
                    h2_col = get_col(df, ['hydrogen'])
                temp['Liquid Fuel'] = 0
                temp['Electricity'] = 0
                temp
