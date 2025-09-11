import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

# Configuração da página
st.set_page_config(
    page_title="Simulador de Despesa com Pessoal (LRF)",
    layout="wide"
)

# Injetando CSS para customizar tema (Cores: Branco, Verde, Laranja)
st.markdown("""
    <style>
        body {
            background-color: #FFFFFF;
            color: #000000;
        }
        .stApp {
            background-color: #FFFFFF;
        }
        header, .stSidebar {
            background-color: #008000; /* Verde */
        }
        .st-bf, .st-af {
            background-color: #FFA500 !important; /* Laranja */
        }
        h1, h2, h3 {
            color: #008000; /* Verde nos títulos */
        }
    </style>
""", unsafe_allow_html=True)

# Título
st.title("📊 Simulador de Despesa com Pessoal (LRF) - Limites Máximo/Prudencial/Alerta")

# Utilitários
def fmt_r(x):
    try:
        return f"R$ {x:,.2f}"
    except:
        return "-"

def calc_limits(rcl_adj, max_pct, prud_factor, alert_factor):
    limite_max = rcl_adj * max_pct
    limite_prud = limite_max * prud_factor
    limite_alert = limite_max * alert_factor
    return limite_max, limite_prud, limite_alert

def compute_adjustments(rcl, desp, max_pct, prud_factor, alert_factor):
    res = {}
    names = ["Máximo", "Prudencial", "Alerta"]
    factors = [1.0, prud_factor, alert_factor]
    for name, f in zip(names, factors):
        limite = rcl * max_pct * f
        if desp > limite:
            reduce_R = desp - limite
            reduce_pct = (reduce_R / desp * 100) if desp else np.nan
        else:
            reduce_R = 0.0
            reduce_pct = 0.0
        denom = max_pct * f
        if denom > 0:
            rcl_needed = desp / denom
            rcl_increase_R = max(0.0, rcl_needed - rcl)
            rcl_increase_pct = (rcl_increase_R / rcl * 100) if rcl else np.nan
        else:
            rcl_increase_R = np.nan
            rcl_increase_pct = np.nan
        res[name] = {
            "limite": limite,
            "reduce_R": reduce_R,
            "reduce_pct": reduce_pct,
            "rcl_increase_R": rcl_increase_R,
            "rcl_increase_pct": rcl_increase_pct
        }
    return res

# Sidebar
st.sidebar.header("⚙️ Entradas e Simulações")
rcl_atual = st.sidebar.number_input("RCL ajustada (Atual) (R$)", value=36273923688.14, format="%.2f", min_value=0.0)
desp_atual = st.sidebar.number_input("Despesa com Pessoal (Atual) (R$)", value=15127218477.20, format="%.2f", min_value=0.0)
max_pct = st.sidebar.slider("Limite Máximo (% RCL)", 0.0, 1.0, 0.49, 0.01)
prud_factor = st.sidebar.slider("Fator Prudencial", 0.0, 1.0, 0.95, 0.01)
alert_factor = st.sidebar.slider("Fator Alerta", 0.0, 1.0, 0.90, 0.01)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Simulação (Cenário Simulado)")

sim_type = st.sidebar.selectbox("Tipo de simulação", (
    "Nenhuma",
    "Aumento despesa (%)", "Aumento despesa (R$)",
    "Redução despesa (%)", "Redução despesa (R$)",
    "Aumento receita (%)", "Aumento receita (R$)",
    "Redução receita (%)", "Redução receita (R$)"
))
sim_val = st.sidebar.number_input("Valor da simulação (percentual ou R$)", value=0.0, format="%.2f")

# Cenários
rcl = {"atual": rcl_atual, "sim": rcl_atual}
desp = {"atual": desp_atual, "sim": desp_atual}

if sim_type == "Aumento despesa (%)":
    desp["sim"] = desp_atual * (1 + sim_val/100.0)
elif sim_type == "Aumento despesa (R$)":
    desp["sim"] = desp_atual + sim_val
elif sim_type == "Redução despesa (%)":
    desp["sim"] = desp_atual * (1 - sim_val/100.0)
elif sim_type == "Redução despesa (R$)":
    desp["sim"] = max(0.0, desp_atual - sim_val)
elif sim_type == "Aumento receita (%)":
    rcl["sim"] = rcl_atual * (1 + sim_val/100.0)
elif sim_type == "Aumento receita (R$)":
    rcl["sim"] = rcl_atual + sim_val
elif sim_type == "Redução receita (%)":
    rcl["sim"] = rcl_atual * (1 - sim_val/100.0)
elif sim_type == "Redução receita (R$)":
    rcl["sim"] = max(0.0, rcl_atual - sim_val)

# Limites
lim_atual = calc_limits(rcl["atual"], max_pct, prud_factor, alert_factor)
lim_sim = calc_limits(rcl["sim"], max_pct, prud_factor, alert_factor)
ajustes = compute_adjustments(rcl["sim"], desp["sim"], max_pct, prud_factor, alert_factor)

# Gauge
st.header("📌 Visão rápida")
pct_atual = (desp["atual"] / lim_atual[0] * 100) if lim_atual[0] else np.nan
pct_sim = (desp["sim"] / lim_sim[0] * 100) if lim_sim[0] else np.nan
fig_g = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=pct_sim,
    delta={'reference': pct_atual},
    title={'text': "Simulado % do Limite Máximo"},
    gauge={
        'axis': {'range': [0, 120]},
        'bar': {'color': "orange"},
        'steps': [
            {'range': [0, 90], 'color': "lightgreen"},
            {'range': [90, 95], 'color': "yellow"},
            {'range': [95, 120], 'color': "red"}
        ]
    }
))
fig_g.update_layout(height=300)
st.plotly_chart(fig_g, use_container_width=True)

# Ajustes necessários
st.markdown("### 🔧 Ajustes Necessários (Cenário Simulado)")
rows = []
for nome in ["Máximo","Prudencial","Alerta"]:
    a = ajustes[nome]
    if a["reduce_R"] > 0:
        txt = f"Reduzir despesa: {fmt_r(a['reduce_R'])} ({a['reduce_pct']:.2f}%)"
    else:
        txt = f"Redução não necessária"
    if a["rcl_increase_R"] > 0:
        txt2 = f"Aumentar RCL: {fmt_r(a['rcl_increase_R'])} ({a['rcl_increase_pct']:.2f}%)"
    else:
        txt2 = f"Aumento RCL não necessário"
    rows.append({"Limite": nome, "Opção 1": txt, "Opção 2": txt2})
df_adj = pd.DataFrame(rows)
st.table(df_adj)

# --- Dashboards e Tabela final mantidos iguais ---
# (coloque aqui o restante da sua aplicação anterior, sem mudanças)
