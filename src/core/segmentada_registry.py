"""Registry das Segmentadas — modelo, montagem de ID, status e reconhecimento.

BRD-012, P1: núcleo testável, sem tela. Cobre o modelo do vínculo
aba-da-planilha ↔ tarefa do Runrun.it, a montagem/leitura do `pricebook_id`
(D1: identidade do registro), o cálculo de status por janela online-from/
online-to e a regra de reconhecimento na importação (Etapa 3), incluindo o
armazenamento local (`JsonFileRegistryStore`).

P5 (compartilhamento, revisado em 22-09-2026): em vez de planilha + Apps
Script/OAuth (que esbarrou em política do Workspace — ver BRD, "Revisão da
Etapa 1"), o compartilhamento é uma **pasta do Google Drive sincronizada
localmente** (Google Drive para computador). Do ponto de vista do SIC é só
um caminho de pasta — zero API, zero OAuth. `SyncedFolderRegistryStore`
grava **um arquivo por `pricebook_id`** nela (evita a maior parte dos
conflitos de sincronização do Drive) e `write_xlsx_snapshot` gera, na
mesma pasta, um `.xlsx` só de leitura — abre como planilha direto pelo
Google Drive, sem o SIC precisar falar com a API do Sheets.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Protocol

import openpyxl

_SCHEMA_VERSION = 1

_WS_RE = re.compile(r"\s+")

# D2: ID automático só para Natura e Avon — Minha Loja (CB) segue manual.
_ID_PREFIX: dict[str, str] = {"natura": "NAT-RR", "avon": "AVN-RR"}
_ID_RE = re.compile(r"^(NAT|AVN)-RR(\d+)$")

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


# ── Modelo ───────────────────────────────────────────────────────────────

@dataclass
class SegmentadaRecord:
    pricebook_id: str  # identidade do registro (D1) — upsert age por este campo
    sheet_name: str
    brand: str
    loja: str
    lp_label: Optional[str] = None
    runrun_id: Optional[str] = None
    campaign_name: Optional[str] = None
    online_from: Optional[str] = None
    online_to: Optional[str] = None
    sku_count: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None  # D2: quem registrou o vínculo no SIC
    task_creator: Optional[str] = None  # D2: quem abriu a tarefa no Runrun.it
    ended_at: Optional[str] = None
    source_file: Optional[str] = None


class MatchConfidence(str, Enum):
    EXACT = "exact"
    SHEET_ONLY = "sheet_only"
    AMBIGUOUS = "ambiguous"
    NONE = "none"


@dataclass
class ResolveResult:
    confidence: MatchConfidence
    record: Optional[SegmentadaRecord] = None
    reasons: list[str] = field(default_factory=list)

    @property
    def is_risky(self) -> bool:
        """Banner vermelho (seção 8): sheet_only, ambiguous, ou exact com
        algum motivo (registro expirado, lp_label divergente, >90 dias)."""
        if self.confidence in (MatchConfidence.SHEET_ONLY, MatchConfidence.AMBIGUOUS):
            return True
        return self.confidence == MatchConfidence.EXACT and bool(self.reasons)


# ── Datas ────────────────────────────────────────────────────────────────

def _parse_iso(value: str) -> datetime:
    return datetime.strptime(value, _ISO_FORMAT).replace(tzinfo=timezone.utc)


# ── Funções puras ────────────────────────────────────────────────────────

def normalize_sheet_name(name: str) -> str:
    """upper + strip + colapsa espaços — usada para casar abas entre ciclos,
    já que o nome é reaproveitado (seção 8)."""
    return _WS_RE.sub(" ", (name or "").strip().upper())


def build_pricebook_id(brand: str, runrun_id: str) -> Optional[str]:
    """D2/Etapa 3: monta `NAT-RR{id}` / `AVN-RR{id}`. `None` para qualquer
    marca fora de Natura/Avon (ex.: `ml`) — a loja CB segue manual."""
    prefix = _ID_PREFIX.get(brand)
    if not prefix or not runrun_id:
        return None
    return f"{prefix}{runrun_id}"


def parse_runrun_id(pricebook_id: str) -> Optional[str]:
    """Inverso de `build_pricebook_id` — extrai o número da tarefa de um
    `pricebook_id` já montado, se ele seguir o padrão automático."""
    match = _ID_RE.match((pricebook_id or "").strip().upper())
    return match.group(2) if match else None


def compute_status(record: SegmentadaRecord, now: Optional[datetime] = None) -> str:
    """`encerrada` (P7) > `expirada` > `agendada` > `ativa`. Sem
    `online_from`/`online_to`, o registro é tratado como `ativa` — faltar
    dado não deve virar alarme falso de vencimento."""
    now = now or datetime.now(timezone.utc)
    if record.ended_at:
        return "encerrada"
    end = _parse_iso(record.online_to) if record.online_to else None
    if end and now > end:
        return "expirada"
    start = _parse_iso(record.online_from) if record.online_from else None
    if start and now < start:
        return "agendada"
    return "ativa"


_PAINEL_HIDDEN_STATUSES = frozenset({"expirada", "encerrada"})


def painel_rows(
    records: list[SegmentadaRecord],
    include_expired: bool = False,
    now: Optional[datetime] = None,
) -> list[tuple[SegmentadaRecord, str]]:
    """Linhas do Painel (Etapa 6): cada registro com seu status calculado,
    escondendo por padrão o que já passou, e com o que vence primeiro no
    topo — quem olha o painel quer ver o que exige ação agora. Registro sem
    `online_to` vai para o fim: não dá para dizer quando vence."""
    now = now or datetime.now(timezone.utc)
    rows = [(r, compute_status(r, now)) for r in records]
    if not include_expired:
        rows = [(r, status) for r, status in rows if status not in _PAINEL_HIDDEN_STATUSES]
    rows.sort(key=lambda pair: (pair[0].online_to is None, pair[0].online_to or ""))
    return rows


def resolve(
    sheet_name: str,
    lp_label: Optional[str],
    brand: str,
    loja: str,
    records: list[SegmentadaRecord],
    now: Optional[datetime] = None,
) -> ResolveResult:
    """Regra de reconhecimento da Etapa 3. A `loja` participa do casamento
    (D4): sem ela, a mesma aba virando pricebook na marca e na Minha Loja
    (CB) cairia em `ambiguous` sem explicar o motivo real."""
    now = now or datetime.now(timezone.utc)
    norm_sheet = normalize_sheet_name(sheet_name)
    same_sheet = [r for r in records if normalize_sheet_name(r.sheet_name) == norm_sheet]
    if not same_sheet:
        return ResolveResult(confidence=MatchConfidence.NONE)

    same_context = [r for r in same_sheet if r.brand == brand and r.loja == loja]

    if len(same_context) >= 2:
        return ResolveResult(
            confidence=MatchConfidence.AMBIGUOUS,
            reasons=["múltiplos registros para esta aba, marca e loja"],
        )

    if not same_context:
        if len(same_sheet) == 1:
            return ResolveResult(
                confidence=MatchConfidence.SHEET_ONLY,
                record=same_sheet[0],
                reasons=["aba conhecida, mas registrada para outra marca/loja"],
            )
        return ResolveResult(
            confidence=MatchConfidence.AMBIGUOUS,
            reasons=["múltiplos registros para esta aba, em outras marcas/lojas"],
        )

    record = same_context[0]
    reasons: list[str] = []

    if lp_label and record.lp_label and normalize_sheet_name(lp_label) != normalize_sheet_name(record.lp_label):
        reasons.append("rótulo LP divergente do registro")

    if compute_status(record, now) == "expirada":
        reasons.append("registro expirado")

    if record.updated_at and (now - _parse_iso(record.updated_at)).days > 90:
        reasons.append("registro com mais de 90 dias")

    return ResolveResult(confidence=MatchConfidence.EXACT, record=record, reasons=reasons)


# ── Armazenamento ────────────────────────────────────────────────────────

class RegistryStore(Protocol):
    """Orientado a registro (`upsert` por `pricebook_id`) — nunca uma API
    `save(lista_inteira)`, que reintroduziria a perda de escrita de colega."""

    def load(self) -> list[SegmentadaRecord]: ...
    def upsert(self, record: SegmentadaRecord) -> None: ...
    def mark_ended(self, pricebook_id: str, ended_at: str) -> None: ...
    def delete(self, pricebook_id: str) -> None: ...


class InMemoryRegistryStore:
    """Para teste e para o futuro `CachedRegistry` (P5)."""

    def __init__(self, records: Optional[list[SegmentadaRecord]] = None) -> None:
        self._records: dict[str, SegmentadaRecord] = {r.pricebook_id: r for r in (records or [])}

    def load(self) -> list[SegmentadaRecord]:
        return list(self._records.values())

    def upsert(self, record: SegmentadaRecord) -> None:
        self._records[record.pricebook_id] = record

    def mark_ended(self, pricebook_id: str, ended_at: str) -> None:
        if pricebook_id in self._records:
            self._records[pricebook_id].ended_at = ended_at

    def delete(self, pricebook_id: str) -> None:
        self._records.pop(pricebook_id, None)


class JsonFileRegistryStore:
    """Armazenamento local (Etapa 2), em um arquivo dentro de
    `app_paths.user_data_dir()`. Escrita atômica (`tmp` + `os.replace`);
    JSON corrompido ou de schema desconhecido vira `.bak` e recomeça vazio,
    em vez de derrubar o registro inteiro."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[SegmentadaRecord]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or raw.get("schema_version") != _SCHEMA_VERSION:
                raise ValueError("schema desconhecido")
            return [SegmentadaRecord(**r) for r in raw.get("records", [])]
        except (json.JSONDecodeError, ValueError, TypeError, OSError):
            self._quarantine()
            return []

    def upsert(self, record: SegmentadaRecord) -> None:
        records = [r for r in self.load() if r.pricebook_id != record.pricebook_id]
        records.append(record)
        self._save(records)

    def mark_ended(self, pricebook_id: str, ended_at: str) -> None:
        records = self.load()
        for r in records:
            if r.pricebook_id == pricebook_id:
                r.ended_at = ended_at
        self._save(records)

    def delete(self, pricebook_id: str) -> None:
        """Escape hatch da P2 (Configurações → Registry de Segmentadas):
        corrige um vínculo salvo errado enquanto a planilha (P5) não existe."""
        records = [r for r in self.load() if r.pricebook_id != pricebook_id]
        self._save(records)

    def _save(self, records: list[SegmentadaRecord]) -> None:
        payload = {"schema_version": _SCHEMA_VERSION, "records": [asdict(r) for r in records]}
        tmp_path = self._path.with_name(self._path.name + ".tmp")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, self._path)

    def _quarantine(self) -> None:
        if self._path.exists():
            backup = self._path.with_name(self._path.name + ".bak")
            try:
                os.replace(self._path, backup)
            except OSError:
                pass


_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _safe_filename(pricebook_id: str) -> str:
    return _FILENAME_SAFE_RE.sub("_", pricebook_id.strip()) or "_"


def merge_by_pricebook_id(*record_lists: list[SegmentadaRecord]) -> list[SegmentadaRecord]:
    """Junta registros de várias fontes (ex.: local + pasta compartilhada),
    resolvendo `pricebook_id` repetido pelo `updated_at` mais recente."""
    by_id: dict[str, SegmentadaRecord] = {}
    for records in record_lists:
        for r in records:
            current = by_id.get(r.pricebook_id)
            if current is None or (r.updated_at or "") >= (current.updated_at or ""):
                by_id[r.pricebook_id] = r
    return list(by_id.values())


class SyncedFolderRegistryStore:
    """Compartilhamento via pasta do Google Drive sincronizada localmente
    (P5, revisado). Um arquivo `<pricebook_id>.json` por registro — duas
    pessoas mexendo em campanhas diferentes nunca disputam o mesmo arquivo,
    o que evita a maioria das "cópias conflitantes" que o Drive cria quando
    o mesmo arquivo é editado por duas máquinas quase ao mesmo tempo.

    Mesma escrita atômica (`tmp` + `os.replace`) do `JsonFileRegistryStore`;
    um arquivo individual corrompido é isolado (`.bak`) sem derrubar os
    demais registros da pasta.
    """

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def load(self) -> list[SegmentadaRecord]:
        if not self._folder.exists():
            return []
        records: list[SegmentadaRecord] = []
        for path in sorted(self._folder.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                records.append(SegmentadaRecord(**raw))
            except (json.JSONDecodeError, TypeError, OSError):
                self._quarantine(path)
        return records

    def upsert(self, record: SegmentadaRecord) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        path = self._folder / f"{_safe_filename(record.pricebook_id)}.json"
        tmp_path = path.with_name(path.name + ".tmp")
        tmp_path.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, path)

    def mark_ended(self, pricebook_id: str, ended_at: str) -> None:
        for record in self.load():
            if record.pricebook_id == pricebook_id:
                record.ended_at = ended_at
                self.upsert(record)
                return

    def delete(self, pricebook_id: str) -> None:
        path = self._folder / f"{_safe_filename(pricebook_id)}.json"
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def _quarantine(self, path: Path) -> None:
        try:
            os.replace(path, path.with_name(path.name + ".bak"))
        except OSError:
            pass


# Ordem fixa das colunas do .xlsx — segue a mesma ordem da tabela "Formato
# do registro" no BRD-012, seção 7 (Etapa 1).
_XLSX_FIELDS: list[str] = [
    "pricebook_id", "sheet_name", "lp_label", "runrun_id", "brand", "loja",
    "campaign_name", "online_from", "online_to", "sku_count",
    "created_at", "updated_at", "created_by", "task_creator",
    "ended_at", "source_file",
]


def write_xlsx_snapshot(records: list[SegmentadaRecord], path: Path) -> None:
    """Gera um `.xlsx` só de leitura na pasta compartilhada — abre direto
    pelo Google Drive como planilha, sem o SIC precisar da API do Sheets.
    Escrita atômica: nunca deixa a pasta com um arquivo pela metade."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "registry"
    ws.append(_XLSX_FIELDS)
    for r in sorted(records, key=lambda r: r.pricebook_id):
        row = asdict(r)
        ws.append([row.get(f) for f in _XLSX_FIELDS])

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    wb.save(tmp_path)
    os.replace(tmp_path, path)
