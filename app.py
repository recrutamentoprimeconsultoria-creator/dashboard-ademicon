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
    page_title="Dashboard de Credenciamento | Ademicon",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização CSS baseada nas cores oficiais da marca Ademicon
st.markdown("""
    <style>
    /* Fundo da aplicação */
    .main {
        background-color: #f4f6f8;
    }
    
    /* Cartões de KPI Elegantes e Corporativos */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border-left: 5px solid #002B49; /* Azul Oficial Ademicon */
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

    /* Títulos e Subtítulos */
    h1, h2, h3 {
        color: #002B49 !important;
        font-weight: 700;
    }
    
    /* Botões Padrão e de Download */
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
    </style>
""", unsafe_allow_html=True)

# Coordenadas geográficas aproximadas dos municípios do Estado do Rio de Janeiro
COORDENADAS_RJ = {
    'RIO DE JANEIRO': (-22.9068, -43.1729),
    'NITERÓI': (-22.8833, -43.1036),
    'SÃO GONÇALO': (-22.8268, -43.0539),
    'DUQUE DE CAXIAS': (-22.7856, -43.3117),
    'NOVA IGUAÇU': (-22.7592, -43.4511),
    'PETRÓPOLIS': (-22.5050, -43.1789),
    'TERESÓPOLIS': (-22.4123, -42.9656),
    'NOVA FRIBURGO': (-22.2819, -42.5311),
    'CABO FRIO': (-22.8892, -42.0268),
    'MACAÉ': (-22.3708, -41.7869),
    'CAMPOS DOS GOYTACAZES': (-21.7545, -41.3244),
    'VOLTA REDONDA': (-22.5231, -44.1042),
    'BARRA MANSA': (-22.5442, -44.1714),
    'ANGRA DOS REIS': (-23.0067, -44.3181),
    'RESENDE': (-22.4689, -44.4497),
    'MARICÁ': (-22.9192, -42.8186),
    'ITABORAÍ': (-22.7444, -42.8594),
    'SÃO JOÃO DE MERITI': (-22.8036, -43.3725),
    'NILÓPOLIS': (-22.8081, -43.4144),
    'BELFORD ROXO': (-22.7642, -43.3997),
    'ARARUAMA': (-22.8728, -42.3425),
    'SAQUAREMA': (-22.9203, -42.5103),
    'SÃO PEDRO DA ALDEIA': (-22.8394, -42.1006),
    'BÚZIOS': (-22.7469, -41.8817),
    'ARMÇÃO DOS BÚZIOS': (-22.7469, -41.8817)
}

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
    
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
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
    st.image(LOGO_URL, width=210)

with col_titulo:
    st.title("📊 Gestão da Rede de Credenciamento")
    st.caption("Visão consolidada de matrículas ativas e descredenciadas por unidade e supervisor.")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. Painel Horizontal de Filtros de Análise
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
# 5. Indicadores Principais (KPIs - Sem Taxa de Retenção)
# ---------------------------------------------------------
tot_ativas = len(df_filtrado[df_filtrado['Status'] == 'Ativo'])
tot_descred = len(df_filtrado[df_filtrado['Status'] == 'Descredenciado'])
tot_geral = tot_ativas + tot_descred

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Matrículas Ativas", f"{tot_ativas:,}".replace(",", "."))
kpi2.metric("Descredenciadas", f"{tot_descred:,}".replace(",", "."))
kpi3.metric("Total na Base", f"{tot_geral:,}".replace(",", "."))

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------
# 6. Gráficos Interativos e Mapa do Rio de Janeiro
# ---------------------------------------------------------
col_g1, col_g2 = st.columns(2)

ademicon_colors = ['#002B49', '#00406C', '#005691', '#006CB7', '#3389C5', '#66A7D4']

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
            color_discrete_sequence=ademicon_colors
        )
        fig_unid.update_traces(textposition='outside', marker_line_color='#002B49', marker_line_width=1)
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
            color_discrete_sequence=['#002B49']
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
# Mapa do Estado do Rio de Janeiro (Bolhas por Praça/Cidade)
# ---------------------------------------------------------
st.subheader("🗺️ Mapeamento Geográfico da Rede - Estado do Rio de Janeiro")

if 'Unidade' in df_filtrado.columns:
    df_mapa = df_filtrado[df_filtrado['Status'] == 'Ativo']['Unidade'].value_counts().reset_index()
    df_mapa.columns = ['Unidade', 'Quantidade']
    
    # Mapear latitude e longitude de cada município
    df_mapa['lat'] = df_mapa['Unidade'].map(lambda u: COORDENADAS_RJ.get(u, (-22.9068, -43.1729))[0])
    df_mapa['lon'] = df_mapa['Unidade'].map(lambda u: COORDENADAS_RJ.get(u, (-22.9068, -43.1729))[1])
    
    fig_mapa = px.scatter_geo(
        df_mapa,
        lat="lat",
        lon="lon",
        size="Quantidade",
        color="Quantidade",
        hover_name="Unidade",
        hover_data={"Quantidade": True, "lat": False, "lon": False},
        color_continuous_scale=["#3389C5", "#002B49"],
        size_max=35,
        fitbounds="locations"
    )
    fig_mapa.update_geos(
        fitbounds="locations",
        visible=True,
        showcountries=False,
        showcoastlines=True,
        showland=True,
        landcolor="#f4f6f8",
        showlakes=True,
        lakecolor="#ffffff"
    )
    fig_mapa.update_layout(
        margin={"r": 0, "t": 10, "l": 0, "b": 10},
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_mapa, use_container_width=True)

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
