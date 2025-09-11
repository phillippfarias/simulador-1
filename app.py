import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

# Configuração da página
st.set_page_config(page_title="Simulador de Despesa com Pessoal (LRF)", layout="wide")

# Título
st.title("📊 Simulador de Despesa com Pessoal (LRF) - Limites Máximo/Prudencial/Alerta")

# ---------------- utilitários ----------------
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
    """Retorna dict com chaves 'Máximo','Prudencial','Alerta' contendo redução necessária e aumento de RCL."""
    res = {}
    names = ["Máximo", "Prudencial", "Alerta"]
    factors = [1.0, prud_factor, alert_factor]
    for name, f in zip(names, factors):
        limite = rcl * max_pct * f
        # redução deDesp
        if desp > limite:
            reduce_R = desp - limite
            reduce_pct = (reduce_R / desp * 100) if desp else np.nan
        else:
            reduce_R = 0.0
            reduce_pct = 0.0
        # aumento de RCL necessário
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

# ---------------- sidebar (entradas) ----------------
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

# ---------------- preparar cenários (consistentes: 'atual' e 'sim') ----------------
rcl = {"atual": rcl_atual, "sim": rcl_atual}
desp = {"atual": desp_atual, "sim": desp_atual}

# aplica simulação
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

# ---------------- limites e ajustes ----------------
lim_atual = calc_limits(rcl["atual"], max_pct, prud_factor, alert_factor)
lim_sim = calc_limits(rcl["sim"], max_pct, prud_factor, alert_factor)
ajustes = compute_adjustments(rcl["sim"], desp["sim"], max_pct, prud_factor, alert_factor)

# ---------------- gauge (logo após o título) ----------------
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

# ---------------- Tabela Ajustes Necessários (sempre visível) ----------------
st.markdown("### 🔧 Ajustes necessários (Cenário Simulado)")
rows = []
for nome in ["Máximo","Prudencial","Alerta"]:
    a = ajustes[nome]
    if a["reduce_R"] > 0:
        txt = f"Reduzir despesa: {fmt_r(a['reduce_R'])} ({a['reduce_pct']:.2f}%)"
    else:
        txt = "Redução não necessária"
    if a["rcl_increase_R"] > 0:
        txt2 = f"Aumentar RCL: {fmt_r(a['rcl_increase_R'])} ({a['rcl_increase_pct']:.2f}%)"
    else:
        txt2 = "Aumento RCL não necessário"
    rows.append({"Limite": nome, "Opção 1": txt, "Opção 2": txt2})
df_adj = pd.DataFrame(rows)
st.table(df_adj)

st.markdown("---")

# ---------------- Dashboards — Atual vs Simulado ----------------
st.header("📊 Dashboards — Atual vs Simulado")

# 1) Limites: comparação Atual vs Simulado (horizontal grouped bars)
lim_df = pd.DataFrame({
    "Limite": ["Máximo","Prudencial","Alerta"],
    "Atual": list(lim_atual),
    "Simulado": list(lim_sim)
})
fig_lim = go.Figure()
fig_lim.add_trace(go.Bar(x=lim_df["Atual"], y=lim_df["Limite"], orientation='h', name="Atual", marker=dict(color="lightgray")))
fig_lim.add_trace(go.Bar(x=lim_df["Simulado"], y=lim_df["Limite"], orientation='h', name="Simulado", marker=dict(color="darkgray")))
fig_lim.update_layout(height=320, barmode='group', xaxis_title="R$ (reais)")
st.plotly_chart(fig_lim, use_container_width=True)
st.caption("Comparação dos limites (Atual vs Simulado).")

# 2) Despesa: Atual vs Simulado (barra simples)
desp_df = pd.DataFrame({
    "Cenário": ["Atual","Simulado"],
    "Despesa": [desp["atual"], desp["sim"]]
})
fig_d = go.Figure()
fig_d.add_trace(go.Bar(x=desp_df["Cenário"], y=desp_df["Despesa"], marker_color=["blue","orange"]))
fig_d.update_layout(height=260, yaxis_title="R$ (reais)")
st.plotly_chart(fig_d, use_container_width=True)

# 3) Margens por limite (comparação Atual vs Simulado)
margens = {
    "Limite": ["Máx","Prud","Alerta"],
    "Margem_Atual": [lim_atual[0]-desp["atual"], lim_atual[1]-desp["atual"], lim_atual[2]-desp["atual"]],
    "Margem_Sim": [lim_sim[0]-desp["sim"], lim_sim[1]-desp["sim"], lim_sim[2]-desp["sim"]]
}
marg_df = pd.DataFrame(margens)
fig_m = go.Figure()
fig_m.add_trace(go.Bar(y=marg_df["Limite"], x=marg_df["Margem_Atual"], orientation='h', name="Margem Atual", marker=dict(color="lightblue")))
fig_m.add_trace(go.Bar(y=marg_df["Limite"], x=marg_df["Margem_Sim"], orientation='h', name="Margem Simulado", marker=dict(color="lightcoral")))
fig_m.update_layout(barmode='group', height=320, xaxis_title="Margem (R$)")
st.plotly_chart(fig_m, use_container_width=True)
st.caption("Margens (diferença entre limite e despesa) — negativo indica extrapolação do limite.")

# 4) Receita x Despesa (scatter) com linhas de limite (do cenário simulado)
fig_sc = go.Figure()
fig_sc.add_trace(go.Scatter(x=[rcl["atual"]], y=[desp["atual"]], mode="markers+text", text=["Atual"], textposition="top center", marker=dict(size=12, color="blue"), name="Atual"))
fig_sc.add_trace(go.Scatter(x=[rcl["sim"]], y=[desp["sim"]], mode="markers+text", text=["Simulado"], textposition="top center", marker=dict(size=12, color="orange"), name="Simulado"))
# linhas horizontais dos limites (simulado)
fig_sc.add_hline(y=lim_sim[0], line=dict(color="red", dash="dash"), annotation_text="Limite Máx (Simulado)", annotation_position="bottom right")
fig_sc.add_hline(y=lim_sim[1], line=dict(color="orange", dash="dot"), annotation_text="Limite Prud (Simulado)", annotation_position="bottom right")
fig_sc.add_hline(y=lim_sim[2], line=dict(color="green", dash="dot"), annotation_text="Limite Alerta (Simulado)", annotation_position="bottom right")
fig_sc.update_layout(title="Receita x Despesa (pontos Atual & Simulado)", xaxis_title="RCL Ajustada (R$)", yaxis_title="Despesa com Pessoal (R$)", height=420)
st.plotly_chart(fig_sc, use_container_width=True)
st.caption("Pontos indicam posição Atual e Simulado; linhas horizontais mostram limites do cenário simulado.")

st.markdown("---")

# ---------------- Tabela detalhada (Atual / Simulado) ----------------
st.header("📋 Tabela detalhada (Atual / Simulado)")

rows = []
scenarios = [("Atual", "atual"), ("Simulado", "sim")]
for display_name, key in scenarios:
    if key == "atual":
        Lm, Lp, La = lim_atual
    else:
        Lm, Lp, La = lim_sim
    D = desp[key]
    rows.append({
        "Cenário": display_name,
        "RCL ajustada (R$)": rcl[key],
        "Despesa Pessoal (R$)": D,
        "Limite Máx (R$)": Lm,
        "Limite Prud (R$)": Lp,
        "Limite Alerta (R$)": La,
        "Margem Máx (R$)": Lm - D,
        "Margem Prud (R$)": Lp - D,
        "Margem Alerta (R$)": La - D,
        "% Ocup Máx": (D / Lm * 100) if Lm else np.nan,
        "% Ocup Prud": (D / Lp * 100) if Lp else np.nan,
        "% Ocup Alerta": (D / La * 100) if La else np.nan,
    })
table_df = pd.DataFrame(rows)
fmt_cols = {
    "RCL ajustada (R$)": "{:,.2f}",
    "Despesa Pessoal (R$)": "{:,.2f}",
    "Limite Máx (R$)": "{:,.2f}",
    "Limite Prud (R$)": "{:,.2f}",
    "Limite Alerta (R$)": "{:,.2f}",
    "Margem Máx (R$)": "{:,.2f}",
    "Margem Prud (R$)": "{:,.2f}",
    "Margem Alerta (R$)": "{:,.2f}",
    "% Ocup Máx": "{:.2f}%",
    "% Ocup Prud": "{:.2f}%",
    "% Ocup Alerta": "{:.2f}%"
}
st.dataframe(table_df.style.format(fmt_cols), height=220)

# ---------------- Exportar ----------------
st.markdown("---")
st.subheader("📥 Exportar tabela")
csv_buf = io.StringIO()
table_df.to_csv(csv_buf, index=False, sep=";")
st.download_button("Baixar CSV (Detalhado)", csv_buf.getvalue().encode("utf-8"), file_name="margens_detalhado.csv", mime="text/csv")

st.caption("Notas: 'Atual' = situação atual; 'Simulado' = após aplicação da simulação escolhida. Ajustes apresentados são sugestões para que a despesa passe a respeitar cada limite.")
