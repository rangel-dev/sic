"""
Seed de dados FAKE no history.db local — só para desenvolvimento/prototipagem
do gráfico "Erros × Acertos por Módulo" da Home (Tarefa 7).

Seguro por construção: escreve apenas no history.db local desta máquina, que
está no .gitignore e nunca entra em commit nem nos builds gerados a partir da
main (PyInstaller/Inno não empacotam nem o banco nem a pasta scripts/).
NUNCA aponte telemetria para a pasta real do Drive ao testar com dados fake.

Uso (na raiz do repo):
    .venv\\Scripts\\python.exe scripts\\dev_seed_history.py               # insere 60 entradas
    .venv\\Scripts\\python.exe scripts\\dev_seed_history.py -n 200        # insere 200
    .venv\\Scripts\\python.exe scripts\\dev_seed_history.py --wipe        # limpa TUDO antes
    .venv\\Scripts\\python.exe scripts\\dev_seed_history.py --clean-fake  # remove só as fake
"""
import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.history_engine import HistoryEngine  # noqa: E402

# (módulo, marca, gerador de contagens) — espelha a semântica real de cada
# call site (ver plano da Tarefa 7). Volumetria fica de fora (módulo ocultado).
_MODULES = [
    ("Auditor", ["Natura / Avon / Minha Loja", "Natura", "Avon"]),
    ("Exportador", ["natura-br-storefront-catalog", "Natura", "Avon"]),
    ("Cupons", ["CUPOM10", "FRETEGRATIS", "BEMVINDA"]),
    ("Cadastro/Pontuação", ["NATBRA"]),
    ("Cadastro/Gestor GCP", ["NATBRA"]),
    ("Menus CB", ["Natura / Avon / CB"]),
]


# Tipos de erro fake por módulo — mesmos rótulos que os call sites reais
# gravam na coluna breakdown (Tarefa 8), pro drill-down ficar demonstrável.
_BREAKDOWN_TYPES = {
    "Auditor": [
        "💰 Divergência de Preço", "📋 Visibilidade em Listas",
        "🚨 Margem de Segurança", "❌ Preço Ausente (DE/POR)",
        "🏷️ Categoria Primária", "🔇 Produto Indisponível",
    ],
    "Cupons": [
        "🗑️ Deletados (caractere inválido)", "🔤 Corrigidos p/ maiúsculas",
        "👥 Duplicatas ignoradas",
    ],
    "Cadastro/Pontuação": ["❓ Não localizados (exceções)"],
    "Cadastro/Gestor GCP": [
        "📆 Fora da janela de ciclo", "❓ Não encontrado no GCP",
    ],
    "Menus CB": ["Faltante no CB", "Inativo no CB", "Oculto no Menu"],
    # Exportador: sem breakdown (não há erro por item), como no app real.
}


def _split_breakdown(module: str, erro: int):
    """Distribui `erro` entre os tipos fake do módulo (None se não houver)."""
    types = _BREAKDOWN_TYPES.get(module)
    if not types or erro <= 0:
        return None
    chosen = random.sample(types, k=min(len(types), random.randint(1, 3)))
    breakdown = {}
    remaining = erro
    for i, label in enumerate(chosen):
        part = remaining if i == len(chosen) - 1 else random.randint(0, remaining)
        if part > 0:
            breakdown[label] = part
        remaining -= part
    return breakdown or None


def _fake_entry(module: str, age_days: float) -> dict:
    """`age_days`: há quanto tempo essa entrada fake "aconteceu". Entradas
    mais antigas têm taxa de erro um pouco maior — dá uma narrativa de
    melhoria contínua, útil pra demonstrar o comparativo de período
    (Tarefa 9) sem depender só da sorte do random."""
    roll = random.random()
    if roll < 0.08:  # ~8% falha de execução
        return dict(
            action="Falha na execução: [FAKE] erro simulado para testes.",
            status="falha", ok_count=None, error_count=None, total=None,
            breakdown=None,
        )

    age_factor = 1.0 + min(age_days, 180) / 180 * 0.9
    total = random.randint(50, 6000)
    base_rate = random.uniform(0.0, 1 / 20)
    erro = min(total, int(total * base_rate * age_factor))
    ok = total - erro
    if module == "Menus CB":  # sem contagem de acertos (como no app real)
        erro = int(random.randint(0, 45) * age_factor)
        return dict(
            action=f"[FAKE] Validação concluída: {erro} divergências detectadas.",
            status="ok", ok_count=None, error_count=erro, total=None,
            breakdown=_split_breakdown(module, erro),
        )
    return dict(
        action=f"[FAKE] Operação concluída: {total} itens, {erro} erros.",
        status="ok", ok_count=ok, error_count=erro, total=total,
        breakdown=_split_breakdown(module, erro),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", type=int, default=60, help="quantidade de entradas")
    parser.add_argument("--wipe", action="store_true",
                        help="limpa TODO o histórico local antes de inserir")
    parser.add_argument("--clean-fake", action="store_true",
                        help="remove só as entradas [FAKE] e sai, preservando o histórico real")
    args = parser.parse_args()

    if args.clean_fake:
        HistoryEngine.init_db()
        with HistoryEngine._get_connection() as conn:
            cur = conn.execute("DELETE FROM history WHERE action LIKE '%[FAKE]%'")
            conn.commit()
            print(f"{cur.rowcount} entradas [FAKE] removidas; histórico real preservado.")
        return

    if args.wipe:
        HistoryEngine.clear_history()
        print("Histórico local limpo.")

    HistoryEngine.init_db()

    # INSERT direto no SQLite — de propósito NÃO usa add_entry(): add_entry
    # também dispara telemetry.write_event(), e se a pasta do Drive estivesse
    # configurada nesta máquina o dado fake vazaria pro dashboard da equipe.
    now = datetime.now()
    with HistoryEngine._get_connection() as conn:
        for _ in range(args.n):
            module, brands = random.choice(_MODULES)
            brand = random.choice(brands)
            # 0-190 dias: cobre janela atual + anterior mesmo no período de
            # 90 dias do seletor da Home (Tarefa 9).
            age_days = random.uniform(0, 190)
            when = now - timedelta(days=age_days)
            entry = _fake_entry(module, age_days)
            breakdown_json = (
                json.dumps(entry["breakdown"], ensure_ascii=False)
                if entry["breakdown"] else None
            )
            conn.execute(
                "INSERT INTO history (timestamp, module, brand, action, details, "
                "status, ok_count, error_count, total, breakdown) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (when.isoformat(), module, brand, entry["action"], "",
                 entry["status"], entry["ok_count"], entry["error_count"],
                 entry["total"], breakdown_json),
            )
        conn.commit()

    print(f"{args.n} entradas FAKE inseridas no history.db local "
          f"(gitignored — nunca entram em build).")


if __name__ == "__main__":
    main()
