import subprocess
import time
import os

# Lista de scripts na ordem exata de execução
scripts = [
    "buscar_vagas.py",
    "analisar_vagas.py",
    "gerar_curriculo.py",
    "analisar_empresa.py",
    "configurar_dashboard.py"
]

def rodar_pipeline():
    print("🚀 INICIANDO O MOTOR DE VAGAS (PIPELINE COMPLETO)\n")
    diretorio_scripts = os.path.dirname(os.path.abspath(__file__))

    for script in scripts:
        print(f"{'='*50}")
        print(f"▶️ Executando: {script}")
        print(f"{'='*50}")
        
        caminho_script = os.path.join(diretorio_scripts, script)
        
        try:
            # Roda o script e espera ele terminar
            subprocess.run(["python", caminho_script], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao executar o script {script}. O pipeline foi pausado.")
            print(f"Detalhes do erro: {e}")
            break
            
        # Pausa de 3 segundos entre os scripts para não sobrecarregar as APIs
        time.sleep(3)
        print("\n")

    print("🎉 PIPELINE FINALIZADO COM SUCESSO!")

if __name__ == "__main__":
    rodar_pipeline()