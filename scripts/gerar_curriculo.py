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

# Pasta onde os currículos gerados serão salvos
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "curriculos"))

def ler_perfil():
    caminho = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "input", "fabiano_tavares", "profile_truth.md"))
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()

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
    Descrição: {descricao_vaga}

    PERFIL DO CANDIDATO:
    {perfil}
    """

    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ Erro ao gerar currículo: {e}")
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

    # Cria a pasta de output se não existir
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
        
        # Processa APENAS vagas com score >= 90 e que ainda não foram geradas
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
            # Salva o arquivo Markdown
            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                f.write(f"# Currículo Otimizado: {titulo} - {empresa}\n\n")
                f.write(texto_curriculo)
            
            print(f"   ✅ Arquivo salvo: output/curriculos/{nome_arquivo}")
            
            # Adiciona a vaga na aba "Vagas_Aprovadas"
            nova_linha = [
                id_vaga, data_coleta, titulo, empresa, local, salario, fonte, url, 
                descricao, score, linha[10], linha[11],
                "Aprovada", "", nome_arquivo, "", "Não"
            ]
            aba_aprovadas.append_row(nova_linha)
            print(f"   ✅ Vaga movida para a aba 'Vagas_Aprovadas'.")
            
            time.sleep(4) # Pausa para limite de API

    print("\n🎉 Processo de geração concluído!")

if __name__ == "__main__":
    main()