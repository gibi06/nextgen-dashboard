import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------------------------------
# 1. SETUP
# ----------------------------------------------------
st.set_page_config(page_title="NextGen Strategy Dashboard", page_icon="🌍", layout="wide")

# This configuration makes all downloaded images (via the camera icon) 3x sharper for PowerPoint
dl_config = {
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'NextGen_Chart_Export',
        'scale': 3 
    }
}

# ----------------------------------------------------
# 2. LOAD & PREPARE DATA
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

    def find_col(columns, keywords):
        for col in columns:
            if any(kw in str(col).lower() for kw in keywords):
                return col
        return columns[0] 

    dfs = []
    for sheet, (scenario, year) in sheet_map.items():
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, skiprows=5)
            
            # Base columns
            c_type = [c for c in df.columns if 'flight type' in str(c).lower()][0]
            c_cost = [c for c in df.columns if 'total cost' in str(c).lower()][0]
            rev_cols = [c for c in df.columns if 'revenue' in str(c).lower() or 'revenu' in str(c).lower()]
            c_rev = rev_cols[-1] 
            c_co2 = [c for c in df.columns if 'total co2' in str(c).lower()][0]
            c_nox = [c for c in df.columns if 'total nox' in str(c).lower()][0]
            c_sox = [c for c in df.columns if 'total sox' in str(c).lower()][0]
            c_freq = [c for c in df.columns if 'frequency' in str(c).lower() or 'flights' in str(c).lower()][0]
            
            # KPI columns
            c_ticket = find_col(df.columns, ['ticket'])
            c_seats = find_col(df.columns, ['seat'])
            c_cargo = find_col(df.columns, ['cargo'])
            
            temp = df[[c_type, c_cost, c_rev, c_co2, c_nox, c_sox, c_freq, c_ticket, c_seats, c_cargo]].dropna(subset=[c_type]).copy()
            freq_numeric = pd.to_numeric(temp[c_freq], errors='coerce').fillna(0)
            
            # -----------------------------------------------------------------
            # FUEL EXTRACTION LOGIC
            # -----------------------------------------------------------------
            if scenario == 'Baseline':
                col_fuel = [c for c in df.columns if c.strip().lower() == 'fuel'][0]
                temp['Liquid Fuel'] = pd.to_numeric(df[col_fuel], errors='coerce').fillna(0)
                temp['Electricity'] = 0
                temp['Hydrogen'] = 0
                
            elif scenario == '100% SAF':
                col_fuel = [c for c in df.columns if c.strip().lower() == 'fuel'][0]
                temp['Liquid Fuel'] = pd.to_numeric(df[col_fuel], errors='coerce').fillna(0)
                temp['Electricity'] = 0
                temp['Hydrogen'] = 0
                
            elif scenario == 'Hybrid-Electric':
                hefa_col = [c for c in df.columns if c.strip().lower() == 'fuel hefa'][0]
                elec_col = [c for c in df.columns if 'electric' in c.lower() and 'cost' not in c.lower()][0]
                temp['Liquid Fuel'] = pd.to_numeric(df[hefa_col], errors='coerce').fillna(0)
                temp['Electricity'] = pd.to_numeric(df[elec_col], errors='coerce').fillna(0)
                temp['Hydrogen'] = 0
                
            elif scenario == 'Hydrogen':
                h2_col = [c for c in df.columns if c.strip().lower() == 'hydrogen'][0]
                temp['Liquid Fuel'] = 0
                temp['Electricity'] = 0
                temp['Hydrogen'] = pd.to_numeric(df[h2_col], errors='coerce').fillna(0)

            # -----------------------------------------------------------------

            # Calculate Totals
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
        except Exception as e:
            continue
            
    routes_df = pd.concat(dfs, ignore_index=True)
    
    # 1. OVERALL AGGREGATION
    agg_df = routes_df.groupby(['Scenario', 'Year']).agg({
        'Total Costs [€]': 'sum', 'Total Revenue [€]': 'sum',
        'CO2 Emissions [tons]': 'sum', 'NOx Emissions [tons]': 'sum', 'SOx Emissions [tons]': 'sum'
    }).reset_index()
    agg_df['Profit Margin [%]'] = ((agg_df['Total Revenue [€]'] - agg_df['Total Costs [€]']) / agg_df['Total Revenue [€]']) * 100
    agg_df['Total Costs [Billion €]'] = agg_df['Total Costs [€]'] / 1e9
    agg_df['Total Revenue [Billion €]'] = agg_df['Total Revenue [€]'] / 1e9
    
    # 2. HAUL AGGREGATION & KPIs
    haul_df = routes_df.groupby(['Scenario', 'Year', 'Flight Type']).agg({
        'Total Costs [€]': 'sum', 'Total Revenue [€]': 'sum',
        'CO2 Emissions [tons]': 'sum', 'NOx Emissions [tons]': 'sum', 'SOx Emissions [tons]': 'sum',
        'Ticket Price [€]': 'mean', 'Seats': 'mean', 'Cargo (Tons)': 'mean',
        'Liquid Fuel': 'mean', 'Electricity': 'mean', 'Hydrogen': 'mean'
    }).reset_index()
    
    # 3. FEASIBILITY DATA
    feasibility = pd.read_excel(file_path, sheet_name="feasibility")
    if "Unnamed" in str(feasibility.columns[0]):
        feasibility.rename(columns={feasibility.columns[0]: "Scenario"}, inplace=True)
        
    return agg_df, haul_df, feasibility

agg_df, haul_df, feasibility = load_data()

b_2025_co2 = agg_df.loc[(agg_df['Scenario'] == 'Baseline') & (agg_df['Year'] == '2025'), 'CO2 Emissions [tons]'].values[0]
b_2025_nox = agg_df.loc[(agg_df['Scenario'] == 'Baseline') & (agg_df['Year'] == '2025'), 'NOx Emissions [tons]'].values[0]
b_2025_sox = agg_df.loc[(agg_df['Scenario'] == 'Baseline') & (agg_df['Year'] == '2025'), 'SOx Emissions [tons]'].values[0]

scenario_order = {'Scenario': ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen']}

# ----------------------------------------------------
# 3. DASHBOARD UI
# ----------------------------------------------------
st.title("🌍 NextGen Innovation Strategy Dashboard")
st.markdown("Prioritizing Environmental Impact (CO₂, NOx, SOx) & Financial Feasibility of 2050 Aviation Transition Strategies.")
st.divider()

st.subheader("Key Environmental Targets (2050 vs Current 2025 Baseline)")
cols = st.columns(4)
display_targets = [
    ('Baseline', '2025', 'Current Operations (2025)'),
    ('100% SAF', '2050', '100% SAF Projection (2050)'),
    ('Hybrid-Electric', '2050', 'Hybrid Projection (2050)'),
    ('Hydrogen', '2050', 'Hydrogen Projection (2050)')
]

for i, (scen, yr, label) in enumerate(display_targets):
    val = agg_df.loc[(agg_df['Scenario'] == scen) & (agg_df['Year'] == yr), 'CO2 Emissions [tons]'].values[0]
    if scen == 'Baseline' and yr == '2025':
        delta_str = None
    else:
        change = ((val - b_2025_co2) / b_2025_co2) * 100
        delta_str = f"{change:+.1f}% CO₂ Emissions" 
    with cols[i]:
        st.metric(label=label, value=f"{val / 1000:,.0f} kton CO₂", delta=delta_str, delta_color="inverse")

st.write("") 

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🌍 Overall Impact & Financials", "✈️ Haul Deep Dive", "⚖️ Feasibility", "📊 Operational KPIs"])

# ==========================================
# TAB 1: OVERALL IMPACT & FINANCIALS
# ==========================================
with tab1:
    st.subheader("1. CO₂ Emissions (2025 vs 2050)")
    def get_comp_data(metric_col, baseline_val, unit="kton", divisor=1000):
        data = []
        for scen in ['100% SAF', 'Hybrid-Electric', 'Hydrogen']:
            scen_val = agg_df.loc[(agg_df['Scenario'] == scen) & (agg_df['Year'] == '2050'), metric_col].values[0]
            change = ((scen_val - baseline_val) / baseline_val) * 100
            data.append({'Scenario': scen, 'Type': 'Baseline 2025', 'Value': baseline_val, 'Label': f"{baseline_val/divisor:,.0f} {unit}"})
            if change > 0:
                data.append({'Scenario': scen, 'Type': '2050 Projection', 'Value': scen_val, 'Label': f"{scen_val/divisor:,.0f} {unit} (<span style='color:red'>+{change:.1f}%</span>)"})
            else:
                data.append({'Scenario': scen, 'Type': '2050 Projection', 'Value': scen_val, 'Label': f"{scen_val/divisor:,.0f} {unit} (<span style='color:green'>{change:.1f}%</span>)"})
        return pd.DataFrame(data)

    co2_df = get_comp_data('CO2 Emissions [tons]', b_2025_co2, unit="kton", divisor=1000)
    fig_co2 = px.bar(co2_df, x='Scenario', y='Value', color='Type', barmode='group', text='Label', 
                     title="Projected CO₂ Emissions by Scenario (Compared to 2025 Baseline)",
                     color_discrete_map={'Baseline 2025': '#94A3B8', '2050 Projection': '#10B981'}, category_orders={'Scenario': ['100% SAF', 'Hybrid-Electric', 'Hydrogen']})
    fig_co2.update_traces(textposition='outside', textfont_size=13)
    fig_co2.update_layout(yaxis_title="CO₂ Emissions [Tons]", yaxis=dict(range=[0, co2_df['Value'].max() * 1.25]))
    st.plotly_chart(fig_co2, use_container_width=True, config=dl_config)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("NOx Emissions [Tons]")
        nox_df = get_comp_data('NOx Emissions [tons]', b_2025_nox, unit="tons", divisor=1)
        fig_nox = px.bar(nox_df, x='Scenario', y='Value', color='Type', barmode='group', text='Label', 
                         title="Projected NOx Emissions by Scenario",
                         color_discrete_map={'Baseline 2025': '#94A3B8', '2050 Projection': '#F59E0B'}, category_orders={'Scenario': ['100% SAF', 'Hybrid-Electric', 'Hydrogen']})
        fig_nox.update_traces(textposition='outside', textfont_size=12)
        fig_nox.update_layout(yaxis=dict(range=[0, nox_df['Value'].max() * 1.25]))
        st.plotly_chart
