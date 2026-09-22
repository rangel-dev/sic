"""Suíte de testes do app_paths (BRD-012, P1)."""
from __future__ import annotations

from pathlib import Path

from src.core.app_paths import data_file, user_data_dir


class TestUserDataDir:
    def test_cria_a_pasta_se_nao_existir(self, tmp_path: Path):
        override = tmp_path / "SIC"
        assert not override.exists()
        result = user_data_dir(override=override)
        assert result == override
        assert override.is_dir()

    def test_reaproveita_pasta_existente(self, tmp_path: Path):
        override = tmp_path / "SIC"
        override.mkdir()
        marker = override / "ja_existia.txt"
        marker.write_text("x", encoding="utf-8")
        user_data_dir(override=override)
        assert marker.exists()


class TestDataFile:
    def test_junta_o_nome_do_arquivo_a_pasta_de_dados(self, tmp_path: Path):
        override = tmp_path / "SIC"
        result = data_file("registry_cache.json", override=override)
        assert result == override / "registry_cache.json"
        assert override.is_dir()
