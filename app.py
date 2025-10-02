import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

# --- Configuração geral ---
st.set_page_config(
    page_title="Simulador de Despesa com Pessoal (LRF)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Título ---
st.title("📊 Simulador de Despesa com Pessoal (LRF) - Limites Máximo/Prudencial/Alerta")

# --- Utilitários ---
def fmt_r(x):
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
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
        falta_r = limite - desp
        falta_pct = (falta_r / limite * 100) if limite > 0 else np.nan
        res[name] = {
            "limite": limite,
            "falta_r": falta_r,
            "falta_pct": falta_pct
        }
    return res

def adjustments_table(rcl, desp, max_pct, prud_factor, alert_factor):
    rows = []
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
        rows.append({
            "Limite": name,
            "Reduzir Despesa (R$)": reduce_R,
            "Reduzir Despesa (%)": reduce_pct,
            "Aumentar Receita (R$)": rcl_increase_R,
            "Aumentar Receita (%)": rcl_increase_pct
        })
    return pd.DataFrame(rows)

# --- Sidebar (Entradas) ---
st.sidebar.header("⚙️ Entradas e Simulações")

rcl_atual = st.sidebar.number_input("RCL ajustada (Atual) (R$)", value=36273923688.14, format="%.2f", min_value=0.0)
desp_atual = st.sidebar.number_input("Despesa com Pessoal (Atual) (R$)", value=15127218477.20, format="%.2f", min_value=0.0)

# Limite máximo fixo como 49% da RCL
max_pct = 0.49
prud_factor = 0.95
alert_factor = 0.90

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
rcl = {"Atual": rcl_atual, "Simulado": rcl_atual}
desp = {"Atual": desp_atual, "Simulado": desp_atual}

if sim_type == "Aumento despesa (%)":
    desp["Simulado"] = desp_atual * (1 + sim_val/100.0)
elif sim_type == "Aumento despesa (R$)":
    desp["Simulado"] = desp_atual + sim_val
elif sim_type == "Redução despesa (%)":
    desp["Simulado"] = desp_atual * (1 - sim_val/100.0)
elif sim_type == "Redução despesa (R$)":
    desp["Simulado"] = max(0.0, desp_atual - sim_val)
elif sim_type == "Aumento receita (%)":
    rcl["Simulado"] = rcl_atual * (1 + sim_val/100.0)
elif sim_type == "Aumento receita (R$)":
    rcl["Simulado"] = rcl_atual + sim_val
elif sim_type == "Redução receita (%)":
    rcl["Simulado"] = rcl_atual * (1 - sim_val/100.0)
elif sim_type == "Redução receita (R$)":
    rcl["Simulado"] = max(0.0, rcl_atual - sim_val)

# --- Limites ---
lim_atual = calc_limits(rcl["Atual"], max_pct, prud_factor, alert_factor)
lim_sim = calc_limits(rcl["Simulado"], max_pct, prud_factor, alert_factor)

# --- Gauge dinâmico ---
pct_atual = desp["Atual"] / rcl["Atual"] * 100
pct_sim = desp["Simulado"] / rcl["Simulado"] * 100

limite_alerta_pct = max_pct * alert_factor * 100  # 44,1%
limite_prud_pct = max_pct * prud_factor * 100     # 46,55%
limite_max_pct = max_pct * 100                     # 49%

# Determinar cor da barra dinamicamente
def get_gauge_color(value):
    if value <= limite_alerta_pct:
        return "#b6e3b6"  # verde
    elif value <= limite_prud_pct:
        return "#ffe599"  # amarelo
    elif value <= limite_max_pct:
        return "#f4cccc"  # laranja
    else:
        return "red"      # vermelho

bar_color = get_gauge_color(pct_sim)

fig_g = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=pct_sim,
    delta={'reference': pct_atual, 'relative': False},
    title={'text': "Despesa como % da RCL"},
    gauge={
        'axis': {'range': [0, 60], 'tickformat': ".1f"},
        'bar': {'color': bar_color},
        'steps': [
            {'range': [0, limite_alerta_pct], 'color': "#b6e3b6"},
            {'range': [limite_alerta_pct, limite_prud_pct], 'color': "#ffe599"},
            {'range': [limite_prud_pct, limite_max_pct], 'color': "#f4cccc"}
        ],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': limite_max_pct
        }
    },
    number={'suffix': "%"}
))
st.plotly_chart(fig_g, use_container_width=True)

# --- Tabela de Ajustes Necessários ---
st.subheader("🔧 Ajustes Necessários (Cenário Simulado)")
df_adj = adjustments_table(rcl["Simulado"], desp["Simulado"], max_pct, prud_factor, alert_factor)
st.dataframe(
    df_adj.style.format({
        "Reduzir Despesa (R$)": fmt_r,
        "Reduzir Despesa (%)": "{:.2f}%",
        "Aumentar Receita (R$)": fmt_r,
        "Aumentar Receita (%)": "{:.2f}%"
    }),
    use_container_width=True
)

st.markdown("---")

# --- Gráfico: Despesa vs Limites ---
st.subheader("📊 Despesa com Pessoal vs Limites")
fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=["Atual", "Simulado"],
    y=[desp["Atual"], desp["Simulado"]],
    mode="lines+markers+text",
    text=[fmt_r(desp["Atual"]), fmt_r(desp["Simulado"])],
    textposition="top center",
    line=dict(color="royalblue"),
    marker=dict(size=12, color=["blue", "orange"]),
    name="Despesa com Pessoal"
))
fig_line.add_hline(y=lim_sim[0], line=dict(color="red", dash="dash"), annotation_text="Limite Máx (Simulado)")
fig_line.add_hline(y=lim_sim[1], line=dict(color="orange", dash="dot"), annotation_text="Limite Prud (Simulado)")
fig_line.add_hline(y=lim_sim[2], line=dict(color="green", dash="dot"), annotation_text="Limite Alerta (Simulado)")
fig_line.update_layout(yaxis_title="R$ (reais)", height=420, plot_bgcolor="white")
st.plotly_chart(fig_line, use_container_width=True)

# --- Distância até os Limites ---
st.markdown("---")
st.subheader("📋 Distância até os Limites")

def dist_table(rcl, desp, max_pct, prud_factor, alert_factor, nome):
    ajustes = compute_adjustments(rcl, desp, max_pct, prud_factor, alert_factor)
    data = []
    for lim in ["Máximo", "Prudencial", "Alerta"]:
        d = ajustes[lim]
        data.append({
            "Limite": lim,
            "Limite (R$)": d["limite"],
            "Despesa (R$)": desp,
            "Falta para atingir (R$)": d["falta_r"],
            "Falta para atingir (%)": d["falta_pct"]
        })
    return pd.DataFrame(data)

# Cenário Atual
st.write("### Cenário Atual")
df_atual = dist_table(rcl["Atual"], desp["Atual"], max_pct, prud_factor, alert_factor, "Atual")
st.dataframe(
    df_atual.style.format({
        "Limite (R$)": fmt_r,
        "Despesa (R$)": fmt_r,
        "Falta para atingir (R$)": fmt_r,
        "Falta para atingir (%)": "{:.2f}%"
    }),
    use_container_width=True
)

# Cenário Simulado
st.write("### Cenário Simulado")
df_sim = dist_table(rcl["Simulado"], desp["Simulado"], max_pct, prud_factor, alert_factor, "Simulado")
st.dataframe(
    df_sim.style.format({
        "Limite (R$)": fmt_r,
        "Despesa (R$)": fmt_r,
        "Falta para atingir (R$)": fmt_r,
        "Falta para atingir (%)": "{:.2f}%"
    }),
    use_container_width=True
)
