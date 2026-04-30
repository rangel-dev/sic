from pathlib import Path


def get_unique_path(path: str) -> str:
    """Se o arquivo já existe, retorna um novo caminho com sufixo (1), (2), …"""
    p = Path(path)
    if not p.exists():
        return path
    stem, suffix, parent = p.stem, p.suffix, p.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return str(candidate)
        counter += 1
