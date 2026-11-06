import os
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from gspread_formatting import (
    DataValidationRule, 
    BooleanCondition, 
    set_data_validation_for_cell_range,
    CellFormat,
    TextFormat,
    Color,
    format_cell_range,
    NumberFormat,
    set_column_width
)

# Carrega as variáveis de ambiente
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CRED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))
SPREADSHEET_ID = "1rssICgKVOgKfm2Fg8LIYurmz5h2ZVyxF1g79XryrGjk"

def main():
    print("📊 Iniciando configuração do Dashboard e Controles...")
    
    creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    planilha = client.open_by_key(SPREADSHEET_ID)
    
    aba_dashboard = planilha.worksheet("Dashboard")
    aba_aprovadas = planilha.worksheet("Vagas_Aprovadas")
    
    # 1. CRIANDO OS MENUS SUSPENSOS (DROPDOWNS) NA COLUNA STATUS
    print("🔧 Criando menus suspensos na coluna Status...")
    opcoes_status = ['Aprovada', 'Currículo Gerado', 'Candidatado', 'Entrevista', 'Oferta', 'Rejeitado', 'Ghosted']
    
    regra_validacao = DataValidationRule(
        BooleanCondition(
            type='ONE_OF_LIST',
            values=opcoes_status
        ),
        showCustomUi=True
    )
    set_data_validation_for_cell_range(aba_aprovadas, 'M2:M1000', regra_validacao)
    
    # 2. CONSTRUINDO AS MÉTRICAS NO DASHBOARD
    print("📈 Construindo as métricas do Dashboard...")
    
    # Limpa o dashboard antes de preencher
    aba_dashboard.clear()
    
    # Cabeçalhos
    cabecalhos = [["Métrica", "Valor"]]
    aba_dashboard.update(values=cabecalhos, range_name="A1:B1")
    
    # Fórmulas (Usando ponto e vírgula ';' por causa do locale pt-BR)
    metricas = [
        ["Total de Vagas Coletadas", "=COUNTA(Vagas_Bruta!A2:A)"],
        ["Total de Vagas Aprovadas (Score >= 70)", "=COUNTA(Vagas_Aprovadas!A2:A)"],
        ["Candidaturas Realizadas (Aplicadas)", "=COUNTIF(Vagas_Aprovadas!M2:M; \"Candidatado\") + COUNTIF(Vagas_Aprovadas!M2:M; \"Entrevista\") + COUNTIF(Vagas_Aprovadas!M2:M; \"Oferta\") + COUNTIF(Vagas_Aprovadas!M2:M; \"Rejeitado\") + COUNTIF(Vagas_Aprovadas!M2:M; \"Ghosted\")"],
        ["Score Médio (Aprovadas)", "=IFERROR(AVERAGE(Vagas_Aprovadas!J2:J); 0)"],
        ["Total de Entrevistas", "=COUNTIF(Vagas_Aprovadas!M2:M; \"Entrevista\")"],
        ["Taxa de Conversão (Entrevista/Candidatura)", "=IFERROR(COUNTIF(Vagas_Aprovadas!M2:M; \"Entrevista\") / COUNTIF(Vagas_Aprovadas!M2:M; \"Candidatado\"); 0)"]
    ]
    
    # Envia as fórmulas com USER_ENTERED
    aba_dashboard.update(values=metricas, range_name="A2", value_input_option="USER_ENTERED")
    
    # 3. FORMATAÇÃO VISUAL DO DASHBOARD
    print("🎨 Formatando o visual...")
    formato_cabecalho = CellFormat(textFormat=TextFormat(bold=True, fontSize=12), backgroundColor=Color(0.8, 0.9, 1.0))
    format_cell_range(aba_dashboard, 'A1:B1', formato_cabecalho)
    
    # Formata a coluna de Taxa de Conversão como porcentagem e o Score como número
    formato_porcentagem = CellFormat(numberFormat=NumberFormat(type='PERCENT', pattern='0.00%'))
    format_cell_range(aba_dashboard, 'B7', formato_porcentagem)
    
    formato_numero = CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='0.0'))
    format_cell_range(aba_dashboard, 'B5', formato_numero)
    
    # Ajusta a largura da coluna A
    set_column_width(aba_dashboard, 'A', 250)
    
    print("✅ Dashboard e Controles configurados com sucesso!")
    print("👉 As fórmulas agora devem mostrar os números calculados.")

if __name__ == "__main__":
    main()