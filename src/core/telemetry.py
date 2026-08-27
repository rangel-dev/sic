"""
Telemetria de equipe (Tarefa 3) — meio-termo simples antes de uma integração
real (Databricks, futuro distante). `history.db` é local por instalação;
aqui cada instalação grava, adicionalmente, um arquivo próprio numa pasta do
Google Drive compartilhada pela equipe, pra dar visão agregada na Home.

Decisões (não reabrir sem alinhar de novo):
- Sem SQLite compartilhado no Drive — sincronização por eventual
  consistência corrompe/gera "cópias em conflito" com escrita concorrente
  num único arquivo .db.
- Um arquivo por instalação, nunca compartilhado entre instalações — zero
  conflito de escrita, mesmo com o Drive sincronizando de forma assíncrona.
- Identificador anônimo por instalação (UUID gerado uma vez, não o usuário
  do Windows) — decisão deliberada de privacidade/LGPD: os KPIs (operações,
  marcas ativas, módulos ativos) são agregados e não precisam saber quem fez
  a operação.
- Rotação mensal dos arquivos ({install_id}_{yyyy-mm}.jsonl) — evita
  crescimento indefinido e mantém a leitura de "período recente" rápida.
- Formato JSONL (uma linha JSON por evento, só append) — reduz ainda mais
  risco de conflito de sincronização comparado a reescrever um arquivo
  inteiro.

Tudo aqui é melhor-esforço: nunca deve lançar exceção nem travar o fluxo
normal do app (mesmo padrão defensivo do teste de webhook em
view_settings.py).
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings

_SETTINGS_ORG = "SIC"
_SETTINGS_APP = "SIC_Suite"
_INSTALL_ID_KEY = "install_id"
_SHARED_FOLDER_KEY = "drive_telemetry_path"


def _settings() -> QSettings:
    return QSettings(_SETTINGS_ORG, _SETTINGS_APP)


def get_install_id() -> str:
    """Lê o UUID anônimo desta instalação, gerando e persistindo um na
    primeira chamada. Nunca identifica a pessoa/usuário do Windows."""
    settings = _settings()
    install_id = settings.value(_INSTALL_ID_KEY, "")
    if not install_id:
        install_id = uuid.uuid4().hex
        settings.setValue(_INSTALL_ID_KEY, install_id)
    return install_id


def get_shared_folder_path() -> str:
    """Caminho da pasta compartilhada do Drive configurado em
    Configurações. String vazia se não configurado."""
    return _settings().value(_SHARED_FOLDER_KEY, "") or ""


def set_shared_folder_path(path: str) -> None:
    _settings().setValue(_SHARED_FOLDER_KEY, path or "")


def _event_file_path(folder: str, install_id: str, when: datetime) -> str:
    return str(Path(folder) / f"{install_id}_{when.strftime('%Y-%m')}.jsonl")


def write_event(
    module: str,
    brand: str,
    action: str,
    *,
    status: str = "ok",
    ok_count: Optional[int] = None,
    error_count: Optional[int] = None,
    total: Optional[int] = None,
    breakdown: Optional[dict] = None,
) -> None:
    """Melhor-esforço: grava uma linha JSON no arquivo do mês corrente desta
    instalação, na pasta compartilhada configurada. Não faz nada
    (silenciosamente) se a pasta não estiver configurada ou não existir —
    nunca deve quebrar o fluxo normal do app (mesmo padrão do teste de
    webhook em view_settings.py).

    Contagens (Tarefa 7): campos opcionais e omitidos quando None — JSONL é
    schemaless, então leitores antigos toleram linhas novas e vice-versa."""
    try:
        folder = get_shared_folder_path()
        if not folder or not os.path.isdir(folder):
            return

        now = datetime.now()
        path = _event_file_path(folder, get_install_id(), now)
        event: dict = {
            "ts": now.isoformat(),
            "module": module,
            "brand": brand,
            "action": action,
            "status": status,
        }
        for key, value in (
            ("ok_count", ok_count), ("error_count", error_count),
            ("total", total), ("breakdown", breakdown),
        ):
            if value is not None:
                event[key] = value
        line = json.dumps(event, ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _months_back(months_back: int) -> list[str]:
    """Lista de sufixos 'yyyy-mm' do mês atual + `months_back` anteriores."""
    suffixes = []
    now = datetime.now().replace(day=1)
    cursor = now
    for _ in range(months_back + 1):
        suffixes.append(cursor.strftime("%Y-%m"))
        # volta pro mês anterior sem depender de dateutil
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    return suffixes


def read_team_events(months_back: int = 2) -> list[dict]:
    """Lê todos os *.jsonl (de qualquer instalação) da pasta compartilhada
    cujo sufixo bate com o mês atual + `months_back` anteriores. Tolerante a
    linha corrompida (ignora, não derruba a leitura). Devolve [] se a pasta
    não existir/não estiver acessível (Drive offline, não configurado etc.)."""
    folder = get_shared_folder_path()
    if not folder or not os.path.isdir(folder):
        return []

    wanted_suffixes = set(_months_back(months_back))
    events: list[dict] = []
    try:
        for name in os.listdir(folder):
            if not name.endswith(".jsonl"):
                continue
            stem = name[: -len(".jsonl")]
            suffix = stem.rsplit("_", 1)[-1] if "_" in stem else ""
            if suffix not in wanted_suffixes:
                continue
            file_path = os.path.join(folder, name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            events.append(json.loads(line))
                        except (json.JSONDecodeError, ValueError):
                            continue
            except OSError:
                continue
    except OSError:
        return []
    return events


def normalize_brands(raw) -> set:
    """Extrai as marcas REAIS de um valor da coluna `brand` do histórico.

    A coluna é usada de forma inconsistente pelas telas (marca real,
    catalog-id, id de cupom, "NATBRA", "N/A"...), então contar valores
    distintos infla o KPI "Marcas Ativas" com strings que não são marca.
    Aqui só Natura, Avon e Minha Loja (CB) contam; o resto vira vazio."""
    if not raw:
        return set()
    s = str(raw).lower()
    brands = set()
    if "natura" in s or "natbra" in s:
        brands.add("Natura")
    if "avon" in s or "avnbra" in s:
        brands.add("Avon")
    if "minha loja" in s or "cbbrazil" in s or re.search(r"\bcb\b", s):
        brands.add("Minha Loja")
    return brands


def compute_team_kpis(events: list[dict]) -> dict:
    """{"operations": total, "brands_active": marcas distintas,
    "modules_active_7d": módulos distintos com evento nos últimos 7 dias}."""
    brands: set = set()
    for e in events:
        brands |= normalize_brands(e.get("brand"))

    cutoff = datetime.now() - timedelta(days=7)
    modules_7d = set()
    for e in events:
        ts = e.get("ts")
        module = e.get("module")
        if not ts or not module:
            continue
        try:
            when = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if when >= cutoff:
            modules_7d.add(module)

    return {
        "operations": len(events),
        "brands_active": len(brands),
        "modules_active_7d": len(modules_7d),
    }
