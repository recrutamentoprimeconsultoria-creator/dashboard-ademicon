import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import os

# ---------------------------------------------------------
# 1. Configuração da Página e CSS Corporativo Ademicon
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard de Credenciamento & Prévias | Ademicon",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #f4f6f8;
    }
    
    /* Cartões de KPI Elegantes e Corporativos */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border-left: 5px solid #002B49;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        padding: 18px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 43, 73, 0.12);
    }
    [data-testid="stMetricValue"] {
        font-size: 2.0rem !important;
        font-weight: 700 !important;
        color: #002B49 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    h1, h2, h3 {
        color: #002B49 !important;
        font-weight: 700;
    }
    
    .stButton>button, .stDownloadButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        background-color: #002B49;
        color: #ffffff;
        border: none;
        padding: 10px 16px;
        transition: background-color 0.2s ease, transform 0.1s ease;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #00406c;
        color: #ffffff;
    }
    
    /* Estilização da Sidebar */
    [data-testid="stSidebar"] {
        background-color: #002B49;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Conexão e Carregamento do Google Sheets
# ---------------------------------------------------------
SHEET_URL_CRED = "https://docs.google.com/spreadsheets/d/14COiWWgyaBJwJT_otJ01O3DFd1iQCTXP15c0dJXbKg8/edit"
SHEET_URL_PREVIAS = "https://docs.google.com/spreadsheets/d/1jqq3qqdojoWPBSWn4LninB0XWxxV3l9DJEjP7lMKC7I/edit"

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
def load_data_cred():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        json_path = os.path.join(".streamlit", "google_credentials.json")
        credentials = Credentials.from_service_account_file(json_path, scopes=scopes)
        
    client = gspread.authorize(credentials)
    sheet = client.open_by_url(SHEET_URL_CRED)
    
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

@st.cache_data(ttl=300)
def load_data_previas():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        json_path = os.path.join(".streamlit", "google_credentials.json")
        credentials = Credentials.from_service_account_file(json_path, scopes=scopes)
        
    client = gspread.authorize(credentials)
    sheet = client.open_by_url(SHEET_URL_PREVIAS)
    
    # Busca a aba exata ou pega a primeira disponível na planilha
    worksheets = sheet.worksheets()
    ws_target = None
    for ws in worksheets:
        if "previa" in ws.title.lower():
            ws_target = ws
            break
    if ws_target is None:
        ws_target = worksheets[0]
        
    df_previas = get_dataframe_from_worksheet(ws_target)
    
    cols_rename = {
        'Matricula': 'Matrícula',
        'NOME CNPJ': 'Razão Social',
        'Ponto Venda (Supervisor)': 'Supervisor / PV',
        'Unidade': 'Unidade',
        'Pessoa Física': 'Consultor (PF)',
        'Email Ademicon': 'E-mail'
    }
    df_previas = df_previas.rename(columns=cols_rename)
    
    if 'Unidade' in df_previas.columns:
        df_previas['Unidade'] = df_previas['Unidade'].astype(str).str.strip().str.upper()
    if 'Supervisor / PV' in df_previas.columns:
        df_previas['Supervisor / PV'] = df_previas['Supervisor / PV'].astype(str).str.strip()
        
    return df_previas

# ---------------------------------------------------------
# 3. Sidebar (Navegação Principal)
# ---------------------------------------------------------
with st.sidebar:
    LOGO_URL = "https://www.ademicon.com.br/api/media/file/ademicon.svg?2026-01-08T16%3A57%3A33.024Z&dpl=dpl_9yCuySMtpVZ3Y8v8qWfgCTVqNMUo"
    st.image(LOGO_URL, width=180)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📌 Navegação")
    
    opcao_menu = st.radio(
        "Selecione o Módulo:",
        ["📊 Rede de Credenciamento", "📋 Prévias"]
    )
    st.markdown("---")
    st.caption("Ademicon - Gestão Corporativa")

# ---------------------------------------------------------
# MÓDULO 1: REDE DE CREDENCIAMENTO
# ---------------------------------------------------------
if opcao_menu == "📊 Rede de Credenciamento":
    try:
        df_raw = load_data_cred()
    except Exception as e:
        st.error(f"⚠️ Erro ao conectar com o Google Sheets: {e}")
        st.stop()

    st.title("📊 Gestão da Rede de Credenciamento")
    st.caption("Visão consolidada de matrículas ativas e descredenciadas por unidade e supervisor.")
    st.markdown("<br>", unsafe_allow_html=True)

    # Filtros
    st.markdown("### 🔍 Filtros de Análise")
    col_f_unidade, col_f_supervisor, col_f_btn = st.columns([2, 2, 1])

    if 'Unidade' in df_raw.columns:
        unid_uniquas = [str(u) for u in df_raw['Unidade'].dropna().unique() if str(u).strip() not in ['', 'NAN', 'NONE']]
        unidades_disponiveis = ["Todas"] + sorted(list(set(unid_uniquas)))
    else:
        unidades_disponiveis = ["Todas"]

    with col_f_unidade:
        unidade_sel = st.selectbox("📍 Praça / Unidade:", unidades_disponiveis)

    df_filtrado = df_raw.copy()
    if unidade_sel != "Todas" and 'Unidade' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['Unidade'] == unidade_sel]

    if 'Supervisor / PV' in df_filtrado.columns:
        sup_unicos = [str(s) for s in df_filtrado['Supervisor / PV'].dropna().unique() if str(s).strip() not in ['', 'NAN', 'NONE']]
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

    # KPIs
    tot_ativas = len(df_filtrado[df_filtrado['Status'] == 'Ativo'])
    tot_descred = len(df_filtrado[df_filtrado['Status'] == 'Descredenciado'])
    tot_geral = tot_ativas + tot_descred

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Matrículas Ativas", f"{tot_ativas:,}".replace(",", "."))
    kpi2.metric("Descredenciadas", f"{tot_descred:,}".replace(",", "."))
    kpi3.metric("Total na Base", f"{tot_geral:,}".replace(",", "."))

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # Gráficos
    col_g1, col_g2 = st.columns(2)
    ademicon_colors = ['#002B49', '#00406C', '#005691', '#006CB7', '#3389C5', '#66A7D4']

    with col_g1:
        st.subheader("🏢 Ativos por Unidade / Praça")
        if 'Unidade' in df_filtrado.columns:
            df_unid = df_filtrado[df_filtrado['Status'] == 'Ativo']['Unidade'].value_counts().reset_index()
            df_unid.columns = ['Unidade', 'Quantidade']
            
            fig_unid = px.bar(
                df_unid, x='Unidade', y='Quantidade', text='Quantidade',
                color='Unidade', color_discrete_sequence=ademicon_colors
            )
            fig_unid.update_traces(textposition='outside', marker_line_color='#002B49', marker_line_width=1)
            fig_unid.update_layout(showlegend=False, xaxis_title="", yaxis_title="Total Ativos", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_unid, use_container_width=True)

    with col_g2:
        st.subheader("👔 Top Supervisores / PVs (Ativos)")
        if 'Supervisor / PV' in df_filtrado.columns:
            df_sup = df_filtrado[df_filtrado['Status'] == 'Ativo']['Supervisor / PV'].value_counts().head(10).reset_index()
            df_sup.columns = ['Supervisor / PV', 'Quantidade']
            
            fig_sup = px.bar(
                df_sup, x='Quantidade', y='Supervisor / PV', orientation='h',
                text='Quantidade', color_discrete_sequence=['#002B49']
            )
            fig_sup.update_traces(textposition='outside')
            fig_sup.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Total Ativos", yaxis_title="", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_sup, use_container_width=True)

    st.divider()

    # Tabela
    st.subheader("📋 Detalhamento dos Parceiros e Consultores")
    col_aba, col_pesquisa, col_export = st.columns([1, 2, 1])

    with col_aba:
        status_filtro = st.radio("Filtrar Tabela:", ["Ativos", "Descredenciados", "Todos"], horizontal=True)

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

    cols_exibicao = ['Matrícula', 'Razão Social', 'Consultor (PF)', 'Unidade', 'Supervisor / PV', 'E-mail', 'Status']
    cols_existentes = [c for c in cols_exibicao if c in df_tabela.columns]

    csv_data = df_tabela[cols_existentes].to_csv(index=False).encode('utf-8')

    with col_export:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("📥 Exportar CSV", data=csv_data, file_name="detalhamento_credenciamento_ademicon.csv", mime="text/csv")

    st.dataframe(df_tabela[cols_existentes], use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# MÓDULO 2: PRÉVIAS
# ---------------------------------------------------------
elif opcao_menu == "📋 Prévias":
    try:
        df_previas_raw = load_data_previas()
    except Exception as e:
        st.error(f"⚠️ Erro ao conectar com a planilha de Prévias: {e}")
        st.info("Verifique se compartilhou a nova planilha com o e-mail: streamlit-ademicon@dashboard-ademicon.iam.gserviceaccount.com")
        st.stop()

    st.title("📋 Gestão de Prévias")
    st.caption("Acompanhamento detalhado das matrículas na fase 'Em Prévia'.")
    st.markdown("<br>", unsafe_allow_html=True)

    # Filtros
    st.markdown("### 🔍 Filtros de Análise")
    col_p_unidade, col_p_supervisor, col_p_btn = st.columns([2, 2, 1])

    if 'Unidade' in df_previas_raw.columns:
        unid_uniquas_p = [str(u) for u in df_previas_raw['Unidade'].dropna().unique() if str(u).strip() not in ['', 'NAN', 'NONE']]
        unidades_previas = ["Todas"] + sorted(list(set(unid_uniquas_p)))
    else:
        unidades_previas = ["Todas"]

    with col_p_unidade:
        unidade_p_sel = st.selectbox("📍 Praça / Unidade:", unidades_previas, key="p_unid")

    df_previas_filt = df_previas_raw.copy()
    if unidade_p_sel != "Todas" and 'Unidade' in df_previas_filt.columns:
        df_previas_filt = df_previas_filt[df_previas_filt['Unidade'] == unidade_p_sel]

    if 'Supervisor / PV' in df_previas_filt.columns:
        sup_unicos_p = [str(s) for s in df_previas_filt['Supervisor / PV'].dropna().unique() if str(s).strip() not in ['', 'NAN', 'NONE']]
        supervisores_previas = ["Todos"] + sorted(list(set(sup_unicos_p)))
    else:
        supervisores_previas = ["Todos"]

    with col_p_supervisor:
        supervisor_p_sel = st.selectbox("👔 Supervisor / Ponto de Venda:", supervisores_previas, key="p_sup")

    if supervisor_p_sel != "Todos" and 'Supervisor / PV' in df_previas_filt.columns:
        df_previas_filt = df_previas_filt[df_previas_filt['Supervisor / PV'] == supervisor_p_sel]

    with col_p_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar Dados", key="p_btn"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # KPI Prévias
    tot_previas = len(df_previas_filt)
    kpi_p1, kpi_p2 = st.columns(2)
    kpi_p1.metric("Total de Prévias", f"{tot_previas:,}".replace(",", "."))
    
    praças_impactadas = len(df_previas_filt['Unidade'].unique()) if 'Unidade' in df_previas_filt.columns else 0
    kpi_p2.metric("Praças com Prévias", f"{praças_impactadas}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # Gráficos
    col_pg1, col_pg2 = st.columns(2)
    ademicon_colors = ['#002B49', '#00406C', '#005691', '#006CB7', '#3389C5', '#66A7D4']

    with col_pg1:
        st.subheader("🏢 Prévias por Unidade / Praça")
        if 'Unidade' in df_previas_filt.columns and not df_previas_filt.empty:
            df_p_unid = df_previas_filt['Unidade'].value_counts().reset_index()
            df_p_unid.columns = ['Unidade', 'Quantidade']
            
            fig_p_unid = px.bar(
                df_p_unid, x='Unidade', y='Quantidade', text='Quantidade',
                color='Unidade', color_discrete_sequence=ademicon_colors
            )
            fig_p_unid.update_traces(textposition='outside', marker_line_color='#002B49', marker_line_width=1)
            fig_p_unid.update_layout(showlegend=False, xaxis_title="", yaxis_title="Total Prévias", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_p_unid, use_container_width=True)

    with col_pg2:
        st.subheader("👔 Top Supervisores / PVs (Prévias)")
        if 'Supervisor / PV' in df_previas_filt.columns and not df_previas_filt.empty:
            df_p_sup = df_previas_filt['Supervisor / PV'].value_counts().head(10).reset_index()
            df_p_sup.columns = ['Supervisor / PV', 'Quantidade']
            
            fig_p_sup = px.bar(
                df_p_sup, x='Quantidade', y='Supervisor / PV', orientation='h',
                text='Quantidade', color_discrete_sequence=['#002B49']
            )
            fig_p_sup.update_traces(textposition='outside')
            fig_p_sup.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Total Prévias", yaxis_title="", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_p_sup, use_container_width=True)

    st.divider()

    # Tabela Prévias
    st.subheader("📋 Detalhamento das Prévias")
    col_p_busca, col_p_export = st.columns([3, 1])

    with col_p_busca:
        termo_p_busca = st.text_input("🔎 Pesquisar na tabela de Prévias:")

    df_p_tabela = df_previas_filt.copy()
    if termo_p_busca:
        cols_para_busca = [c for c in df_p_tabela.columns if df_p_tabela[c].dtype == 'object']
        mascara = pd.Series(False, index=df_p_tabela.index)
        for col in cols_para_busca:
            mascara |= df_p_tabela[col].astype(str).str.contains(termo_p_busca, case=False, na=False)
        df_p_tabela = df_p_tabela[mascara]

    csv_p_data = df_p_tabela.to_csv(index=False).encode('utf-8')

    with col_p_export:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("📥 Exportar CSV (Prévias)", data=csv_p_data, file_name="previas_ademicon.csv", mime="text/csv")

    st.dataframe(df_p_tabela, use_container_width=True, hide_index=True)
