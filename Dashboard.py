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

    # Safe scanner that prevents crashing if a column name has a typo
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
            
            # Smart Fuel Extraction
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
                temp['Hydrogen'] = pd.to_numeric(df[h2_col], errors='coerce').fillna(0)

            # Calculations
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
            st.warning(f"Note: Could not fully process sheet '{sheet}' due to formatting. Check column names.")
            continue
            
    if dfs:
        routes_df = pd.concat(dfs, ignore_index=True)
    else:
        st.error("Critical Error: No data could be processed. Please check the Excel file formatting.")
        st.stop()
    
    # OVERALL AGGREGATION
    agg_df = routes_df.groupby(['Scenario', 'Year']).agg({
        'Total Costs [€]': 'sum', 'Total Revenue [€]': 'sum',
        'CO2 Emissions [tons]': 'sum', 'NOx Emissions [tons]': 'sum', 'SOx Emissions [tons]': 'sum'
    }).reset_index()
    agg_df['Profit Margin [%]'] = ((agg_df['Total Revenue [€]'] - agg_df['Total Costs [€]']) / agg_df['Total Revenue [€]']) * 100
    agg_df['Total Costs [Billion €]'] = agg_df['Total Costs [€]'] / 1e9
    agg_df['Total Revenue [Billion €]'] = agg_df['Total Revenue [€]'] / 1e9
    
    # HAUL AGGREGATION
    haul_df = routes_df.groupby(['Scenario', 'Year', 'Flight Type']).agg({
        'Total Costs [€]': 'sum', 'Total Revenue [€]': 'sum',
        'CO2 Emissions [tons]': 'sum', 'NOx Emissions [tons]': 'sum', 'SOx Emissions [tons]': 'sum',
        'Ticket Price [€]': 'mean', 'Seats': 'mean', 'Cargo (Tons)': 'mean',
        'Liquid Fuel': 'mean', 'Electricity': 'mean', 'Hydrogen': 'mean'
    }).reset_index()
    
    # FEASIBILITY DATA
    try:
        feasibility = pd.read_excel(file_path, sheet_name="feasibility")
        if "Unnamed" in str(feasibility.columns[0]):
            feasibility.rename(columns={feasibility.columns[0]: "Scenario"}, inplace=True)
    except:
        feasibility = pd.DataFrame({'Scenario': ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen'], 'Data': ['No data found']*4})
        
    return agg_df, haul_df, feasibility

agg_df, haul_df, feasibility = load_data()

# Safe data retrieval
def safe_val(df, scen, yr, col):
    val = df.loc[(df['Scenario'] == scen) & (df['Year'] == yr), col].values
    return val[0] if len(val) > 0 else 0

def get_feas_val(scen, col_idx):
    try:
        match = feasibility[feasibility['Scenario'].str.contains(scen[:5], case=False, na=False)]
        if not match.empty:
            return match.iloc[0, col_idx]
    except:
        pass
    return "N/A"

b_2025_co2 = safe_val(agg_df, 'Baseline', '2025', 'CO2 Emissions [tons]')
b_2025_nox = safe_val(agg_df, 'Baseline', '2025', 'NOx Emissions [tons]')
b_2025_sox = safe_val(agg_df, 'Baseline', '2025', 'SOx Emissions [tons]')

scenario_order = {'Scenario': ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen']}

# ----------------------------------------------------
# 3. DASHBOARD UI - EXECUTIVE SUMMARY (ONE PAGE)
# ----------------------------------------------------
st.title("🌍 NextGen Innovation Strategy Dashboard")

# --- DATA TRANSPARENCY SECTION ---
st.info("""
**📚 Data Transparency & Sources:**
All KPIs and metrics displayed in this dashboard are calculated using data directly extracted from the project file: **`Cost Calculation Scenarios.xlsx`**. 
* **Financials:** Derived from flight frequencies, calculated ticket prices, and detailed cost breakdowns (e.g., crew, maintenance, fuel) found in the sheet.
* **Emissions & Sustainability:** CO₂ penalties are calculated using the 2050 assumption of €500/ton. Emission factors used: Jet-A1 (3.84 kg/kg) and SAF/HEFA (1.30 kg/kg).
* **Feasibility:** Extracted directly from the qualitative assessment in the 'feasibility' tab.
""")

st.subheader("📋 Executive Summary: All Key Performance Indicators (2050)")
st.markdown("This table provides a comprehensive one-page overview of all Sustainability, Financial, and Feasibility KPIs across the 2050 transition strategies, as requested in the PPG.")

# --- ONE-PAGE KPI TABLE ---
scenarios = ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen']
kpi_data = {
    "KPI / Metric (2050 Projection)": [
        "🌍 Total CO₂ Emissions (kton)",
        "🌍 Total NOx Emissions (tons)",
        "🌍 Total SOx Emissions (tons)",
        "💰 Total Financial Costs (Billion €)",
        "💰 Total Revenue (Billion €)",
        "📈 Profit Margin (%)",
        "✈️ Average Ticket Price (€)",
        "⚖️ Technical Feasibility",
        "⚖️ Regulatory Feasibility",
        "⚖️ Safety Feasibility"
    ]
}

for scen in scenarios:
    co2 = safe_val(agg_df, scen, '2050', 'CO2 Emissions [tons]') / 1000
    nox = safe_val(agg_df, scen, '2050', 'NOx Emissions [tons]')
    sox = safe_val(agg_df, scen, '2050', 'SOx Emissions [tons]')
    cost = safe_val(agg_df, scen, '2050', 'Total Costs [Billion €]')
    rev = safe_val(agg_df, scen, '2050', 'Total Revenue [Billion €]')
    margin = safe_val(agg_df, scen, '2050', 'Profit Margin [%]')
    avg_ticket = haul_df[(haul_df['Year'] == '2050') & (haul_df['Scenario'] == scen)]['Ticket Price [€]'].mean()
    
    kpi_data[scen] = [
        f"{co2:,.0f} kton",
        f"{nox:,.0f} tons",
        f"{sox:,.0f} tons",
        f"€{cost:,.2f}B",
        f"€{rev:,.2f}B",
        f"{margin:,.1f}%",
        f"€{avg_ticket:,.0f}" if pd.notnull(avg_ticket) else "N/A",
        get_feas_val(scen, 1),
        get_feas_val(scen, 2),
        get_feas_val(scen, 3)
    ]

kpi_table = pd.DataFrame(kpi_data)
st.dataframe(kpi_table, use_container_width=True, hide_index=True)

st.divider()

# ----------------------------------------------------
# 4. DEEP DIVE VISUALIZATIONS (TABS)
# ----------------------------------------------------
st.markdown("### 📊 Interactive Deep-Dive Visualizations")
tab1, tab2, tab3 = st.tabs(["🌍 Emissions & Financials", "✈️ Haul & Capacity Deep Dive", "⚡ Operational Energy Mix"])

with tab1:
    def get_comp_data(metric_col, baseline_val, unit="kton", divisor=1000):
        data = []
        for scen in ['100% SAF', 'Hybrid-Electric', 'Hydrogen']:
            scen_val = safe_val(agg_df, scen, '2050', metric_col)
            change = ((scen_val - baseline_val) / baseline_val) * 100 if baseline_val > 0 else 0
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

    melted_fin = agg_df.melt(id_vars=['Scenario', 'Year'], value_vars=['Total Costs [Billion €]', 'Total Revenue [Billion €]'], var_name='Metric', value_name='Amount')
    fig_fin = px.bar(melted_fin, x='Scenario', y='Amount', color='Metric', barmode='group', facet_col='Year', 
                     title="Total Financial Costs vs. Total Revenue (in Billions)",
                     color_discrete_map={'Total Costs [Billion €]': '#EF553B', 'Total Revenue [Billion €]': '#00CC96'}, category_orders=scenario_order)
    fig_fin.update_traces(texttemplate='€%{y:,.2f}B', textposition='outside', textfont_size=12)
    fig_fin.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig_fin.update_yaxes(range=[0, melted_fin['Amount'].max() * 1.25])
    st.plotly_chart(fig_fin, use_container_width=True, config=dl_config)

with tab2:
    selected_year = st.radio("Select Year for Haul Analysis:", ["2025", "2050"], horizontal=True, key="year_tab2")
    filtered_haul = haul_df[haul_df['Year'] == selected_year]
    
    col_a, col_b = st.columns(2)
    with col_a:
        fig_haul_co2 = px.bar(filtered_haul, x='Flight Type', y='CO2 Emissions [tons]', color='Scenario', barmode='group', 
                              title=f"Total CO₂ Emissions by Flight Type ({selected_year})", category_orders=scenario_order)
        st.plotly_chart(fig_haul_co2, use_container_width=True, config=dl_config)
        
    with col_b:
        fig_haul_cost = px.bar(filtered_haul, x='Flight Type', y='Total Costs [€]', color='Scenario', barmode='group', 
                               title=f"Total Financial Cost by Flight Type ({selected_year})", category_orders=scenario_order)
        st.plotly_chart(fig_haul_cost, use_container_width=True, config=dl_config)

    cap_data = filtered_haul.melt(id_vars=['Scenario', 'Flight Type'], value_vars=['Seats', 'Cargo (Tons)'])
    fig_cap = px.bar(cap_data, x='Flight Type', y='value', color='Scenario', facet_col='variable', 
                     barmode='group', title=f"Aircraft Capacity: Passenger Seats vs Cargo Volume ({selected_year})", category_orders=scenario_order)
    fig_cap.update_yaxes(matches=None, showticklabels=True)
    fig_cap.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig_cap.update_yaxes(title_text="")
    st.plotly_chart(fig_cap, use_container_width=True, config=dl_config)
    
with tab3:
    ops_year = st.radio("Select Year for Energy Data:", ["2025", "2050"], horizontal=True, key="year_tab4")
    ops_data = haul_df[haul_df['Year'] == ops_year]
    
    energy_data = ops_data.melt(id_vars=['Scenario', 'Flight Type'], value_vars=['Liquid Fuel', 'Hydrogen', 'Electricity'])
    fig_energy = px.bar(energy_data, x='Flight Type', y='value', color='Scenario', facet_col='variable', 
                        barmode='group', 
                        title=f"Average Energy Consumption per Flight by Source ({ops_year})", 
                        category_orders=scenario_order)
    
    fig_energy.update_yaxes(matches=None, showticklabels=True)
    fig_energy.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig_energy.update_yaxes(title_text="")
    st.plotly_chart(fig_energy, use_container_width=True, config=dl_config)
