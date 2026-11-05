import re
import json
import sys
from pathlib import Path

def parse_profile(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    
    # --- 1. Dados básicos ---
    name_match = re.search(r"\*\*Nome:\*\*\s*(.+)", text)
    name = name_match.group(1).strip() if name_match else "Fabiano Tavares"
    
    obj_match = re.search(r"\*\*Objetivo profissional \(resumo\):\*\*\s*(.+)", text)
    label = obj_match.group(1).strip() if obj_match else ""
    
    # Resumo (pega o bloco entre "## 2." e "## 3.")
    summary_match = re.search(r"## 2\. Resumo profissional.*?\n\n(.*?)\n\n## 3\.", text, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else ""
    # Limpa quebras de linha extras
    summary = re.sub(r"\n+", " ", summary).strip()
    
    # --- 2. Experiências ---
    work = []
    # Divide pelas seções de experiência (### 3.x)
    exp_blocks = re.split(r"\n### 3\.\d+\s+", text)[1:]
    for block in exp_blocks:
        lines = block.strip().split("\n")
        company = lines[0].strip()
        cargo_match = re.search(r"\*\*Cargo:\*\*\s*(.+)", block)
        position = cargo_match.group(1).strip() if cargo_match else ""
        periodo_match = re.search(r"\*\*Período:\*\*\s*(.+)", block)
        period_str = periodo_match.group(1).strip() if periodo_match else ""
        
        # Converte período "01/2025 – atual" para "2025-01"
        start_date = ""
        end_date = ""
        if period_str:
            parts = re.split(r"–|-", period_str)
            if len(parts) >= 1:
                start_raw = parts[0].strip()
                if "/" in start_raw:
                    m, y = start_raw.split("/")
                    start_date = f"{y}-{m.zfill(2)}"
            if len(parts) >= 2:
                end_raw = parts[1].strip()
                if "/" in end_raw:
                    m, y = end_raw.split("/")
                    end_date = f"{y}-{m.zfill(2)}"
                elif end_raw.lower() == "atual":
                    end_date = "atual"
        
        # Extrai highlights (linhas que começam com "-" ou "  -" na seção de atividades)
        highlights = []
        # Pega tudo após "Atividades" ou "Atividades e resultados:"
        act_match = re.search(r"\*\*Atividades.*?:\*\*\s*\n(.*?)(?=\n### |\Z)", block, re.DOTALL)
        if act_match:
            act_text = act_match.group(1)
            for line in act_text.split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    highlights.append(line[2:].strip())
        
        work.append({
            "name": company,
            "position": position,
            "location": "",
            "startDate": start_date,
            "endDate": end_date,
            "highlights": highlights
        })
    
    # --- 3. Formação ---
    education = []
    edu_match = re.search(r"## 4\. Formação acadêmica\n\n(.*?)\n\n## 5\.", text, re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(1)
        # Exemplo: "- **Graduação em Telecomunicações** | Tecnologia | Exatas\n- **Período:** 2005 – 2008\n- **Instituição:** Universidade Cidade de S.Paulo"
        course_match = re.search(r"\*\*(.+?)\*\*", edu_text)
        area = course_match.group(1).strip() if course_match else ""
        inst_match = re.search(r"\*\*Instituição:\*\*\s*(.+)", edu_text)
        institution = inst_match.group(1).strip() if inst_match else ""
        period_match = re.search(r"\*\*Período:\*\*\s*(\d{4})\s*–\s*(\d{4})", edu_text)
        start_year = period_match.group(1) if period_match else ""
        end_year = period_match.group(2) if period_match else ""
        
        education.append({
            "institution": institution,
            "studyType": "Graduação",
            "area": area,
            "startDate": start_year,
            "endDate": end_year
        })
    
    # --- 4. Certificações ---
    certificates = []
    cert_match = re.search(r"## 5\. Certificações e cursos\n\n(.*?)\n\n## 6\.", text, re.DOTALL)
    if cert_match:
        cert_text = cert_match.group(1)
        for line in cert_text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                cert_name = line[2:].strip()
                # Tenta extrair ano e emissor (opcional)
                year_match = re.search(r"\((\d{4})\)", cert_name)
                date = year_match.group(1) if year_match else ""
                certificates.append({
                    "name": cert_name,
                    "issuer": "",
                    "date": date
                })
    
    # --- 5. Idiomas ---
    languages = []
    lang_match = re.search(r"## 6\. Idiomas\n\n(.*?)\n\n## 7\.", text, re.DOTALL)
    if lang_match:
        lang_text = lang_match.group(1)
        for line in lang_text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                lang_line = line[2:].strip()
                if ":" in lang_line:
                    lang, fluency = lang_line.split(":", 1)
                    languages.append({
                        "language": lang.strip(),
                        "fluency": fluency.strip()
                    })
    
    # --- 6. Skills (ferramentas) ---
    skills = []
    skills_match = re.search(r"## 7\. CRM e ferramentas\n\n(.*?)\n\n## 8\.", text, re.DOTALL)
    if skills_match:
        skills_text = skills_match.group(1)
        keywords = []
        for line in skills_text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                keywords.append(line[2:].strip())
        if keywords:
            skills.append({
                "name": "Ferramentas e CRM",
                "keywords": keywords
            })
    
    # --- Monta o JSON final ---
    resume = {
        "basics": {
            "name": name,
            "label": label,
            "email": "",
            "phone": "",
            "url": "",
            "summary": summary,
            "location": {
                "city": "",
                "region": "",
                "countryCode": "BR"
            },
            "profiles": [
                {
                    "network": "LinkedIn",
                    "username": "",
                    "url": ""
                }
            ]
        },
        "work": work,
        "education": education,
        "skills": skills,
        "certificates": certificates,
        "languages": languages,
        "projects": []
    }
    
    return resume

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python generate_resume_json.py <caminho_profile_truth.md> <caminho_saida_resume.json>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    if not input_path.exists():
        print(f"Arquivo não encontrado: {input_path}")
        sys.exit(1)
    
    resume_data = parse_profile(input_path)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(resume_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ resume.json gerado com sucesso em: {output_path}")
