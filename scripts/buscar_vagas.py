import os
import requests
import datetime
import uuid
import json
import gspread
from dotenv import load_dotenv
from apify_client import ApifyClient
from google.oauth2.service_account import Credentials

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações de APIs
APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Configurações do Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CRED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))
SPREADSHEET_ID = "1rssICgKVOgKfm2Fg8LIYurmz5h2ZVyxF1g79XryrGjk"

def carregar_configuracoes():
    """Lê o arquivo JSON com as buscas booleanas"""
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config_busca.json"))
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erro ao ler config_busca.json: {e}")
        return {"localizacao_padrao": "Sao Paulo", "termos_busca": ["Sales Manager"]}

def conectar_sheets():
    creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)

def formatar_data_hoje():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def buscar_adzuna(termo, localizacao):
    vagas = []
    if not APP_ID or not APP_KEY: return vagas
    url = f"https://api.adzuna.com/v1/api/jobs/br/search/1"
    params = {
        "app_id": APP_ID, "app_key": APP_KEY, "results_per_page": 5, 
        "what": termo, "where": localizacao
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        for vaga in response.json().get("results", []):
            vagas.append({
                "titulo": vaga.get("title"),
                "empresa": vaga.get("company", {}).get("display_name", "Não informada"),
                "local": vaga.get("location", {}).get("display_name", "Não informado"),
                "salario": "Não informado",
                "fonte": "Adzuna",
                "url": vaga.get("redirect_url"),
                "descricao": vaga.get("description", "")
            })
    except Exception as e:
        print(f"⚠️ Erro Adzuna ({termo[:20]}...): {e}")
    return vagas

def buscar_linkedin(termo, localizacao):
    vagas = []
    if not APIFY_TOKEN:
        print("⚠️ APIFY_TOKEN não configurado. Pulando LinkedIn.")
        return vagas

    client = ApifyClient(APIFY_TOKEN)
    run_input = {
        "keywords": termo,
        "location": localizacao,
        "maxItems": 5,
        "datePosted": "7"
    }
    try:
        run = client.actor("harshmaur/linkedin-jobs-scraper").call(run_input=run_input)
        if run:
            dataset_id = run.default_dataset_id
            if dataset_id:
                for item in client.dataset(dataset_id).iterate_items():
                    # CORREÇÃO: Tenta pegar o link em vários campos possíveis que o Apify retorna
                    url_vaga = item.get("jobUrl") or item.get("url") or item.get("link") or ""
                    
                    vagas.append({
                        "titulo": item.get("title", ""),
                        "empresa": item.get("companyName", "Não informada"),
                        "local": item.get("location", "Não informado"),
                        "salario": "Não informado",
                        "fonte": "LinkedIn",
                        "url": url_vaga,
                        "descricao": item.get("descriptionText", item.get("description", ""))
                    })
    except Exception as e:
        print(f"⚠️ Erro LinkedIn ({termo[:20]}...): {e}")
    return vagas

def main():
    print("🔍 Iniciando busca multi-fonte baseada em BUSCAS BOOLEANAS...")
    
    config = carregar_configuracoes()
    localizacao = config.get("localizacao_padrao", "Sao Paulo")
    termos_busca = config.get("termos_busca", [])

    todas_vagas = []

    for i, termo in enumerate(termos_busca, 1):
        print(f"\n[{i}/{len(termos_busca)}] Buscando: {termo[:50]}...")

        v_adzuna = buscar_adzuna(termo, localizacao)
        print(f"  - Adzuna: {len(v_adzuna)} vagas.")
        todas_vagas.extend(v_adzuna)

        v_linkedin = buscar_linkedin(termo, localizacao)
        print(f"  - LinkedIn: {len(v_linkedin)} vagas.")
        todas_vagas.extend(v_linkedin)

    # Deduplicação: agora ele só remove vagas se o link for vazio, mas mantém a vaga!
    vagas_unicas = {}
    for v in todas_vagas:
        chave = v.get('url') or str(uuid.uuid4()) # Se não tiver link, gera um ID aleatório para não descartar
        vagas_unicas[chave] = v
        
    vagas_finais = list(vagas_unicas.values())

    if not vagas_finais:
        print("Nenhuma vaga encontrada hoje.")
        return

    print(f"\n✅ Total de {len(vagas_finais)} vagas únicas encontradas. Salvando na planilha...")

    try:
        planilha = conectar_sheets()
        aba_bruta = planilha.worksheet("Vagas_Bruta")

        linhas_para_inserir = []
        data_hoje = formatar_data_hoje()

        for v in vagas_finais:
            linhas_para_inserir.append([
                str(uuid.uuid4())[:8], data_hoje, v["titulo"], v["empresa"],
                v["local"], v["salario"], v["fonte"], v["url"],
                v["descricao"], "", "", ""
            ])

        aba_bruta.append_rows(linhas_para_inserir, value_input_option="USER_ENTERED")
        print(f"🎉 {len(linhas_para_inserir)} vagas salvas com sucesso na aba 'Vagas_Bruta'!")

    except Exception as e:
        print(f"❌ Erro ao salvar no Google Sheets: {e}")

if __name__ == "__main__":
    main()