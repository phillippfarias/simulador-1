import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

# Configuração inicial
st.set_page_config(page_title="Simulador de Despesa com Pessoal (LRF)", layout="wide")
st.title("📊 Simulador de Despesa com Pessoal (LRF) - Limites Máximo/Prudencial/Alerta")

# Funções auxiliares
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

# --- Sidebar ---
st.sidebar.header("⚙️ Entradas e Simulações")

rcl_atual = st.sidebar.number_input("RCL ajustada (Atual) (R$)", value=36273923688.14, format="%.2f", min_value=0.0)
desp_atual = st.sidebar.number_input("Despesa com Pessoal (Atual) (R$)", value=15127218477.20, format="%.2f", min_value=0.0)

max_pct = st.sidebar.slider("Limite Máximo (% RCL)", min_value=0.0, max_value=1.0, value=0.49, step=0.01, format="%.2f")
prud_factor = st.sidebar.slider("Fator Prudencial", min_value=0.0, max_value=1.0, value=0.95, step=0.01)
alert_factor = st.sidebar.slider("Fator Alerta", min_value=0.0, max_value=1.0, value=0.90, step=0.01)

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

# --- Cálculos ---
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

lim_atual = calc_limits(rcl["atual"], max_pct, prud_factor, alert_factor)
lim_sim = calc_limits(rcl["sim"], max_pct, prud_factor, alert_factor)
ajustes = compute_adjustments(rcl["sim"], desp["sim"], max_pct, prud_factor, alert_factor)

# --- Gauge ---
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

# --- Tabela Ajustes Necessários ---
st.markdown("### 🔧 Ajustes necessários (Cenário Simulado)")
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
st.table(df_adj.style.format({"Limite": str}))

st.markdown("---")

# --- Dashboards ---
st.header("📊 Dashboards — Atual vs Simulado")

# Receita x Despesa (linhas, mais fácil de comparar)
fig_sc = go.Figure()
fig_sc.add_trace(go.Scatter(x=["Atual","Simulado"], y=[desp["atual"], desp["sim"]],
                            mode="lines+markers+text", text=["Atual","Simulado"],
                            textposition="top center", marker=dict(size=12), name="Despesa"))
fig_sc.add_trace(go.Scatter(x=["Atual","Simulado"], y=[lim_atual[0], lim_sim[0]],
                            mode="lines+markers", name="Limite Máximo", line=dict(color="red", dash="dash")))
fig_sc.add_trace(go.Scatter(x=["Atual","Simulado"], y=[lim_atual[1], lim_sim[1]],
                            mode="lines+markers", name="Limite Prudencial", line=dict(color="orange", dash="dot")))
fig_sc.add_trace(go.Scatter(x=["Atual","Simulado"], y=[lim_atual[2], lim_sim[2]],
                            mode="lines+markers", name="Limite Alerta", line=dict(color="green", dash="dot")))
fig_sc.update_layout(title="Receita x Despesa (Atual vs Simulado)",
                     xaxis_title="Cenário", yaxis_title="R$",
                     height=420)
st.plotly_chart(fig_sc, use_container_width=True)

# --- Distância até os limites ---
st.header("📋 Distância até os limites")
rows = []
for key, (Lm, Lp, La) in {"Atual": lim_atual, "Simulado": lim_sim}.items():
    D = desp[key.lower()]
    rows.append({
        "Cenário": key,
        "Diferença até Máx (R$)": Lm - D,
        "Diferença até Prud (R$)": Lp - D,
        "Diferença até Alerta (R$)": La - D,
        "Diferença até Máx (%)": ((Lm - D)/Lm*100) if Lm else np.nan,
        "Diferença até Prud (%)": ((Lp - D)/Lp*100) if Lp else np.nan,
        "Diferença até Alerta (%)": ((La - D)/La*100) if La else np.nan,
    })
dist_df = pd.DataFrame(rows)
st.dataframe(dist_df.style.format({
    "Diferença até Máx (R$)": "{:,.2f}",
    "Diferença até Prud (R$)": "{:,.2f}",
    "Diferença até Alerta (R$)": "{:,.2f}",
    "Diferença até Máx (%)": "{:.2f}%",
    "Diferença até Prud (%)": "{:.2f}%",
    "Diferença até Alerta (%)": "{:.2f}%"
}), height=220)
