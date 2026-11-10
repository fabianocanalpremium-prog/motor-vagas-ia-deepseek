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

def ler_perfil():
    caminho_perfil = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "input", "fabiano_tavares", "profile_truth.md"))
    with open(caminho_perfil, "r", encoding="utf-8") as f:
        return f.read()[:10000]

# --- FUNÇÕES DE IA COM RETRY ---
def analisar_com_groq(prompt):
    if not client_groq: return "ERRO"
    
    max_tentativas = 2
    for tentativa in range(max_tentativas):
        try:
            print("      🟢 Tentando Groq...")
            response = client_groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            erro_str = str(e).lower()
            if "429" in erro_str or "rate limit" in erro_str:
                if "per day" in erro_str or "tpd" in erro_str:
                    print("      🔴 Cota DIÁRIA da Groq esgotada.")
                    return "LIMITE_DIARIO"
                else:
                    print(f"      ⏳ Limite por minuto na Groq. Aguardando 60s (Tentativa {tentativa+1}/{max_tentativas})...")
                    time.sleep(60)
            elif "413" in erro_str:
                print("      🔴 Texto muito grande para a Groq.")
                return "LIMITE_DIARIO"
            else:
                print(f"      ⚠️ Erro na Groq: {e}")
                return "ERRO"
                
    print("      🔴 Groq falhou após tentativas.")
    return "LIMITE_DIARIO"

def analisar_com_openrouter(prompt):
    if not client_openrouter: return "ERRO"
    try:
        print("      🟠 Tentando OpenRouter...")
        response = client_openrouter.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        erro_str = str(e).lower()
        if "429" in erro_str or "rate limit" in erro_str:
            print("      🔴 Cota do OpenRouter esgotada.")
            return "LIMITE_DIARIO"
        print(f"      ⚠️ Erro no OpenRouter: {e}")
        return "ERRO"

def analisar_com_gemini(prompt):
    if not client_gemini: return "ERRO"
    try:
        print("      🔵 Tentando Gemini...")
        response = client_gemini.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return response.text
    except Exception as e:
        erro_str = str(e).lower()
        if "429" in erro_str or "quota" in erro_str or "503" in erro_str:
            print("      🔴 Cota/Sobrecarga do Gemini.")
            return "LIMITE_DIARIO"
        print(f"      ⚠️ Erro no Gemini: {e}")
        return "ERRO"

def analisar_vaga_inteligente(prompt_completo):
    # 1. Groq
    if api_status["groq"]:
        res = analisar_com_groq(prompt_completo)
        if res == "LIMITE_DIARIO": api_status["groq"] = False
        elif res and res != "ERRO": return res

    # 2. OpenRouter
    if api_status["openrouter"]:
        res = analisar_com_openrouter(prompt_completo)
        if res == "LIMITE_DIARIO": api_status["openrouter"] = False
        elif res and res != "ERRO": return res

    # 3. Gemini
    if api_status["gemini"]:
        res = analisar_com_gemini(prompt_completo)
        if res == "LIMITE_DIARIO": api_status["gemini"] = False
        elif res and res != "ERRO": return res

    # Se todas as APIs esgotaram
    if not api_status["groq"] and not api_status["openrouter"] and not api_status["gemini"]:
        return "TUDO_ESGOTADO"
    return None

# --- FUNÇÃO PRINCIPAL ---
def main():
    print("🧠 Iniciando análise e tradução com Motor de Fallback (Groq -> OpenRouter -> Gemini)...")
    
    perfil = ler_perfil()
    
    creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
    client_sheets = gspread.authorize(creds)
    planilha = client_sheets.open_by_key(SPREADSHEET_ID)
    aba_bruta = planilha.worksheet("Vagas_Bruta")
    
    dados = aba_bruta.get_all_values()
    if len(dados) <= 1:
        print("Nenhuma vaga para analisar.")
        return

    vagas_pendentes = 0
    vagas_analisadas = 0

    for i, linha in enumerate(dados[1:], start=2):
        if len(linha) < 9: continue
        
        descricao = linha[8]
        score_atual = linha[9] if len(linha) > 9 else ""
        
        if score_atual.strip():
            continue
            
        vagas_pendentes += 1
        print(f"🔍 Analisando vaga {i}: {linha[2][:40]}...")
        
        salario = linha[5] if len(linha) > 5 else "Não informado"
        prompt_completo = f"""
        Você é um recrutador especialista. Analise a vaga abaixo e compare com o perfil do candidato.
        Retorne APENAS um JSON válido, sem formatação markdown (sem ```json), com a estrutura:
        {{
          "descricao_ptbr": "Texto da descrição traduzido para o português",
          "score": (número inteiro de 0 a 100),
          "salario_compativel": ("Sim" ou "Não" ou "Indefinido"),
          "palavras_chave_faltantes": ["palavra1", "palavra2"]
        }}
        PERFIL: {perfil}
        VAGA: {descricao[:4000]}
        SALÁRIO: {salario}
        """
        
        analise = analisar_vaga_inteligente(prompt_completo)
        
        if analise == "TUDO_ESGOTADO":
            print("\n🛑 TODAS AS COTAS DE IA ESGOTADAS! O robô vai parar e continuar amanhã.")
            break
            
        if not analise:
            print(f"   ⚠️ Erro ao analisar a vaga {i}. Pulando para a próxima.")
            continue

        try:
            # Limpa possíveis blocos de código que a IA possa ter colocado
            texto_limpo = analise.replace("```json", "").replace("```", "").strip()
            resultado = json.loads(texto_limpo)
            
            aba_bruta.update_cell(i, 9, resultado.get("descricao_ptbr", ""))
            aba_bruta.update_cell(i, 10, resultado.get("score", 0))
            aba_bruta.update_cell(i, 11, resultado.get("salario_compativel", "Indefinido"))
            aba_bruta.update_cell(i, 12, ", ".join(resultado.get("palavras_chave_faltantes", [])))
            
            print(f"   ✅ Score: {resultado.get('score')} | Salário: {resultado.get('salario_compativel')}")
            vagas_analisadas += 1
            
            time.sleep(5) # Pausa para evitar bloqueios
            
        except json.JSONDecodeError:
            print(f"   ⚠️ Erro ao decodificar o JSON da vaga {i}. A IA retornou um formato inválido.")
            continue

    print(f"\n🎉 Processo finalizado! {vagas_analisadas} vagas analisadas de {vagas_pendentes} pendentes.")

if __name__ == "__main__":
    main()