import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# CONFIGURACAO
# ------------------------------------------------------------
st.set_page_config(
    page_title="Salinas Resorts | Gestão de Cotas",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ARQUIVOS_RESORTS = {
    "Beach Resort": "Salinas Beach Resort.xlsx",
    "Exclusive Resort": "Salinas Exclusive Resort.xlsx",
    "Park Resort": "Salinas Park Resort.xlsx",
    "Premium Resort": "Salinas Premium Resort.xlsx",
}

# ------------------------------------------------------------
# ESTILO VISUAL
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

    :root {
        --navy: #102d52;
        --navy-2: #174779;
        --blue: #1769aa;
        --sky: #eaf3fb;
        --ink: #1d2b3a;
        --muted: #667789;
        --line: #dfe7ef;
        --surface: #ffffff;
        --bg: #f4f7fb;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp { background: var(--bg); }
    [data-testid="stHeader"] { background: rgba(244,247,251,0.92); }
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1500px; }

    [data-testid="stSidebar"] {
        background: #102d52;
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    [data-testid="stSidebar"] * { color: #f5f8fc !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #d9e6f3 !important; }

    .brand-eyebrow {
        text-transform: uppercase; letter-spacing: .18em; font-size: .72rem;
        color: #c7d9ec; font-weight: 700; margin-bottom: .55rem;
    }
    .hero {
        background-color: #143e62;
        background-image: linear-gradient(90deg, rgba(8,34,54,.91) 0%, rgba(8,34,54,.70) 48%, rgba(8,34,54,.16) 100%),
          url('https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=1800&q=85');
        background-size: cover; background-position: center 55%;
        color: white; border-radius: 22px; padding: 65px 42px;
        box-shadow: 0 16px 38px rgba(16,45,82,.16);
        margin-bottom: 25px; position: relative; overflow: hidden;
        min-height: 350px; display: flex; flex-direction: column; justify-content: center;
    }
    .hero h1 {
        font-family: 'Playfair Display', serif; font-size: clamp(2.4rem, 4.5vw, 4.2rem);
        line-height: 1.15; margin: 0 0 10px 0; color: #fff;
    }
    .hero p { margin: 0; color: #f0f5f8; font-size: 1.05rem; max-width: 610px; line-height: 1.7; }
    .hero-tag {
        display: inline-block; align-self: flex-start; border: 1px solid rgba(255,255,255,.48);
        border-radius: 999px; padding: 6px 12px; margin-bottom: 16px;
        color: #eaf3fb; font-size: .75rem; letter-spacing: .06em;
    }
    .section-heading { color: var(--ink); font-size: 1.35rem; font-weight: 700; margin: 8px 0 4px 0; }
    .section-subtitle { color: var(--muted); margin: 0 0 18px 0; font-size: .93rem; }
    .panel {
        background: white; border: 1px solid var(--line); border-radius: 18px;
        padding: 22px 24px; margin: 10px 0 22px 0;
        box-shadow: 0 5px 18px rgba(20,50,80,.035);
    }
    .metric-card {
        background: white; border: 1px solid var(--line); border-radius: 16px;
        padding: 17px 19px; min-height: 100px;
    }
    .metric-label { color: var(--muted); font-size: .8rem; margin-bottom: 7px; }
    .metric-value { color: var(--navy); font-size: 1.65rem; font-weight: 700; line-height: 1.2; }
    .result-card {
        background: #fff; border: 1px solid #e0e8f0; border-radius: 17px;
        padding: 20px 22px; margin: 12px 0;
        box-shadow: 0 6px 20px rgba(18,48,78,.045);
    }
    .result-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
    .result-title { color: var(--navy); font-weight: 700; font-size: 1.1rem; margin: 0 0 5px 0; }
    .result-subtitle { color: var(--muted); font-size: .88rem; margin: 0; }
    .status-pill {
        display: inline-block; white-space: nowrap; border-radius: 999px;
        background: #e8f6ef; color: #16734b; font-weight: 700;
        padding: 6px 10px; font-size: .75rem;
    }
    .result-details {
        display: grid; grid-template-columns: repeat(3, minmax(0,1fr));
        gap: 12px; margin-top: 18px;
    }
    .detail-box { background: #f6f9fc; border-radius: 11px; padding: 11px 13px; }
    .detail-label { color: #6c7d8e; font-size: .73rem; margin-bottom: 4px; }
    .detail-value { color: #203b57; font-weight: 600; font-size: .9rem; overflow-wrap: anywhere; }
    .empty-state {
        background: white; border: 1px dashed #c9d7e5; border-radius: 16px;
        padding: 28px; text-align: center; color: var(--muted); margin-top: 12px;
    }
    div.stButton > button[kind="primary"] {
        background: #1769aa; border: 1px solid #1769aa; border-radius: 10px;
        min-height: 3rem; font-weight: 700; letter-spacing: .01em;
        box-shadow: 0 5px 12px rgba(23,105,170,.15);
    }
    div.stButton > button[kind="primary"]:hover { background: #12568e; border-color: #12568e; }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        border-radius: 10px !important; border-color: #d6e0e9 !important;
    }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
    @media (max-width: 700px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .hero { padding: 40px 22px; min-height: 310px; border-radius: 17px; background-position: 60% center; }
        .result-details { grid-template-columns: 1fr; }
        .result-top { display: block; }
        .status-pill { margin-top: 10px; }
        .panel { padding: 17px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# LEITURA DOS EXCEL
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def carregar_todos_os_dados():
    dados_consolidados = {}
    avisos = []

    for nome_resort, arquivo in ARQUIVOS_RESORTS.items():
        if not os.path.exists(arquivo):
            dados_consolidados[nome_resort] = {}
            avisos.append(f"Arquivo não encontrado: {arquivo}")
            continue

        try:
            abas = pd.read_excel(arquivo, sheet_name=None, header=None)
            abas_validas = {}

            for aba_nome, bruto in abas.items():
                linha_cabecalho = None
                palavras_chave = ("CHECK", "COTA", "UNIDADE", "DATA", "ENTRADA", "SAÍDA", "SAIDA")

                for idx, row in bruto.iterrows():
                    texto = " ".join(row.fillna("").astype(str).str.upper().tolist())
                    if any(palavra in texto for palavra in palavras_chave):
                        linha_cabecalho = idx
                        break

                if linha_cabecalho is None:
                    linha_cabecalho = 2 if len(bruto) > 2 else 0

                df = pd.read_excel(arquivo, sheet_name=aba_nome, header=linha_cabecalho)
                df = df.dropna(how="all")
                if df.empty:
                    continue

                df.columns = [
                    str(c).strip() if not str(c).startswith("Unnamed:") else f"Coluna {i + 1}"
                    for i, c in enumerate(df.columns)
                ]
                primeira_coluna = df.columns[0]
                df[primeira_coluna] = df[primeira_coluna].ffill()
                abas_validas[aba_nome] = df

            dados_consolidados[nome_resort] = abas_validas
        except Exception as exc:
            dados_consolidados[nome_resort] = {}
            avisos.append(f"Não foi possível ler {arquivo}: {exc}")

    return dados_consolidados, avisos


def localizar_colunas_data(df):
    col_checkin, col_checkout = None, None

    for coluna in df.columns:
        nome = str(coluna).strip().upper()
        if col_checkin is None and any(x in nome for x in ("CHECK-IN", "CHECKIN", "ENTRADA", "DATA INICIAL", "INÍCIO", "INICIO")):
            col_checkin = coluna
        if col_checkout is None and any(x in nome for x in ("CHECK-OUT", "CHECKOUT", "SAÍDA", "SAIDA", "TÉRMINO", "TERMINO", "DATA FINAL", "FINAL")):
            col_checkout = coluna

    # Fallback apenas quando os cabeçalhos não ajudam.
    if col_checkin is None and len(df.columns) > 1:
        col_checkin = df.columns[1]
    if col_checkout is None and len(df.columns) > 2:
        col_checkout = df.columns[2]

    return col_checkin, col_checkout


def data_segura(valor):
    if pd.isna(valor):
        return pd.NaT
    try:
        return pd.to_datetime(valor, errors="coerce", dayfirst=True)
    except (ValueError, TypeError):
        return pd.NaT


base_dados, avisos_arquivos = carregar_todos_os_dados()
total_abas = sum(len(abas) for abas in base_dados.values())
total_resorts_com_dados = sum(bool(abas) for abas in base_dados.values())

# ------------------------------------------------------------
# MENU LATERAL
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🏖️ SALINAS")
    st.markdown("**GESTÃO DE COTAS**")
    st.markdown("---")
    menu = st.radio(
        "MENU PRINCIPAL",
        ["🔎 Consultar cotas", "📅 Cronogramas", "⚙️ Cadastros"],
        label_visibility="visible",
    )
    st.markdown("---")
    st.caption("Painel administrativo")
    st.caption("Consulta de períodos e cotas")
    if st.button("🔄 Atualizar planilhas", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ------------------------------------------------------------
# CABECALHO
# ------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <div class="brand-eyebrow">Sua próxima experiência começa aqui</div>
        <div class="hero-tag">GESTÃO DE COTAS E ESTADIAS</div>
        <h1>Salinas Resorts</h1>
        <p>O seu refúgio no litoral paraense. Explore os períodos cadastrados e organize cada estadia com conforto e praticidade.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Avisos dos arquivos, sem interromper a aplicação
if avisos_arquivos:
    with st.expander("Verificar arquivos Excel", expanded=False):
        st.warning("Confira se os quatro arquivos estão na mesma pasta do aplicativo.")
        for aviso in avisos_arquivos:
            st.write(f"• {aviso}")

# ------------------------------------------------------------
# CONSULTA
# ------------------------------------------------------------
if menu == "🔎 Consultar cotas":
    st.markdown('<div class="section-heading">Planeje sua próxima estadia</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Escolha seu resort, selecione as datas e descubra os períodos cadastrados para sua viagem.</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        col_resort, col_andar = st.columns([1.4, 1])
        with col_resort:
            opcoes_resorts = ["Todos os resorts"] + list(ARQUIVOS_RESORTS.keys())
            resort_selecionado = st.selectbox("Resort", opcoes_resorts)
        with col_andar:
            andar_pref = st.selectbox(
                "Preferência de andar",
                ["Qualquer andar", "Andar alto", "Andar médio", "Andar baixo"],
            )
            st.caption("A preferência de andar só será aplicada quando essa informação existir na planilha.")

        col_in, col_out = st.columns(2)
        with col_in:
            data_entrada = st.date_input("Check-in", value=date.today(), format="DD/MM/YYYY")
        with col_out:
            data_saida = st.date_input("Check-out", value=date.today(), format="DD/MM/YYYY")

        buscar = st.button("🔎  Buscar cotas no período", type="primary", use_container_width=True)

    if buscar:
        if data_saida <= data_entrada:
            st.error("A data de check-out precisa ser posterior à data de check-in.")
        else:
            resorts_alvo = list(ARQUIVOS_RESORTS.keys()) if resort_selecionado == "Todos os resorts" else [resort_selecionado]
            resultados = []

            with st.spinner("Consultando as planilhas..."):
                for nome_resort in resorts_alvo:
                    for nome_aba, df_original in base_dados.get(nome_resort, {}).items():
                        df = df_original.copy()
                        col_in_excel, col_out_excel = localizar_colunas_data(df)

                        if col_in_excel is None or col_out_excel is None:
                            continue

                        df["_data_in"] = df[col_in_excel].apply(data_segura)
                        df["_data_out"] = df[col_out_excel].apply(data_segura)

                        # Intervalo de hospedagem: check-out é exclusivo.
                        # O período cadastrado deve cobrir toda a estadia solicitada.
                        inicio = pd.Timestamp(data_entrada)
                        fim = pd.Timestamp(data_saida)
                        filtro = (
                            df["_data_in"].notna()
                            & df["_data_out"].notna()
                            & (df["_data_in"] <= inicio)
                            & (df["_data_out"] >= fim)
                        )

                        for _, linha in df.loc[filtro].iterrows():
                            cota = linha.iloc[0]
                            detalhes = []
                            for coluna in df.columns:
                                nome_coluna = str(coluna).lower()
                                if coluna in ("_data_in", "_data_out", col_in_excel, col_out_excel):
                                    continue
                                if any(p in nome_coluna for p in ("andar", "torre", "bloco", "apartamento", "unidade", "observ")):
                                    valor = linha[coluna]
                                    if pd.notna(valor) and str(valor).strip().lower() != "nan":
                                        detalhes.append(f"{coluna}: {valor}")

                            resultados.append({
                                "resort": nome_resort,
                                "cota": str(cota),
                                "aba": nome_aba,
                                "entrada": linha["_data_in"].strftime("%d/%m/%Y"),
                                "saida": linha["_data_out"].strftime("%d/%m/%Y"),
                                "detalhes": " • ".join(detalhes) if detalhes else "Sem detalhes adicionais na planilha",
                            })

            st.markdown("---")
            st.markdown('<div class="section-heading">Resultado da consulta</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="section-subtitle">Período solicitado: {data_entrada.strftime("%d/%m/%Y")} a {data_saida.strftime("%d/%m/%Y")}</div>',
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Registros encontrados</div><div class="metric-value">{len(resultados)}</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Resorts consultados</div><div class="metric-value">{len(resorts_alvo)}</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Planilhas com dados</div><div class="metric-value">{total_resorts_com_dados}</div></div>', unsafe_allow_html=True)

            if resultados:
                st.caption("Importante: os resultados refletem os períodos encontrados nas planilhas. Esta consulta não confirma nem bloqueia uma reserva.")
                for item in resultados:
                    st.markdown(
                        f"""
                        <div class="result-card">
                            <div class="result-top">
                                <div>
                                    <div class="result-title">🏨 {item['resort']}</div>
                                    <p class="result-subtitle">Cota {item['cota']}</p>
                                </div>
                                <span class="status-pill">Encontrado na planilha</span>
                            </div>
                            <div class="result-details">
                                <div class="detail-box">
                                    <div class="detail-label">CHECK-IN CADASTRADO</div>
                                    <div class="detail-value">{item['entrada']}</div>
                                </div>
                                <div class="detail-box">
                                    <div class="detail-label">CHECK-OUT CADASTRADO</div>
                                    <div class="detail-value">{item['saida']}</div>
                                </div>
                                <div class="detail-box">
                                    <div class="detail-label">ABA / PERÍODO</div>
                                    <div class="detail-value">{item['aba']}</div>
                                </div>
                            </div>
                            <p style="color:#667789;font-size:.84rem;margin:14px 0 0 0;">{item['detalhes']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    """
                    <div class="empty-state">
                        <h3 style="color:#203b57;margin-top:0;">Nenhum período correspondente foi encontrado</h3>
                        <p>Confira as datas, selecione outro resort ou verifique os cronogramas importados.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ------------------------------------------------------------
# CRONOGRAMAS
# ------------------------------------------------------------
elif menu == "📅 Cronogramas":
    st.markdown('<div class="section-heading">Cronogramas dos resorts</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Consulte os dados importados dos arquivos Excel.</div>', unsafe_allow_html=True)

    col_r, col_a = st.columns(2)
    with col_r:
        resort_bruto = st.selectbox("Selecione o resort", list(ARQUIVOS_RESORTS.keys()))
    abas = base_dados.get(resort_bruto, {})
    with col_a:
        aba_bruta = st.selectbox("Selecione a aba / período", list(abas.keys()) if abas else ["Nenhuma aba encontrada"])

    if abas and aba_bruta in abas:
        df_exibir = abas[aba_bruta]
        filtro_texto = st.text_input("Filtrar linhas", placeholder="Digite cota, unidade ou informação...")
        if filtro_texto:
            mascara = df_exibir.astype(str).apply(
                lambda coluna: coluna.str.contains(filtro_texto, case=False, na=False, regex=False)
            ).any(axis=1)
            df_exibir = df_exibir[mascara]
        st.caption(f"{len(df_exibir)} linha(s) exibida(s) • Aba: {aba_bruta}")
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Baixar esta tabela em CSV",
            data=df_exibir.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{resort_bruto}_{aba_bruta}.csv".replace("/", "-"),
            mime="text/csv",
        )
    else:
        st.warning("Nenhum dado foi encontrado para este resort. Confira se o arquivo Excel está na pasta do aplicativo.")

# ------------------------------------------------------------
# CADASTROS
# ------------------------------------------------------------
elif menu == "⚙️ Cadastros":
    st.markdown('<div class="section-heading">Cadastro de cotistas</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Área preparada para organizar os dados de contato dos cotistas.</div>',
        unsafe_allow_html=True,
    )
    st.info("Nesta versão, os cadastros ainda não são gravados permanentemente. Para evitar perda de informações, o formulário abaixo é apenas demonstrativo até definirmos onde os dados serão armazenados.")

    with st.container(border=True):
        with st.form("form_cotista"):
            nome_cotista = st.text_input("Nome do cotista")
            numero_cota = st.text_input("Número da cota")
            telefone = st.text_input("Telefone / WhatsApp")
            resort_cadastro = st.selectbox("Resort relacionado", list(ARQUIVOS_RESORTS.keys()))
            observacoes = st.text_area("Observações", placeholder="Informações adicionais (opcional)")
            enviado = st.form_submit_button("Validar cadastro", type="primary", use_container_width=True)

        if enviado:
            if not nome_cotista.strip() or not numero_cota.strip():
                st.error("Preencha pelo menos o nome do cotista e o número da cota.")
            else:
                st.success("Dados validados nesta sessão. Eles ainda não foram salvos em um banco de dados.")

# ------------------------------------------------------------
# RODAPE
# ------------------------------------------------------------
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#8190a0;font-size:.78rem;">Salinas Resorts • Painel administrativo de consulta de cotas</p>',
    unsafe_allow_html=True,
)
