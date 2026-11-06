import os
import json
import time
import gspread
from dotenv import load_dotenv
from google import genai
from google.oauth2.service_account import Credentials

# Carrega as variáveis de ambiente
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CRED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))
SPREADSHEET_ID = "1rssICgKVOgKfm2Fg8LIYurmz5h2ZVyxF1g79XryrGjk"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-3.5-flash"

def analisar_empresa_gemini(nome_empresa):
    if nome_empresa == "Não informada" or nome_empresa == "Não informado":
        return {
            "missao": "Não disponível",
            "cultura": "Não disponível",
            "red_flags": "Não disponível",
            "veredito": "Empresa não informada na vaga. Análise não realizada."
        }

    prompt = f"""
    Você é um analista de mercado especialista em cultura organizacional.
    Faça uma breve análise sobre a empresa "{nome_empresa}".
    Se você não tiver dados suficientes ou atualizados sobre essa empresa em sua base de conhecimento, diga explicitamente "Dados insuficientes na base pública" em vez de inventar.

    Retorne APENAS um JSON válido (sem ```json) com esta estrutura exata:
    {{
      "missao": "Resumo da missão/objetivo da empresa",
      "cultura": "Resumo do ambiente de trabalho, valores e clima",
      "red_flags": "Alertas conhecidos no mercado, se houver. Se não houver, escreva 'Nenhum alerta encontrado'.",
      "veredito": "Um parágrafo com um veredito final sobre se parece ser um bom ambiente para um profissional de vendas B2B"
    }}
    """
    
    # Sistema de retentativa (Tenta 3 vezes se o servidor estiver sobrecarregado)
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            response = client.models.generate_content(model=MODEL_ID, contents=prompt)
            texto_limpo = response.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(texto_limpo)
        except Exception as e:
            print(f"⚠️ Tentativa {tentativa + 1} falhou para {nome_empresa}: {e}")
            if tentativa < max_tentativas - 1:
                print("⏳ Servidor sobrecarregado. Aguardando 10 segundos para tentar novamente...")
                time.sleep(10)
            else:
                print(f"❌ Falha definitiva ao analisar {nome_empresa} após {max_tentativas} tentativas.")
                return None

def main():
    print("🏢 Iniciando análise de empresas...")
    
    creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
    client_sheets = gspread.authorize(creds)
    planilha = client_sheets.open_by_key(SPREADSHEET_ID)
    
    aba_aprovadas = planilha.worksheet("Vagas_Aprovadas")
    aba_analise = planilha.worksheet("Analise_Empresas")
    
    dados = aba_aprovadas.get_all_values()
    if len(dados) <= 1:
        print("Nenhuma vaga aprovada para analisar.")
        return

    # Pega as empresas que já foram analisadas para não repetir
    empresas_analisadas = [linha[0] for linha in aba_analise.get_all_values()[1:]]

    for i, linha in enumerate(dados[1:], start=2):
        empresa = linha[3] if len(linha) > 3 else ""
        empresa_analisada_status = linha[16] if len(linha) > 16 else ""
        
        if not empresa or empresa_analisada_status == "Sim":
            continue
            
        print(f"🔍 Analisando empresa: {empresa}...")
        
        resultado = analisar_empresa_gemini(empresa)
        
        if resultado:
            linha_analise = [
                empresa,
                time.strftime("%Y-%m-%d %H:%M:%S"),
                resultado.get("missao"),
                resultado.get("cultura"),
                resultado.get("red_flags"),
                "Base de conhecimento da IA",
                resultado.get("veredito")
            ]
            aba_analise.append_row(linha_analise)
            
            # Marca como "Sim" na coluna Q (17) da aba Vagas_Aprovadas
            aba_aprovadas.update_cell(i, 17, "Sim")
            print(f"   ✅ Análise da {empresa} concluída e salva com sucesso.")
            
            time.sleep(4) 

    print("\n🎉 Análise de empresas finalizada!")

if __name__ == "__main__":
    main()