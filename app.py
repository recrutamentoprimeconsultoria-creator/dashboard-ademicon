import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import os

# ---------------------------------------------------------
# 1. Configuração da Página e Estilo Elegante (CSS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard de Credenciamento | Ademicon",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    
    .filter-card {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.03);
        margin-bottom: 25px;
    }

    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.08);
    }
    [data-testid="stMetricValue"] {
        font-size: 2.0rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    h1, h2, h3 {
        color: #0f172a;
        font-weight: 700;
    }
    
    .stButton>button, .stDownloadButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        background-color: #004b87;
        color: white;
        border: none;
        padding: 10px 16px;
        transition: background-color 0.2s ease;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #003366;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Carregamento e Tratamento de Dados (Google Sheets)
# ---------------------------------------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/14COiWWgyaBJwJT_otJ01O3DFd1iQCTXP15c0dJXbKg8/edit"

def get_dataframe_from_worksheet(ws):
    data = ws.get_all_values()
    if not data:
        return pd.DataFrame()
    headers = data[0]
    seen = {}
    new_headers = []
    for i, h in enumerate(headers):
        h_str = str(h).strip() if str(h).strip() != "" else f"Coluna_{i+1}"
        if h_str in seen:
            seen[h_str] += 1
            new_headers.append(f"{h_str}_{seen[h_str]}")
        else:
            seen[h_str] = 0
            new_headers.append(h_str)
    
    return pd.DataFrame(data[1:], columns=new_headers)

@st.cache_data(ttl=300)
def load_data():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # 1. Tenta carregar primeiro das Secrets do Streamlit Cloud
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        # 2. Se for localmente no VS Code, carrega da pasta local
        json_path = os.path.join(".streamlit", "google_credentials.json")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Arquivo de credenciais não encontrado em: {json_path}")
        credentials = Credentials.from_service_account_file(json_path, scopes=scopes)
        
    client = gspread.authorize(credentials)
    sheet = client.open_by_url(SHEET_URL)
    
    ws_ativas = sheet.worksheet("Matriculas real")
    df_ativas = get_dataframe_from_worksheet(ws_ativas)
    
    ws_descred = sheet.worksheet("matriculas descredenciadas")
    df_descred = get_dataframe_from_worksheet(ws_descred)
    
    cols_rename = {
        'Matricula': 'Matrícula',
        'NOME CNPJ': 'Razão Social',
        'Ponto Venda (Supervisor)': 'Supervisor / PV',
        'Unidade': 'Unidade',
        'Pessoa Física': 'Consultor (PF)',
        'Email Ademicon': 'E-mail'
    }
    
    df_ativas = df_ativas.rename(columns=cols_rename)
    df_descred = df_descred.rename(columns=cols_rename)
    
    df_ativas['Status'] = 'Ativo'
    df_descred['Status'] = 'Descredenciado'
    
    df_total = pd.concat([df_ativas, df_descred], ignore_index=True)
    
    if 'Unidade' in df_total.columns:
        df_total['Unidade'] = df_total['Unidade'].astype(str).str.strip().str.upper()
    if 'Supervisor / PV' in df_total.columns:
        df_total['Supervisor / PV'] = df_total['Supervisor / PV'].astype(str).str.strip()
    
    return df_total

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"⚠️ Erro ao conectar com o Google Sheets: {e}")
    st.info("Verifique se as credenciais do Google foram configuradas nos Secrets do Streamlit Cloud.")
    st.stop()

# ---------------------------------------------------------
# 3. Cabeçalho Principal (Logo + Título)
# ---------------------------------------------------------
col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    LOGO_URL = "https://www.ademicon.com.br/api/media/file/ademicon.svg?2026-01-08T16%3A57%3A33.024Z&dpl=dpl_9yCuySMtpVZ3Y8v8qWfgCTVqNMUo"
    st.image(LOGO_URL, width=200)

with col_titulo:
    st.title("📊 Gestão da Rede de Credenciamento")
    st.caption("Visão consolidada de matrículas ativas e descredenciadas por unidade e supervisor.")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. Painel Horizontal de Filtros de Análise (Na página)
# ---------------------------------------------------------
st.markdown("### 🔍 Filtros de Análise")

col_f_unidade, col_f_supervisor, col_f_btn = st.columns([2, 2, 1])

if 'Unidade' in df_raw.columns:
    unid_uniquas = [str(u) for u in df_raw['Unidade'].dropna().unique() if str(u).strip() not in ['', 'NAN', 'NONE', 'NONE']]
    unidades_disponiveis = ["Todas"] + sorted(list(set(unid_uniquas)))
else:
    unidades_disponiveis = ["Todas"]

with col_f_unidade:
    unidade_sel = st.selectbox("📍 Praça / Unidade:", unidades_disponiveis)

df_filtrado = df_raw.copy()
if unidade_sel != "Todas" and 'Unidade' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['Unidade'] == unidade_sel]

if 'Supervisor / PV' in df_filtrado.columns:
    sup_unicos = [str(s) for s in df_filtrado['Supervisor / PV'].dropna().unique() if str(s).strip() not in ['', 'NAN', 'NONE', 'NONE']]
    supervisores_disponiveis = ["Todos"] + sorted(list(set(sup_unicos)))
else:
    supervisores_disponiveis = ["Todos"]

with col_f_supervisor:
    supervisor_sel = st.selectbox("👔 Supervisor / Ponto de Venda:", supervisores_disponiveis)

if supervisor_sel != "Todos" and 'Supervisor / PV' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['Supervisor / PV'] == supervisor_sel]

with col_f_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. Indicadores Principais (KPIs)
# ---------------------------------------------------------
tot_ativas = len(df_filtrado[df_filtrado['Status'] == 'Ativo'])
tot_descred = len(df_filtrado[df_filtrado['Status'] == 'Descredenciado'])
tot_geral = tot_ativas + tot_descred
taxa_retencao = (tot_ativas / tot_geral * 100) if tot_geral > 0 else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Matrículas Ativas", f"{tot_ativas:,}".replace(",", "."))
kpi2.metric("Descredenciadas", f"{tot_descred:,}".replace(",", "."))
kpi3.metric("Total na Base", f"{tot_geral:,}".replace(",", "."))
kpi4.metric("Taxa de Retenção", f"{taxa_retencao:.1f}%")

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------
# 6. Gráficos Interativos
# ---------------------------------------------------------
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("🏢 Ativos por Unidade / Praça")
    if 'Unidade' in df_filtrado.columns:
        df_unid = df_filtrado[df_filtrado['Status'] == 'Ativo']['Unidade'].value_counts().reset_index()
        df_unid.columns = ['Unidade', 'Quantidade']
        
        fig_unid = px.bar(
            df_unid,
            x='Unidade',
            y='Quantidade',
            text='Quantidade',
            color='Unidade',
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_unid.update_traces(textposition='outside')
        fig_unid.update_layout(
            showlegend=False,
            xaxis_title="",
            yaxis_title="Total Ativos",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_unid, use_container_width=True)

with col_g2:
    st.subheader("👔 Top Supervisores / PVs (Ativos)")
    if 'Supervisor / PV' in df_filtrado.columns:
        df_sup = df_filtrado[df_filtrado['Status'] == 'Ativo']['Supervisor / PV'].value_counts().head(10).reset_index()
        df_sup.columns = ['Supervisor / PV', 'Quantidade']
        
        fig_sup = px.bar(
            df_sup,
            x='Quantidade',
            y='Supervisor / PV',
            orientation='h',
            text='Quantidade',
            color_discrete_sequence=['#004b87']
        )
        fig_sup.update_traces(textposition='outside')
        fig_sup.update_layout(
            yaxis=dict(autorange="reversed"),
            xaxis_title="Total Ativos",
            yaxis_title="",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_sup, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# 7. Tabela Detalhada com Busca e Exportação CSV
# ---------------------------------------------------------
st.subheader("📋 Detalhamento dos Parceiros e Consultores")

col_aba, col_pesquisa, col_export = st.columns([1, 2, 1])

with col_aba:
    status_filtro = st.radio(
        "Filtrar Tabela:",
        ["Ativos", "Descredenciados", "Todos"],
        horizontal=True
    )

if status_filtro == "Ativos":
    df_tabela = df_filtrado[df_filtrado['Status'] == 'Ativo']
elif status_filtro == "Descredenciados":
    df_tabela = df_filtrado[df_filtrado['Status'] == 'Descredenciado']
else:
    df_tabela = df_filtrado.copy()

with col_pesquisa:
    termo_busca = st.text_input("🔎 Pesquisar por Razão Social, Consultor ou E-mail:")

if termo_busca:
    df_tabela = df_tabela[
        (df_tabela['Razão Social'].astype(str).str.contains(termo_busca, case=False, na=False) if 'Razão Social' in df_tabela.columns else False) |
        (df_tabela['Consultor (PF)'].astype(str).str.contains(termo_busca, case=False, na=False) if 'Consultor (PF)' in df_tabela.columns else False) |
        (df_tabela['E-mail'].astype(str).str.contains(termo_busca, case=False, na=False) if 'E-mail' in df_tabela.columns else False)
    ]

cols_exibicao = [
    'Matrícula', 'Razão Social', 'Consultor (PF)', 'Unidade',
    'Supervisor / PV', 'E-mail', 'Status'
]
cols_existentes = [c for c in cols_exibicao if c in df_tabela.columns]

csv_data = df_tabela[cols_existentes].to_csv(index=False).encode('utf-8')

with col_export:
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="📥 Exportar CSV",
        data=csv_data,
        file_name="detalhamento_credenciamento_ademicon.csv",
        mime="text/csv"
    )

st.dataframe(
    df_tabela[cols_existentes],
    use_container_width=True,
    hide_index=True
)
