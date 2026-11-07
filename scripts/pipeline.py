import subprocess
import time
import os
import sys

# Lista de scripts na ordem exata de execução do nosso sistema
scripts = [
    "buscar_vagas.py",       # 1. Busca booleanas no LinkedIn e Adzuna
    "analisar_vagas.py",     # 2. Traduz e dá nota de aderência com Gemini
    "gerar_curriculo.py",    # 3. Gera .md apenas para score >= 90
    "analisar_empresa.py",   # 4. Pesquisa cultura da empresa
    "exportar_curriculo.py", # 5. Converte os .md em PDF e DOCX
    "notificar_email.py",    # 6. Envia o resumo diário por e-mail
    "configurar_dashboard.py" # 7. Atualiza os gráficos da planilha
]

def rodar_pipeline():
    print("🚀 INICIANDO O MOTOR DE VAGAS (PIPELINE COMPLETO)\n")
    diretorio_scripts = os.path.dirname(os.path.abspath(__file__))

    for script in scripts:
        print(f"{'='*60}")
        print(f"▶️ Executando: {script}")
        print(f"{'='*60}")
        
        caminho_script = os.path.join(diretorio_scripts, script)
        
        try:
            # Usa sys.executable para garantir o caminho correto do Python
            subprocess.run([sys.executable, caminho_script], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao executar o script {script}.")
            print(f"O pipeline foi pausado para evitar erros em cascata.")
            break
            
        # Pausa entre os scripts para não sobrecarregar as APIs
        time.sleep(3)
        print("\n")

    print("🎉 PIPELINE FINALIZADO!")

if __name__ == "__main__":
    rodar_pipeline()