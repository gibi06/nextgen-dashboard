import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------------------------------
# 1. SETUP
# ----------------------------------------------------
st.set_page_config(page_title="NextGen Strategy Dashboard", page_icon="🌍", layout="wide")

# ----------------------------------------------------
# 2. LOAD & PREPARE DATA
# ----------------------------------------------------
@st.cache_data
def load_data():
    # UPDATED: Reference to the new file version
    file_path = r"C:\Users\gilbert\OneDrive - HvA\Abdulla Alkwidr's files - Block 8 (Col2-5)\project\Cost Calculation Scenarios.xlsx"
    
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

    dfs = []
    for sheet, (scenario, year) in sheet_map.items():
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, skiprows=5)
            
            # Find columns dynamically
            c_type = [c for c in df.columns if 'flight type' in str(c).lower()][0]
            c_cost = [c for c in df.columns if 'total cost' in str(c).lower()][0]
            
            # Revenue
            rev_cols = [c for c in df.columns if 'revenue' in str(c).lower() or 'revenu' in str(c).lower()]
            c_rev = rev_cols[-1] 
            
            # Emissions
            c_co2 = [c for c in df.columns if 'total co2' in str(c).lower()][0]
            c_nox = [c for c in df.columns if 'total nox' in str(c).lower()][0]
            c_sox = [c for c in df.columns if 'total sox' in str(c).lower()][0]
            
            # Find the Flight Frequency / # flights column dynamically
            c_freq = [c for c in df.columns if 'frequency' in str(c).lower() or 'flights' in str(c).lower()][0]
            
            # Extract all needed columns
            temp = df[[c_type, c_cost, c_rev, c_co2, c_nox, c_sox, c_freq]].dropna(subset=[c_type]).copy()
            
            # Capture frequency as a strict numeric value
            freq_numeric = pd.to_numeric(temp[c_freq], errors='coerce').fillna(0)
            
            # Multiply per-flight Cost and Revenue by Frequency to get Annual Totals
            temp[c_cost] = pd.to_numeric(temp[c_cost], errors='coerce').fillna(0) * freq_numeric
            temp[c_rev] = pd.to_numeric(temp[c_rev], errors='coerce').fillna(0) * freq_numeric
            
            # FIX: Convert emissions to numeric to handle Excel dashes ('-') which act as strings for zero.
            temp[c_co2] = pd.to_numeric(temp[c_co2], errors='coerce').fillna(0)
            temp[c_nox] = pd.to_numeric(temp[c_nox], errors='coerce').fillna(0)
            temp[c_sox] = pd.to_numeric(temp[c_sox], errors='coerce').fillna(0)
            
            # NOTE: If your new Excel file lists emissions "per flight" (just like costs), 
            # you must UNCOMMENT the 3 lines below to multiply them by frequency:
            # temp[c_co2] = temp[c_co2] * freq_numeric
            # temp[c_nox] = temp[c_nox] * freq_numeric
            # temp[c_sox] = temp[c_sox] * freq_numeric
            
            # Drop the frequency column now as it is no longer needed
            temp = temp[[c_type, c_cost, c_rev, c_co2, c_nox, c_sox]]
            
            # Rename for standardization
            temp.columns = ['Flight Type', 'Total Costs [€]', 'Total Revenue [€]', 'CO2 Emissions [tons]', 'NOx Emissions [tons]', 'SOx Emissions [tons]']
            temp['Scenario'] = scenario
            temp['Year'] = year
            dfs.append(temp)
        except Exception as e:
            st.error(f"Error loading {sheet}: {e}")
            
    routes_df = pd.concat(dfs, ignore_index=True)
    
    # 1. OVERALL AGGREGATION
    agg_df = routes_df.groupby(['Scenario', 'Year'])[['Total Costs [€]', 'Total Revenue [€]', 'CO2 Emissions [tons]', 'NOx Emissions [tons]', 'SOx Emissions [tons]']].sum().reset_index()
    agg_df['Profit Margin [%]'] = ((agg_df['Total Revenue [€]'] - agg_df['Total Costs [€]']) / agg_df['Total Revenue [€]']) * 100
    
    # Convert to Billions for Executive Display
    agg_df['Total Costs [Billion €]'] = agg_df['Total Costs [€]'] / 1e9
    agg_df['Total Revenue [Billion €]'] = agg_df['Total Revenue [€]'] / 1e9
    
    # 2. HAUL AGGREGATION (Grouped by Long/Short Haul)
    haul_df = routes_df.groupby(['Scenario', 'Year', 'Flight Type'])[['Total Costs [€]', 'Total Revenue [€]', 'CO2 Emissions [tons]', 'NOx Emissions [tons]', 'SOx Emissions [tons]']].sum().reset_index()
    
    # 3. FEASIBILITY DATA
    feasibility = pd.read_excel(file_path, sheet_name="feasibility")
    
    if "Unnamed" in str(feasibility.columns[0]):
        feasibility.rename(columns={feasibility.columns[0]: "Scenario"}, inplace=True)
        
    return agg_df, haul_df, feasibility

agg_df, haul_df, feasibility = load_data()

# --- Get Baselines for Math ---
b_2025_co2 = agg_df.loc[(agg_df['Scenario'] == 'Baseline') & (agg_df['Year'] == '2025'), 'CO2 Emissions [tons]'].values[0]
b_2025_nox = agg_df.loc[(agg_df['Scenario'] == 'Baseline') & (agg_df['Year'] == '2025'), 'NOx Emissions [tons]'].values[0]
b_2025_sox = agg_df.loc[(agg_df['Scenario'] == 'Baseline') & (agg_df['Year'] == '2025'), 'SOx Emissions [tons]'].values[0]

# --- UNIVERSAL CHART SORTING ORDER ---
scenario_order = {'Scenario': ['Baseline', '100% SAF', 'Hybrid-Electric', 'Hydrogen']}

# ----------------------------------------------------
# 3. DASHBOARD UI
# ----------------------------------------------------
st.title("🌍 NextGen Innovation Strategy Dashboard")
st.markdown("Prioritizing Environmental Impact (CO₂, NOx, SOx) & Financial Feasibility of 2050 Aviation Transition Strategies.")
st.divider()

# --- TOP KPI METRICS ---
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
        st.metric(
            label=label,
            value=f"{val / 1000:,.0f} kton CO₂",
            delta=delta_str,
            delta_color="inverse" 
        )

st.write("") 

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🌍 Overall Impact & Financials", "✈️ Haul Deep Dive (Short vs Long)", "⚖️ Feasibility"])

# ==========================================
# TAB 1: ENVIRONMENTAL & FINANCIAL OVERVIEW
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
    fig_co2 = px.bar(co2_df, x='Scenario', y='Value', color='Type', barmode='group', text='Label', color_discrete_map={'Baseline 2025': '#94A3B8', '2050 Projection': '#10B981'}, category_orders={'Scenario': ['100% SAF', 'Hybrid-Electric', 'Hydrogen']})
    fig_co2.update_traces(textposition='outside', textfont_size=13)
    fig_co2.update_layout(yaxis_title="CO₂ Emissions [Tons]", yaxis=dict(range=[0, co2_df['Value'].max() * 1.25]))
    st.plotly_chart(fig_co2, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("NOx Emissions [Tons]")
        nox_df = get_comp_data('NOx Emissions [tons]', b_2025_nox, unit="tons", divisor=1)
        fig_nox = px.bar(nox_df, x='Scenario', y='Value', color='Type', barmode='group', text='Label', color_discrete_map={'Baseline 2025': '#94A3B8', '2050 Projection': '#F59E0B'}, category_orders={'Scenario': ['100% SAF', 'Hybrid-Electric', 'Hydrogen']})
        fig_nox.update_traces(textposition='outside', textfont_size=12)
        fig_nox.update_layout(yaxis=dict(range=[0, nox_df['Value'].max() * 1.25]))
        st.plotly_chart(fig_nox, use_container_width=True)
        
    with c2:
        st.subheader("SOx Emissions [Tons]")
        sox_df = get_comp_data('SOx Emissions [tons]', b_2025_sox, unit="tons", divisor=1)
        fig_sox = px.bar(sox_df, x='Scenario', y='Value', color='Type', barmode='group', text='Label', color_discrete_map={'Baseline 2025': '#94A3B8', '2050 Projection': '#EF4444'}, category_orders={'Scenario': ['100% SAF', 'Hybrid-Electric', 'Hydrogen']})
        fig_sox.update_traces(textposition='outside', textfont_size=12)
        fig_sox.update_layout(yaxis=dict(range=[0, sox_df['Value'].max() * 1.25]))
        st.plotly_chart(fig_sox, use_container_width=True)

    st.divider()

    st.subheader("2. Financial Volume & Profitability (2025 vs 2050)")
    st.markdown("Observe the financial cost required to achieve the environmental targets above (Values in **Billions**).")
    
    melted_fin = agg_df.melt(id_vars=['Scenario', 'Year'], value_vars=['Total Costs [Billion €]', 'Total Revenue [Billion €]'], var_name='Metric', value_name='Amount')
    
    f1, f2 = st.columns(2)
    with f1:
        fig_fin = px.bar(melted_fin, x='Scenario', y='Amount', color='Metric', barmode='group', facet_col='Year', color_discrete_map={'Total Costs [Billion €]': '#EF553B', 'Total Revenue [Billion €]': '#00CC96'}, category_orders=scenario_order)
        fig_fin.update_traces(texttemplate='€%{y:,.2f}B', textposition='outside', textfont_size=12)
        fig_fin.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig_fin.update_yaxes(range=[0, melted_fin['Amount'].max() * 1.25])
        st.plotly_chart(fig_fin, use_container_width=True)
        
    with f2:
        fig_margin = px.bar(agg_df, x='Scenario', y='Profit Margin [%]', color='Year', barmode='group', text_auto='.1f', title='Profit Margin by Scenario', color_discrete_map={'2025': '#94A3B8', '2050': '#3B82F6'}, category_orders=scenario_order)
        
        # FIX: cliponaxis=False ensures negative text is not cut out of the chart's bounding box
        fig_margin.update_traces(texttemplate='%{y:.1f}%', textposition='outside', textfont_size=13, cliponaxis=False)
        
        # FIX: Let Plotly naturally scale both positive and negative values while adding a distinct zero line 
        fig_margin.update_layout(
            yaxis_title="Profit Margin (%)", 
            yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black')
        )
        st.plotly_chart(fig_margin, use_container_width=True)


# ==========================================
# TAB 2: HAUL DEEP DIVE (SHORT VS LONG)
# ==========================================
with tab2:
    st.subheader("Analysis by Flight Type (Short Haul vs Long Haul)")
    st.markdown("Observe how costs and environmental impacts distribute across flight types. Use the toggle below to project 2050 outcomes.")
    
    selected_year = st.radio("Select Year:", ["2025", "2050"], horizontal=True)
    filtered_haul = haul_df[haul_df['Year'] == selected_year]
    
    col_a, col_b = st.columns(2)
    with col_a:
        fig_haul_co2 = px.bar(filtered_haul, x='Flight Type', y='CO2 Emissions [tons]', color='Scenario', barmode='group', title=f"Total CO₂ by Flight Type ({selected_year})", category_orders=scenario_order)
        st.plotly_chart(fig_haul_co2, use_container_width=True)
        
    with col_b:
        fig_haul_cost = px.bar(filtered_haul, x='Flight Type', y='Total Costs [€]', color='Scenario', barmode='group', title=f"Total Cost by Flight Type ({selected_year})", category_orders=scenario_order)
        st.plotly_chart(fig_haul_cost, use_container_width=True)

    st.markdown(f"### Exact Haul Data ({selected_year})")
    display_table = filtered_haul[['Scenario', 'Flight Type', 'Total Costs [€]', 'Total Revenue [€]', 'CO2 Emissions [tons]', 'NOx Emissions [tons]', 'SOx Emissions [tons]']]
    st.dataframe(display_table, use_container_width=True, hide_index=True)
    
# ==========================================
# TAB 3: FEASIBILITY
# ==========================================
with tab3:
    st.subheader("Feasibility Assessment")
    
    st.markdown("""
    <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; background-color: #ffffff; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: white;">
        <div style="background-color: darkgreen; padding: 8px 15px; border-radius: 4px; font-weight: bold; text-align: center; flex: 1; margin: 0 5px;">++ Very strong</div>
        <div style="background-color: #32CD32; color: black; padding: 8px 15px; border-radius: 4px; font-weight: bold; text-align: center; flex: 1; margin: 0 5px;">+ Strong</div>
        <div style="background-color: darkorange; padding: 8px 15px; border-radius: 4px; font-weight: bold; text-align: center; flex: 1; margin: 0 5px;">++/- Intermediate</div>
        <div style="background-color: #FFA500; color: black; padding: 8px 15px; border-radius: 4px; font-weight: bold; text-align: center; flex: 1; margin: 0 5px;">+/- Moderate</div>
        <div style="background-color: red; padding: 8px 15px; border-radius: 4px; font-weight: bold; text-align: center; flex: 1; margin: 0 5px;">- Challenging</div>
    </div>
    """, unsafe_allow_html=True)
    
    def style_symbols(val):
        color_mapping = {
            '++': ('darkgreen', 'white'),
            '+': ('#32CD32', 'black'),
            '++/-': ('darkorange', 'white'),
            '+/-': ('#FFA500', 'black'),
            '-': ('red', 'white')
        }
        
        val_str = str(val).strip()
        if val_str in color_mapping:
            bg_color, text_color = color_mapping[val_str]
            return f'background-color: {bg_color}; color: {text_color}; font-weight: bold; text-align: center;'
        return ''

    if hasattr(feasibility.style, 'map'):
        styled_feasibility = feasibility.style.map(style_symbols)
    else:
        styled_feasibility = feasibility.style.applymap(style_symbols)
        
    st.dataframe(styled_feasibility, use_container_width=True)