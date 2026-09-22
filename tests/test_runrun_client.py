"""Suíte de testes do RunrunClient (BRD-012, Etapa 5/P6).

`requests` é mockado — nenhum destes testes faz chamada de rede de
verdade. Cobre os casos já confirmados na seção 14 do BRD (V4, V5, V6,
V8) e os caminhos de erro que as validações CA-22/CA-25/CA-27 exigem.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.runrun_client import RunrunClient, RunrunRateLimited, RunrunUnavailable


def _client() -> RunrunClient:
    return RunrunClient(app_key="fake-app-key", user_token="fake-user-token", timeout=1.0)


def _mock_response(status_code: int, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is None:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_data
    return resp


class TestGetTask:
    def test_numero_visivel_resolve_a_tarefa(self):
        payload = {"title": "Favoritos RR18/21", "is_closed": False, "task_status_name": "Em andamento"}
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(200, payload)) as mock_get:
            task = _client().get_task("2388")

        assert task.number == "2388"
        assert task.title == "Favoritos RR18/21"
        assert task.is_closed is False
        assert task.status_name == "Em andamento"
        called_url = mock_get.call_args.args[0]
        assert called_url.endswith("/tasks/2388")

    def test_envia_app_key_e_user_token_nos_headers(self):
        payload = {"title": "X", "is_closed": False}
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(200, payload)) as mock_get:
            _client().get_task("1")
        headers = mock_get.call_args.kwargs["headers"]
        assert headers["App-Key"] == "fake-app-key"
        assert headers["User-Token"] == "fake-user-token"
        assert headers["Content-Type"] == "application/json"

    def test_tarefa_inexistente_levanta_runrun_unavailable(self):
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(404)):
            with pytest.raises(RunrunUnavailable):
                _client().get_task("9999999")

    def test_429_levanta_runrun_rate_limited_sem_repetir(self):
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(429)) as mock_get:
            with pytest.raises(RunrunRateLimited):
                _client().get_task("2388")
        assert mock_get.call_count == 1  # CA-27: nenhuma repetição automática

    def test_outro_http_erro_levanta_runrun_unavailable(self):
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(500)):
            with pytest.raises(RunrunUnavailable):
                _client().get_task("2388")

    def test_falha_de_rede_levanta_runrun_unavailable(self):
        with patch("src.core.runrun_client.requests.get", side_effect=requests.exceptions.ConnectTimeout()):
            with pytest.raises(RunrunUnavailable):
                _client().get_task("2388")

    def test_resposta_sem_json_valido_levanta_runrun_unavailable(self):
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(200, json_data=None)):
            with pytest.raises(RunrunUnavailable):
                _client().get_task("2388")

    def test_tarefa_encerrada_e_marcada(self):
        payload = {"title": "Campanha Antiga", "is_closed": True}
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(200, payload)):
            task = _client().get_task("1111")
        assert task.is_closed is True

    def test_creator_name_vem_de_user_name(self):
        payload = {"title": "X", "is_closed": False, "user_name": "Fulano de Tal"}
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(200, payload)):
            task = _client().get_task("1")
        assert task.creator_name == "Fulano de Tal"

    def test_sem_user_name_creator_name_e_none(self):
        payload = {"title": "X", "is_closed": False}
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(200, payload)):
            task = _client().get_task("1")
        assert task.creator_name is None


class TestGetCurrentUserName:
    def test_retorna_o_nome_de_users_me(self):
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(200, {"name": "Edgar Silva"})) as mock_get:
            name = _client().get_current_user_name()
        assert name == "Edgar Silva"
        assert mock_get.call_args.args[0].endswith("/users/me")

    def test_falha_devolve_none_sem_levantar(self):
        with patch("src.core.runrun_client.requests.get", side_effect=requests.exceptions.ConnectTimeout()):
            assert _client().get_current_user_name() is None

    def test_http_erro_devolve_none(self):
        with patch("src.core.runrun_client.requests.get", return_value=_mock_response(403)):
            assert _client().get_current_user_name() is None
