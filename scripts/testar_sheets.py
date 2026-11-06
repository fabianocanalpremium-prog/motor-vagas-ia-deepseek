import gspread
import os
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Garante que o Python ache o credentials.json na pasta raiz, mesmo o script estando em /scripts
CRED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))

# ID da sua planilha (extraído da URL)
SPREADSHEET_ID = "1rssICgKVOgKfm2Fg8LIYurmz5h2ZVyxF1g79XryrGjk"

def testar_conexao():
    try:
        # Verifica se o arquivo existe antes de tentar conectar
        if not os.path.exists(CRED_FILE):
            print(f"❌ Erro: O arquivo não foi encontrado no caminho: {CRED_FILE}")
            print("Verifique se o nome do arquivo é exatamente 'credentials.json' (sem .json.json) e se ele está na raiz do projeto.")
            return

        creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # Abre a planilha pelo ID
        planilha = client.open_by_key(SPREADSHEET_ID)
        
        # Lista o nome de todas as abas
        abas = [aba.title for aba in planilha.worksheets()]
        print("✅ Conexão bem-sucedida!")
        print(f"Abas encontradas na planilha: {abas}")
        
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")

if __name__ == "__main__":
    testar_conexao()