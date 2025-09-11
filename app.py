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
    """Retorna um dict com chaves 'Máximo','Prudencial','Alerta' e valores com redução necessária e aumento de RCL."""
    res = {}
    names = ["Máximo", "Prudencial", "Alerta"]
    factors = [1.0, prud_factor, alert_factor]
    for name, f in zip(names, factors):
        limite = rcl * max_pct * f
        # redução de despesa necessária (R$ e %)
        if desp > limite:
            reduce_R = desp - limite
            reduce_pct = (reduce_R / desp * 100) if desp else np.nan
        else:
            reduce_R = 0.0
            reduce_pct = 0.0
        # aumento de RCL necessário (R$ e %)
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

# Sidebar (entradas)
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

# Preparar cenários com chaves consistentes
rcl = {"Atual": rcl_atual, "Simulado": rcl_atual}
desp = {"Atual": desp_atual, "Simulado": desp_atual}

# Aplica simulação
if sim_type == "Aumento despesa (%)":
    desp["Simulado"] = desp_atual * (1 + sim_val / 100.0)
elif sim_type == "Aumento despesa (R$)":
    desp["Simulado"] = desp_atual + sim_val
elif sim_type == "Redução despesa (%)":
    desp["Simulado"] = desp_atual * (1 - sim_val / 100.0)
elif sim_type == "Redução despesa (R$)":
    desp["Simulado"] = max(0.0, desp_atual - sim_val)
elif sim_type == "Aumento receita (%)":
    rcl["Simulado"] = rcl_atual * (1 + sim_val / 100.0)
elif sim_type == "Aumento receita (R$)":
    rcl["Simulado"] = rcl_atual + sim_val
elif sim_type == "Redução receita (%)":
    rcl["Simulado"] = rcl_atual * (1 - sim_val / 100.0)
elif sim_type == "Redução receita (R$)":
    rcl["Simulado"] = max(0.0, rcl_atual - sim_val)

# Limites
lim_atual = calc_limits(rcl["Atual"], max_pct, prud_factor, alert_factor)
lim_sim = calc_limits(rcl["Simulado"], max_pct, prud_factor, alert_factor)

# Ajustes a partir do cenário SIMULADO (para mostrar recomendações)
ajustes = compute_adjustments(rcl["Simulado"], desp["Simulado"], max_pct, prud_factor, alert_factor)

# --- Gauge (logo após título) ---
st.header("📌 Visão rápida")
pct_atual = (desp["Atual"] / lim_atual[0] * 100) if lim_atual[0] else np.nan
pct_sim = (desp["Simulado"] / lim_sim[0] * 100) if lim_sim[0] else np.nan

fig_g = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=pct_sim,
    delta={'reference': pct_atual, 'relative': False},
    title={'text': "Despesa como % do Limite Máximo"},
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
fig_g.update_layout(height=320)
st.plotly_chart(fig_g, use_container_width=True)

# --- Tabela Ajustes Necessários (sempre visível) ---
st.markdown("### 🔧 Ajustes necessários (Cenário Simulado)")
rows = []
for nome in ["Máximo", "Prudencial", "Alerta"]:
    a = ajustes[nome]
    if a["reduce_R"] > 0:
        txt1 = f"Reduzir despesa: {fmt_r(a['reduce_R'])} ({a['reduce_pct']:.2f}%)"
    else:
        txt1 = "Redução não necessária"
    if a["rcl_increase_R"] > 0:
        txt2 = f"Aumentar RCL: {fmt_r(a['rcl_increase_R'])} ({a['rcl_increase_pct']:.2f}%)"
    else:
        txt2 = "Aumento RCL não necessário"
    rows.append({"Limite": nome, "Opção 1": txt1, "Opção 2": txt2})
df_adj = pd.DataFrame(rows)
st.table(df_adj)

st.markdown("---")

# --- Gráfico Receita x Despesa (linhas + marcadores) ---
st.header("📊 Receita x Despesa (Atual vs Simulado)")

fig_sc = go.Figure()
# Despesas (linha entre Atual e Simulado)
fig_sc.add_trace(go.Scatter(
    x=["Atual", "Simulado"],
    y=[desp["Atual"], desp["Simulado"]],
    mode="lines+markers+text",
    text=[fmt_r(desp["Atual"]), fmt_r(desp["Simulado"])],
    textposition="top center",
    line=dict(color="royalblue"),
    marker=dict(size=10),
    name="Despesa com Pessoal"
))
# Limites (linhas conectando atual -> simulado)
fig_sc.add_trace(go.Scatter(
    x=["Atual", "Simulado"],
    y=[lim_atual[0], lim_sim[0]],
    mode="lines+markers",
    name="Limite Máximo",
    line=dict(color="red", dash="dash"),
    marker=dict(symbol="line-ew")
))
fig_sc.add_trace(go.Scatter(
    x=["Atual", "Simulado"],
    y=[lim_atual[1], lim_sim[1]],
    mode="lines+markers",
    name="Limite Prudencial",
    line=dict(color="orange", dash="dot")
))
fig_sc.add_trace(go.Scatter(
    x=["Atual", "Simulado"],
    y=[lim_atual[2], lim_sim[2]],
    mode="lines+markers",
    name="Limite Alerta",
    line=dict(color="green", dash="dot")
))

fig_sc.update_layout(
    xaxis_title="Cenário",
    yaxis_title="R$",
    height=420,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_sc, use_container_width=True)

# --- Distância até os limites (última seção) ---
st.markdown("---")
st.header("📋 Distância até os limites")

rows = []
lims_map = {"Atual": lim_atual, "Simulado": lim_sim}
for key, (Lm, Lp, La) in lims_map.items():
    D = desp[key]
    rows.append({
        "Cenário": key,
        "Diferença até Máx (R$)": Lm - D,
        "Diferença até Prud (R$)": Lp - D,
        "Diferença até Alerta (R$)": La - D,
        "Diferença até Máx (%)": ((Lm - D) / Lm * 100) if Lm else np.nan,
        "Diferença até Prud (%)": ((Lp - D) / Lp * 100) if Lp else np.nan,
        "Diferença até Alerta (%)": ((La - D) / La * 100) if La else np.nan,
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
