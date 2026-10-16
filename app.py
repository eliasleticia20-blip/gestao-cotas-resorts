import os
import html
import json
import hmac
import re
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from datetime import date, datetime
import calendar

import pandas as pd
import streamlit as st

# Utilitários de exibição e exportação de fichas administrativas.
def data_br(valor):
    if not valor:
        return "—"
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(valor)


def gerar_pdf_reserva(ficha):
    """Gera ficha administrativa em memória, sem gravar dados pessoais em disco."""
    from io import BytesIO
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    fonte = "Helvetica"
    caminho_fonte = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if os.path.isfile(caminho_fonte):
        if "SalinasSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("SalinasSans", caminho_fonte))
        fonte = "SalinasSans"
    azul = colors.HexColor("#102D52")
    dourado = colors.HexColor("#C5A26B")
    cinza = colors.HexColor("#65758B")
    fundo = colors.HexColor("#F3F7FB")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SalTitle", fontName=fonte, fontSize=18, leading=24, textColor=azul, alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="SalSub", fontName=fonte, fontSize=9, leading=15, textColor=cinza, alignment=TA_CENTER, spaceAfter=14))
    styles.add(ParagraphStyle(name="SalHead", fontName=fonte, fontSize=11, leading=16, textColor=azul, spaceBefore=13, spaceAfter=8))
    styles.add(ParagraphStyle(name="SalBody", fontName=fonte, fontSize=9, leading=15, textColor=azul))
    styles.add(ParagraphStyle(name="SalFoot", fontName=fonte, fontSize=8, leading=12, textColor=cinza))
    def txt(v):
        return escape(str(v) if v not in (None, "") else "—")
    def linha(campo, valor):
        return [Paragraph(f"<b>{txt(campo)}</b>", styles["SalBody"]), Paragraph(txt(valor), styles["SalBody"])]
    def tabela(pares):
        t = Table([linha(k, v) for k, v in pares], colWidths=[48*mm, 126*mm], hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,-1),fundo), ("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),10), ("RIGHTPADDING",(0,0),(-1,-1),10), ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7), ("LINEBELOW",(0,0),(-1,-2),.4,colors.HexColor("#DCE5EF"))]))
        return t
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=20*mm, bottomMargin=18*mm, title="Ficha de reserva - Salinas Resorts")
    itens = [Paragraph("SALINAS RESORTS", styles["SalTitle"]), Paragraph("FICHA ADMINISTRATIVA DE RESERVA", styles["SalSub"])]
    faixa = Table([[""]], colWidths=[174*mm], rowHeights=[2*mm])
    faixa.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),dourado)]))
    itens += [faixa, Paragraph("Dados da hospedagem", styles["SalHead"]), tabela([("Resort", ficha.get("resort")), ("Cota", ficha.get("cota")), ("Check-in", data_br(ficha.get("checkin"))), ("Check-out", data_br(ficha.get("checkout"))), ("Situação", str(ficha.get("status") or "—").capitalize()), ("ID da reserva", ficha.get("id") or ficha.get("reserva_id"))])]
    hospede = ficha.get("hospede")
    if isinstance(hospede, dict):
        itens += [Paragraph("Hóspede principal", styles["SalHead"]), tabela([("Nome", hospede.get("nome")), ("CPF", hospede.get("cpf")), ("WhatsApp", hospede.get("whatsapp")), ("E-mail", hospede.get("email"))])]
        acompanhantes = ficha.get("acompanhantes") or []
        itens.append(Paragraph("Acompanhantes", styles["SalHead"]))
        if acompanhantes:
            for i, a in enumerate(acompanhantes, 1):
                itens.append(KeepTogether([tabela([("Acompanhante", str(i)), ("Nome", a.get("nome")), ("CPF", a.get("cpf"))]), Spacer(1, 3*mm)]))
        else:
            itens.append(Paragraph("Nenhum acompanhante cadastrado.", styles["SalBody"]))
        itens += [Spacer(1, 5*mm), Paragraph("Versão dos termos aceitos: " + txt(hospede.get("versao_termo")), styles["SalFoot"])]
    else:
        itens += [Spacer(1, 6*mm), Paragraph("Pré-check-in ainda não concluído.", styles["SalBody"])]
    itens += [Spacer(1, 12*mm), Paragraph("Documento gerado pelo sistema de gestão de cotas. Não substitui voucher, confirmação ou autorização oficial do resort.", styles["SalFoot"])]
    doc.build(itens)
    return buffer.getvalue()


# Ícones vetoriais discretos para os componentes HTML do painel.
_ICON_PATHS = {
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    "check": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="m8 12 3 3 5-6"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7.1-7.1l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7.1 7.1l1.7-1.7"/>',
    "building": '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "waves": '<path d="M2 8c2.5 0 2.5 2 5 2s2.5-2 5-2 2.5 2 5 2 2.5-2 5-2M2 14c2.5 0 2.5 2 5 2s2.5-2 5-2 2.5 2 5 2 2.5-2 5-2"/>',
}


def icone(nome, tamanho=24, cor="currentColor"):
    caminho = _ICON_PATHS.get(nome, _ICON_PATHS["waves"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(tamanho)}" '
            f'height="{int(tamanho)}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{cor}" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{caminho}</svg>')


# Leitor PDF incorporado ao arquivo original (sem módulo separado).
"""Leitura posicional dos cronogramas Salinas. Requer PyMuPDF (fitz)."""
import fitz

ARQUIVOS_PDF = {
    'Beach Resort': 'Beath Resort.pdf',
    'Exclusive Resort': 'Exclusive Resort.pdf',
    'Park Resort': 'Park Resort.pdf',
    'Premium Resort': 'Premium Resort.pdf',
}
DATA_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')


def ler_pagina(page, resort, numero_pagina):
    palavras = page.get_text('words')
    cabecalho = ' '.join(w[4] for w in sorted((w for w in palavras if 10 < w[1] < 67), key=lambda w:(round(w[1]/9),w[0])))
    if 'Cronograma' not in cabecalho or 'Resort' not in cabecalho:
        return [], None
    partes = re.search(r'(Bloco\s*\d+[^\n]*|Torre\s+[\wÀ-ÿ-]+)', cabecalho, re.I)
    local = partes.group(1).strip() if partes else 'Local não identificado'
    # Retirar textos alheios ao nome do bloco, como títulos de outras seções.
    if local.lower().startswith('bloco'):
        local = re.split(r'\s+(?:COTA|CHECK-IN|20\d{2})\b', local, maxsplit=1, flags=re.I)[0]
    # Identificar coordenadas do cabeçalho da tabela para estabelecer as colunas.
    heads = [w for w in palavras if w[4].upper() in ('COTA', 'CHECK-IN', 'CHECK-OUT') and 55 < w[1] < 105]
    hc = next((w for w in heads if w[4].upper() == 'COTA'), None)
    hi = next((w for w in heads if w[4].upper() == 'CHECK-IN'), None)
    ho = next((w for w in heads if w[4].upper() == 'CHECK-OUT'), None)
    if not all((hc,hi,ho)):
        return [], f'{resort}: página {numero_pagina}, cabeçalho da tabela não identificado'
    lim_cota = (hc[2] + hi[0])/2
    lim_entrada = (hi[2] + ho[0])/2
    lim_saida = ho[2] + 13
    # Rótulos de cotas são células mescladas, centralizadas verticalmente.
    cotas = sorted([((w[1]+w[3])/2, w[4]) for w in palavras if w[0] < lim_cota and w[1] > hc[3] and (w[4].isdigit() or w[4].upper() == 'ADM')])
    if not cotas:
        return [], f'{resort}: página {numero_pagina}, nenhuma cota identificada'
    entradas = sorted([w for w in palavras if lim_cota < (w[0]+w[2])/2 < lim_entrada + 8 and DATA_RE.fullmatch(w[4]) and w[1] > hc[3]], key=lambda w:w[1])
    saidas = [w for w in palavras if lim_entrada < (w[0]+w[2])/2 < lim_saida and DATA_RE.fullmatch(w[4]) and w[1] > hc[3]]
    linhas=[]
    for ent in entradas:
        cy=(ent[1]+ent[3])/2
        sai=min(saidas, key=lambda w:abs((w[1]+w[3])/2-cy), default=None)
        if sai is None or abs((sai[1]+sai[3])/2-cy)>5:
            return [], f'{resort}: página {numero_pagina}, check-out não encontrado'
        # Atribuir pela distância ao centro da célula mesclada, não por ffill.
        cota=min(cotas, key=lambda x:abs(x[0]-cy))[1]
        if cota.upper()=='ADM':
            continue
        try:
            di=datetime.strptime(ent[4],'%d/%m/%Y')
            df=datetime.strptime(sai[4],'%d/%m/%Y')
            if df<=di or (df-di).days>35:
                raise ValueError('intervalo inconsistente')
        except ValueError:
            return [], f'{resort}: página {numero_pagina}, intervalo inválido: {ent[4]} - {sai[4]}'
        outros=[w for w in palavras if w[0]>365 and abs((w[1]+w[3])/2-cy)<4.5 and w[1]>hc[3]]
        periodo=' '.join(w[4] for w in sorted(outros,key=lambda w:w[0]))
        linhas.append({'Cota':str(cota),'Check-in':di,'Check-out':df,'Período':periodo,'Local':local,'Página PDF':numero_pagina})
    if not linhas:
        return [], f'{resort}: página {numero_pagina}, nenhuma data identificada'
    # Todas as cotas numéricas precisam ter pelo menos uma data.
    faltantes={v for _,v in cotas if v.isdigit()}-{x['Cota'] for x in linhas}
    if faltantes:
        return [], f'{resort}: página {numero_pagina}, cotas sem datas: {sorted(faltantes)}'
    return linhas, None


def carregar_pdfs(diretorio='.'):
    dados={}
    avisos=[]
    for resort,arquivo in ARQUIVOS_PDF.items():
        caminho=os.path.join(diretorio,arquivo)
        if not os.path.isfile(caminho):
            dados[resort]={}
            avisos.append(f'Arquivo não encontrado: {arquivo}')
            continue
        registros=[]
        try:
            with fitz.open(caminho) as pdf:
                for indice,pagina in enumerate(pdf):
                    # Páginas de capa e divisórias não possuem tabelas.
                    if 'CHECK-IN' not in pagina.get_text():
                        continue
                    linhas,erro=ler_pagina(pagina,resort,indice+1)
                    if erro:
                        avisos.append(erro)
                    else:
                        registros.extend(linhas)
        except Exception as exc:
            avisos.append(f'Erro ao abrir {arquivo}: {exc}')
        if registros:
            df=pd.DataFrame(registros)
            dados[resort]={local:grupo.reset_index(drop=True) for local,grupo in df.groupby('Local',sort=False)}
        else:
            dados[resort]={}
    return dados,avisos


# ------------------------------------------------------------
# CONFIGURACAO
# ------------------------------------------------------------
st.set_page_config(
    page_title="Salinas Resorts | Gestão de Cotas",
    page_icon=":material/beach_access:",
    layout="wide",
    initial_sidebar_state="expanded",
)

ARQUIVOS_RESORTS = ARQUIVOS_PDF

# A chave secreta fica exclusivamente no servidor Streamlit.
def config_segura(nome):
    return st.secrets.get(nome, os.getenv(nome, ""))


def chamar_supabase(funcao, dados):
    url = config_segura("SUPABASE_URL").rstrip("/")
    chave = config_segura("SUPABASE_KEY")
    if not url or not chave or "COLE_AQUI" in chave:
        raise RuntimeError("Configure SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit.")
    req = Request(
        f"{url}/rest/v1/rpc/{funcao}",
        data=json.dumps(dados).encode("utf-8"),
        headers={"apikey": chave, "Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except HTTPError as erro:
        try:
            detalhe = json.loads(erro.read().decode("utf-8")).get("message", "Erro no banco de dados")
        except Exception:
            detalhe = "Erro no banco de dados"
        raise RuntimeError(detalhe) from erro
    except URLError as erro:
        raise RuntimeError("Não foi possível conectar ao Supabase.") from erro


def validar_cpf(cpf):
    digitos = re.sub(r"\D", "", cpf)
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for tamanho in (9, 10):
        resto = (sum(int(digitos[i]) * (tamanho + 1 - i) for i in range(tamanho)) * 10) % 11
        if (0 if resto == 10 else resto) != int(digitos[tamanho]):
            return False
    return True


def tela_cliente(token):
    # Estilo exclusivo do link do hóspede; não modifica o painel administrativo.
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700&display=swap');
    :root { color-scheme: light; }
    .stApp {
        background: linear-gradient(120deg,rgba(5,32,54,.23),rgba(9,45,67,.08) 42%,rgba(8,38,60,.30)),
          url('https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=2000&q=90') center center / cover fixed !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stDecoration"] { display:none; }
    [data-testid="stSidebar"] { display:none !important; }
    .block-container {
        max-width: 980px !important;
        margin: 70px auto 70px !important;
        padding: 35px clamp(20px,4vw,48px) 42px !important;
        background: rgba(255,255,255,.97) !important;
        border: 1px solid rgba(255,255,255,.75);
        border-radius: 26px;
        box-shadow: 0 26px 80px rgba(3,27,48,.25);
    }
    .client-brand { text-align:center; color:#10395a; font-size:.78rem; font-weight:800; letter-spacing:.28em; margin:0 0 16px; }
    .client-brand span { color:#ba9250; }
    .client-head { text-align:center; margin-bottom:24px; }
    .client-kicker { color:#b28a49; letter-spacing:.24em; font-size:.73rem; font-weight:800; text-transform:uppercase; }
    .client-head h1 { color:#0c3554 !important; font-family:'Playfair Display',Georgia,serif !important; font-size:clamp(2rem,4.2vw,3.1rem) !important; line-height:1.18 !important; margin:9px 0 !important; font-weight:700 !important; }
    .client-head p { color:#60768b; font-size:.95rem; margin:0; }
    .booking-summary { display:grid; grid-template-columns:1.2fr .65fr 1.4fr; background:#eaf3fa; border:1px solid #dcebf5; border-radius:16px; padding:19px 20px; margin:18px 0 17px; gap:14px; }
    .booking-detail { padding:0 12px; border-right:1px solid #cbdde9; min-width:0; }
    .booking-detail:last-child { border-right:none; }
    .booking-detail .small { font-size:.75rem; color:#637e93; margin-bottom:6px; }
    .booking-detail .value { font-size:1rem; font-weight:800; color:#10395a; overflow-wrap:anywhere; }
    .client-note { background:#f5f9fc; border-left:3px solid #c49a55; padding:11px 15px; border-radius:7px; font-size:.82rem; color:#4f6477; margin-bottom:23px; }
    .client-section { background:linear-gradient(90deg,#f4e8d3,#fbf7f0); color:#123c5d; border-radius:12px; padding:12px 17px; font-weight:800; font-size:1.05rem; margin:15px 0 15px; }
    .client-section .gold { color:#b38b4a; margin-right:8px; }
    [data-testid="stForm"] { border:none !important; padding:0 !important; background:transparent !important; }
    [data-testid="stWidgetLabel"] p, label p { font-family:'DM Sans',sans-serif !important; font-weight:600 !important; color:#173d5c !important; }
    div[data-baseweb="input"] > div { background:#fff !important; border:1px solid #d3dfe8 !important; border-radius:11px !important; min-height:51px; }
    div[data-baseweb="input"] input { color:#173d5c !important; }
    div[data-baseweb="input"] > div:focus-within { border-color:#2877a9 !important; box-shadow:0 0 0 2px rgba(40,119,169,.10); }
    [data-testid="stNumberInput"] { padding:12px 16px; background:#f5f9fc; border-radius:12px; margin-bottom:10px; }
    [data-testid="stFormSubmitButton"] button { background:linear-gradient(90deg,#07517d,#0d3d65) !important; color:#fff !important; border:none !important; border-radius:13px !important; min-height:58px !important; font-size:1.08rem !important; font-weight:800 !important; box-shadow:0 9px 24px rgba(5,64,102,.20); }
    [data-testid="stFormSubmitButton"] button:hover { background:#0c6594 !important; }
    [data-testid="stCheckbox"] { margin:12px 0; }
    .client-footer { text-align:center; color:#688094; font-size:.77rem; margin-top:20px; }
    @media(max-width:700px) {
      .stApp { background-attachment:scroll !important; background-position:60% center !important; }
      .block-container { margin:20px 10px 30px !important; padding:23px 17px 27px !important; border-radius:19px !important; }
      .booking-summary { grid-template-columns:1fr 1fr; gap:15px 8px; padding:16px 10px; }
      .booking-detail { padding:0 8px; }
      .booking-detail:nth-child(2) { border-right:none; }
      .booking-detail:last-child { grid-column:1 / -1; border-top:1px solid #cbdde9; padding-top:12px; }
      .client-head h1 { font-size:2rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="client-brand">SALINAS <span>RESORTS</span></div><div class="client-head"><div class="client-kicker">Sua próxima experiência começa aqui</div><h1>Confirmação de Reserva</h1><p>Preencha seus dados para concluir sua hospedagem.</p></div>', unsafe_allow_html=True)
    try:
        reserva = chamar_supabase("consultar_link_reserva", {"p_token": str(uuid.UUID(token))})
    except (ValueError, RuntimeError) as erro:
        st.error(f"Não foi possível consultar o link: {erro}")
        st.stop()
    if not reserva.get("valido"):
        st.warning("Este link é inválido, expirou ou já foi utilizado.")
        st.stop()
    def data_cliente(valor):
        try:
            return datetime.strptime(str(valor)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(valor)
    resort_html = html.escape(str(reserva['resort']))
    cota_html = html.escape(str(reserva['cota']))
    periodo_html = html.escape(f"{data_cliente(reserva['checkin'])} a {data_cliente(reserva['checkout'])}")
    st.markdown(f"""<div class="booking-summary">
      <div class="booking-detail"><div class="small">RESORT</div><div class="value">{resort_html}</div></div>
      <div class="booking-detail"><div class="small">COTA</div><div class="value">{cota_html}</div></div>
      <div class="booking-detail"><div class="small">PERÍODO DA ESTADIA</div><div class="value">{periodo_html}</div></div>
    </div><div class="client-note">A confirmação é registrada automaticamente, sujeita à disponibilidade no momento do envio.</div>""", unsafe_allow_html=True)
    st.markdown('<div class="client-section"><span class="gold">✦</span> Pessoas na hospedagem</div>', unsafe_allow_html=True)
    qtd = st.number_input("Quantidade de acompanhantes (além do hóspede principal, máximo de 7)", min_value=0, max_value=7, value=0, step=1, key="qtd_acompanhantes")
    st.markdown('<div class="client-section"><span class="gold">✦</span> Dados do hóspede principal</div>', unsafe_allow_html=True)
    with st.form("confirmacao_cliente"):
        nome = st.text_input("Nome completo do hóspede principal *", placeholder="Digite seu nome completo")
        col_cpf, col_whats = st.columns(2)
        with col_cpf:
            cpf = st.text_input("CPF do hóspede principal *", placeholder="000.000.000-00")
        with col_whats:
            whatsapp = st.text_input("WhatsApp com DDD *", placeholder="(00) 00000-0000")
        email = st.text_input("E-mail *", placeholder="seuemail@exemplo.com")
        acompanhantes = []
        if qtd:
            st.markdown('<div class="client-section"><span class="gold">✦</span> Dados dos acompanhantes</div>', unsafe_allow_html=True)
        for i in range(int(qtd)):
            st.markdown(f"**Acompanhante {i + 1}**")
            col_nome, col_cpf_ac = st.columns([1.4, 1])
            with col_nome:
                nome_ac = st.text_input("Nome completo", key=f"nome_ac_{i}")
            with col_cpf_ac:
                cpf_ac = st.text_input("CPF (se possuir)", key=f"cpf_ac_{i}")
            acompanhantes.append({"nome": nome_ac, "cpf": cpf_ac})
        st.markdown('<div class="client-section"><span class="gold">✦</span> Termos da reserva</div>', unsafe_allow_html=True)
        st.caption("Termos da reserva (versão v1-2026-10)")
        st.write("Confira resort, cota, datas e dados antes de confirmar. A confirmação deste formulário registra a solicitação no sistema. Condições de pagamento, alteração e cancelamento devem constar do acordo fornecido pelo responsável pela reserva.")
        aceite = st.checkbox("Li e aceito os termos apresentados e autorizo o tratamento dos dados informados para organizar a hospedagem.")
        enviar = st.form_submit_button("Confirmar reserva", type="primary", use_container_width=True)
    if enviar:
        if not aceite:
            st.error("É necessário aceitar os termos.")
        elif not nome.strip() or not validar_cpf(cpf) or not re.fullmatch(r"\d{10,13}", re.sub(r"\D", "", whatsapp)) or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
            st.error("Confira nome, CPF, WhatsApp e e-mail.")
        elif any(not a["nome"].strip() or (a["cpf"].strip() and not validar_cpf(a["cpf"])) for a in acompanhantes):
            st.error("Confira os dados dos acompanhantes.")
        else:
            try:
                resposta = chamar_supabase("confirmar_reserva_cliente", {"p_token": token, "p_nome": nome, "p_cpf": re.sub(r"\D", "", cpf), "p_whatsapp": re.sub(r"\D", "", whatsapp), "p_email": email.strip(), "p_versao_termo": "v1-2026-10", "p_acompanhantes": acompanhantes})
                st.success(f"Reserva confirmada! {resposta['resort']} — cota {resposta['cota']} — {resposta['checkin']} a {resposta['checkout']}.")
                st.balloons()
            except RuntimeError as erro:
                st.error(f"Reserva não confirmada: {erro}")
    st.markdown('<div class="client-footer">SALINAS RESORTS · Conforto e tranquilidade para sua estadia</div>', unsafe_allow_html=True)
    st.stop()


# O link do cliente não dá acesso ao painel administrativo.
_token_cliente = st.query_params.get("reserva")
if _token_cliente:
    tela_cliente(_token_cliente)

senha_admin = config_segura("ADMIN_PASSWORD")
if not senha_admin:
    st.error("Configure ADMIN_PASSWORD nos Secrets antes de disponibilizar o painel administrativo.")
    st.stop()
if not st.session_state.get("admin_autenticado", False):
    # Aparência exclusiva da tela de login; não altera o painel ou o formulário do hóspede.
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap');
    .stApp {
        background:
          linear-gradient(180deg, rgba(22,18,41,.27) 0%, rgba(40,24,47,.10) 36%, rgba(5,29,45,.48) 100%),
          url('https://images.unsplash.com/photo-1514282401047-d79a71a590e8?auto=format&fit=crop&w=1800&q=85') center center / cover no-repeat fixed !important;
        min-height: 100vh;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stToolbar"] { background: transparent !important; }
    [data-testid="stDecoration"] { display: none; }
    .block-container {
        max-width: 740px !important;
        padding: clamp(100px, 21vh, 240px) 24px 100px !important;
    }
    h1 {
        font-family: 'Playfair Display', Georgia, serif !important;
        font-weight: 600 !important;
        font-size: clamp(2.7rem, 8vw, 5rem) !important;
        line-height: 1.13 !important;
        letter-spacing: -.035em !important;
        color: #fff7ed !important;
        text-shadow: 0 3px 20px rgba(0,0,0,.48);
        margin-bottom: 1.6rem !important;
    }
    [data-testid="stForm"] {
        background: rgba(22, 29, 43, .49) !important;
        border: 1px solid rgba(255,255,255,.35) !important;
        border-radius: 22px !important;
        padding: clamp(20px, 4vw, 32px) !important;
        box-shadow: 0 22px 70px rgba(0,0,0,.24) !important;
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
    }
    [data-testid="stForm"] label, [data-testid="stForm"] p {
        color: #fffaf2 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
    }
    [data-testid="stForm"] [data-baseweb="input"] > div {
        background: rgba(255,255,255,.92) !important;
        border: 1px solid rgba(255,255,255,.65) !important;
        border-radius: 12px !important;
        min-height: 54px;
    }
    [data-testid="stForm"] input { color: #1b3341 !important; }
    [data-testid="stFormSubmitButton"] button {
        width: 100% !important;
        background: #087d8c !important;
        color: #fff !important;
        border: 1px solid rgba(255,255,255,.15) !important;
        border-radius: 12px !important;
        min-height: 54px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1.08rem !important;
        font-weight: 700 !important;
        box-shadow: 0 8px 24px rgba(0,0,0,.22);
    }
    [data-testid="stFormSubmitButton"] button:hover {
        background: #096977 !important;
        color: #fff !important;
    }
    @media (max-width: 650px) {
        .block-container { padding: 19vh 22px 80px !important; }
        [data-testid="stForm"] { border-radius: 18px !important; }
        .stApp { background-attachment: scroll !important; }
    }
    </style>
    """, unsafe_allow_html=True)
    st.title("Acesso administrativo")
    with st.form("login_admin"):
        senha_digitada = st.text_input("Senha de administrador", type="password")
        entrar = st.form_submit_button("Entrar")
    if entrar:
        if hmac.compare_digest(senha_digitada, senha_admin):
            st.session_state["admin_autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

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
    /* Painel premium, responsivo e integrado aos controles Streamlit */
    .stApp { background: #f1f5fb !important; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg,#071d3d,#0b2b54 65%,#071a36) !important; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { font-weight: 600; }
    [data-testid="stSidebar"] [role="radiogroup"] { gap: 5px; }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 11px 13px; border-radius: 11px; transition: background .15s;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,.10); }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: #1766b5; box-shadow: 0 5px 18px rgba(0,0,0,.16);
    }
    .side-brand { text-align:center; padding: 26px 4px 20px; }
    .side-symbol { line-height: 1.2; display:flex; justify-content:center; margin-bottom:12px; }
    .side-name { font-size: 1.8rem; letter-spacing: .11em; font-weight: 800; color: #fff; }
    .side-small { font-size: .73rem; letter-spacing: .38em; color:#e9c99c; }
    .side-caption { font-size: .67rem; letter-spacing: .21em; color: #b4cbe5; margin-top: 12px; }
    .hero { min-height: 270px; padding: 38px 40px; border-radius: 19px;
        background-image: linear-gradient(90deg,rgba(5,26,52,.94),rgba(5,26,52,.65) 48%,rgba(5,26,52,.08)),
        url('https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=1800&q=85'); }
    .hero h1 { font-size: clamp(2.3rem,4.2vw,4rem); }
    .home-eyebrow { color:#e5bf83; font-weight:700; font-size:.78rem; letter-spacing:.16em; margin-bottom:10px; }
    .dashboard-title { color:#112b4e; font-size:1.16rem; font-weight:800; margin: 10px 0 12px; }
    .dashboard-sub { color:#6a7d93; font-size:.88rem; }
    .dash-card { background:#fff; border:1px solid #e1e9f3; border-radius:16px;
        padding:18px 19px; box-shadow:0 6px 24px rgba(18,44,80,.045); min-height:108px; }
    .dash-card .label { color:#71829b; font-size:.81rem; margin-bottom:7px; }
    .dash-card .value { font-size:1.9rem; color:#102d52; font-weight:800; line-height:1.1; }
    .dash-card .glyph { float:right; display:inline-flex; opacity:.85; }
    .home-panel { background:white; border:1px solid #e1e9f3; border-radius:16px;
        padding:19px; margin: 5px 0 15px; box-shadow:0 6px 22px rgba(18,44,80,.04); }
    .calendar-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:5px; }
    .calendar-day { min-height:33px; display:flex; align-items:center; justify-content:center;
        border-radius:8px; color:#24405d; font-size:.83rem; }
    .calendar-day.head { font-weight:700; color:#77879c; background:#f2f6fa; }
    .calendar-day.booked { background:#ffe3e3; color:#a93240; font-weight:800; }
    .calendar-day.pending { background:#fff0d6; color:#946012; font-weight:800; }
    .calendar-day.today { outline:2px solid #2276cc; outline-offset:-2px; }
    .booking-row { padding:11px 0; border-bottom:1px solid #eef2f6; font-size:.86rem; color:#213954; }
    .booking-row:last-child { border-bottom:0; }
    .booking-status { font-size:.73rem; font-weight:700; color:#147b58; }
    .resort-row { padding:11px 0; border-bottom:1px solid #eef2f6; font-size:.87rem; }
    .resort-row:last-child { border-bottom:0; }
    .dashboard-title svg, .result-title svg { vertical-align:-4px; margin-right:7px; color:#1769aa; }
    .legend-dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:3px; }
    .booked-dot { background:#d95b65; } .pending-dot { background:#d6a04c; } .today-dot { background:#2276cc; }
    [data-testid="stSidebar"] [role="radiogroup"] label { border-left:2px solid transparent; }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { border-left-color:#d9bb80; }
    
    .resort-name { font-weight:700; color:#17395c; }
    .resort-meta { color:#78889a; font-size:.77rem; }
    @media(max-width:700px){ .hero {padding:34px 22px;min-height:260px;} .home-panel {padding:14px;} }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# LEITURA DOS CRONOGRAMAS PDF
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def carregar_todos_os_dados(assinaturas):
    dados, avisos = carregar_pdfs('.')
    base = {}
    for resort, locais in dados.items():
        base[resort] = {}
        for local, tabela in locais.items():
            df = tabela.copy()
            # A chave completa impede que cotas de locais distintos se misturem.
            df.insert(0, 'Identificação da cota', df['Local'] + ' | Cota ' + df['Cota'].astype(str))
            base[resort][local] = df
    return base, avisos

assinaturas_pdf = tuple((nome, os.path.getmtime(arquivo), os.path.getsize(arquivo))
    if os.path.isfile(arquivo) else (nome, None, None)
    for nome, arquivo in ARQUIVOS_RESORTS.items())
base_dados, avisos_arquivos = carregar_todos_os_dados(assinaturas_pdf)
total_abas = sum(len(abas) for abas in base_dados.values())
total_resorts_com_dados = sum(bool(abas) for abas in base_dados.values())

# ------------------------------------------------------------
# MENU LATERAL
# ------------------------------------------------------------
with st.sidebar:
    st.markdown(f'<div class="side-brand"><div class="side-symbol">{icone("waves", 45, "#d9bb80")}</div><div class="side-name">SALINAS</div><div class="side-small">R E S O R T S</div><div class="side-caption">GESTÃO DE COTAS</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio(
        "MENU PRINCIPAL",
        ["Início", "Consultar cotas", "Gerenciar Reservas", "Cronogramas", "Cadastros"],
        label_visibility="visible",
        key="menu_principal",
    )
    st.markdown("---")
    st.caption("Painel administrativo")
    st.caption("Consulta de períodos e cotas")
    if st.button("Atualizar PDFs", icon=":material/refresh:", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# Avisos dos arquivos, sem interromper a aplicação
if avisos_arquivos:
    with st.expander("Verificar arquivos PDF", expanded=False):
        st.warning("Confira se os quatro PDFs estão na mesma pasta do aplicativo.")
        for aviso in avisos_arquivos:
            st.write(f"• {aviso}")

# Verificacao de ocupacao com dados atuais do Supabase (sem cache).
# A verificacao visual nao substitui a validacao atomica no RPC de criacao.
def converter_data_reserva(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(str(valor)[:10], "%d/%m/%Y").date()
        except (ValueError, TypeError):
            return None


def situacao_cota(item, registros):
    entrada = datetime.strptime(item["entrada"], "%d/%m/%Y").date()
    saida = datetime.strptime(item["saida"], "%d/%m/%Y").date()
    for registro in registros:
        cota_reserva = str(registro.get("cota") or "").strip().casefold()
        cota_completa = str(item["cota"]).strip().casefold()
        cota_simples = cota_completa.rsplit(' | cota ', 1)[-1]
        if (str(registro.get("resort") or "").strip().casefold() != str(item["resort"]).strip().casefold()
                or cota_reserva not in (cota_completa, cota_simples)):
            continue
        inicio = converter_data_reserva(registro.get("checkin"))
        fim = converter_data_reserva(registro.get("checkout"))
        if not inicio or not fim:
            # Registro sem datas confiaveis: nao presumir disponibilidade.
            return "Indisponível (verificar cadastro)"
        if entrada >= fim or saida <= inicio:
            continue
        status = str(registro.get("status") or "").strip().lower()
        if status in ("confirmado", "preenchido"):
            return "Reservada"
        if status == "pendente" and not registro.get("expirado", False):
            return "Aguardando confirmação"
    return "Disponível"


# ------------------------------------------------------------
# PAINEL INICIAL - dados reais dos PDFs e do Supabase
# ------------------------------------------------------------
if menu == "Início":
    st.markdown("""
    <div class="hero">
      <div class="home-eyebrow">GESTÃO DE COTAS E ESTADIAS</div>
      <h1>Salinas Resorts</h1>
      <p>Organize suas cotas, acompanhe reservas e proporcione experiências inesquecíveis.</p>
    </div>""", unsafe_allow_html=True)

    registros_inicio = []
    erro_inicio = None
    try:
        registros_inicio = chamar_supabase("listar_reservas_admin", {})
        if isinstance(registros_inicio, str):
            registros_inicio = json.loads(registros_inicio)
        if not isinstance(registros_inicio, list):
            raise RuntimeError("Resposta inesperada do banco de dados.")
    except (RuntimeError, ValueError, TypeError) as exc:
        erro_inicio = str(exc)
        st.warning("Não foi possível consultar as reservas agora. Os indicadores de reservas estão indisponíveis.")

    total_periodos = sum(len(df) for abas in base_dados.values() for df in abas.values())
    confirmadas = sum(r.get("status") == "confirmado" for r in registros_inicio)
    pendentes = sum(r.get("status") == "pendente" and not r.get("expirado") for r in registros_inicio)
    canceladas = sum(r.get("status") == "cancelado" for r in registros_inicio)
    metricas = [
        ("Períodos nos PDFs", str(total_periodos), "calendar"),
        ("Reservas confirmadas", str(confirmadas) if not erro_inicio else "—", "check"),
        ("Links pendentes", str(pendentes) if not erro_inicio else "—", "link"),
        ("Resorts com dados", str(total_resorts_com_dados), "building"),
    ]
    for col, (rotulo, valor, simbolo) in zip(st.columns(4), metricas):
        with col:
            st.markdown(f'<div class="dash-card"><span class="glyph">{icone(simbolo, 27, "#1769aa")}</span><div class="label">{rotulo}</div><div class="value">{valor}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="dashboard-title">Planeje sua próxima estadia</div><div class="dashboard-sub">Acesse a consulta para encontrar períodos e gerar links de reserva.</div>', unsafe_allow_html=True)
    def abrir_consulta():
        st.session_state["menu_principal"] = "Consultar cotas"
    st.button("Consultar períodos disponíveis", icon=":material/search:", type="primary", use_container_width=True, on_click=abrir_consulta)

    painel_cal, painel_res, painel_hot = st.columns([1.12, 1, 1])
    with painel_cal:
        st.markdown(f'<div class="dashboard-title">{icone("calendar", 20)} Calendário de reservas</div>', unsafe_allow_html=True)
        hoje = date.today()
        mes_inicio = date(hoje.year, hoje.month, 1)
        mes_ref = st.date_input("Mês de referência", value=mes_inicio, format="DD/MM/YYYY", key="calendario_inicio")
        ano, mes = mes_ref.year, mes_ref.month
        nomes_meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        ocupados, aguardando = set(), set()
        for reg in registros_inicio:
            if reg.get("status") not in ("confirmado", "preenchido", "pendente") or reg.get("expirado"):
                continue
            inicio, fim = converter_data_reserva(reg.get("checkin")), converter_data_reserva(reg.get("checkout"))
            if not inicio or not fim or fim <= inicio:
                continue
            for dia in range(1, calendar.monthrange(ano, mes)[1] + 1):
                atual = date(ano, mes, dia)
                if inicio <= atual < fim:
                    (aguardando if reg.get("status") == "pendente" else ocupados).add(dia)
        dias_html = ''.join(f'<div class="calendar-day head">{d}</div>' for d in ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"))
        for semana in calendar.monthcalendar(ano, mes):
            for dia in semana:
                if not dia:
                    dias_html += '<div class="calendar-day"></div>'
                else:
                    classes = 'calendar-day' + (' booked' if dia in ocupados else ' pending' if dia in aguardando else '') + (' today' if (ano, mes, dia) == (hoje.year, hoje.month, hoje.day) else '')
                    dias_html += f'<div class="{classes}">{dia}</div>'
        st.markdown(f'<div class="home-panel"><strong>{nomes_meses[mes]} de {ano}</strong><div style="height:12px"></div><div class="calendar-grid">{dias_html}</div><div style="margin-top:14px;color:#708198;font-size:.75rem"><span class="legend-dot booked-dot"></span> Há reserva &nbsp; <span class="legend-dot pending-dot"></span> Há link pendente &nbsp; <span class="legend-dot today-dot"></span> Hoje</div><div style="margin-top:6px;color:#8593a4;font-size:.72rem">Datas sem marcação não garantem disponibilidade; consulte cada cota.</div></div>', unsafe_allow_html=True)
    with painel_res:
        st.markdown(f'<div class="dashboard-title">{icone("clock", 20)} Próximas reservas</div>', unsafe_allow_html=True)
        proximas = []
        for reg in registros_inicio:
            entrada = converter_data_reserva(reg.get("checkin"))
            if entrada and entrada >= date.today() and reg.get("status") in ("confirmado", "pendente", "preenchido") and not reg.get("expirado"):
                proximas.append((entrada, reg))
        proximas.sort(key=lambda x: x[0])
        linhas = ''
        for entrada, reg in proximas[:5]:
            nome = html.escape(str(reg.get("nome") or "Hóspede ainda não informado"))
            resort = html.escape(str(reg.get("resort") or "Resort"))
            status = "Confirmada" if reg.get("status") == "confirmado" else "Pendente"
            linhas += f'<div class="booking-row"><strong>{nome}</strong><div class="resort-meta">{entrada.strftime("%d/%m/%Y")} · {resort}</div><span class="booking-status">{status}</span></div>'
        if not linhas:
            linhas = '<div class="dashboard-sub">Nenhuma próxima reserva encontrada.</div>'
        st.markdown(f'<div class="home-panel">{linhas}</div>', unsafe_allow_html=True)
    with painel_hot:
        st.markdown(f'<div class="dashboard-title">{icone("building", 20)} Resorts cadastrados</div>', unsafe_allow_html=True)
        linhas = ''
        for resort, abas in base_dados.items():
            qtd = sum(len(df) for df in abas.values())
            linhas += f'<div class="resort-row"><div class="resort-name">{html.escape(resort)}</div><div class="resort-meta">{qtd} registros nos PDFs</div></div>'
        st.markdown(f'<div class="home-panel">{linhas}</div>', unsafe_allow_html=True)
    st.caption(f"Reservas canceladas no histórico: {canceladas}" if not erro_inicio else "Histórico de reservas temporariamente indisponível.")

# ------------------------------------------------------------
# CONSULTA
# ------------------------------------------------------------
elif menu == "Consultar cotas":
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
            st.caption("A preferência de andar é informativa; confira o pavimento nos resultados.")

        col_in, col_out = st.columns(2)
        with col_in:
            data_entrada = st.date_input("Check-in", value=date.today(), format="DD/MM/YYYY")
        with col_out:
            data_saida = st.date_input("Check-out", value=date.today(), format="DD/MM/YYYY")

        buscar = st.button("Buscar cotas no período", icon=":material/search:", type="primary", use_container_width=True)

    if buscar:
        st.session_state["busca_ativa"] = True

    if st.session_state.get("busca_ativa", False):
        if data_saida <= data_entrada:
            st.error("A data de check-out precisa ser posterior à data de check-in.")
        else:
            resorts_alvo = list(ARQUIVOS_RESORTS.keys()) if resort_selecionado == "Todos os resorts" else [resort_selecionado]
            resultados = []

            with st.spinner("Consultando os PDFs..."):
                for nome_resort in resorts_alvo:
                    for nome_aba, df_original in base_dados.get(nome_resort, {}).items():
                        for _, linha in df_original.iterrows():
                            inicio = linha['Check-in'].date()
                            fim = linha['Check-out'].date()
                            if inicio > data_entrada or fim < data_saida:
                                continue
                            cota_id = str(linha['Identificação da cota'])
                            resultados.append({
                                'resort': nome_resort,
                                'cota': cota_id,
                                'aba': nome_aba,
                                'entrada': inicio.strftime('%d/%m/%Y'),
                                'saida': fim.strftime('%d/%m/%Y'),
                                'detalhes': f"Cota {linha['Cota']} • {nome_aba} • {linha['Período'] or 'Período comum'} • Página {linha['Página PDF']} do PDF",
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
                st.markdown(f'<div class="metric-card"><div class="metric-label">PDFs com dados</div><div class="metric-value">{total_resorts_com_dados}</div></div>', unsafe_allow_html=True)

            if resultados:
                st.caption("Os períodos vêm dos PDFs; a ocupação é consultada no Supabase a cada atualização da página.")
                try:
                    reservas_atuais = chamar_supabase("listar_reservas_admin", {})
                    if isinstance(reservas_atuais, str):
                        reservas_atuais = json.loads(reservas_atuais)
                    if not isinstance(reservas_atuais, list):
                        raise RuntimeError("A consulta não retornou uma lista válida.")
                    consulta_reservas_ok = True
                except (RuntimeError, ValueError, TypeError) as erro:
                    reservas_atuais = []
                    consulta_reservas_ok = False
                    st.error(f"Não foi possível verificar as reservas no Supabase: {erro}. Por segurança, novas reservas estão bloqueadas até a conexão voltar.")

                if avisos_arquivos:
                    st.error("Há páginas com erro de leitura ou PDFs ausentes. Por segurança, a criação de reservas fica bloqueada até corrigir os avisos.")
                    consulta_reservas_ok = False

                for indice, item in enumerate(resultados):
                    situacao = situacao_cota(item, reservas_atuais) if consulta_reservas_ok else "Verificação indisponível"
                    disponivel = situacao == "Disponível" and consulta_reservas_ok
                    if not disponivel and st.session_state.get("cota_selecionada") == item:
                        st.session_state.pop("cota_selecionada", None)
                        st.session_state.pop("link_gerado", None)
                    with st.container(border=True):
                        topo_nome, topo_status, topo_botao = st.columns(
                            [3, 1.7, 2.2], vertical_alignment="center"
                        )
                        with topo_nome:
                            st.markdown(
                                f"<div class='result-title'>{icone('building', 19)} {html.escape(str(item['resort']))}</div>"
                                f"<p class='result-subtitle'>Cota {html.escape(str(item['cota']))}</p>",
                                unsafe_allow_html=True,
                            )
                        with topo_status:
                            if situacao == "Disponível":
                                st.success("Disponível (consulta)")
                            elif situacao == "Reservada":
                                st.error("Reservada")
                            else:
                                st.warning(f"{situacao}")
                        with topo_botao:
                            if st.button(
                                "Reservar para cliente" if disponivel else "Indisponível para reserva",
                                 icon=":material/event_available:" if disponivel else ":material/lock:",
                                key=f"reservar_{indice}_{item['resort']}_{item['cota']}_{item['entrada']}_{item['saida']}",
                                use_container_width=True,
                                disabled=not disponivel,
                            ):
                                st.session_state["cota_selecionada"] = item
                                st.session_state.pop("link_gerado", None)

                        st.markdown(
                            f"""
                            <div class="result-details">
                                <div class="detail-box">
                                    <div class="detail-label">CHECK-IN CADASTRADO</div>
                                    <div class="detail-value">{html.escape(str(item['entrada']))}</div>
                                </div>
                                <div class="detail-box">
                                    <div class="detail-label">CHECK-OUT CADASTRADO</div>
                                    <div class="detail-value">{html.escape(str(item['saida']))}</div>
                                </div>
                                <div class="detail-box">
                                    <div class="detail-label">BLOCO / PAVIMENTO</div>
                                    <div class="detail-value">{html.escape(str(item['aba']))}</div>
                                </div>
                            </div>
                            <p style="color:#667789;font-size:.84rem;margin:14px 0 0 0;">
                                {html.escape(str(item['detalhes']))}
                            </p>
                            """,
                            unsafe_allow_html=True,
                        )

                        if st.session_state.get("cota_selecionada") == item:
                            st.caption("Crie um link exclusivo para o cliente. O link expira em 48 horas.")
                            if st.button("Gerar link de reserva", key=f"link_{indice}", type="primary"):
                                try:
                                    reservas_revalidadas = chamar_supabase("listar_reservas_admin", {})
                                    if isinstance(reservas_revalidadas, str):
                                        reservas_revalidadas = json.loads(reservas_revalidadas)
                                    if not isinstance(reservas_revalidadas, list):
                                        raise RuntimeError("Não foi possível validar a disponibilidade.")
                                    if situacao_cota(item, reservas_revalidadas) != "Disponível":
                                        raise RuntimeError("Esta cota já possui uma reserva ou link ativo. Atualize a consulta.")
                                    token = chamar_supabase("criar_link_reserva", {
                                        "p_resort": item["resort"], "p_cota": item["cota"],
                                        "p_checkin": datetime.strptime(item["entrada"], "%d/%m/%Y").date().isoformat(),
                                        "p_checkout": datetime.strptime(item["saida"], "%d/%m/%Y").date().isoformat(),
                                    })
                                    st.session_state["link_gerado"] = f"{config_segura('APP_URL').rstrip('/')}?{urlencode({'reserva': token})}"
                                except RuntimeError as erro:
                                    st.error(f"Não foi possível gerar o link: {erro}")
                            if st.session_state.get("link_gerado"):
                                st.code(st.session_state["link_gerado"], language=None)
                                st.caption("Copie e envie ao cliente pelo WhatsApp.")
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
# GERENCIAR RESERVAS (acesso somente ao administrador autenticado)
# ------------------------------------------------------------
elif menu == "Gerenciar Reservas":
    st.markdown('<div class="section-heading">Gerenciar Reservas</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Consulte links e reservas, cancele registros ou exclua definitivamente reservas já canceladas.</div>', unsafe_allow_html=True)

    if st.button("Atualizar lista de reservas", icon=":material/refresh:", use_container_width=False):
        st.rerun()

    try:
        registros = chamar_supabase("listar_reservas_admin", {})
        if isinstance(registros, str):
            registros = json.loads(registros)
        if not isinstance(registros, list):
            raise RuntimeError("O Supabase não retornou uma lista de reservas.")
    except (RuntimeError, ValueError, TypeError) as erro:
        st.error(f"Não foi possível carregar as reservas: {erro}")
        st.info("Verifique se o arquivo SQL de gerenciamento foi executado no Supabase.")
        st.stop()

    total_confirmadas = sum(r.get("status") == "confirmado" for r in registros)
    total_pendentes = sum(r.get("status") == "pendente" and not r.get("expirado") for r in registros)
    total_canceladas = sum(r.get("status") == "cancelado" for r in registros)
    col1, col2, col3 = st.columns(3)
    col1.metric("Confirmadas", total_confirmadas)
    col2.metric("Links pendentes", total_pendentes)
    col3.metric("Canceladas", total_canceladas)

    filtro_status = st.selectbox("Filtrar por situação", ["Todas", "Pendentes", "Confirmadas", "Canceladas", "Expiradas"])
    pesquisa = st.text_input("Pesquisar", placeholder="Nome do hóspede, resort ou cota")
    texto_busca = pesquisa.strip().casefold()

    def status_exibicao(r):
        if r.get("status") == "pendente" and r.get("expirado"):
            return "Expiradas"
        return {"pendente": "Pendentes", "confirmado": "Confirmadas", "cancelado": "Canceladas"}.get(r.get("status"), "Outras")

    filtradas = [r for r in registros if
                 (filtro_status == "Todas" or status_exibicao(r) == filtro_status)
                 and (not texto_busca or any(texto_busca in str(r.get(k) or "").casefold()
                                              for k in ("nome", "resort", "cota", "id")))]
    st.caption(f"{len(filtradas)} registro(s) encontrado(s)")
    if not filtradas:
        st.info("Nenhuma reserva corresponde aos filtros.")

    for r in filtradas:
        id_reserva = str(r.get("id", ""))
        situacao = status_exibicao(r)
        with st.container(border=True):
            st.markdown(f"**{r.get('resort') or 'Resort não informado'} — Cota {r.get('cota') or '-'}**")
            st.write(f"**Período:** {data_br(r.get('checkin'))} a {data_br(r.get('checkout'))}")
            st.write(f"**Hóspede:** {r.get('nome') or 'Ainda não informado'}")
            st.write(f"**Situação:** {situacao[:-1] if situacao.endswith('s') else situacao}")
            st.caption(f"Identificador: {id_reserva}")

            # Consulta individual: dados pessoais nunca entram na listagem geral.
            aberto = st.session_state.get("detalhes_reserva_aberta") == id_reserva
            if st.button(
                "Fechar detalhes" if aberto else "Ver detalhes",
                key=f"detalhes_{id_reserva}",
                icon=":material/visibility_off:" if aberto else ":material/visibility:",
            ):
                st.session_state["detalhes_reserva_aberta"] = None if aberto else id_reserva
                st.rerun()

            if aberto:
                with st.container(border=True):
                    st.markdown("#### Ficha da reserva")
                    try:
                        ficha = chamar_supabase("detalhes_reserva_admin", {"p_reserva_id": str(uuid.UUID(id_reserva))})
                        if not isinstance(ficha, dict) or not ficha.get("encontrada"):
                            st.warning("Não foi possível localizar os dados desta reserva.")
                        else:
                            st.markdown("**Dados da hospedagem**")
                            d1, d2 = st.columns(2)
                            d1.write(f"**Resort:** {ficha.get('resort') or '—'}")
                            d2.write(f"**Cota:** {ficha.get('cota') or '—'}")
                            d1.write(f"**Check-in:** {data_br(ficha.get('checkin'))}")
                            d2.write(f"**Check-out:** {data_br(ficha.get('checkout'))}")
                            st.write(f"**Situação:** {ficha.get('status') or '—'}")
                            hospede = ficha.get("hospede")
                            if isinstance(hospede, dict):
                                st.markdown("**Hóspede principal**")
                                d1, d2 = st.columns(2)
                                d1.write(f"**Nome:** {hospede.get('nome') or '—'}")
                                d2.write(f"**CPF:** {hospede.get('cpf') or '—'}")
                                d1.write(f"**WhatsApp:** {hospede.get('whatsapp') or '—'}")
                                d2.write(f"**E-mail:** {hospede.get('email') or '—'}")
                                st.markdown("**Acompanhantes**")
                                lista = ficha.get("acompanhantes") or []
                                if lista:
                                    for pos, acompanhante in enumerate(lista, 1):
                                        st.write(f"{pos}. **{acompanhante.get('nome') or 'Não informado'}** — CPF: {acompanhante.get('cpf') or 'Não informado'}")
                                else:
                                    st.caption("Nenhum acompanhante cadastrado.")
                                st.caption(f"Termos aceitos: {hospede.get('versao_termo') or 'Não informado'}")
                            else:
                                st.info("O cliente ainda não concluiu o formulário de pré-check-in.")
                            if isinstance(hospede, dict):
                                try:
                                    pdf_bytes = gerar_pdf_reserva(ficha)
                                    st.download_button(
                                        "Baixar ficha da reserva (PDF)",
                                        data=pdf_bytes,
                                        file_name=f"ficha_reserva_{id_reserva[:8]}.pdf",
                                        mime="application/pdf",
                                        icon=":material/picture_as_pdf:",
                                        key=f"pdf_reserva_{id_reserva}",
                                        use_container_width=True,
                                    )
                                    st.caption("Contém dados pessoais. Compartilhe somente com pessoas autorizadas.")
                                except Exception as erro_pdf:
                                    st.warning("Não foi possível gerar o PDF. Verifique se a biblioteca reportlab está instalada no aplicativo.")
                    except (RuntimeError, ValueError, TypeError) as erro:
                        st.error(f"Não foi possível consultar os detalhes: {erro}")
                        st.caption("Confira se o SQL de detalhes já foi executado no Supabase.")

            if r.get("status") in ("pendente", "confirmado"):
                if r.get("status") == "confirmado":
                    st.warning("Atenção: cancelar aqui não cancela a hospedagem diretamente com o resort. Verifique o procedimento com a GAV.")
                confirmar = st.checkbox("Estou ciente e desejo cancelar este registro e liberar a cota.", key=f"confirmar_cancelamento_{id_reserva}")
                if st.button("Cancelar reserva / link", key=f"cancelar_{id_reserva}", disabled=not confirmar):
                    try:
                        resposta = chamar_supabase("cancelar_reserva_admin", {"p_reserva_id": id_reserva})
                        if isinstance(resposta, dict) and resposta.get("cancelada") is True:
                            st.success("Registro cancelado. A cota foi liberada no sistema, caso não exista outro bloqueio.")
                            st.rerun()
                        else:
                            st.error("O Supabase não confirmou o cancelamento. Confira a situação da reserva.")
                    except RuntimeError as erro:
                        st.error(f"Não foi possível cancelar: {erro}")
            elif r.get("status") == "cancelado":
                with st.expander("Excluir definitivamente esta reserva"):
                    st.warning("Esta ação é irreversível. A reserva, o pré-check-in e os dados dos acompanhantes serão apagados do banco de dados. Não afeta registros da GAV.")
                    texto_confirmacao = st.text_input(
                        "Para confirmar, digite EXCLUIR",
                        key=f"texto_exclusao_{id_reserva}",
                        placeholder="EXCLUIR",
                    )
                    if st.button(
                        "Excluir definitivamente",
                        key=f"excluir_{id_reserva}",
                        type="primary",
                        disabled=texto_confirmacao.strip() != "EXCLUIR",
                    ):
                        try:
                            resposta = chamar_supabase("excluir_reserva_cancelada_admin", {"p_reserva_id": id_reserva})
                            if isinstance(resposta, dict) and resposta.get("excluida") is True:
                                st.success("Reserva excluída definitivamente do sistema.")
                                st.rerun()
                            else:
                                st.error("O Supabase não confirmou a exclusão.")
                        except RuntimeError as erro:
                            st.error(f"Não foi possível excluir: {erro}")

# ------------------------------------------------------------
# CRONOGRAMAS
# ------------------------------------------------------------
elif menu == "Cronogramas":
    st.markdown('<div class="section-heading">Cronogramas dos resorts</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Consulte os períodos extraídos dos cronogramas PDF.</div>', unsafe_allow_html=True)

    col_r, col_a = st.columns(2)
    with col_r:
        resort_bruto = st.selectbox("Selecione o resort", list(ARQUIVOS_RESORTS.keys()))
    abas = base_dados.get(resort_bruto, {})
    with col_a:
        aba_bruta = st.selectbox("Selecione o bloco / torre", list(abas.keys()) if abas else ["Nenhum local encontrado"])

    if abas and aba_bruta in abas:
        df_exibir = abas[aba_bruta]
        filtro_texto = st.text_input("Filtrar linhas", placeholder="Digite cota, unidade ou informação...")
        if filtro_texto:
            mascara = df_exibir.astype(str).apply(
                lambda coluna: coluna.str.contains(filtro_texto, case=False, na=False, regex=False)
            ).any(axis=1)
            df_exibir = df_exibir[mascara]
        st.caption(f"{len(df_exibir)} linha(s) exibida(s) • Local: {aba_bruta}")
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)
        st.download_button(
            "Baixar esta tabela em CSV",
            icon=":material/download:",
            data=df_exibir.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{resort_bruto}_{aba_bruta}.csv".replace("/", "-"),
            mime="text/csv",
        )
    else:
        st.warning("Nenhum dado foi encontrado para este resort. Confira se o PDF está na pasta do aplicativo.")

# ------------------------------------------------------------
# CADASTROS
# ------------------------------------------------------------
elif menu == "Cadastros":
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
