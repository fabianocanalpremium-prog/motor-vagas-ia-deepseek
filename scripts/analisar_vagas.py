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

# --- CONFIGURAÇÃO DOS CLIENTES DE IA ---
# 1. Groq (Prioridade)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client_groq = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY) if GROQ_API_KEY else None
GROQ_MODEL = "openai/gpt-oss-120b"

# 2. Gemini (Fallback)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client_gemini = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
GEMINI_MODEL = "gemini-3.5-flash"

# Status das APIs (True = disponível, False = esgotada)
api_status = {"groq": True, "gemini": True}

def ler_perfil():
    caminho_perfil = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "input", "fabiano_tavares", "profile_truth.md"))
    with open(caminho_perfil, "r", encoding="utf-8") as f:
        return f.read()

def extrair_json(texto):
    """Limpa a resposta da IA e tenta converter para JSON"""
    texto_limpo = texto.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(texto_limpo)
    except json.JSONDecodeError:
        # Se falhar, tenta achar o primeiro '{' e o último '}'
        inicio = texto_limpo.find('{')
        fim = texto_limpo.rfind('}')
        if inicio != -1 and fim != -1:
            try:
                return json.loads(texto_limpo[inicio:fim+1])
            except:
                pass
        return None

def analisar_com_groq(perfil, descricao, salario):
    if not client_groq: return "ERRO"
    # Trunca para evitar o erro 413 da Groq
    descricao = descricao[:4000]
    perfil = perfil[:10000]
    
    prompt = f"""
    Analise a vaga e o perfil. Retorne APENAS um JSON válido:
    {{"descricao_ptbr": "Tradução", "score": 0-100, "salario_compativel": "Sim/Não/Indefinido", "palavras_chave_faltantes": ["p1", "p2"]}}
    
    VAGA: {descricao}
    SALÁRIO: {salario}
    PERFIL: {perfil}
    """
    try:
        response = client_groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Você é um assistente que retorna apenas JSON válido."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return extrair_json(response.choices[0].message.content)
    except Exception as e:
        erro_str = str(e).lower()
        if "429" in erro_str or "rate limit" in erro_str or "413" in erro_str:
            return "LIMITE_ATINGIDO"
        print(f"      ⚠️ Erro na Groq: {e}")
        return "ERRO"

def analisar_com_gemini(perfil, descricao, salario):
    if not client_gemini: return "ERRO"
    
    prompt = f"""
    Analise a vaga e o perfil. Retorne APENAS um JSON válido, sem formatação markdown:
    {{"descricao_ptbr": "Tradução", "score": 0-100, "salario_compativel": "Sim/Não/Indefinido", "palavras_chave_faltantes": ["p1", "p2"]}}
    
    VAGA: {descricao[:5000]}
    SALÁRIO: {salario}
    PERFIL: {perfil[:15000]}
    """
    try:
        response = client_gemini.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return extrair_json(response.text)
    except Exception as e:
        erro_str = str(e).lower()
        if "429" in erro_str or "quota" in erro_str:
            return "LIMITE_ATINGIDO"
        print(f"      ⚠️ Erro no Gemini: {e}")
        return "ERRO"

def analisar_vaga_inteligente(perfil, descricao, salario):
    """O Maestro que decide qual IA usar"""
    
    # 1. Tenta Groq (se estiver disponível)
    if api_status["groq"]:
        print("      🟢 Tentando Groq...")
        resultado = analisar_com_groq(perfil, descricao, salario)
        
        if resultado == "LIMITE_ATINGIDO":
            print("      🔴 Cota da Groq esgotada. Alternando para o Gemini...")
            api_status["groq"] = False
        elif resultado and resultado != "ERRO":
            return resultado

    # 2. Tenta Gemini (se Groq falhou ou já estava esgotado)
    if api_status["gemini"]:
        print("      🔵 Tentando Gemini...")
        resultado = analisar_com_gemini(perfil, descricao, salario)
        
        if resultado == "LIMITE_ATINGIDO":
            print("      🔴 Cota do Gemini esgotada.")
            api_status["gemini"] = False
        elif resultado and resultado != "ERRO":
            return resultado

    # Se ambos falharam
    if not api_status["groq"] and not api_status["gemini"]:
        return "TUDO_ESGOTADO"
        
    return None

def main():
    print("🧠 Iniciando análise com Motor de Fallback (Groq -> Gemini)...")
    
    if not api_status["groq"] and not api_status["gemini"]:
        print("❌ Nenhuma chave de API configurada no .env.")
        return

    perfil = ler_perfil()
    
    creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
    client_sheets = gspread.authorize(creds)
    planilha = client_sheets.open_by_key(SPREADSHEET_ID)
    aba_bruta = planilha.worksheet("Vagas_Bruta")
    
    dados = aba_bruta.get_all_values()
    if len(dados) <= 1:
        print("Nenhuma vaga para analisar.")
        return

    for i, linha in enumerate(dados[1:], start=2):
        if len(linha) < 9: continue
        
        descricao = linha[8]
        score_atual = linha[9] if len(linha) > 9 else ""
        
        if score_atual.strip():
            continue
            
        print(f"🔍 Analisando vaga {i}: {linha[2][:40]}...")
        
        salario = linha[5] if len(linha) > 5 else "Não informado"
        resultado = analisar_vaga_inteligente(perfil, descricao, salario)
        
        if resultado == "TUDO_ESGOTADO":
            print("\n🛑 TODAS AS COTAS DE IA ESGOTADAS!")
            print("O robô vai parar e continuar de onde parou amanhã.")
            break
            
        if resultado:
            aba_bruta.update_cell(i, 9, resultado.get("descricao_ptbr", ""))
            aba_bruta.update_cell(i, 10, resultado.get("score", 0))
            aba_bruta.update_cell(i, 11, resultado.get("salario_compativel", "Indefinido"))
            aba_bruta.update_cell(i, 12, ", ".join(resultado.get("palavras_chave_faltantes", [])))
            
            print(f"   ✅ Vaga {i} processada com sucesso!")
            
            time.sleep(2) # Pequena pausa para não sobrecarregar

    print("\n🎉 Processo finalizado!")

if __name__ == "__main__":
    main()