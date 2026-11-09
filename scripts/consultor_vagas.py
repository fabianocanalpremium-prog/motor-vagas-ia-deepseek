import os
import re
import json
import time
import requests
import smtplib
import subprocess
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Carrega as variáveis de ambiente
load_dotenv()

# --- CONFIGURAÇÕES DO TELEGRAM ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().replace('"', '').replace("'", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip().replace('"', '').replace("'", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

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

# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA_APP = os.getenv("EMAIL_SENHA_APP")
EMAIL_DESTINATARIO = EMAIL_REMETENTE

# PROMPT DO CONSULTOR
PROMPT_CONSULTOR = """
Com base no descritivo da vaga e no meu currículo (que está no arquivo profile_truth.md), atue como um Consultor Sênior de RH.
Gere um relatório completo e detalhado em formato **Markdown** com as seguintes seções:

# Relatório de Aderência e Consultoria

## 1. Taxa de Aderência
Crie uma tabela Markdown com as colunas: Responsabilidade da Vaga, Evidência no seu Currículo, Grau de Aderência.
**IMPORTANTE:** Na coluna "Grau de Aderência", use OBRIGATORIAMENTE percentuais numéricos (ex: 95%, 80%, 100%) e NÃO palavras como "Alta" ou "Média".
No final, destaque a Aderência Geral (ex: 94%).

## 2. Dores e Soluções (Encantamento)
Crie uma tabela Markdown com as colunas: Dor/Desafio da Empresa, Como seu perfil resolve, Ideia de Encantamento.

## 3. Cenário de Remuneração
Crie uma tabela Markdown com Cargo, Faixa Salarial Base, Bônus/PLR, Total Anual.
Inclua uma recomendação de negociação.

## 4. Apresentação Persuasiva
- **E-mail de Candidatura:** (Assunto e Corpo do texto)
- **Frases para LinkedIn:** (3 opções prontas)
- **Pitch para Entrevista:** (30 segundos)

## 5. Reescrita do Currículo (ATS)
Liste as palavras-chave essenciais. Reescreva o resumo profissional focado nessa vaga.

FORMATE TUDO COM TABELAS E NEGRITO. Não use blocos de código (```), apenas texto Markdown puro.
"""

def enviar_mensagem_telegram(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": texto})

def raspar_texto_vaga(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        titulo_vaga = "Vaga Analisada"
        if soup.title: titulo_vaga = soup.title.string
        elif soup.h1: titulo_vaga = soup.h1.get_text(strip=True)
        
        titulo_vaga = re.sub(r'\|.*', '', titulo_vaga).strip()
        titulo_vaga = re.sub(r' - .*', '', titulo_vaga).strip()

        for script in soup(["script", "style"]): script.extract()
        texto = soup.get_text(separator=' ', strip=True)
        
        if len(texto) < 500:
            return None, titulo_vaga
            
        return texto[:10000], titulo_vaga
    except Exception as e:
        print(f"Erro ao raspar: {e}")
        return None, None

def ler_perfil():
    caminho = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "input", "fabiano_tavares", "profile_truth.md"))
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()[:10000]

# --- FUNÇÕES DE IA ---
def analisar_com_groq(prompt):
    if not client_groq: return "ERRO"
    try:
        print("      🟢 Tentando Groq...")
        response = client_groq.chat.completions.create(model=GROQ_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return response.choices[0].message.content
    except Exception as e:
        erro_str = str(e).lower()
        if "429" in erro_str or "rate limit" in erro_str or "413" in erro_str:
            print("      🔴 Cota da Groq esgotada.")
            return "LIMITE_ATINGIDO"
        print(f"      ⚠️ Erro na Groq: {e}")
        return "ERRO"

def analisar_com_openrouter(prompt):
    if not client_openrouter: return "ERRO"
    try:
        print("      🟠 Tentando OpenRouter...")
        response = client_openrouter.chat.completions.create(model=OPENROUTER_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return response.choices[0].message.content
    except Exception as e:
        erro_str = str(e).lower()
        if "429" in erro_str or "rate limit" in erro_str:
            print("      🔴 Cota do OpenRouter esgotada.")
            return "LIMITE_ATINGIDO"
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
            return "LIMITE_ATINGIDO"
        print(f"      ⚠️ Erro no Gemini: {e}")
        return "ERRO"

def analisar_vaga_inteligente(prompt_completo):
    if api_status["groq"]:
        res = analisar_com_groq(prompt_completo)
        if res == "LIMITE_ATINGIDO": api_status["groq"] = False
        elif res and res != "ERRO": return res

    if api_status["openrouter"]:
        res = analisar_com_openrouter(prompt_completo)
        if res == "LIMITE_ATINGIDO": api_status["openrouter"] = False
        elif res and res != "ERRO": return res

    if api_status["gemini"]:
        res = analisar_com_gemini(prompt_completo)
        if res == "LIMITE_ATINGIDO": api_status["gemini"] = False
        elif res and res != "ERRO": return res

    if not api_status["groq"] and not api_status["openrouter"] and not api_status["gemini"]:
        return "TUDO_ESGOTADO"
    return None

# --- FUNÇÕES DE ARQUIVO E E-MAIL ---
def gerar_pdf_profissional(texto_markdown, caminho_pdf):
    caminho_md = caminho_pdf.replace(".pdf", ".md")
    texto_limpo = texto_markdown.replace("```markdown", "").replace("```", "").strip()
    
    with open(caminho_md, "w", encoding="utf-8") as f:
        f.write(texto_limpo)
        
    print("🎨 Gerando PDF com design profissional (Pandoc)...")
    try:
        subprocess.run([
            "pandoc", caminho_md, "-o", caminho_pdf,
            "--pdf-engine=xelatex",
            "-V", "geometry:margin=2cm",
            "-V", "mainfont=DejaVu Sans",
            "-V", "colorlinks=true",
            "-V", "linkcolor=blue"
        ], check=True)
        os.remove(caminho_md)
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")

def enviar_email_com_anexo(caminho_pdf, titulo_vaga):
    msg = MIMEMultipart()
    msg['Subject'] = f"📊 Relatório de Aderência: {titulo_vaga}"
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO
    msg.attach(MIMEText(f"Olá Fabiano,\n\nSegue em anexo o relatório completo gerado pela IA para a vaga: {titulo_vaga}.\n\nBoa sorte!", 'plain'))
    
    with open(caminho_pdf, "rb") as f:
        anexo = MIMEApplication(f.read(), _subtype="pdf")
        anexo.add_header('Content-Disposition', 'attachment', filename=f"Analise_{titulo_vaga[:20].replace(' ', '_')}.pdf")
        msg.attach(anexo)
        
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
    server.send_message(msg)
    server.quit()

# --- FUNÇÃO PRINCIPAL (Webhook Mode) ---
def main():
    if not TELEGRAM_TOKEN:
        print("❌ Abortando: Token do Telegram ausente.")
        return

    # Pega a URL enviada pelo Cloudflare/GitHub Actions
    url_vaga = os.getenv("VAGA_URL")
    
    if not url_vaga:
        print("❌ Nenhuma URL de vaga encontrada. Este script deve ser rodado via Webhook.")
        enviar_mensagem_telegram("⚠️ Erro: O robô não recebeu o link da vaga. Tente enviar novamente.")
        return

    print(f"🔗 Link recebido do Webhook: {url_vaga}")
    enviar_mensagem_telegram(f"🔍 Recebi o link! Iniciando análise. Isso pode levar alguns minutos...")
    
    texto_vaga, titulo_vaga = raspar_texto_vaga(url_vaga)
    
    if not texto_vaga:
        enviar_mensagem_telegram("❌ Não consegui ler o conteúdo deste site (provavelmente bloqueou o acesso). Tente enviar um link do LinkedIn.")
        print("❌ Falha na leitura do site. Abortando análise.")
        return

    print(f"📄 Título da Vaga: {titulo_vaga}")
    perfil = ler_perfil()
    prompt_completo = f"{PROMPT_CONSULTOR}\n\nCURRÍCULO:\n{perfil}\n\nVAGA:\n{texto_vaga}"
    
    analise = analisar_vaga_inteligente(prompt_completo)
    
    if analise == "TUDO_ESGOTADO":
        enviar_mensagem_telegram("🛑 Todas as cotas de IA esgotaram. Tente novamente mais tarde.")
        print("❌ Todas as cotas esgotadas.")
        return
        
    if not analise:
        enviar_mensagem_telegram("❌ Ocorreu um erro ao gerar a análise. Tente novamente.")
        return

    caminho_pdf = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Analise_Vaga.pdf"))
    gerar_pdf_profissional(analise, caminho_pdf)
    
    try:
        enviar_email_com_anexo(caminho_pdf, titulo_vaga)
        enviar_mensagem_telegram(f"✅ Análise da vaga '{titulo_vaga}' concluída! O relatório em PDF foi enviado para o seu e-mail.")
        print("✅ Processo finalizado com sucesso.")
    except Exception as e:
        enviar_mensagem_telegram(f"❌ Erro ao enviar o e-mail: {e}")
        print(f"❌ Erro no e-mail: {e}")

if __name__ == "__main__":
    main()