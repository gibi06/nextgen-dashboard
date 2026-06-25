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
    delta_str = None if (scen == 'Baseline' and yr == '2025') or b_2025_co2 == 0 else f"{((val - b_2025_co2) / b_2025_co2) * 100:+.1f}% CO₂ Emissions" 
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
            scen_val = safe_val(agg_df, scen, '2050', metric_col)
            change = ((scen_val - baseline_val) / baseline_val) * 100 if baseline_val > 0 else 0
            data.append({'Scenario': scen, 'Type': 'Baseline 2025', 'Value': baseline_val, 'Label': f"{baseline_val/divisor:,.0f} {unit}"})
            data.append({'Scenario': scen, 'Type': '2050 Projection', 'Value': scen_val, 'Label': f"{scen_val/divisor:,.0f} {unit} (<span style='color: {'red' if change > 0 else 'green'}'>{change:+.1f}%</span>)"})
        return pd.DataFrame(data)

    co2_df = get_comp_data('CO2 Emissions [tons]', b_2025_co2, unit="kton", divisor=1000)
    fig_co2 = px.bar(co2_df, x='Scenario', y='Value', color='Type', barmode='group', text='Label', 
                     title="Projected CO₂ Emissions by Scenario (Compared to 2025 Baseline)",
                     color_discrete_map={'Baseline 2025': '#94A3B8', '2050 Projection': '#10B981'}, category_orders={'Scenario': ['100% SAF', 'Hybrid-Electric', 'Hydrogen']})
    fig_co2.update_traces(textposition='outside', textfont_size=13)
    st.plotly_chart(fig_co2, use_container_width=True, config=dl_config)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("NOx Emissions [Tons]")
        nox_df = get_comp_data('NOx Emissions [tons]', b_2025_nox, unit="tons", divisor=1)
        fig_nox = px.bar(nox_df, x='Scenario', y='Value', color='Type', barmode='group', text='Label', title="Projected NOx Emissions", color_discrete_map={'Baseline 2025': '#94A3B8', '2050 Projection': '#F59E0B'})
        st.plotly_chart(fig_nox, use_container_width=True, config=dl_config)
    with c2:
        st.subheader("SOx Emissions [Tons]")
        sox_df = get_comp_data('SOx Emissions [tons]', b_2025_sox, unit="tons", divisor=1)
        fig_sox = px.bar(sox_df, x='Scenario', y='Value', color='Type', barmode='group', text='Label', title="Projected SOx Emissions", color_discrete_map={'Baseline 2025': '#94A3B8', '2050 Projection': '#EF4444'})
        st.plotly_chart(fig_sox, use_container_width=True, config=dl_config)

    st.divider()
    st.subheader("2. Financial Volume & Profitability")
    f1, f2 = st.columns(2)
    with f1:
        melted_fin = agg_df.melt(id_vars=['Scenario', 'Year'], value_vars=['Total Costs [Billion €]', 'Total Revenue [Billion €]'], var_name='Metric', value_name='Amount')
        fig_fin = px.bar(melted_fin, x='Scenario', y='Amount', color='Metric', barmode='group', facet_col='Year', title="Financial Costs vs Revenue", color_discrete_map={'Total Costs [Billion €]': '#EF553B', 'Total Revenue [Billion €]': '#00CC96'})
        st.plotly_chart(fig_fin, use_container_width=True, config=dl_config)
    with f2:
        fig_margin = px.bar(agg_df, x='Scenario', y='Profit Margin [%]', color='Year', barmode='group', text_auto='.1f', title='Company Profit Margin (%)', color_discrete_map={'2025': '#94A3B8', '2050': '#3B82F6'})
        st.plotly_chart(fig_margin, use_container_width=True, config=dl_config)

    # --- DATA SOURCES SECTION---
    st.divider()
    st.subheader("Data Sources & Methodology")
    st.markdown("""
   **📚 Data Transparency & Sources:**
All KPIs and metrics displayed in this dashboard are calculated using data directly extracted from the project file: **`Cost Calculation Scenarios.xlsx`**. 
* **Financials:** Derived from flight frequencies, calculated ticket prices, and detailed cost breakdowns (e.g., crew, maintenance, fuel).
* **Emissions & Sustainability:** CO₂ penalties are calculated using the 2050 assumption of €500/ton. Emission factors used: Jet-A1 (3.84 kg/kg) and SAF/HEFA (1.30 kg/kg).
* **Feasibility:** Extracted directly from the qualitative assessment in the 'feasibility' tab.
""")
# ==========================================
# TAB 2: HAUL DEEP DIVE
# ==========================================
with tab2:
    st.subheader("Analysis by Flight Type (Short Haul vs Long Haul)")
    selected_year = st.radio("Select Year:", ["2025", "2050"], horizontal=True, key="year_tab2")
    filtered_haul = haul_df[haul_df['Year'] == selected_year]
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(px.bar(filtered_haul, x='Flight Type', y='CO2 Emissions [tons]', color='Scenario', barmode='group', title=f"CO₂ by Flight Type ({selected_year})"), use_container_width=True, config=dl_config)
    with col_b:
        st.plotly_chart(px.bar(filtered_haul, x='Flight Type', y='Total Costs [€]', color='Scenario', barmode='group', title=f"Cost by Flight Type ({selected_year})"), use_container_width=True, config=dl_config)
    st.dataframe(filtered_haul, use_container_width=True, hide_index=True)

# ==========================================
# TAB 3: FEASIBILITY
# ==========================================
with tab3:
    st.subheader("Feasibility Assessment")
    def style_symbols(val):
        color_mapping = {'++': ('darkgreen', 'white'), '+': ('#32CD32', 'black'), '++/-': ('darkorange', 'white'), '+/-': ('#FFA500', 'black'), '-': ('red', 'white')}
        return f'background-color: {color_mapping[str(val).strip()][0]}; color: {color_mapping[str(val).strip()][1]};' if str(val).strip() in color_mapping else ''
    
    styled_feasibility = feasibility.style.applymap(style_symbols) if hasattr(feasibility.style, 'applymap') else feasibility.style.map(style_symbols)
    st.dataframe(styled_feasibility, use_container_width=True)

# ==========================================
# TAB 4: OPERATIONAL KPIs
# ==========================================
with tab4:
    st.subheader("Operational & Technical KPIs")
    ops_year = st.radio("Select Year for Operational Data:", ["2025", "2050"], horizontal=True, key="year_tab4")
    ops_data = haul_df[haul_df['Year'] == ops_year]
    
    fig_tickets = px.bar(ops_data, x='Flight Type', y='Ticket Price [€]', color='Scenario', barmode='group', title=f"Avg Ticket Price ({ops_year})")
    st.plotly_chart(fig_tickets, use_container_width=True, config=dl_config)
    
    fig_energy = px.bar(ops_data.melt(id_vars=['Scenario', 'Flight Type'], value_vars=['Liquid Fuel', 'Hydrogen', 'Electricity']), 
                        x='Flight Type', y='value', color='Scenario', facet_col='variable', barmode='group', title=f"Energy Consumption by Source ({ops_year})")
    st.plotly_chart(fig_energy, use_container_width=True, config=dl_config)

    fig_cap = px.bar(ops_data.melt(id_vars=['Scenario', 'Flight Type'], value_vars=['Seats', 'Cargo (Tons)']), 
                     x='Flight Type', y='value', color='Scenario', facet_col='variable', barmode='group', title=f"Capacity ({ops_year})")
    st.plotly_chart(fig_cap, use_container_width=True, config=dl_config)
