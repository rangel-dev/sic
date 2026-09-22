"""Registry das Segmentadas — modelo, montagem de ID, status e reconhecimento.

BRD-012, P1: núcleo testável, sem tela. Cobre o modelo do vínculo
aba-da-planilha ↔ tarefa do Runrun.it, a montagem/leitura do `pricebook_id`
(D1: identidade do registro), o cálculo de status por janela online-from/
online-to e a regra de reconhecimento na importação (Etapa 3), incluindo o
armazenamento local (`JsonFileRegistryStore`). O compartilhamento via
planilha (`GoogleSheetRegistryStore`, P5) e o cache entre as duas fontes
(`CachedRegistry`) ainda não existem — entram quando a P5 for construída.
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
