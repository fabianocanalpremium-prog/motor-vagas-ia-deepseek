import os
import time
import smtplib
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA_APP = os.getenv("EMAIL_SENHA_APP")
EMAIL_DESTINATARIO = EMAIL_REMETENTE

# Termo único e específico
TERMO_BUSCA = 'Segurança Eletrônica'

def buscar_posts_apify(termo):
    if not APIFY_TOKEN:
        print("❌ APIFY_TOKEN não configurado.")
        return []

    client = ApifyClient(APIFY_TOKEN)
    
    # Alterando a ordenação para 'recent' (Mais recentes)
    run_input = {
        "searchQueries": [termo],
        "maxPosts": 10,
        "postedLimit": "month",
        "sortBy": "recent",
        "location": "Brazil",
        "sort_type": "recent" # Alguns atores usam sort_type
    }

    print(f"🔍 Buscando posts mais recentes para: {termo} (Brasil)...")
    try:
        run = client.actor("apimaestro/linkedin-posts-search-scraper-no-cookies").call(run_input=run_input)
        posts = []
        
        if run:
            dataset_id = run.default_dataset_id
            if dataset_id:
                for idx, item in enumerate(client.dataset(dataset_id).iterate_items()):
                    if len(posts) >= 10:
                        break
                    
                    if idx == 0:
                        print(f"🔑 Chaves retornadas pelo Apify: {list(item.keys())}")

                    # CORREÇÃO: Extraindo os dados com os nomes exatos que o log revelou
                    url_post = item.get("post_url", "")
                    texto = item.get("text", "")
                    data_post = item.get("posted_at", "Data não informada")
                    
                    # Tratamento do autor (pode vir como dict ou string)
                    autor_info = item.get("author", {})
                    if isinstance(autor_info, dict):
                        autor = autor_info.get("name", "Autor Desconhecido")
                        headline = autor_info.get("headline", "")
                    else:
                        autor = str(autor_info) if autor_info else "Autor Desconhecido"
                        headline = ""

                    posts.append({
                        "autor": autor,
                        "titulo_autor": headline,
                        "texto": texto[:300] + "...",
                        "url": url_post,
                        "data": data_post
                    })
        
        print(f"   ✅ Encontrados {len(posts)} posts válidos.")
        return posts
    except Exception as e:
        print(f"⚠️ Erro ao buscar no Apify: {e}")
        return []

def gerar_html_email(posts):
    html = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f7f6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; }
            h2 { color: #0056b3; border-bottom: 2px solid #0056b3; padding-bottom: 10px; }
            .post { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px; background: #fafafa; }
            .autor { font-weight: bold; color: #000; font-size: 16px; }
            .headline { font-size: 12px; color: #666; margin-bottom: 10px; }
            .texto { font-size: 14px; line-height: 1.5; color: #333; margin-bottom: 10px; }
            .link { display: inline-block; background-color: #0056b3; color: #fff; padding: 8px 15px; text-decoration: none; border-radius: 5px; font-size: 12px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📡 Radar de Oportunidades: Segurança Eletrônica</h2>
            <p>Olá, Fabiano! Aqui estão as publicações <b>mais recentes</b> dos últimos 30 dias (Brasil) que podem indicar oportunidades de negócios ou vagas ocultas:</p>
    """

    if posts:
        for p in posts:
            if p['url']:
                botao_link = f'<a href="{p["url"]}" class="link">Ver Publicação no LinkedIn</a>'
            else:
                botao_link = '<span style="color: #999; font-size: 12px;">Link não disponível na API</span>'

            html += f"""
            <div class="post">
                <div class="autor">{p['autor']}</div>
                <div class="headline">{p['titulo_autor']}</div>
                <div class="texto">"{p['texto']}"</div>
                <div style="font-size: 12px; color: #999; margin-bottom: 10px;">Postado em: {p['data']}</div>
                {botao_link}
            </div>
            """
    else:
        html += "<p>Nenhuma publicação nova encontrada nos últimos 30 dias para este termo no Brasil.</p>"

    html += """
            <p style="font-size: 12px; color: #888; text-align: center; margin-top: 20px;">Gerado automaticamente pelo seu Motor de Vagas IA.</p>
        </div>
    </body>
    </html>
    """
    return html

def enviar_email(html_content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📡 Radar LinkedIn: Segurança Eletrônica ({datetime.now().strftime('%d/%m/%Y')})"
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO
    msg.attach(MIMEText(html_content, 'html'))

    try:
        print("📤 Enviando e-mail...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
        server.send_message(msg)
        server.quit()
        print("✅ E-mail enviado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")

def main():
    print("🚀 Iniciando Monitoramento de Posts do LinkedIn...")
    
    posts = buscar_posts_apify(TERMO_BUSCA)
    html_final = gerar_html_email(posts)
    enviar_email(html_final)
    
    print("🎉 Processo finalizado!")

if __name__ == "__main__":
    main()