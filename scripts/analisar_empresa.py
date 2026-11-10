import os
import json
import time
import gspread
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from google.oauth2.service_account import Credentials

# Carrega as variáveis de ambiente
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CRED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))
SPREADSHEET_ID = "1rssICgKVOgKfm2Fg8LIYurmz5h2ZVyxF1g79XryrGjk"

# --- CONFIGURAÇÕES DE IA (FALLBACK) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client_groq = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY) if GROQ_API_KEY else None
GROQ_MODEL = "openai/gpt-oss-120b"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
client_openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={"HTTP-Referer": "https://github.com/fabianocanalpremium-prog/motor-vagas-ia-deepseek", "X-Title": "Motor de Vagas IA"}
) if OPENROUTER_API_KEY else None
OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct:free"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client_gemini = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
GEMINI_MODEL = "gemini-3.5-flash"

api_status = {"groq": True, "openrouter": True, "gemini": True}

def analisar_empresa_com_ia(nome_empresa):
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
    
    # 1. Tenta Groq
    if api_status["groq"]:
        max_tentativas = 2
        for tentativa in range(max_tentativas):
            try:
                print("      🟢 Analisando com Groq...")
                response = client_groq.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                erro_str = str(e).lower()
                if "429" in erro_str or "rate limit" in erro_str:
                    if "per day" in erro_str or "tpd" in erro_str:
                        print("      🔴 Cota DIÁRIA da Groq esgotada.")
                        api_status["groq"] = False
                        break
                    else:
                        print(f"      ⏳ Limite por minuto na Groq. Aguardando 60s (Tentativa {tentativa+1}/{max_tentativas})...")
                        time.sleep(60)
                else:
                    print(f"      ⚠️ Erro na Groq: {e}")
                    break

    # 2. Tenta OpenRouter
    if api_status["openrouter"]:
        try:
            print("      🟠 Analisando com OpenRouter...")
            response = client_openrouter.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            erro_str = str(e).lower()
            if "429" in erro_str or "rate limit" in erro_str:
                print("      🔴 Cota do OpenRouter esgotada.")
                api_status["openrouter"] = False
            else:
                print(f"      ⚠️ Erro no OpenRouter: {e}")

    # 3. Tenta Gemini
    if api_status["gemini"]:
        try:
            print("      🔵 Analisando com Gemini...")
            response = client_gemini.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            texto_limpo = response.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(texto_limpo)
        except Exception as e:
            erro_str = str(e).lower()
            if "429" in erro_str or "quota" in erro_str or "503" in erro_str:
                print("      🔴 Cota/Sobrecarga do Gemini.")
                api_status["gemini"] = False
            else:
                print(f"      ⚠️ Erro no Gemini: {e}")

    # Se todas as APIs falharem
    if not api_status["groq"] and not api_status["openrouter"] and not api_status["gemini"]:
        return "TUDO_ESGOTADO"
        
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

    empresas_analisadas = [linha[0] for linha in aba_analise.get_all_values()[1:] if len(linha) > 0]

    for i, linha in enumerate(dados[1:], start=2):
        empresa = linha[3] if len(linha) > 3 else ""
        empresa_analisada_status = linha[16] if len(linha) > 16 else ""
        
        if not empresa or empresa_analisada_status == "Sim" or empresa in empresas_analisadas:
            continue
            
        print(f"🔍 Analisando empresa: {empresa}...")
        
        resultado = analisar_empresa_com_ia(empresa)
        
        if resultado == "TUDO_ESGOTADO":
            print("\n🛑 TODAS AS COTAS DE IA ESGOTADAS! O robô vai parar e continuar amanhã.")
            break
            
        if resultado:
            linha_analise = [
                empresa,
                time.strftime("%Y-%m-%d %H:%M:%S"),
                resultado.get("missao", ""),
                resultado.get("cultura", ""),
                resultado.get("red_flags", ""),
                "Base de conhecimento da IA",
                resultado.get("veredito", "")
            ]
            aba_analise.append_row(linha_analise)
            
            # Marca como "Sim" na coluna Q (17) da aba Vagas_Aprovadas
            aba_aprovadas.update_cell(i, 17, "Sim")
            print(f"   ✅ Análise da {empresa} concluída e salva com sucesso.")
            
            time.sleep(5)

    print("\n🎉 Análise de empresas finalizada!")

if __name__ == "__main__":
    main()