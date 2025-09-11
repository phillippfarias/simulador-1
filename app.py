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

max_pct = st.sidebar.slider("Limite Máximo (% RCL)", 0.0, 1.0, 0.49, 0.01, format="%.2f")
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

# limites
lim_atual = calc_limits(rcl["Atual"], max_pct, prud_factor, alert_factor)
lim_sim = calc_limits(rcl["Simulado"], max_pct, prud_factor, alert_factor)

# --- Gauge logo após o título ---
pct_atual = (desp["Atual"] / lim_atual[0] * 100) if lim_atual[0] else np.nan
pct_sim = (desp["Simulado"] / lim_sim[0] * 100) if lim_sim[0] else np.nan

fig_g = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=pct_sim,
    delta={'reference': pct_atual},
    title={'text': "Despesa como % do Limite Máximo"},
    gauge={
        'axis': {'range': [0, 120]},
        'bar': {'color': "royalblue"},
        'steps': [
            {'range': [0, 90], 'color': "#b6e3b6"},
            {'range': [90, 95], 'color': "#ffe599"},
            {'range': [95, 120], 'color': "#f4cccc"}
        ]
    }
))
st.plotly_chart(fig_g, use_container_width=True)

# --- Tabela de Ajustes Necessários ---
if sim_type != "Nenhuma":
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

# --- Gráfico Receita x Despesa ---
fig_sc = go.Figure()
fig_sc.add_trace(go.Scatter(
    x=[rcl["Atual"]], y=[desp["Atual"]],
    mode="markers+text", text=["Atual"],
    textposition="top center", marker=dict(size=12, color="blue"), name="Atual"
))
fig_sc.add_trace(go.Scatter(
    x=[rcl["Simulado"]], y=[desp["Simulado"]],
    mode="markers+text", text=["Simulado"],
    textposition="top center", marker=dict(size=12, color="orange"), name="Simulado"
))
fig_sc.add_hline(y=lim_sim[0], line=dict(color="red", dash="dash"), annotation_text="Limite Máx (Simulado)")
fig_sc.add_hline(y=lim_sim[1], line=dict(color="orange", dash="dot"), annotation_text="Limite Prud (Simulado)")
fig_sc.add_hline(y=lim_sim[2], line=dict(color="green", dash="dot"), annotation_text="Limite Alerta (Simulado)")
fig_sc.update_layout(
    title="Receita x Despesa",
    xaxis_title="RCL Ajustada (R$)",
    yaxis_title="Despesa com Pessoal (R$)",
    height=420,
    plot_bgcolor="white"
)
st.plotly_chart(fig_sc, use_container_width=True)

# --- Tabela Distância até os Limites (última seção) ---
st.markdown("---")
st.subheader("📋 Distância até os Limites")

def dist_table(rcl, desp, max_pct, prud_factor, alert_factor, nome):
    ajustes = compute_adjustments(rcl, desp, max_pct, prud_factor, alert_factor)
    data = []
    for lim in ["Máximo", "Prudencial", "Alerta"]:
        d = ajustes[lim]
        data.append({
            "Cenário": nome,
            "Limite": lim,
            "Limite (R$)": d["limite"],
            "Despesa (R$)": desp,
            "Falta para atingir (R$)": d["falta_r"],
            "Falta para atingir (%)": d["falta_pct"]
        })
    return pd.DataFrame(data)

df_atual = dist_table(rcl["Atual"], desp["Atual"], max_pct, prud_factor, alert_factor, "Atual")
df_sim = dist_table(rcl["Simulado"], desp["Simulado"], max_pct, prud_factor, alert_factor, "Simulado")
df_dist = pd.concat([df_atual, df_sim], ignore_index=True)

st.dataframe(
    df_dist.style.format({
        "Limite (R$)": fmt_r,
        "Despesa (R$)": fmt_r,
        "Falta para atingir (R$)": fmt_r,
        "Falta para atingir (%)": "{:.2f}%"
    }),
    use_container_width=True
)


