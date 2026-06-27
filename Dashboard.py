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
        'Scenario 3 2050': ('Hydrogen', '2050'),
    }
    
    list_agg = []
    list_haul = []
    
    # Haalbaarheid Matrix (Kwalitatief)
    feasibility_data = {
        'Metric': ['Technical Readiness', 'Infrastructure Req.', 'Regulatory Approval', 'Public Acceptance', 'Scalability'],
        '100% SAF': ['High', 'Low', 'Approved', 'High', 'Medium'],
        'Hybrid-Electric': ['Medium', 'Medium', 'Pending', 'High', 'Low'],
        'Hydrogen': ['Low', 'High', 'Concept', 'Medium', 'High']
    }
    feasibility_df = pd.DataFrame(feasibility_data)

    for sheet, (scen, yr) in sheet_map.items():
        try:
            # 1. Totaaloverzicht inlezen
            df_tot = pd.read_excel(file_path, sheet_name=sheet, nrows=15)
            
            # Extractie van hoofdvariabelen met foutafhandeling
            def get_val(lbl, col_idx=1):
                row = df_tot[df_tot.iloc[:, 0].astype(str).str.contains(lbl, case=False, na=False)]
                return float(row.iloc[0, col_idx]) if not row.empty else 0.0

            co2 = get_val('CO2 Emissions')
            nox = get_val('NOx')
            sox = get_val('SOx')
            costs = get_val('Total Costs')
            rev = get_val('Total Revenue')
            margin = get_val('Profit Margin')

            list_agg.append({
                'Scenario': scen, 'Year': yr,
                'CO2 Emissions [tons]': co2, 'NOx [tons]': nox, 'SOx [tons]': sox,
                'Total Costs [Billion €]': costs, 'Total Revenue [Billion €]': rev,
                'Profit Margin [%]': margin
            })

            # 2. Haul (Afstands) data inlezen
            df_haul = pd.read_excel(file_path, sheet_name=sheet, skiprows=18)
            df_haul = df_haul.dropna(subset=[df_haul.columns[0]])
            df_haul.columns = [
                'Flight Type', 'Distance [km]', 'Frequency/Week', 'Seats', 'Cargo (Tons)',
                'Fuel Burn [kg]', 'CO2 [tons]', 'Ticket Price [€]', 'Liquid Fuel', 'Hydrogen', 'Electricity'
            ]
            df_haul['Scenario'] = scen
            df_haul['Year'] = yr
            list_haul.append(df_haul)

        except Exception as e:
            st.error(f"Fout bij laden van sheet '{sheet}': {e}")

    return pd.DataFrame(list_agg), pd.concat(list_haul, ignore_index=True), feasibility_df

agg_df, haul_df, feasibility = load_data()

# Helperfunctie voor risicoloze data-lookups
def safe_val(df, scen, yr, col):
    sub = df[(df['Scenario'] == scen) & (df['Year'] == yr)]
    return sub[col].values[0] if not sub.empty else 0.0

# Baseline referentiewaarde bepalen
b_2025_co2 = safe_val(agg_df, 'Baseline', '2025', 'CO2 Emissions [tons]')

# ----------------------------------------------------
# 3. PERMANENTE SIDEBAR (DATA TRANSPARANTIE & BRONNEN)
# ----------------------------------------------------
with st.sidebar:
    st.header("📚 Data Transparantie & Bronnen")
    st.markdown("""
    Alle getoonde KPI's en grafieken in dit dashboard zijn direct berekend op basis van de officiële projectdata.
    
    **Brondocumentatie:**
    * **Hoofdbron:** `Cost Calculation Scenarios.xlsx`
    * **Financiële Data:** Geaggregeerd op basis van vlutfrequencies, dynamische ticketprijzen en operationele kosten.
    * **Duurzaamheid & Emissies:** CO₂-beprijzing berekend volgens de 2050 EU-richtlijn (€500/ton). 
    * **Emissiefactoren:** Jet-A1 (3.84 kg/kg) en SAF/HEFA (1.30 kg/kg).
    * **Feasibility:** Gebaseerd op de kwalitatieve haalbaarheidsmatrix uit het strategische PPG-document.
    """)
    st.divider()
    st.info("💡 *Dit overzicht blijft altijd in beeld om volledige data-transparantie te garanderen.*")

# ----------------------------------------------------
# 4. HOOFDPAGINA: TITEL & DIRECT CENTRAAL KPI OVERZICHT
# ----------------------------------------------------
st.title("🌍 NextGen Aviation Strategy Dashboard")
st.markdown("Dit dashboard biedt direct inzicht in de strategische afwegingen tussen duurzaamheid, financiële haalbaarheid en operationele metrics voor 2050.")

st.divider()

# --- VERPLICHT CENTRAAL EENPAGINA-OVERZICHT VAN ALLE KPI'S (EIS RONALD JANSSEN) ---
st.subheader("📌 Centrale Strategie KPI Overzicht (2050 Projecties vs. 2025 Baseline)")

# Rij 1: Duurzaamheid KPI's (Milieu)
st.markdown("**🍀 Milieu-impact (CO₂ Totale Uitstoot & Reductie %):**")
cols_env = st.columns(4)
display_targets = [
    ('Baseline', '2025', 'Huidige Operatie (2025 Baseline)'), 
    ('100% SAF', '2050', '100% SAF (Projectie 2050)'), 
    ('Hybrid-Electric', '2050', 'Hybrid-Electric (Projectie 2050)'), 
    ('Hydrogen', '2050', 'Hydrogen (Projectie 2050)')
]
for i, (scen, yr, label) in enumerate(display_targets):
    val = safe_val(agg_df, scen, yr, 'CO2 Emissions [tons]')
    if (scen == 'Baseline' and yr == '2025') or b_2025_co2 == 0:
        delta_str = "Referentie"
    else:
        delta_str = f"{((val - b_2025_co2) / b_2025_co2) * 100:+.1f}% vs Baseline"
    with cols_env[i]:
        st.metric(label=label, value=f"{val / 1000:,.1f} kton CO₂", delta=delta_str, delta_color="inverse" if "Ref" not in delta_str else "normal")

# Rij 2: Financiële KPI's & Rendement (Nu direct op de hoofdpagina zichtbaar)
st.markdown("**💰 Financieel Rendement & Kosten (Projecties 2050):**")
cols_fin = st.columns(3)
scenarios = ['100% SAF', 'Hybrid-Electric', 'Hydrogen']
for i, scen in enumerate(scenarios):
    margin_2050 = safe_val(agg_df, scen, '2050', 'Profit Margin [%]')
    revenue_2050 = safe_val(agg_df, scen, '2050', 'Total Revenue [Billion €]')
    costs_2050 = safe_val(agg_df, scen, '2050', 'Total Costs [Billion €]')
    with cols_fin[i]:
        st.metric(
            label=f"Scenario: {scen}", 
            value=f"Marge: {margin_2050:.1f}%", 
            delta=f"Kosten: €{costs_2050:.2f}B | Omzet: €{revenue_2050:.2f}B",
            delta_color="normal"
        )

st.divider()

# ----------------------------------------------------
# 5. DIEPTEDIVISIE EN GRAFIEKEN PER THEMA (TABBLADEN)
# ----------------------------------------------------
st.markdown("### 📊 Gedetailleerde Trendanalyses & Diepduiken")
tab1, tab2, tab3, tab4 = st.tabs(["🌍 Milieu & Financiële Trends", "✈️ Afstands- & Routeanalyse", "⚖️ Strategische Haalbaarheid", "⚙️ Operationele Parameters"])

scenario_order = {"Scenario": ["Baseline", "100% SAF", "Hybrid-Electric", "Hydrogen"]}

# ==========================================
# TAB 1: EMISSIONS & FINANCIALS TRENDS
# ==========================================
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Totale CO₂ Emissies per Scenario")
        fig_co2 = px.bar(agg_df, x='Year', y='CO2 Emissions [tons]', color='Scenario', barmode='group',
                         title="CO₂ Emissie Ontwikkeling (2025 vs 2050)", category_orders=scenario_order)
        st.plotly_chart(fig_co2, use_container_width=True, config=dl_config)
        
    with col2:
        st.subheader("Winstmarges (%) Ontwikkeling")
        fig_margin = px.line(agg_df, x='Year', y='Profit Margin [%]', color='Scenario', markers=True,
                             title="Profit Margin Ontwikkeling over Tijd", category_orders=scenario_order)
        st.plotly_chart(fig_margin, use_container_width=True, config=dl_config)

    st.subheader("Gedetailleerde Financiële Splitsing (€ Miljard)")
    fig_fin = px.bar(agg_df.melt(id_vars=['Scenario', 'Year'], value_vars=['Total Costs [Billion €]', 'Total Revenue [Billion €]']),
                     x='Year', y='value', color='variable', facet_col='Scenario', barmode='group',
                     title="Kosten vs Omzet per Scenario")
    st.plotly_chart(fig_fin, use_container_width=True, config=dl_config)

# ==========================================
# TAB 2: HAUL DEEP DIVE
# ==========================================
with tab2:
    st.subheader("Analyse per Route/Afstandstype")
    scen_year = st.radio("Selecteer Jaar voor Route-analyse:", ["2025", "2050"], horizontal=True, key="year_tab2")
    
    filtered_haul = haul_df[haul_df['Year'] == scen_year]
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        fig_route_co2 = px.bar(filtered_haul, x='Flight Type', y='CO2 [tons]', color='Scenario', barmode='group',
                               title=f"CO₂ Uitstoot per Routetype ({scen_year})", category_orders=scenario_order)
        st.plotly_chart(fig_route_co2, use_container_width=True, config=dl_config)
    with col_h2:
        fig_freq = px.bar(filtered_haul, x='Flight Type', y='Frequency/Week', color='Scenario', barmode='group',
                          title=f"Vluchtfrequentie per Week ({scen_year})", category_orders=scenario_order)
        st.plotly_chart(fig_freq, use_container_width=True, config=dl_config)

# ==========================================
# TAB 3: FEASIBILITY MATRIX
# ==========================================
with tab3:
    st.subheader("Kwalitatieve Haalbaarheidsmatrix (Feasibility)")
    st.markdown("Dit overzicht toont de operationele en infrastructurele risico's per 2050 transitiepad:")
    
    def style_symbols(val):
        if val in ['High', 'Approved']: return 'background-color: #d4edda; color: #155724;'
        if val in ['Medium', 'Pending']: return 'background-color: #fff3cd; color: #856404;'
        if val in ['Low', 'High Req.', 'Concept']: return 'background-color: #f8d7da; color: #721c24;'
        return ''
    
    styled_feasibility = feasibility.style.applymap(style_symbols) if hasattr(feasibility.style, 'applymap') else feasibility.style.map(style_symbols)
    st.dataframe(styled_feasibility, use_container_width=True)

# ==========================================
# TAB 4: OPERATIONAL KPIs
# ==========================================
with tab4:
    st.subheader("Operationele & Technische Parameters")
    ops_year = st.radio("Selecteer Jaar voor Operationele Data:", ["2025", "2050"], horizontal=True, key="year_tab4")
    ops_data = haul_df[haul_df['Year'] == ops_year]
    
    fig_tickets = px.bar(ops_data, x='Flight Type', y='Ticket Price [€]', color='Scenario', barmode='group', title=f"Gemiddelde Ticketprijs per Route ({ops_year})", category_orders=scenario_order)
    st.plotly_chart(fig_tickets, use_container_width=True, config=dl_config)
    
    fig_energy = px.bar(ops_data.melt(id_vars=['Scenario', 'Flight Type'], value_vars=['Liquid Fuel', 'Hydrogen', 'Electricity']), 
                        x='Flight Type', y='value', color='Scenario', facet_col='variable', barmode='group', title=f"Energieverbruik naar Bron ({ops_year})", category_orders=scenario_order)
    st.plotly_chart(fig_energy, use_container_width=True, config=dl_config)

    cap_data = ops_data.melt(id_vars=['Scenario', 'Flight Type'], value_vars=['Seats', 'Cargo (Tons)'])
    fig_cap = px.bar(cap_data, x='Flight Type', y='value', color='Scenario', facet_col='variable', 
                     barmode='group', title=f"Vliegtuigcapaciteit: Passagiersstoelen vs Vrachtvolume ({ops_year})", category_orders=scenario_order)
    fig_cap.update_yaxes(matches=None, showticklabels=True)
    fig_cap.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig_cap.update_yaxes(title_text="")
    st.plotly_chart(fig_cap, use_container_width=True, config=dl_config)
