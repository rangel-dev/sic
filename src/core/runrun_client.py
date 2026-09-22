"""Cliente somente leitura da API do Runrun.it (BRD-012, Etapa 5/P6).

Sem Qt — só `requests` (já dependência do projeto). Qualquer falha (rede,
HTTP, parsing) vira `RunrunUnavailable`, nunca uma exceção de biblioteca
solta pra UI — a tela sempre trata "sem resposta do Runrun.it" como
discreto, nunca como erro fatal (seção 8: o registro nunca bloqueia o
trabalho).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

BASE_URL = "https://runrun.it/api/v1.0"


class RunrunUnavailable(Exception):
    """Falha ao consultar o Runrun.it — rede, HTTP, parsing, tarefa
    inexistente. Sempre tratada como "sem confirmação", nunca fatal."""


class RunrunRateLimited(RunrunUnavailable):
    """HTTP 429 — CA-27: sem repetição automática. Quem chama decide
    quando (se) tentar de novo; o cliente nunca reenvia sozinho."""


@dataclass
class RunrunTask:
    number: str
    title: str
    is_closed: bool
    status_name: Optional[str] = None
    creator_name: Optional[str] = None  # D2/task_creator — ver seção 14 do BRD


class RunrunClient:
    def __init__(self, app_key: str, user_token: str, timeout: float = 5.0) -> None:
        self._app_key = app_key
        self._user_token = user_token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "App-Key": self._app_key,
            "User-Token": self._user_token,
            "Content-Type": "application/json",
        }

    def get_task(self, number: str) -> RunrunTask:
        """V4 confirmada (seção 14): `/tasks/{numero}` aceita direto o
        número visível da tarefa, sem identificador interno separado."""
        try:
            resp = requests.get(
                f"{BASE_URL}/tasks/{number}",
                headers=self._headers(),
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise RunrunUnavailable(str(exc)) from exc

        if resp.status_code == 429:
            raise RunrunRateLimited("limite de requisições do Runrun.it excedido")
        if resp.status_code == 404:
            raise RunrunUnavailable(f"tarefa {number} não encontrada")
        if resp.status_code != 200:
            raise RunrunUnavailable(f"Runrun.it respondeu HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise RunrunUnavailable("resposta do Runrun.it não é um JSON válido") from exc

        return RunrunTask(
            number=number,
            title=data.get("title") or "",
            is_closed=bool(data.get("is_closed")),
            status_name=data.get("task_status_name"),
            creator_name=data.get("user_name") or None,
        )

    def get_current_user_name(self) -> Optional[str]:
        """V8 resolvida (seção 14): `/users/me` identifica o dono do
        token — fonte automática de `created_by` (D2). `None` em
        qualquer falha, nunca levanta exceção — é sempre um "melhor
        esforço", com fallback já definido em D2."""
        try:
            resp = requests.get(
                f"{BASE_URL}/users/me",
                headers=self._headers(),
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException:
            return None
        if resp.status_code != 200:
            return None
        try:
            return resp.json().get("name") or None
        except ValueError:
            return None
