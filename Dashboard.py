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
        except Exception as e:
            st.warning(f"Note: Could not fully process sheet '{sheet}' due to formatting.")
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

scenario_order = {'Scenario': ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen']}

# Filter for 2050 Data for the Executive Summary
df_2050 = agg_df[agg_df['Year'] == '2050'].copy()
df_2050['CO2 Emissions [kton]'] = df_2050['CO2 Emissions [tons]'] / 1000

# Average ticket price per scenario in 2050
ticket_2050 = haul_df[haul_df['Year'] == '2050'].groupby('Scenario')['Ticket Price [€]'].mean().reset_index()

# ----------------------------------------------------
# 3. DASHBOARD UI - VISUAL EXECUTIVE SUMMARY
# ----------------------------------------------------
st.title("🌍 NextGen Innovation Strategy Dashboard")

st.subheader("📊 Executive Summary: One-Page KPI Overview (2050 Projection)")
st.markdown("This section provides a complete visual overview of all required Sustainability, Financial, and Feasibility KPIs across the 2050 transition strategies, exactly as requested.")

# --- 2x2 VISUAL GRID FOR SUMMARY ---
col1, col2 = st.columns(2)

# Graph 1: Sustainability (CO2)
with col1:
    fig_co2_sum = px.bar(df_2050, x='Scenario', y='CO2 Emissions [kton]', color='Scenario',
                         title="🌍 Total CO₂ Emissions by Scenario (kton)",
                         category_orders=scenario_order,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_co2_sum.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
    fig_co2_sum.update_layout(yaxis=dict(range=[0, df_2050['CO2 Emissions [kton]'].max() * 1.25]), showlegend=False)
    st.plotly_chart(fig_co2_sum, use_container_width=True, config=dl_config)

# Graph 2: Financials (Costs vs Revenue)
with col2:
    melted_fin_sum = df_2050.melt(id_vars=['Scenario'], value_vars=['Total Costs [Billion €]', 'Total Revenue [Billion €]'], var_name='Metric', value_name='Amount')
    fig_fin_sum = px.bar(melted_fin_sum, x='Scenario', y='Amount', color='Metric', barmode='group',
                         title="💰 Financial Feasibility: Costs vs Revenue (Billion €)",
                         category_orders=scenario_order,
                         color_discrete_map={'Total Costs [Billion €]': '#EF553B', 'Total Revenue [Billion €]': '#00CC96'})
    fig_fin_sum.update_traces(texttemplate='€%{y:,.1f}B', textposition='outside')
    fig_fin_sum.update_layout(yaxis=dict(range=[0, melted_fin_sum['Amount'].max() * 1.25]), legend=dict(orientation="h", ybottom=-0.2, yanchor="top", xanchor="center", x=0.5))
    st.plotly_chart(fig_fin_sum, use_container_width=True, config=dl_config)

col3, col4 = st.columns(2)

# Graph 3: Consumer / Ticket Prices
with col3:
    fig_ticket_sum = px.bar(ticket_2050, x='Scenario', y='Ticket Price [€]', color='Scenario',
                            title="✈️ Average Consumer Ticket Price (€)",
                            category_orders=scenario_order,
                            color_discrete_sequence=px.colors.qualitative.Prism)
    fig_ticket_sum.update_traces(texttemplate='€%{y:,.0f}', textposition='outside')
    fig_ticket_sum.update_layout(yaxis=dict(range=[0, ticket_2050['Ticket Price [€]'].max() * 1.25]), showlegend=False)
    st.plotly_chart(fig_ticket_sum, use_container_width=True, config=dl_config)

# Graph 4: Feasibility (Visual Grid)
with col4:
    st.markdown("### ⚖️ Technical & Safety Feasibility Assessment")
    st.markdown("Qualitative scoring based on 2050 projections.")
    
    # Styling function for the grid
    def style_symbols(val):
        color_mapping = {'++': ('darkgreen', 'white'), '+': ('#32CD32', 'black'), '++/-': ('darkorange', 'white'), '+/-': ('#FFA500', 'black'), '-': ('red', 'white')}
        val_str = str(val).strip()
        if val_str in color_mapping:
            bg_color, text_color = color_mapping[val_str]
            return f'background-color: {bg_color}; color: {text_color}; font-weight: bold; text-align: center;'
        return 'text-align: center;'

    if hasattr(feasibility.style, 'map'):
        styled_feasibility = feasibility.style.map(style_symbols)
    else:
        styled_feasibility = feasibility.style.applymap(style_symbols)
        
    st.dataframe(styled_feasibility, use_container_width=True, height=250)
    st.markdown("<small><i>Legend: [++] Very Strong | [+] Strong | [+/-] Moderate | [-] Challenging</i></small>", unsafe_allow_html=True)

# --- DATA TRANSPARENCY SECTION (MOVED TO THE BOTTOM OF THE SUMMARY) ---
st.write("") # small spacing
st.info("""
**📚 Data Transparency & Sources:**
All KPIs and metrics displayed in this dashboard are calculated using data directly extracted from the project file: **`Cost Calculation Scenarios.xlsx`**. 
* **Financials:** Derived from flight frequencies, calculated ticket prices, and detailed cost breakdowns (e.g., crew, maintenance, fuel).
* **Emissions & Sustainability:** CO₂ penalties are calculated using the 2050 assumption of €500/ton. Emission factors used: Jet-A1 (3.84 kg/kg) and SAF/HEFA (1.30 kg/kg).
* **Feasibility:** Extracted directly from the qualitative assessment in the 'feasibility' tab.
""")

st.divider()

# ----------------------------------------------------
# 4. DEEP DIVE VISUALIZATIONS (EXTRA TABS)
# ----------------------------------------------------
st.markdown("### 🔍 Interactive Deep-Dive Visualizations (Extra Details)")
tab1, tab2 = st.tabs(["✈️ Haul & Capacity Deep Dive", "⚡ Operational Energy Mix"])

with tab1:
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
    
with tab2:
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
