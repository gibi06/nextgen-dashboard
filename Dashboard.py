import streamlit as st
import pandas as pd
import plotly.express as px
import os

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
# 2. CRASH-PROOF DATA LOADING
# ----------------------------------------------------
@st.cache_data
def load_data():
    file_path = "Cost Calculation Scenarios.xlsx"
    
    if not os.path.exists(file_path):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), f"⚠️ FOUT: Bestand '{file_path}' niet gevonden! Zorg dat de naam EXACT overeenkomt (inclusief hoofdletters) en in dezelfde map op GitHub staat."

    sheet_map = {
        'Baseline 2025': ('Baseline', '2025'), 'Baseline 2050': ('Baseline', '2050'),
        'Scenario 1 2025': ('100% SAF', '2025'), 'Scenario 1 2050': ('100% SAF', '2050'),
        'Scenario 2 2025': ('Hybrid-Electric', '2025'), 'Scenario 2 2050': ('Hybrid-Electric', '2050'),
        'Scenario 3 2025': ('Hydrogen', '2025'), 'Scenario 3 2050': ('Hydrogen', '2050')
    }

    def get_col(df, keywords):
        for c in df.columns:
            if any(k in str(c).lower() for k in keywords): 
                val = df[c]
                return val.iloc[:, 0] if isinstance(val, pd.DataFrame) else val
        return pd.Series([0]*len(df))

    dfs = []
    for sheet, (scenario, year) in sheet_map.items():
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, skiprows=5)
            if df.empty: continue
            
            temp = pd.DataFrame()
            freq = pd.to_numeric(get_col(df, ['frequency', 'flights']), errors='coerce').fillna(1)
            temp['Total Costs [€]'] = pd.to_numeric(get_col(df, ['total cost']), errors='coerce').fillna(0) * freq
            
            rev_col = [c for c in df.columns if 'revenue' in str(c).lower()]
            if rev_col:
                rev_val = df[rev_col[0]]
                rev_data = rev_val.iloc[:, 0] if isinstance(rev_val, pd.DataFrame) else rev_val
            else:
                rev_data = pd.Series([0]*len(df))
            temp['Total Revenue [€]'] = pd.to_numeric(rev_data, errors='coerce').fillna(0) * freq
            
            temp['CO2 Emissions [tons]'] = pd.to_numeric(get_col(df, ['co2']), errors='coerce').fillna(0)
            temp['Ticket Price [€]'] = pd.to_numeric(get_col(df, ['ticket']), errors='coerce').fillna(0)
            temp['Seats'] = pd.to_numeric(get_col(df, ['seat']), errors='coerce').fillna(0)
            temp['Cargo (Tons)'] = pd.to_numeric(get_col(df, ['cargo']), errors='coerce').fillna(0)
            temp['Flight Type'] = df.iloc[:,0] 
            
            if scenario in ['Baseline', '100% SAF']: 
                temp['Liquid Fuel'] = pd.to_numeric(get_col(df, ['fuel']), errors='coerce').fillna(0)
            elif scenario == 'Hybrid-Electric': 
                temp['Liquid Fuel'] = pd.to_numeric(get_col(df, ['hefa']), errors='coerce').fillna(0)
                temp['Electricity'] = pd.to_numeric(get_col(df, ['electric']), errors='coerce').fillna(0)
            elif scenario == 'Hydrogen': 
                temp['Hydrogen'] = pd.to_numeric(get_col(df, ['hydrogen']), errors='coerce').fillna(0)

            temp['Scenario'], temp['Year'] = scenario, year
            dfs.append(temp.dropna(subset=['Flight Type']))
        except Exception:
            continue

    if not dfs:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "⚠️ FOUT: Geen data kunnen inlezen. Controleer de opmaak van het Excel bestand."
        
    routes_df = pd.concat(dfs, ignore_index=True)
    routes_df = routes_df[routes_df['Flight Type'].astype(str).str.strip() != '0']
    
    agg_df = routes_df.groupby(['Scenario', 'Year']).agg({'Total Costs [€]': 'sum', 'Total Revenue [€]': 'sum', 'CO2 Emissions [tons]': 'sum'}).reset_index()
    agg_df['Total Costs [Billion €]'] = agg_df['Total Costs [€]'] / 1e9
    agg_df['Total Revenue [Billion €]'] = agg_df['Total Revenue [€]'] / 1e9
    
    haul_df = routes_df.groupby(['Scenario', 'Year', 'Flight Type']).agg({
        'Total Costs [€]': 'sum', 'Total Revenue [€]': 'sum', 'CO2 Emissions [tons]': 'sum',
        'Ticket Price [€]': 'mean', 'Seats': 'mean', 'Cargo (Tons)': 'mean',
        'Liquid Fuel': 'mean', 'Electricity': 'mean', 'Hydrogen': 'mean'
    }).reset_index()
    
    try:
        feasibility = pd.read_excel(file_path, sheet_name="feasibility")
        if "Unnamed" in str(feasibility.columns[0]):
            feasibility.rename(columns={feasibility.columns[0]: "Scenario"}, inplace=True)
    except:
        feasibility = pd.DataFrame({'Scenario': ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen'], 'Data': ['No data found']*4})
        
    return agg_df, haul_df, feasibility, None

agg_df, haul_df, feasibility, error_msg = load_data()

# ----------------------------------------------------
# 3. UI LAYOUT
# ----------------------------------------------------
st.title("🌍 NextGen Innovation Strategy Dashboard")

if error_msg:
    st.error(error_msg)
    st.stop()

st.info("""
**📚 Data Transparency & Sources:**
All KPIs and metrics displayed in this dashboard are calculated using data directly extracted from the project file: **`Cost Calculation Scenarios.xlsx`**. 
* **Financials:** Derived from flight frequencies, calculated ticket prices, and detailed cost breakdowns.
* **Emissions & Sustainability:** CO₂ penalties are calculated using the 2050 assumption of €500/ton. Emission factors used: Jet-A1 (3.84 kg/kg) and SAF/HEFA (1.30 kg/kg).
* **Feasibility:** Extracted directly from the qualitative assessment in the 'feasibility' tab.
""")

st.header("1. Executive Summary: KPI Overview (2050 Projection)")
st.markdown("This section provides a complete visual overview of all required Sustainability, Financial, and Feasibility KPIs across the 2050 transition strategies.")

scenario_order = {'Scenario': ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen']}

def safe_max(series):
    try:
        m = pd.to_numeric(series, errors='coerce').max()
        return float(m * 1.25) if pd.notna(m) and m > 0 and m != float('inf') else 1.0
    except Exception:
        return 1.0

df_2050 = agg_df[agg_df['Year'] == '2050'].copy()
if df_2050.empty:
    df_2050 = pd.DataFrame({'Scenario': ['Baseline'], 'CO2 Emissions [tons]': [0], 'Total Costs [Billion €]': [0], 'Total Revenue [Billion €]': [0]})
df_2050['CO2 Emissions [kton]'] = df_2050['CO2 Emissions [tons]'] / 1000

col1, col2 = st.columns(2)

with col1:
    fig_co2 = px.bar(df_2050, x='Scenario', y='CO2 Emissions [kton]', color='Scenario',
                     title="🌍 Total CO₂ Emissions by Scenario (kton)", category_orders=scenario_order,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_co2.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
    fig_co2.update_layout(yaxis=dict(range=[0, safe_max(df_2050['CO2 Emissions [kton]'])]), showlegend=False)
    st.plotly_chart(fig_co2, use_container_width=True, config=dl_config)

with col2:
    melted_fin = df_2050.melt(id_vars=['Scenario'], value_vars=['Total Costs [Billion €]', 'Total Revenue [Billion €]'], var_name='Metric', value_name='Amount')
    fig_fin = px.bar(melted_fin, x='Scenario', y='Amount', color='Metric', barmode='group',
                     title="💰 Financial Feasibility: Costs vs Revenue (Billion €)", category_orders=scenario_order,
                     color_discrete_map={'Total Costs [Billion €]': '#EF553B', 'Total Revenue [Billion €]': '#00CC96'})
    fig_fin.update_traces(texttemplate='€%{y:,.1f}B', textposition='outside')
    # OPGELOST: ybottom is nu simpelweg y!
    fig_fin.update_layout(yaxis=dict(range=[0, safe_max(melted_fin['Amount'])]), legend=dict(orientation="h", y=-0.2, yanchor="top", xanchor="center", x=0.5))
    st.plotly_chart(fig_fin, use_container_width=True, config=dl_config)

col3, col4 = st.columns(2)

with col3:
    ticket_2050 = haul_df[haul_df['Year'] == '2050'].groupby('Scenario')['Ticket Price [€]'].mean().reset_index()
    if ticket_2050.empty:
        ticket_2050 = pd.DataFrame({'Scenario': ['Baseline'], 'Ticket Price [€]': [0]})
        
    fig_ticket = px.bar(ticket_2050, x='Scenario', y='Ticket Price [€]', color='Scenario',
                        title="✈️ Average Consumer Ticket Price (€)", category_orders=scenario_order,
                        color_discrete_sequence=px.colors.qualitative.Prism)
    fig_ticket.update_traces(texttemplate='€%{y:,.0f}', textposition='outside')
    fig_ticket.update_layout(yaxis=dict(range=[0, safe_max(ticket_2050['Ticket Price [€]'])]), showlegend=False)
    st.plotly_chart(fig_ticket, use_container_width=True, config=dl_config)

with col4:
    st.markdown("### ⚖️ Technical & Safety Feasibility")
    st.markdown("Qualitative scoring based on 2050 projections.")
    
    def style_symbols(val):
        color_mapping = {'++': ('darkgreen', 'white'), '+': ('#32CD32', 'black'), '++/-': ('darkorange', 'white'), '+/-': ('#FFA500', 'black'), '-': ('red', 'white')}
        val_str = str(val).strip()
        if val_str in color_mapping: 
            return f'background-color: {color_mapping[val_str][0]}; color: {color_mapping[val_str][1]}; font-weight: bold; text-align: center;'
        return 'text-align: center;'
    
    if hasattr(feasibility.style, 'map'):
        st.dataframe(feasibility.style.map(style_symbols), use_container_width=True)
    else:
        st.dataframe(feasibility.style.applymap(style_symbols), use_container_width=True)

st.divider()

# ----------------------------------------------------
# 4. DEEP DIVE 
# ----------------------------------------------------
st.header("2. Deep-Dive: Flight Type & Energy Analysis")
ops_year = st.radio("Select Year for detailed breakdown:", ["2025", "2050"], horizontal=True)
filtered_haul = haul_df[haul_df['Year'] == ops_year]

if filtered_haul.empty:
    st.warning(f"Geen data beschikbaar voor jaar {ops_year}")
else:
    col_a, col_b = st.columns(2)
    with col_a:
        fig_haul_co2 = px.bar(filtered_haul, x='Flight Type', y='CO2 Emissions [tons]', color='Scenario', barmode='group', title=f"Total CO₂ by Flight Type ({ops_year})", category_orders=scenario_order)
        st.plotly_chart(fig_haul_co2, use_container_width=True, config=dl_config)

    with col_b:
        energy_data = filtered_haul.melt(id_vars=['Scenario', 'Flight Type'], value_vars=['Liquid Fuel', 'Hydrogen', 'Electricity'])
        fig_energy = px.bar(energy_data, x='Flight Type', y='value', color='Scenario', facet_col='variable', barmode='group', title=f"Energy Consumption by Source ({ops_year})", category_orders=scenario_order)
        fig_energy.update_yaxes(matches=None, showticklabels=True)
        fig_energy.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig_energy.update_yaxes(title_text="")
        st.plotly_chart(fig_energy, use_container_width=True, config=dl_config)

st.markdown("<div style='text-align: center; color: gray;'><br><br><i>NextGen Aviation - End of Dashboard Overview</i></div>", unsafe_allow_html=True)
