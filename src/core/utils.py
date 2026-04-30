from pathlib import Path

def get_unique_path(path: str) -> str:
    \"\"\"
    Retorna um caminho único adicionando (1), (2), etc. se o arquivo já existir.
    Evita erros de permissão quando o arquivo está aberto por outro programa.
    \"\"\"
    p = Path(path)
    if not p.exists():
        return path
    
    base = p.parent / p.stem
    ext = p.suffix
    counter = 1
    while True:
        new_path = f"{base} ({counter}){ext}"
        if not Path(new_path).exists():
            return new_path
        counter += 1
