import gspread
import os
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

CRED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))
SPREADSHEET_ID = "1rssICgKVOgKfm2Fg8LIYurmz5h2ZVyxF1g79XryrGjk"

def configurar_abas():
    try:
        creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        planilha = client.open_by_key(SPREADSHEET_ID)

        # Define a estrutura das abas e suas colunas
        estrutura = {
            "Vagas_Bruta": [
                "ID", "Data_Coleta", "Titulo", "Empresa", "Local", "Salario", 
                "Fonte", "URL", "Descricao", "Score_Aderencia", 
                "Salario_Compativel", "Palavras_Chave_Faltantes"
            ],
            "Vagas_Aprovadas": [
                "ID", "Data_Coleta", "Titulo", "Empresa", "Local", "Salario", 
                "Fonte", "URL", "Descricao", "Score_Aderencia", 
                "Salario_Compativel", "Palavras_Chave_Faltantes",
                "Status", "Data_Candidatura", "Link_Curriculo", "Coverage_Score", "Empresa_Analisada"
            ],
            "Analise_Empresas": [
                "Empresa", "Data_Analise", "Missao", "Cultura_Resumo", "Red_Flags", "Fontes", "Veredito_Cultural"
            ],
            "Dashboard": [
                "Metrica", "Valor"
            ]
        }

        abas_existentes = [aba.title for aba in planilha.worksheets()]

        for nome_aba, colunas in estrutura.items():
            if nome_aba not in abas_existentes:
                print(f"Criando aba: {nome_aba}...")
                nova_aba = planilha.add_worksheet(title=nome_aba, rows="1000", cols=len(colunas))
                # Insere os cabeçalhos na primeira linha
                nova_aba.insert_row(colunas, index=1)
                # Formata a primeira linha (negrito) para ficar bonito
                nova_aba.format("A1:Z1", {"textFormat": {"bold": True}})
                print(f"✅ Aba '{nome_aba}' criada com sucesso.")
            else:
                print(f"ℹ️ Aba '{nome_aba}' já existe. Pulando...")

        # Deletar a aba "Página1" se ela estiver vazia e as novas abas foram criadas
        if "Página1" in abas_existentes:
            pagina1 = planilha.worksheet("Página1")
            if len(pagina1.get_all_values()) <= 1: # Se só tiver cabeçalho ou vazia
                planilha.del_worksheet(pagina1)
                print("🗑️ Aba 'Página1' vazia removida.")

        print("\n🎉 Estrutura da planilha configurada com sucesso!")

    except Exception as e:
        print(f"❌ Erro ao configurar planilha: {e}")

if __name__ == "__main__":
    configurar_abas()