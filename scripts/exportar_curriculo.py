import os
import subprocess
import glob

# Caminhos das pastas
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CURRICULOS_DIR = os.path.join(BASE_DIR, "output", "curriculos")

def converter_curriculos():
    print("📄 Iniciando conversão de currículos para PDF e DOCX...")
    
    # Procura todos os arquivos .md na pasta de currículos
    arquivos_md = glob.glob(os.path.join(CURRICULOS_DIR, "*.md"))
    
    if not arquivos_md:
        print("⚠️ Nenhum arquivo .md encontrado na pasta output/curriculos.")
        return

    sucesso = 0
    for arquivo_md in arquivos_md:
        nome_base = os.path.splitext(arquivo_md)[0]
        arquivo_pdf = f"{nome_base}.pdf"
        arquivo_docx = f"{nome_base}.docx"

        # Pula se já existir o PDF e o DOCX (para não refazer toda vez)
        if os.path.exists(arquivo_pdf) and os.path.exists(arquivo_docx):
            print(f"⏩ Arquivos já existem para {os.path.basename(arquivo_md)}. Pulando...")
            continue

        print(f"🔄 Convertendo: {os.path.basename(arquivo_md)}...")

        try:
            # Converte para PDF (A CORREÇÃO ESTÁ AQUI: trocamos Arial por DejaVu Sans)
            subprocess.run([
                "pandoc", arquivo_md, "-o", arquivo_pdf,
                "--pdf-engine=xelatex",
                "-V", "geometry:margin=2cm",
                "-V", "mainfont=DejaVu Sans"
            ], check=True)
            
            # Converte para DOCX (Word / Google Docs)
            subprocess.run([
                "pandoc", arquivo_md, "-o", arquivo_docx
            ], check=True)

            print(f"   ✅ Gerado: {os.path.basename(arquivo_pdf)} e {os.path.basename(arquivo_docx)}")
            sucesso += 1
            
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Erro ao converter {os.path.basename(arquivo_md)}: {e}")

    if sucesso > 0:
        print(f"\n🎉 Conversão finalizada! {sucesso} currículos foram exportados.")
    else:
        print("\nNenhum arquivo novo precisou ser convertido.")

if __name__ == "__main__":
    converter_curriculos()