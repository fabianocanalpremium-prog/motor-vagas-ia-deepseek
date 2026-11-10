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

# Pasta onde os currículos gerados serão salvos
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "curriculos"))

def ler_perfil():
    caminho = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "input", "fabiano_tavares", "profile_truth.md"))
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()[:15000]

def gerar_texto_curriculo(perfil, titulo_vaga, empresa, descricao_vaga):
    prompt = f"""
    Você é um especialista em recrutamento e otimização de currículos para ATS (Applicant Tracking Systems).
    Sua tarefa é adaptar o currículo do candidato para a vaga especificada abaixo.

    REGRA DE OURO: NÃO INVENTE NADA. Use estritamente as informações, cargos, datas e experiências contidas no PERFIL DO CANDIDATO. Seu trabalho é reescrever e destacar as experiências que já existem usando as palavras-chave da vaga para passar no ATS.

    Gere o conteúdo em formato Markdown com a seguinte estrutura:
    1. **Resumo Profissional Otimizado:** Um parágrafo de 4 a 5 linhas destacando as experiências do candidato que mais se alinham com a vaga.
    2. **Competências-Chave (Skills):** Uma lista com as ferramentas e habilidades do candidato que a vaga exige (extraídas do perfil).
    3. **Experiências Relevantes:** Destaque as 2 ou 3 experiências mais relevantes do perfil, reescrevendo as atividades com foco nas necessidades da vaga.
    4. **Análise ATS:** Uma breve lista informando quais palavras-chave da vaga foram incorporadas com sucesso e quais o candidato não possui (as "faltantes").

    VAGA:
    Título: {titulo_vaga}
    Empresa: {empresa}
    Descrição: {descricao_vaga[:4000]}

    PERFIL DO CANDIDATO:
    {perfil}
    """
    
    # 1. Tenta Groq
    if api_status["groq"]:
        max_tentativas = 2
        for tentativa in range(max_tentativas):
            try:
                print("      🟢 Gerando com Groq...")
                response = client_groq.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                return response.choices[0].message.content
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
            print("      🟠 Gerando com OpenRouter...")
            response = client_openrouter.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
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
            print("      🔵 Gerando com Gemini...")
            response = client_gemini.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            return response.text
        except Exception as e:
            erro_str = str(e).lower()
            if "429" in erro_str or "quota" in erro_str or "503" in erro_str:
                print("      🔴 Cota/Sobrecarga do Gemini.")
                api_status["gemini"] = False
            else:
                print(f"      ⚠️ Erro no Gemini: {e}")

    # Se todas as APIs falharem
    print("      ❌ Todas as cotas de IA esgotadas para gerar este currículo.")
    return None

def main():
    print("📄 Iniciando geração de currículos sob medida (Filtro de Score >= 90)...")
    
    perfil = ler_perfil()
    
    creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
    client_sheets = gspread.authorize(creds)
    planilha = client_sheets.open_by_key(SPREADSHEET_ID)
    
    aba_bruta = planilha.worksheet("Vagas_Bruta")
    aba_aprovadas = planilha.worksheet("Vagas_Aprovadas")
    
    dados = aba_bruta.get_all_values()
    if len(dados) <= 1:
        print("Nenhuma vaga para processar.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for i, linha in enumerate(dados[1:], start=2):
        if len(linha) < 12: continue
        
        id_vaga = linha[0]
        data_coleta = linha[1]
        titulo = linha[2]
        empresa = linha[3]
        local = linha[4]
        salario = linha[5]
        fonte = linha[6]
        url = linha[7]
        descricao = linha[8]
        score = linha[9]
        
        # Processa APENAS vagas com score >= 90
        if not score or int(score) < 90:
            continue
            
        nome_arquivo = f"CV_{empresa.replace(' ', '_')}_{titulo.replace(' ', '_')}.md"
        caminho_arquivo = os.path.join(OUTPUT_DIR, nome_arquivo)
        
        if os.path.exists(caminho_arquivo):
            print(f"⏩ Currículo para '{titulo}' já existe. Pulando...")
            continue

        print(f"✍️ Gerando currículo para: {titulo} na empresa {empresa} (Score: {score})...")
        
        texto_curriculo = gerar_texto_curriculo(perfil, titulo, empresa, descricao)
        
        if texto_curriculo:
            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                f.write(f"# Currículo Otimizado: {titulo} - {empresa}\n\n")
                f.write(texto_curriculo)
            
            print(f"   ✅ Arquivo salvo: output/curriculos/{nome_arquivo}")
            
            # Adiciona a vaga na aba "Vagas_Aprovadas" se ainda não estiver lá
            # Para evitar duplicatas, verificamos se o ID já está na aba de aprovadas
            ids_aprovados = [r[0] for r in aba_aprovadas.get_all_values()[1:] if len(r) > 0]
            if id_vaga not in ids_aprovados:
                nova_linha = [
                    id_vaga, data_coleta, titulo, empresa, local, salario, fonte, url, 
                    descricao, score, linha[10], linha[11],
                    "Aprovada", "", nome_arquivo, "", "Não"
                ]
                aba_aprovadas.append_row(nova_linha)
                print(f"   ✅ Vaga movida para a aba 'Vagas_Aprovadas'.")
            else:
                print(f"   ℹ️ Vaga já constava na aba 'Vagas_Aprovadas'. Não foi duplicada.")
            
            time.sleep(5) # Pausa entre vagas

    print("\n🎉 Processo de geração concluído!")

if __name__ == "__main__":
    main()