import os
import json
import time
import gspread
from dotenv import load_dotenv
from google import genai
from google.oauth2.service_account import Credentials

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações do Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CRED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))
SPREADSHEET_ID = "1rssICgKVOgKfm2Fg8LIYurmz5h2ZVyxF1g79XryrGjk"

# Configurações do Gemini (SDK google-genai)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("❌ Erro: GEMINI_API_KEY não encontrada no .env")
    exit()

client = genai.Client(api_key=GEMINI_API_KEY)
# Modelo atual recomendado (o 2.5-flash foi descontinuado)
MODEL_ID = "gemini-3.5-flash"

def ler_perfil():
    caminho_perfil = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "input", "fabiano_tavares", "profile_truth.md"))
    with open(caminho_perfil, "r", encoding="utf-8") as f:
        return f.read()

def analisar_vaga_com_gemini(perfil, descricao_vaga, salario_vaga):
    prompt = f"""
    Você é um recrutador especialista. Analise a vaga abaixo e compare com o perfil do candidato.
    
    Sua tarefa tem duas partes:
    1. Traduzir a descrição da vaga para o Português do Brasil (PT-BR).
    2. Avaliar a aderência do candidato à vaga.

    Retorne APENAS um JSON válido, sem formatação markdown (sem ```json), com a seguinte estrutura exata:
    {{
      "descricao_ptbr": "Texto da descrição traduzido para o português",
      "score": (número inteiro de 0 a 100),
      "salario_compativel": ("Sim" ou "Não" ou "Indefinido"),
      "palavras_chave_faltantes": ["palavra1", "palavra2"]
    }}
    
    REGRA 1: Avalie o salário com base no objetivo do perfil e no mercado para o cargo.
    REGRA 2: Se o salário não for informado na vaga, retorne "Indefinido".
    REGRA 3: O score deve refletir a aderência real. Não infle a nota.
    REGRA 4: Liste termos técnicos ou requisitos que a vaga pede e o candidato NÃO tem no perfil.

    PERFIL DO CANDIDATO:
    {perfil}

    DESCRIÇÃO DA VAGA (Original):
    {descricao_vaga}

    SALÁRIO DA VAGA (se houver):
    {salario_vaga}
    """

    try:
        # Usando a nova Interactions API, recomendada pelo Google
        interaction = client.interactions.create(
            model=MODEL_ID,
            input=prompt
        )
        texto_limpo = interaction.output_text.strip().replace("```json", "").replace("```", "").strip()
        resultado = json.loads(texto_limpo)
        return resultado
    except Exception as e:
        print(f"⚠️ Erro ao analisar com Gemini: {e}")
        return None

def main():
    print(f"🧠 Iniciando análise e tradução com Gemini ({MODEL_ID})...")
    
    # 1. Ler o Perfil
    perfil = ler_perfil()
    
    # 2. Conectar ao Sheets
    creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
    client_sheets = gspread.authorize(creds)
    planilha = client_sheets.open_by_key(SPREADSHEET_ID)
    aba_bruta = planilha.worksheet("Vagas_Bruta")
    
    # 3. Pega todos os dados
    dados = aba_bruta.get_all_values()
    if len(dados) <= 1:
        print("Nenhuma vaga para analisar.")
        return

    # 4. Itera sobre as linhas (pulando o cabeçalho)
    for i, linha in enumerate(dados[1:], start=2):
        if len(linha) < 9: continue
        
        descricao = linha[8]
        score_atual = linha[9] if len(linha) > 9 else ""
        
        if score_atual.strip():
            print(f"⏩ Vaga {i} ({linha[2]}) já analisada. Pulando...")
            continue
            
        print(f"🔍 Analisando vaga {i}: {linha[2]} na empresa {linha[3]}...")
        
        salario = linha[5] if len(linha) > 5 else "Não informado"
        resultado = analisar_vaga_com_gemini(perfil, descricao, salario)
        
        if resultado:
            # Atualiza a coluna I (Descrição Traduzida)
            if "descricao_ptbr" in resultado:
                aba_bruta.update_cell(i, 9, resultado.get("descricao_ptbr"))
                
            # Atualiza as colunas J (Score), K (Salário) e L (Palavras)
            aba_bruta.update_cell(i, 10, resultado.get("score"))
            aba_bruta.update_cell(i, 11, resultado.get("salario_compativel"))
            aba_bruta.update_cell(i, 12, ", ".join(resultado.get("palavras_chave_faltantes", [])))
            
            print(f"   ✅ Score: {resultado.get('score')} | Salário: {resultado.get('salario_compativel')} | Descrição traduzida.")
            
            # Pausa de 4 segundos para respeitar o limite gratuito
            time.sleep(4) 

    print("\n🎉 Análise concluída!")

if __name__ == "__main__":
    main()