import os
import smtplib
import gspread
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações do Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CRED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))
SPREADSHEET_ID = "1rssICgKVOgKfm2Fg8LIYurmz5h2ZVyxF1g79XryrGjk"

# Configurações de E-mail
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA_APP = os.getenv("EMAIL_SENHA_APP")
EMAIL_DESTINATARIO = EMAIL_REMETENTE # Envia para você mesmo

def buscar_vagas_na_planilha():
    creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    planilha = client.open_by_key(SPREADSHEET_ID)
    aba_bruta = planilha.worksheet("Vagas_Bruta")
    
    # Pega todos os dados
    dados = aba_bruta.get_all_values()
    if len(dados) <= 1:
        return []
    
    # Pega as últimas 15 vagas inseridas para não fazer um e-mail gigante
    # O [1:] pula o cabeçalho
    vagas_recentes = dados[-15:] 
    
    vagas_formatadas = []
    for linha in vagas_recentes:
        if len(linha) < 9: continue
        
        vagas_formatadas.append({
            "titulo": linha[2],
            "empresa": linha[3],
            "local": linha[4],
            "fonte": linha[6],
            "url": linha[7],
            "score": linha[9] if len(linha) > 9 and linha[9] else "Pendente"
        })
    
    # Inverte para mostrar as mais recentes primeiro
    return vagas_formatadas[::-1]

def gerar_html_email(vagas):
    html = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; color: #333; }
            h2 { color: #0056b3; }
            .vaga { border-bottom: 1px solid #ccc; padding: 10px 0; }
            .titulo { font-size: 16px; font-weight: bold; color: #000; }
            .empresa { color: #555; font-style: italic; }
            .detalhes { font-size: 12px; color: #777; margin-top: 5px; }
            .link { color: #0056b3; text-decoration: none; font-weight: bold; }
        </style>
    </head>
    <body>
        <h2>🚀 Resumo Diário de Vagas - Motor de Busca IA</h2>
        <p>Olá, Fabiano! Aqui estão as vagas mais recentes capturadas pelo seu robô:</p>
    """
    
    for v in vagas:
        html += f"""
        <div class="vaga">
            <div class="titulo">{v['titulo']}</div>
            <div class="empresa">{v['empresa']} | {v['local']}</div>
            <div class="detalhes">Fonte: {v['fonte']} | Adêrencia IA: {v['score']}</div>
            <div style="margin-top: 5px;">
                <a href="{v['url']}" class="link">👉 Clique aqui para ver a vaga</a>
            </div>
        </div>
        """
        
    html += """
        <br>
        <p>Boa sorte nas candidaturas!<br>Robô de Vagas 🤖</p>
    </body>
    </html>
    """
    return html

def enviar_email():
    print("📧 Iniciando preparação do e-mail...")
    
    if not EMAIL_REMETENTE or not EMAIL_SENHA_APP:
        print("❌ Erro: Credenciais de e-mail não encontradas no arquivo .env")
        return

    vagas = buscar_vagas_na_planilha()
    if not vagas:
        print("Nenhuma vaga encontrada para enviar.")
        return

    # Cria a mensagem
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🚀 {len(vagas)} Novas Vagas Capturadas (Adêrencia IA)"
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO

    # Gera o corpo do e-mail em HTML
    corpo_html = gerar_html_email(vagas)
    msg.attach(MIMEText(corpo_html, 'html'))

    try:
        print(f"📤 Conectando ao Gmail e enviando para {EMAIL_DESTINATARIO}...")
        # Conecta ao servidor SMTP do Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # Inicia conexão segura
        server.login(EMAIL_REMETENTE, EMAIL_SENHA_APP) # Faz login com a Senha de App
        server.send_message(msg)
        server.quit()
        print("✅ E-mail enviado com sucesso! Verifique sua caixa de entrada.")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")

if __name__ == "__main__":
    enviar_email()