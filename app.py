import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ----------------------
# Configuração inicial
# ----------------------
st.set_page_config(page_title="Simulador de Despesa com Pessoal (LRF)", layout="wide")

st.title("📊 Simulador de Despesa com Pessoal (LRF) - Limites Máximo/Prudencial/Alerta")

# ----------------------
# Funções auxiliares
# ----------------------
def fmt_r(x):
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "-"

def calc_ajuste(limite, despesa):
    if despesa <= limite:
        return "OK", 0, 0
    else:
        reducao = despesa - limite
        perc_reducao = reducao / despesa * 100
        return "Excedido", reducao, perc_reducao

def dist_table(rcl, desp, max_pct, prud_factor, alert_factor):
    limites = {
        "Máximo": rcl * max_pct,
        "Prudencial": rcl * max_pct * prud_factor,
        "Alerta": rcl * max_pct * alert_factor
    }
    data = []
    for nome, limite in limites.items():
        falta_r = limite - desp
        falta_pct = (falta_r / limite * 100) if limite > 0 else np.nan
        data.append({
            "Limite": nome,
            "Limite (R$)": limite,
            "Despesa (R$)": desp,
            "Falta para atingir (R$)": falta_r,
            "Falta para atingir (%)": falta_pct
        })
    return pd.DataFrame(data)

# ----------------------
# Entradas iniciais
# ----------------------
st.sidebar.header("⚙️ Entradas Atuais")
receita_atual = st.sidebar.number_input("Receita Corrente Líquida (R$)", value=1000000.0, step=10000.0, format="%.2f")
despesa_atual = st.sidebar.number_input("Despesa com Pessoal Atual (R$)", value=400000.0, step=10000.0, format="%.2f")

st.sidebar.header("🎯 Simulações")
delta_receita = st.sidebar.number_input("Variação Receita (%)", value=0.0, step=1.0)
delta_despesa = st.sidebar.number_input("Variação Despesa (%)", value=0.0, step=1.0)

# ----------------------
# Cálculos
# ----------------------
# Receita e despesa simuladas
receita_simulada = receita_atual * (1 + delta_receita/100)
despesa_simulada = despesa_atual * (1 + delta_despesa/100)

# --- Parâmetros fixos da ótica (49% da RCL) ---
max_pct = 0.49
prud_factor = 0.95
alert_factor = 0.90

# Limites (em R$)
limite_max = receita_simulada * max_pct
limite_prud = limite_max * prud_factor
limite_alerta = limite_max * alert_factor

# Percentuais em relação à RCL
perc_atual = (despesa_atual / receita_atual) * 100
perc_simulado = (despesa_simulada / receita_simulada) * 100

# Percentuais em relação ao teto (49%)
perc_atual_teto = (despesa_atual / receita_atual) / max_pct * 100
perc_simulado_teto = (despesa_simulada / receita_simulada) / max_pct * 100

# ----------------------
# Tabela comparativa
# ----------------------
df = pd.DataFrame({
    "Situação": ["Atual", "Simulado"],
    "Receita (R$)": [receita_atual, receita_simulada],
    "Despesa (R$)": [despesa_atual, despesa_simulada],
    "% Despesa/RCL": [perc_atual, perc_simulado],
    "% do Teto (49% RCL)": [perc_atual_teto, perc_simulado_teto]
})
st.subheader("📋 Resumo Atual x Simulado")
st.dataframe(
    df.style.format({
        "Receita (R$)": fmt_r,
        "Despesa (R$)": fmt_r,
        "% Despesa/RCL": "{:.2f}%",
        "% do Teto (49% RCL)": "{:.2f}%"
    }),
    use_container_width=True
)

# ----------------------
# Gráficos Gauge
# ----------------------
st.subheader("⏱️ Situação Atual e Simulada")
col1, col2 = st.columns(2)

with col1:
    gauge_atual = go.Figure(go.Indicator(
        mode="gauge+number",
        value=perc_atual_teto,
        title={'text': "Atual"},
        gauge={
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 90], 'color': "lightgreen"},
                {'range': [90, 95], 'color': "yellow"},
                {'range': [95, 100], 'color': "orange"}
            ],
            'bar': {'color': "royalblue"}
        }
    ))
    st.plotly_chart(gauge_atual, use_container_width=True)

with col2:
    gauge_sim = go.Figure(go.Indicator(
        mode="gauge+number",
        value=perc_simulado_teto,
        title={'text': "Simulado"},
        gauge={
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 90], 'color': "lightgreen"},
                {'range': [90, 95], 'color': "yellow"},
                {'range': [95, 100], 'color': "orange"}
            ],
            'bar': {'color': "darkorange"}
        }
    ))
    st.plotly_chart(gauge_sim, use_container_width=True)

# ----------------------
# Gráfico comparativo de barras
# ----------------------
st.subheader("📊 Comparativo de Receita e Despesa (R$)")
bar = go.Figure(data=[
    go.Bar(name="Receita", x=["Atual", "Simulado"], y=[receita_atual, receita_simulada], marker_color="green"),
    go.Bar(name="Despesa", x=["Atual", "Simulado"], y=[despesa_atual, despesa_simulada], marker_color="red")
])
bar.update_layout(barmode='group', yaxis_title="R$")
st.plotly_chart(bar, use_container_width=True)

# ----------------------
# Gráfico de linha em valores R$
# ----------------------
st.subheader("📈 Despesa com Pessoal vs Limites (R$)")
fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=["Atual", "Simulado"],
    y=[despesa_atual, despesa_simulada],
    mode="lines+markers+text",
    text=[fmt_r(despesa_atual), fmt_r(despesa_simulada)],
    textposition="top center",
    line=dict(color="royalblue"),
    marker=dict(size=12, color=["blue", "orange"]),
    name="Despesa (R$)"
))
fig_line.add_hline(y=limite_max, line=dict(color="red", dash="dash"), annotation_text="Limite Máximo")
fig_line.add_hline(y=limite_prud, line=dict(color="orange", dash="dot"), annotation_text="Limite Prudencial")
fig_line.add_hline(y=limite_alerta, line=dict(color="green", dash="dot"), annotation_text="Limite Alerta")
fig_line.update_layout(yaxis_title="R$ (reais)", height=420, plot_bgcolor="white")
st.plotly_chart(fig_line, use_container_width=True)

# ----------------------
# Cálculo de ajustes necessários
# ----------------------
st.subheader("🔧 Ajustes Necessários (Simulação)")
for nome, limite in {"Alerta": limite_alerta, "Prudencial": limite_prud, "Máximo": limite_max}.items():
    status, reducao, perc_reducao = calc_ajuste(limite, despesa_simulada)
    if status == "OK":
        st.success(f"{nome}: Dentro do limite.")
    else:
        st.error(f"{nome}: Excedido. Necessário reduzir {fmt_r(reducao)} ({perc_reducao:.2f}%).")

# ----------------------
# Distância até os Limites
# ----------------------
st.markdown("---")
st.subheader("📋 Distância até os Limites")

# Cenário Atual
st.write("### Cenário Atual")
df_atual = dist_table(receita_atual, despesa_atual, max_pct, prud_factor, alert_factor)
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
df_sim = dist_table(receita_simulada, despesa_simulada, max_pct, prud_factor, alert_factor)
st.dataframe(
    df_sim.style.format({
        "Limite (R$)": fmt_r,
        "Despesa (R$)": fmt_r,
        "Falta para atingir (R$)": fmt_r,
        "Falta para atingir (%)": "{:.2f}%"
    }),
    use_container_width=True
)
