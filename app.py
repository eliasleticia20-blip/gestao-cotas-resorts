import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Gestão de Cotas - Salinas Resorts",
    page_icon="🏖️",
    layout="wide"
)

# Estilização visual moderna
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .welcome-box { background: linear-gradient(135deg, #0b2545 0%, #134074 100%); color: white; padding: 25px; border-radius: 15px; margin-bottom: 20px; }
    .card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #134074; }
    </style>
""", unsafe_allow_html=True)

# Função altamente resiliente para carregar os 4 arquivos Excel
@st.cache_data
def carregar_todos_os_dados():
    arquivos = {
        "Beach Resort": "Salinas Beach Resort.xlsx",
        "Exclusive Resort": "Salinas Exclusive Resort.xlsx",
        "Park Resort": "Salinas Park Resort.xlsx",
        "Premium Resort": "Salinas Premium Resort.xlsx"
    }
    
    dados_consolidados = {}
    
    for nome_resort, arquivo in arquivos.items():
        if os.path.exists(arquivo):
            try:
                abas = pd.read_excel(arquivo, sheet_name=None)
                abas_validas = {}
                
                for aba_nome, df in abas.items():
                    # Tenta achar a linha de cabeçalho correta baseada em palavras-chave
                    linha_cabecalho = None
                    for idx, row in df.iterrows():
                        row_str = row.astype(str).str.upper()
                        if row_str.str.contains('CHECK|COTA|UNIDADE|DATA|202').any():
                            linha_cabecalho = idx
                            break
                    
                    if linha_cabecalho is None and len(df) > 2:
                        linha_cabecalho = 2
                        
                    # Recarrega o DataFrame com o cabeçalho correto
                    df_tratado = pd.read_excel(arquivo, sheet_name=aba_nome, header=linha_cabecalho)
                    df_tratado = df_tratado.dropna(how='all')
                    
                    if not df_tratado.empty:
                        # Garante que a primeira coluna (Cota) seja preenchida para baixo (ffill)
                        primeira_coluna = df_tratado.columns[0]
                        df_tratado[primeira_coluna] = df_tratado[primeira_coluna].ffill()
                        abas_validas[aba_nome] = df_tratado
                        
                dados_consolidados[nome_resort] = abas_validas
            except Exception as e:
                dados_consolidados[nome_resort] = {}
        else:
            dados_consolidados[nome_resort] = {}
            
    return dados_consolidados

# Carregando os dados
base_dados = carregar_todos_os_dados()

# Cabeçalho do App
st.markdown("""
    <div class="welcome-box">
        <h2>🏖️ Salinas Resorts - Sistema de Gestão de Cotas</h2>
        <p style="margin:0; font-size: 1.1rem;">Painel Administrativo para consulta e baixa de cotas por período.</p>
    </div>
""", unsafe_allow_html=True)

# Menu Lateral de Navegação
menu = st.sidebar.radio("Navegação", ["🔍 Consultar & Alugar", "📅 Visualizar Cronogramas Brutos", "⚙️ Cadastros"])

if menu == "🔍 Consultar & Alugar":
    st.subheader("🔍 Painel de Busca por Período e Resort")
    
    lista_resorts = ["🌍 Todos os Resorts"] + list(base_dados.keys())
    
    col1, col2 = st.columns(2)
    with col1:
        resort_selecionado = st.selectbox("Selecione o Resort", lista_resorts)
    with col2:
        andar_pref = st.selectbox("Preferência de Andar", ["Qualquer", "Andar Alto", "Andar Médio", "Andar Baixo"])
        
    st.write("### 📅 Escolha o Período Desejado (Dia / Mês / Ano)")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        data_entrada = st.date_input("Data de Entrada (Check-in)", value=datetime.today())
    with col_d2:
        data_saida = st.date_input("Data de Saída (Check-out)", value=datetime.today())
        
    st.write("---")
    
    if st.button("🔎 Buscar Cotas Disponíveis", type="primary", use_container_width=True):
        
        entrada_br = data_entrada.strftime('%d/%m/%Y')
        saida_br = data_saida.strftime('%d/%m/%Y')
        
        resorts_alvo = list(base_dados.keys()) if resort_selecionado == "🌍 Todos os Resorts" else [resort_selecionado]
        
        st.success(f"Buscando em **{resort_selecionado}** para o período de **{entrada_br}** a **{saida_br}**:")
        
        total_encontrados = 0
        
        for r_nome in resorts_alvo:
            abas_resort = base_dados.get(r_nome, {})
            
            for aba_nome, df in abas_resort.items():
                # Identifica dinamicamente quais colunas são de Check-in e Check-out
                col_checkin = None
                col_checkout = None
                
                for col in df.columns:
                    c_str = str(col).upper()
                    if 'CHECK' in c_str or 'ENTRADA' in c_str or 'DATA INICIAL' in c_str:
                        if not col_checkin:
                            col_checkin = col
                    elif 'OUT' in c_str or 'SAÍDA' in c_str or 'TERMINO' in c_str or 'FINAL' in c_str:
                        if not col_checkout:
                            col_checkout = col
                
                # Se não achou pelos títulos, tenta deduzir pelas colunas 1 e 2 (padrão comum)
                if not col_checkin and len(df.columns) > 1:
                    col_checkin = df.columns[1]
                if not col_checkout and len(df.columns) > 2:
                    col_checkout = df.columns[2]
                
                if col_checkin and col_checkout:
                    # Converte as colunas para formato de data de forma segura
                    df['Data_In'] = pd.to_datetime(df[col_checkin], errors='coerce', dayfirst=True).dt.date
                    df['Data_Out'] = pd.to_datetime(df[col_checkout], errors='coerce', dayfirst=True).dt.date
                    
                    # Filtro flexível: Verifica se a data buscada coincide com o intervalo cadastrado
                    resultados_filtrados = df[
                        (df['Data_In'].notnull()) & 
                        (df['Data_Out'].notnull()) &
                        (df['Data_In'] <= data_saida) & 
                        (df['Data_Out'] >= data_entrada)
                    ]
                    
                    if not resultados_filtrados.empty:
                        for _, row in resultados_filtrados.iterrows():
                            total_encontrados += 1
                            cota_id = row[df.columns[0]]
                            
                            d_in = row['Data_In'].strftime('%d/%m/%Y')
                            d_out = row['Data_Out'].strftime('%d/%m/%Y')
                            
                            # Tenta capturar o nome do período/evento se houver coluna extra
                            detalhe_extra = ""
                            if len(df.columns) > 6:
                                val_extra = row[df.columns[6]]
                                if pd.notnull(val_extra) and str(val_extra) != 'nan':
                                    detalhe_extra = f" | Evento: {val_extra}"
                            
                            st.markdown(f"""
                                <div class="card">
                                    <h4>🏨 Resort: {r_nome} | 🔑 Cota: {cota_id}</h4>
                                    <p><b>Período na Planilha:</b> {d_in} até {d_out}{detalhe_extra}</p>
                                    <p><b>Aba / Mês:</b> {aba_nome}</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
        if total_encontrados == 0:
            st.warning("⚠️ Nenhuma cota bateu exatamente com esse intervalo de datas na busca automática.")
            st.info("💡 **Dica:** Vá até a aba lateral **'Visualizar Cronogramas Brutos'**, selecione o resort desejado e confira exatamente como as datas estão escritas na sua planilha para realizar a busca com precisão.")

elif menu == "📅 Visualizar Cronogramas Brutos":
    st.subheader("📊 Inspeção Completa dos Arquivos Excel")
    resort_escolhido_bruto = st.selectbox("Escolha o Resort para inspecionar", list(base_dados.keys()))
    abas_brutas = base_dados.get(resort_escolhido_bruto, {})
    
    if abas_brutas:
        aba_escolhida = st.selectbox("Selecione a Aba (Mês/Ano)", list(abas_brutas.keys()))
        st.info(f"Exibindo os dados limpos do resort **{resort_escolhido_bruto}** na aba **{aba_escolhida}**:")
        st.dataframe(abas_brutas[aba_escolhida], use_container_width=True)
    else:
        st.error("Nenhum dado encontrado para este resort.")

elif menu == "⚙️ Cadastros":
    st.subheader("⚙️ Configurações e Cadastros de Cotistas")
    st.text_input("Nome do Cotista", "Ex: Elias / Carol / Carlos")
    st.text_input("Número da Cota", "Ex: Cota 01")
    st.button("Salvar Cadastro")