from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Motor de Vagas IA - Retrospectiva do Projeto', border=False, align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', align='C')

def criar_pdf():
    pdf = PDF()
    pdf.add_page()
    
    # Configuração de fontes
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Data: 07 de Novembro de 2026", ln=True)
    pdf.ln(5)
    
    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 6, "Objetivo: Estruturar uma central de inteligência autônoma para recolocação profissional.\n")
    pdf.ln(5)

    # Dia 1
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(0, 102, 204) # Azul
    pdf.cell(0, 8, "Dia 1 (05/11/2026): A Fundacao e o Cerebro", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 10)
    itens_dia1 = [
        "- Criacao do profile_truth.md (Fonte unica da verdade).",
        "- Integracao com Google Cloud e Sheets.",
        "- Estruturacao da planilha (Vagas_Bruta, Aprovadas, Analise, Dashboard).",
        "- Integracao com Adzuna e analise de IA (Gemini 3.5-Flash).",
        "- Geracao de curriculo ATS e analise de cultura da empresa."
    ]
    for item in itens_dia1:
        pdf.cell(0, 6, item, ln=True)
    pdf.ln(5)

    # Dia 2
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(0, 102, 204)
    pdf.cell(0, 8, "Dia 2 (06/11/2026): A Nuvem e a Seguranca", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 10)
    itens_dia2 = [
        "- Configuracao do GitHub Actions (Cronjob 08:00 e 15:00).",
        "- Seguranca: Uso de Secrets e remocao de arquivos sensiveis do Git.",
        "- Instalacao do Pandoc e LaTeX para exportacao."
    ]
    for item in itens_dia2:
        pdf.cell(0, 6, item, ln=True)
    pdf.ln(5)

    # Dia 3
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(0, 102, 204)
    pdf.cell(0, 8, "Dia 3 (07/11/2026): A Escala e a Produtividade", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 10)
    itens_dia3 = [
        "- Integracao com LinkedIn (via Apify).",
        "- Implementacao de Buscas Booleanas (config_busca.json).",
        "- Filtro de Score >= 90 para gerar curriculos.",
        "- Envio de e-mail diario com as vagas.",
        "- Exportacao automatica de PDF e DOCX.",
        "- Criacao do pipeline.py e tratamento de cota da API."
    ]
    for item in itens_dia3:
        pdf.cell(0, 6, item, ln=True)
    pdf.ln(5)

    # Conclusao
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(0, 153, 51) # Verde
    pdf.cell(0, 8, "Status: Todos os 5 objetivos iniciais foram concluidos!", ln=True)
    
    # Salva o PDF
    caminho_pdf = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "Apresentacao_Motor_Vagas.pdf"))
    pdf.output(caminho_pdf)
    print(f"✅ Apresentação gerada com sucesso em: {caminho_pdf}")

if __name__ == "__main__":
    criar_pdf()