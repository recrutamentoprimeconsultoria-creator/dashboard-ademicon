import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import os

# ---------------------------------------------------------
# 1. Configuração da Página e CSS Corporativo Responsivo
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Corporativo | Gente & Gestão",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .main {
        background-color: #f4f6f8;
    }
    
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border-left: 5px solid #002B49;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        padding: 18px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
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
        transition: background-color 0.2s ease;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #00406c;
        color: #ffffff;
    }

    /* Remove barra lateral */
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Conexão e Carregamento do Google Sheets
# ---------------------------------------------------------
SHEET_URL_CRED = "https://docs.google.com/spreadsheets/d/14COiWWgyaBJwJT_otJ01O3DFd1iQCTXP15c0dJXbKg8/edit"
SHEET_URL_PREVIAS = "https://docs.google.com/spreadsheets/d/1jqq3qqdojoWPBSWn4LninB0XWxxV3l9DJEjP7lMKC7I/edit"
SHEET_URL_CURSO_CRED = "https://docs.google.com/spreadsheets/d/1RVagsSTtPNbAcNERu3ZaRVjVTcqF6CTbzMTpYVU2LzQ/edit"
SHEET_URL_CURSO_PRO = "https://docs.google.com/spreadsheets/d/1oKRVHe41Inn41RzjQXT5GKFJjUWZwHj9slZJm3LcjZ8/edit"

def get_dataframe_from_worksheet(ws):
    data = ws.get_all_values()
    if not data or len(data) == 0:
        return pd.DataFrame()
    headers = [str(h).strip() if str(h).strip() != "" else f"Coluna_{i+1}" for i, h in enumerate(data[0])]
    seen = {}
    new_headers = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            new_headers.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            new_headers.append(h)
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
    if 'Consultor (PF)' in df_total.columns:
        df_total['Consultor_Match'] = df_total['Consultor (PF)'].astype(str).str.strip().str.lower()

    try:
        sheet_curso = client.open_by_url(SHEET_URL_CURSO_CRED)
        ws_curso = sheet_curso.get_worksheet(0)
        dados_curso = ws_curso.get_all_values()
        if len(dados_curso) > 1:
            lista_cursos = []
            for linha in dados_curso[1:]:
                if len(linha) >= 5:
                    nome_pessoa = str(linha[1]).strip()
                    status_curso = str(linha[4]).strip()
                    if nome_pessoa and nome_pessoa.lower() not in ['', 'none', 'nan']:
                        lista_cursos.append({
                            'Consultor_Match': nome_pessoa.lower(),
                            'Consultor de Sucesso': status_curso if status_curso else 'Pendente'
                        })
            df_curso = pd.DataFrame(lista_cursos)
            if not df_curso.empty:
                df_curso = df_curso.drop_duplicates(subset=['Consultor_Match'])
                df_total = pd.merge(df_total, df_curso, on='Consultor_Match', how='left')
                df_total['Consultor de Sucesso'] = df_total['Consultor de Sucesso'].fillna('Sem Registro')
            else:
                df_total['Consultor de Sucesso'] = 'Sem Registro'
        else:
            df_total['Consultor de Sucesso'] = 'Sem Registro'
    except Exception:
        df_total['Consultor de Sucesso'] = 'Sem Registro'

    if 'Consultor_Match' in df_total.columns:
        df_total = df_total.drop(columns=['Consultor_Match'])
    
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
    
    try:
        ws_target = sheet.worksheet("Em Previa")
    except Exception:
        ws_target = sheet.worksheet("Em Prévia")
        
    df_previas = get_dataframe_from_worksheet(ws_target)
    
    if df_previas.empty:
        return pd.DataFrame()
        
    col_mapping = {
        'Processo': 'Status do Processo',
        'Atualização Processo': 'Última Atualização',
        'Matr': 'Matrícula',
        'Data': 'Data Abertura',
        'Candidato': 'Candidato',
        'Whatsapp': 'WhatsApp',
        'Supervisor': 'Supervisor / PV',
        'Origem': 'Origem',
        'Cidade': 'Cidade'
    }
    
    df_previas = df_previas.rename(columns=col_mapping)
    
    if 'Última Atualização' in df_previas.columns:
        df_previas['Última Atualização'] = df_previas['Última Atualização'].astype(str).str.replace('h', '', case=False).str.strip()
    
    for col in df_previas.columns:
        df_previas[col] = df_previas[col].astype(str).str.strip()
        df_previas[col] = df_previas[col].replace(['', 'None', 'NaN', 'none', 'nan', 'NONE', 'NAN'], None)
    
    if 'Cidade' in df_previas.columns:
        df_previas['Cidade'] = df_previas['Cidade'].str.upper()

    if 'Candidato' in df_previas.columns and 'Status do Processo' in df_previas.columns:
        df_previas = df_previas.dropna(subset=['Candidato', 'Status do Processo'])
        df_previas = df_previas[
            (df_previas['Candidato'].str.lower() != 'none') & 
            (df_previas['Status do Processo'].str.lower() != 'none')
        ]
        df_previas['Candidato_Match'] = df_previas['Candidato'].astype(str).str.strip().str.lower()

    try:
        sheet_pro = client.open_by_url(SHEET_URL_CURSO_PRO)
        ws_pro = sheet_pro.get_worksheet(0)
        dados_pro = ws_pro.get_all_values()
        if len(dados_pro) > 1:
            lista_pro = []
            for linha in dados_pro[1:]:
                if len(linha) >= 5:
                    nome_cand = str(linha[1]).strip()
                    status_pro = str(linha[4]).strip()
                    if nome_cand and nome_cand.lower() not in ['', 'none', 'nan']:
                        lista_pro.append({
                            'Candidato_Match': nome_cand.lower(),
                            'Consultor PRO': status_pro if status_pro else 'Pendente'
                        })
            df_pro = pd.DataFrame(lista_pro)
            if not df_pro.empty:
                df_pro = df_pro.drop_duplicates(subset=['Candidato_Match'])
                df_previas = pd.merge(df_previas, df_pro, on='Candidato_Match', how='left')
                df_previas['Consultor PRO'] = df_previas['Consultor PRO'].fillna('Sem Registro')
            else:
                df_previas['Consultor PRO'] = 'Sem Registro'
        else:
            df_previas['Consultor PRO'] = 'Sem Registro'
    except Exception:
        df_previas['Consultor PRO'] = 'Sem Registro'

    if 'Status do Processo' in df_previas.columns and 'Consultor PRO' in df_previas.columns:
        status_sem_acesso = ['aguardando docs pf', 'assinar termo', 'em análise']
        mask_sem_acesso = df_previas['Status do Processo'].str.lower().isin(status_sem_acesso)
        df_previas.loc[mask_sem_acesso, 'Consultor PRO'] = 'Sem Acesso'

    if 'Candidato_Match' in df_previas.columns:
        df_previas = df_previas.drop(columns=['Candidato_Match'])

    return df_previas

# ---------------------------------------------------------
# 3. Gerenciamento de Estado da Navegação
# ---------------------------------------------------------
if 'menu_selecionado' not in st.session_state:
    st.session_state.menu_selecionado = "🏠 Página Inicial"

opcao_atual = st.session_state.menu_selecionado
LOGO_ADEMICON = "https://www.ademicon.com.br/api/media/file/ademicon.svg?2026-01-08T16%3A57%3A33.024Z&dpl=dpl_9yCuySMtpVZ3Y8v8qWfgCTVqNMUo"

# ---------------------------------------------------------
# PÁGINA INICIAL (100% CENTRALIZADA E SEM LOGO NO TOPO)
# ---------------------------------------------------------
if opcao_atual == "🏠 Página Inicial":
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; color: #002B49; font-size: 2rem;'>Dashboard Corporativo | Gente & Gestão</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.05rem;'>Selecione abaixo o módulo gerencial que deseja acompanhar:</p>", unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Cards centralizados
    _, card1, card2, _ = st.columns([1.5, 4, 4, 1.5])
    
    with card1:
        st.markdown("""
            <div style="background-color: #ffffff; padding: 22px; border-radius: 8px; border-top: 4px solid #002B49; box-shadow: 0 4px 10px rgba(0,0,0,0.05); text-align: center; height: 140px;">
                <h3 style="color: #002B49; margin-bottom: 6px; font-size: 1.15rem;">📋 Prévias</h3>
                <p style="color: #475569; font-size: 0.8rem; line-height: 1.3; margin-bottom: 0px;">
                    Gestão tática do pipeline de candidatos, status de cadastro e controle do curso <b>Consultor PRO</b>.
                </p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Acessar Gestão de Prévias", key="btn_p_vFINAL"):
            st.session_state.menu_selecionado = "📋 Prévias (Gestão de Candidatos)"
            st.rerun()

    with card2:
        st.markdown("""
            <div style="background-color: #ffffff; padding: 22px; border-radius: 8px; border-top: 4px solid #002B49; box-shadow: 0 4px 10px rgba(0,0,0,0.05); text-align: center; height: 140px;">
                <h3 style="color: #002B49; margin-bottom: 6px; font-size: 1.15rem;">📈 Matrículas Concluídas</h3>
                <p style="color: #475569; font-size: 0.8rem; line-height: 1.3; margin-bottom: 0px;">
                    Visão consolidada de parceiros ativos e descredenciados e monitoramento do <b>Consultor de Sucesso</b>.
                </p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Acessar Matrículas Concluídas", key="btn_m_vFINAL"):
            st.session_state.menu_selecionado = "📈 Matrículas Concluídas"
            st.rerun()

    # Rodapé elegante e centralizado
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center;">
            <span style="color: #64748b; font-size: 0.9rem; font-weight: 600;">Fabio Pelegrino - Head de Pessoas</span>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# MÓDULO 1: PRÉVIAS
# ---------------------------------------------------------
elif opcao_atual == "📋 Prévias (Gestão de Candidatos)":
    top_c1, top_c2, top_c3 = st.columns([2, 6, 2])
    with top_c1:
        if st.button("🏠 Voltar ao Menu Inicial", key="voltar_menu_previas"):
            st.session_state.menu_selecionado = "🏠 Página Inicial"
            st.rerun()
    with top_c3:
        st.markdown(f"<div style='text-align: right;'><img src='{LOGO_ADEMICON}' width='90'/></div>", unsafe_allow_html=True)

    try:
        df_previas_raw = load_data_previas()
    except Exception as e:
        st.error(f"⚠️ Erro ao conectar com a planilha de Prévias ou Curso PRO: {e}")
        st.stop()

    st.title("📋 Gestão de Prévias (Pipeline de Candidatos)")
    st.caption("Acompanhamento do status de cadastro e captação de novos parceiros.")
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 🔍 Filtros de Análise")
    
    col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns([2, 2, 2, 2, 1])

    if 'Supervisor / PV' in df_previas_raw.columns:
        sup_unicos_p = [str(s) for s in df_previas_raw['Supervisor / PV'].dropna().unique() if str(s).strip() != '']
        supervisores_previas = ["Todos"] + sorted(list(set(sup_unicos_p)))
    else:
        supervisores_previas = ["Todos"]

    with col_p1:
        supervisor_p_sel = st.selectbox("👔 Supervisor:", supervisores_previas, key="p_sup_sel")

    df_previas_filt = df_previas_raw.copy()
    if supervisor_p_sel != "Todos" and 'Supervisor / PV' in df_previas_filt.columns:
        df_previas_filt = df_previas_filt[df_previas_filt['Supervisor / PV'] == supervisor_p_sel]

    if 'Cidade' in df_previas_filt.columns:
        cid_unicas = [str(c) for c in df_previas_filt['Cidade'].dropna().unique() if str(c).strip() != '']
        cidades_previas = ["Todas"] + sorted(list(set(cid_unicas)))
    else:
        cidades_previas = ["Todas"]

    with col_p2:
        cidade_sel = st.selectbox("📍 Cidade:", cidades_previas, key="p_cid_sel")

    if cidade_sel != "Todas" and 'Cidade' in df_previas_filt.columns:
        df_previas_filt = df_previas_filt[df_previas_filt['Cidade'] == cidade_sel]

    if 'Status do Processo' in df_previas_filt.columns:
        status_unicos = [str(st_p) for st_p in df_previas_filt['Status do Processo'].dropna().unique() if str(st_p).strip() != '']
        status_previas = ["Todos"] + sorted(list(set(status_unicos)))
    else:
        status_previas = ["Todos"]

    with col_p3:
        status_sel = st.selectbox("📌 Status do Processo:", status_previas, key="p_status_sel")

    if status_sel != "Todos" and 'Status do Processo' in df_previas_filt.columns:
        df_previas_filt = df_previas_filt[df_previas_filt['Status do Processo'] == status_sel]

    with col_p4:
        curso_pro_sel = st.selectbox("🎓 Consultor PRO:", ["Todos", "Concluído", "Pendente", "Sem Registro", "Sem Acesso"], key="p_curso_pro_sel")

    if curso_pro_sel != "Todos" and 'Consultor PRO' in df_previas_filt.columns:
        df_previas_filt = df_previas_filt[df_previas_filt['Consultor PRO'].str.lower() == curso_pro_sel.lower()]

    with col_p5:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", key="p_btn_refresh"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    tot_candidatos = len(df_previas_filt)
    cidades_validas = df_previas_filt['Cidade'].dropna() if 'Cidade' in df_previas_filt.columns else pd.Series()
    cidades_unicas = len(cidades_validas.unique())

    kpi_p1, kpi_p2 = st.columns(2)
    kpi_p1.metric("Candidatos em Prévia", f"{tot_candidatos:,}".replace(",", "."))
    kpi_p2.metric("Cidades de Origem", f"{cidades_unicas}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    ademicon_colors = ['#002B49', '#00406C', '#005691', '#006CB7', '#3389C5', '#66A7D4']
    
    st.subheader("📊 Candidatos por Status do Processo")
    if 'Status do Processo' in df_previas_filt.columns and not df_previas_filt.empty:
        df_st = df_previas_filt['Status do Processo'].dropna().value_counts().reset_index()
        df_st.columns = ['Status do Processo', 'Quantidade']
        
        fig_st = px.bar(
            df_st, x='Status do Processo', y='Quantidade', text='Quantidade',
            color='Status do Processo', color_discrete_sequence=ademicon_colors
        )
        fig_st.update_traces(textposition='outside', marker_line_color='#002B49', marker_line_width=1)
        fig_st.update_layout(showlegend=False, xaxis_title="", yaxis_title="Candidatos", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_st, use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    st.subheader("🎓 Painel Gerencial: Status do Curso Consultor PRO (Prévias)")
    st.caption("Acompanhamento do andamento do curso obrigatório para os candidatos em pipeline.")

    total_previas_curso = len(df_previas_filt)
    total_pro_concluidos = len(df_previas_filt[df_previas_filt['Consultor PRO'].str.lower() == 'concluído']) if 'Consultor PRO' in df_previas_filt.columns else 0
    total_pro_pendentes = len(df_previas_filt[df_previas_filt['Consultor PRO'].str.lower() == 'pendente']) if 'Consultor PRO' in df_previas_filt.columns else 0
    total_pro_sem_registro = len(df_previas_filt[df_previas_filt['Consultor PRO'].str.lower() == 'sem registro']) if 'Consultor PRO' in df_previas_filt.columns else 0
    total_pro_sem_acesso = len(df_previas_filt[df_previas_filt['Consultor PRO'].str.lower() == 'sem acesso']) if 'Consultor PRO' in df_previas_filt.columns else 0
    taxa_pro_conclusao = (total_pro_concluidos / total_previas_curso * 100) if total_previas_curso > 0 else 0

    mp_kpi1, mp_kpi2, mp_kpi3, mp_kpi4, mp_kpi5 = st.columns(5)
    mp_kpi1.metric("Total na Seleção", f"{total_previas_curso}")
    mp_kpi2.metric("PRO Concluído", f"{total_pro_concluidos}")
    mp_kpi3.metric("PRO Pendente", f"{total_pro_pendentes}")
    mp_kpi4.metric("PRO Sem Registro", f"{total_pro_sem_registro}")
    mp_kpi5.metric("Taxa Conclusão PRO", f"{taxa_pro_conclusao:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    col_mp_graf, col_mp_ranking = st.columns(2)

    with col_mp_graf:
        st.subheader("📊 Proporção Curso Consultor PRO")
        if total_previas_curso > 0 and 'Consultor PRO' in df_previas_filt.columns:
            df_pro_count = df_previas_filt['Consultor PRO'].value_counts().reset_index()
            df_pro_count.columns = ['Status do Curso', 'Quantidade']
            
            fig_donut_pro = px.pie(
                df_pro_count, values='Quantidade', names='Status do Curso',
                color='Status do Curso',
                color_discrete_map={'Concluído': '#002B49', 'Pendente': '#3389C5', 'Sem Registro': '#94a3b8', 'Sem Acesso': '#e2e8f0'},
                hole=0.5
            )
            fig_donut_pro.update_traces(textinfo='percent+label', textfont_size=14)
            fig_donut_pro.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_donut_pro, use_container_width=True)

    with col_mp_ranking:
        st.subheader("🏆 Prévias: Top Supervisores com Pendência PRO")
        if not df_previas_filt.empty and 'Supervisor / PV' in df_previas_filt.columns and 'Consultor PRO' in df_previas_filt.columns:
            df_pro_pendentes_calc = df_previas_filt[df_previas_filt['Consultor PRO'].str.lower() == 'pendente']
            if not df_pro_pendentes_calc.empty:
                df_sup_pro_pend = df_pro_pendentes_calc['Supervisor / PV'].value_counts().head(8).reset_index()
                df_sup_pro_pend.columns = ['Supervisor / PV', 'Pendências PRO']
                
                fig_rank_pro = px.bar(
                    df_sup_pro_pend, x='Pendências PRO', y='Supervisor / PV', orientation='h',
                    text='Pendências PRO', color_discrete_sequence=['#002B49']
                )
                fig_rank_pro.update_traces(textposition='outside')
                fig_rank_pro.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Pendências PRO", yaxis_title="", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_rank_pro, use_container_width=True)
            else:
                st.success("🎉 Parabéns! Não há pendências PRO nestas prévias.")

    st.divider()
    st.subheader("📋 Funil de Candidatos - Acompanhamento do Supervisor")
    
    col_p_busca, col_p_export = st.columns([3, 1])
    with col_p_busca:
        termo_p_busca = st.text_input("🔎 Pesquisar Candidato, Status, WhatsApp ou Cidade:")

    df_p_tabela = df_previas_filt.copy()
    if termo_p_busca:
        cols_para_busca = [c for c in df_p_tabela.columns if df_p_tabela[c].dtype == 'object']
        mascara = pd.Series(False, index=df_p_tabela.index)
        for col in cols_para_busca:
            mascara |= df_p_tabela[col].astype(str).str.contains(termo_p_busca, case=False, na=False)
        df_p_tabela = df_p_tabela[mascara]

    cols_ordem_supervisor = [
        'Status do Processo', 'Candidato', 'WhatsApp', 'Supervisor / PV',
        'Consultor PRO', 'Origem', 'Cidade', 'Data Abertura', 'Última Atualização', 'Matrícula'
    ]
    cols_finais = [c for c in cols_ordem_supervisor if c in df_p_tabela.columns]
    csv_p_data = df_p_tabela[cols_finais].to_csv(index=False).encode('utf-8')

    with col_p_export:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("📥 Exportar Lista (CSV)", data=csv_p_data, file_name="pipeline_candidatos_previas.csv", mime="text/css")

    st.dataframe(df_p_tabela[cols_finais], use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# MÓDULO 2: MATRÍCULAS CONCLUÍDAS
# ---------------------------------------------------------
elif opcao_atual == "📈 Matrículas Concluídas":
    top_c1, top_c2, top_c3 = st.columns([2, 6, 2])
    with top_c1:
        if st.button("🏠 Voltar ao Menu Inicial", key="voltar_menu_matriculas"):
            st.session_state.menu_selecionado = "🏠 Página Inicial"
            st.rerun()
    with top_c3:
        st.markdown(f"<div style='text-align: right;'><img src='{LOGO_ADEMICON}' width='90'/></div>", unsafe_allow_html=True)

    try:
        df_raw = load_data_cred()
    except Exception as e:
        st.error(f"⚠️ Erro ao conectar com o Google Sheets: {e}")
        st.stop()

    st.title("📈 Matrículas Concluídas")
    st.caption("Visão consolidada de matrículas ativas e descredenciadas por unidade e supervisor.")
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 🔍 Filtros de Análise")
    col_f_unidade, col_f_supervisor, col_f_curso, col_f_btn = st.columns([2, 2, 2, 1])

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

    with col_f_curso:
        curso_sel = st.selectbox("🎓 Consultor de Sucesso:", ["Todos", "Concluído", "Pendente", "Sem Registro"])

    if curso_sel != "Todos" and 'Consultor de Sucesso' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['Consultor de Sucesso'].str.lower() == curso_sel.lower()]

    with col_f_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    tot_ativas = len(df_filtrado[df_filtrado['Status'] == 'Ativo'])
    tot_descred = len(df_filtrado[df_filtrado['Status'] == 'Descredenciado'])
    tot_geral = tot_ativas + tot_descred

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Matrículas Ativas", f"{tot_ativas:,}".replace(",", "."))
    kpi2.metric("Descredenciadas", f"{tot_descred:,}".replace(",", "."))
    kpi3.metric("Total na Base", f"{tot_geral:,}".replace(",", "."))

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

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

    cols_exibicao = ['Matrícula', 'Razão Social', 'Consultor (PF)', 'Unidade', 'Supervisor / PV', 'Consultor de Sucesso', 'E-mail', 'Status']
    cols_existentes = [c for c in cols_exibicao if c in df_tabela.columns]
    csv_data = df_tabela[cols_existentes].to_csv(index=False).encode('utf-8')

    with col_export:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("📥 Exportar CSV", data=csv_data, file_name="detalhamento_credenciamento_ademicon.csv", mime="text/csv")

    st.dataframe(df_tabela[cols_existentes], use_container_width=True, hide_index=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    st.subheader("🎓 Painel Gerencial: Status do Curso Obrigatório (Apenas Ativos)")
    st.caption("Acompanhamento exclusivo dos consultores ativos na rede para cobrança e conclusão do curso obrigatório.")

    df_ativos_gerencial = df_raw[df_raw['Status'] == 'Ativo'].copy()
    col_mg_unidade, _ = st.columns([2, 2])
    if 'Unidade' in df_ativos_gerencial.columns:
        unid_gerencial_list = ["Todas"] + sorted([str(u) for u in df_ativos_gerencial['Unidade'].dropna().unique() if str(u).strip() not in ['', 'NAN', 'NONE']])
    else:
        unid_gerencial_list = ["Todas"]

    with col_mg_unidade:
        unidade_gerencial_sel = st.selectbox("📍 Filtrar Unidade para Análise de Cursos:", unid_gerencial_list, key="mg_unidade_sel")

    df_mg = df_ativos_gerencial.copy()
    if unidade_gerencial_sel != "Todas" and 'Unidade' in df_mg.columns:
        df_mg = df_mg[df_mg['Unidade'] == unidade_gerencial_sel]

    total_unid_curso = len(df_mg)
    total_concluidos = len(df_mg[df_mg['Consultor de Sucesso'].str.lower() == 'concluído'])
    total_pendentes = len(df_mg[df_mg['Consultor de Sucesso'].str.lower() == 'pendente'])
    total_sem_registro = len(df_mg[df_mg['Consultor de Sucesso'].str.lower() == 'sem registro'])
    taxa_conclusao = (total_concluidos / total_unid_curso * 100) if total_unid_curso > 0 else 0

    mg_kpi1, mg_kpi2, mg_kpi3, mg_kpi4, mg_kpi5 = st.columns(5)
    mg_kpi1.metric("Colaboradores Ativos", f"{total_unid_curso}")
    mg_kpi2.metric("Concluídos", f"{total_concluidos}")
    mg_kpi3.metric("Pendentes", f"{total_pendentes}")
    mg_kpi4.metric("Sem Registro", f"{total_sem_registro}")
    mg_kpi5.metric("Taxa de Conclusão", f"{taxa_conclusao:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    col_mg_graf, col_mg_ranking = st.columns(2)

    with col_mg_graf:
        st.subheader("📊 Proporção de Conclusão (Ativos)")
        if total_unid_curso > 0 and 'Consultor de Sucesso' in df_mg.columns:
            df_curso_count = df_mg['Consultor de Sucesso'].value_counts().reset_index()
            df_curso_count.columns = ['Status do Curso', 'Quantidade']
            
            fig_donut = px.pie(
                df_curso_count, values='Quantidade', names='Status do Curso',
                color='Status do Curso',
                color_discrete_map={'Concluído': '#002B49', 'Pendente': '#3389C5', 'Sem Registro': '#e2e8f0'},
                hole=0.5
            )
            fig_donut.update_traces(textinfo='percent+label', textfont_size=14)
            fig_donut.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_donut, use_container_width=True)

    with col_mg_ranking:
        st.subheader("🏆 Top Supervisores com Pendências")
        if not df_mg.empty and 'Supervisor / PV' in df_mg.columns and 'Consultor de Sucesso' in df_mg.columns:
            df_pend = df_mg[df_mg['Consultor de Sucesso'].str.lower() == 'pendente']
            if not df_pend.empty:
                df_sup_pend = df_pend['Supervisor / PV'].value_counts().head(8).reset_index()
                df_sup_pend.columns = ['Supervisor / PV', 'Ocorrências']
                
                fig_rank = px.bar(
                    df_sup_pend, x='Ocorrências', y='Supervisor / PV', orientation='h',
                    text='Ocorrências', color_discrete_sequence=['#002B49']
                )
                fig_rank.update_traces(textposition='outside')
                fig_rank.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Pendências", yaxis_title="", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_rank, use_container_width=True)
            else:
                st.success("🎉 Parabéns! Não há pendências para os filtros selecionados.")
