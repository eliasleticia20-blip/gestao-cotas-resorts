import pandas as pd
import os

arquivos = {
    "Beach Resort": "Salinas Beach Resort.xlsx",
    "Exclusive Resort": "Salinas Exclusive Resort.xlsx",
    "Park Resort": "Salinas Park Resort.xlsx",
    "Premium Resort": "Salinas Premium Resort.xlsx"
}

def processar_e_limpar_dados():
    for nome_resort, arquivo in arquivos.items():
        print(f"\n==================================================")
        print(f"PROCESSANDO: {nome_resort}")
        print(f"==================================================")
        
        if os.path.exists(arquivo):
            try:
                abas = pd.read_excel(arquivo, sheet_name=None)
                
                for aba_nome, df in abas.items():
                    print(f"\n   📂 Aba: '{aba_nome}'")
                    
                    # Procura a linha de cabeçalho baseada em termos úteis ou presença de dados
                    linha_cabecalho = None
                    for idx, row in df.iterrows():
                        row_str = row.astype(str).str.upper()
                        if row_str.str.contains('COTA|UNIDADE|CHECK|DATA').any():
                            linha_cabecalho = idx
                            break
                    
                    # Se não achar por palavra-chave, pega a terceira linha como padrão (geralmente onde começam os títulos)
                    if linha_cabecalho is None and len(df) > 2:
                        linha_cabecalho = 2
                        
                    if linha_cabecalho is not None:
                        # Carrega a tabela a partir da linha encontrada
                        df_limpo = pd.read_excel(arquivo, sheet_name=aba_nome, header=linha_cabecalho)
                        df_limpo = df_limpo.dropna(how='all')
                        
                        # A primeira coluna (índice 0) é sempre a que contém as cotas/unidades
                        coluna_cota = df_limpo.columns[0]
                        
                        # Preenche os espaços vazios para baixo (ffill)
                        df_limpo[coluna_cota] = df_limpo[coluna_cota].ffill()
                        
                        print(f"   ✅ Sucesso! Linhas: {len(df_limpo)} | Coluna de Cota (1ª coluna): '{coluna_cota}'")
                        print(df_limpo.head(3).to_string())
                    else:
                        print(f"   ⚠️ Não foi possível determinar o cabeçalho desta aba.")
                        
            except Exception as e:
                print(f"   ❌ Erro ao ler {arquivo}: {e}")
        else:
            print(f"   ❌ Arquivo não encontrado: {arquivo}")

if __name__ == "__main__":
    processar_e_limpar_dados()