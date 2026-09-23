"""Rituais (Lumina, Ekos, Chronos) — categorização pela coluna TIPO da Grade."""
from __future__ import annotations

from pathlib import Path

import openpyxl
from lxml import etree

from src.core.sync_engine import CATALOG_NS, RITUAL_TIPO_MAP, SyncEngine


def _catalog(products: dict[str, bool], assignments: dict | None = None) -> dict:
    """products: {pid: is_master}."""
    return {
        "products": {pid: {"id": pid, "isMaster": m} for pid, m in products.items()},
        "assignments": assignments or {},
    }


def _assignments(xml: bytes) -> list[dict]:
    root = etree.fromstring(xml)
    return [
        {"category-id": ca.get("category-id"), "product-id": ca.get("product-id"), "mode": ca.get("mode")}
        for ca in root.findall(f"{{{CATALOG_NS}}}category-assignment")
    ]


class TestRitualTipoMap:
    def test_doze_entradas_com_os_ids_da_especificacao(self):
        assert RITUAL_TIPO_MAP == {
            "RITUAL-LUMINA-LIMPEZA": "ritual-lumina-limpeza",
            "RITUAL-LUMINA-CONDICIONAMENTO": "ritual-lumina-condicionamento",
            "RITUAL-LUMINA-TRATAMENTO": "ritual-lumina-tratamento",
            "RITUAL-LUMINA-FINALIZACAO": "ritual-lumina-finalizacao",
            "RITUAL-EKOS-LIMPEZA": "ritual-ekos-limpeza",
            "RITUAL-EKOS-ESFOLIACAO": "ritual-ekos-esfoliacao",
            "RITUAL-EKOS-NUTRIR": "ritual-ekos-nutrir",
            "RITUAL-EKOS-HIDRATACAO": "ritual-ekos-hidratacao",
            "RITUAL-CHRONOS-LIMPEZA": "ritual-chronos-derma-limpeza",
            "RITUAL-CHRONOS-TRAT.ROSTO": "ritual-chronos-derma-tratamento-rosto",
            "RITUAL-CHRONOS-HIDRATACAO": "ritual-chronos-derma-hidratacao",
            "RITUAL-CHRONOS-PROT.SOLAR": "ritual-chronos-derma-protecao-solar",
        }


class TestComputeRitualTargets:
    def test_tipo_mapeado_entra_na_categoria_correta(self):
        catalog_state = _catalog({"NATBRA-001": False})
        grade_map = {"NATBRA-001": {"tipo": "RITUAL-EKOS-LIMPEZA"}}
        targets = SyncEngine()._compute_ritual_targets(catalog_state, grade_map, "natura")
        assert targets["ritual-ekos-limpeza"] == {"NATBRA-001"}
        assert len(targets) == 12
        assert all(v == set() for k, v in targets.items() if k != "ritual-ekos-limpeza")

    def test_todas_as_12_marcacoes_classificam(self):
        pids = {f"NATBRA-{i:03d}": tipo for i, tipo in enumerate(RITUAL_TIPO_MAP)}
        catalog_state = _catalog({pid: False for pid in pids})
        grade_map = {pid: {"tipo": tipo} for pid, tipo in pids.items()}
        targets = SyncEngine()._compute_ritual_targets(catalog_state, grade_map, "natura")
        for pid, tipo in pids.items():
            assert targets[RITUAL_TIPO_MAP[tipo]] == {pid}

    def test_marcacao_tolera_caixa_e_espacos(self):
        catalog_state = _catalog({"NATBRA-001": False})
        grade_map = {"NATBRA-001": {"tipo": "  ritual-chronos-trat.rosto "}}
        targets = SyncEngine()._compute_ritual_targets(catalog_state, grade_map, "natura")
        assert targets["ritual-chronos-derma-tratamento-rosto"] == {"NATBRA-001"}

    def test_tipo_vazio_ou_nao_mapeado_e_ignorado(self):
        catalog_state = _catalog({"NATBRA-001": False, "NATBRA-002": False, "NATBRA-003": False, "NATBRA-004": False})
        grade_map = {
            "NATBRA-001": {"tipo": "RITUAL-LUMINA-LIMPEZA"},
            "NATBRA-002": {"tipo": ""},
            "NATBRA-003": {"tipo": "VNP"},
            "NATBRA-004": {"tipo": "RITUAL-EKOS-INEXISTENTE"},
        }
        targets = SyncEngine()._compute_ritual_targets(catalog_state, grade_map, "natura")
        assert set().union(*targets.values()) == {"NATBRA-001"}

    def test_grade_sem_nenhuma_marcacao_esvazia_as_12_categorias(self):
        """A Grade é a fonte da verdade: coluna TIPO presente mas sem nenhum
        RITUAL- -> as 12 chaves vêm vazias (e o XML remove o que houver no SF)."""
        catalog_state = _catalog({"NATBRA-001": False})
        grade_map = {"NATBRA-001": {"tipo": "VNP"}}
        targets = SyncEngine()._compute_ritual_targets(catalog_state, grade_map, "natura")
        assert targets == {cat: set() for cat in RITUAL_TIPO_MAP.values()}

    def test_grade_sem_coluna_tipo_nao_roda(self):
        """Coluna TIPO ausente (tipo None) ou nenhuma Grade -> None: erro de
        leitura não pode apagar os rituais do SF."""
        catalog_state = _catalog({"NATBRA-001": False})
        engine = SyncEngine()
        assert engine._compute_ritual_targets(catalog_state, {"NATBRA-001": {"tipo": None}}, "natura") is None
        assert engine._compute_ritual_targets(catalog_state, {"NATBRA-001": {}}, "natura") is None
        assert engine._compute_ritual_targets(catalog_state, {}, "natura") is None

    def test_avon_nao_e_impactada(self):
        catalog_state = _catalog({"AVNBRA-001": False})
        grade_map = {"AVNBRA-001": {"tipo": "RITUAL-EKOS-LIMPEZA"}}
        assert SyncEngine()._compute_ritual_targets(catalog_state, grade_map, "avon") is None

    def test_master_e_fora_da_grade_nao_entram(self):
        catalog_state = _catalog({"NATBRA-M": True, "NATBRA-001": False, "NATBRA-002": False})
        grade_map = {
            "NATBRA-M": {"tipo": "RITUAL-EKOS-NUTRIR"},
            "NATBRA-001": {"tipo": "RITUAL-EKOS-NUTRIR"},
        }
        targets = SyncEngine()._compute_ritual_targets(catalog_state, grade_map, "natura")
        assert targets["ritual-ekos-nutrir"] == {"NATBRA-001"}


class TestRitualXml:
    def test_add_e_remove_com_ids_exatos(self):
        catalog_state = _catalog(
            {"NATBRA-001": False, "NATBRA-002": False},
            assignments={"RITUAL-EKOS-LIMPEZA": {"NATBRA-002"}},
        )
        ritual_targets = {cat: set() for cat in RITUAL_TIPO_MAP.values()}
        ritual_targets["ritual-ekos-hidratacao"] = {"NATBRA-001"}
        xml = SyncEngine()._generate_catalog_xml(
            {"products": []}, "cat-id", {}, catalog_state, "natura", None, ritual_targets
        )
        assert sorted(_assignments(xml), key=lambda c: c["category-id"]) == [
            {"category-id": "ritual-ekos-hidratacao", "product-id": "NATBRA-001", "mode": None},
            {"category-id": "ritual-ekos-limpeza", "product-id": "NATBRA-002", "mode": "delete"},
        ]

    def test_ja_atribuido_nao_gera_delta(self):
        catalog_state = _catalog(
            {"NATBRA-001": False},
            assignments={"RITUAL-LUMINA-TRATAMENTO": {"NATBRA-001"}},
        )
        ritual_targets = {cat: set() for cat in RITUAL_TIPO_MAP.values()}
        ritual_targets["ritual-lumina-tratamento"] = {"NATBRA-001"}
        xml = SyncEngine()._generate_catalog_xml(
            {"products": []}, "cat-id", {}, catalog_state, "natura", None, ritual_targets
        )
        assert _assignments(xml) == []

    def test_grade_sem_marcacao_remove_rituais_existentes_no_sf(self):
        catalog_state = _catalog(
            {"NATBRA-001": False, "NATBRA-002": False},
            assignments={
                "RITUAL-LUMINA-TRATAMENTO": {"NATBRA-001"},
                "RITUAL-EKOS-NUTRIR": {"NATBRA-002"},
            },
        )
        grade_map = {"NATBRA-001": {"tipo": "VNP"}, "NATBRA-002": {"tipo": ""}}
        engine = SyncEngine()
        ritual_targets = engine._compute_ritual_targets(catalog_state, grade_map, "natura")
        xml = engine._generate_catalog_xml(
            {"products": []}, "cat-id", {}, catalog_state, "natura", None, ritual_targets
        )
        assert sorted(_assignments(xml), key=lambda c: c["category-id"]) == [
            {"category-id": "ritual-ekos-nutrir", "product-id": "NATBRA-002", "mode": "delete"},
            {"category-id": "ritual-lumina-tratamento", "product-id": "NATBRA-001", "mode": "delete"},
        ]

    def test_ritual_targets_none_nao_gera_nenhum_delta(self):
        catalog_state = _catalog(
            {"NATBRA-001": False},
            assignments={"RITUAL-LUMINA-TRATAMENTO": {"NATBRA-001"}},
        )
        xml = SyncEngine()._generate_catalog_xml(
            {"products": []}, "cat-id", {}, catalog_state, "natura", None, None
        )
        assert _assignments(xml) == []


class TestRitualMetricas:
    def _catalog_state_completo(self, assignments: dict) -> dict:
        state = _catalog({"NATBRA-001": False, "NATBRA-002": False}, assignments)
        for p in state["products"].values():
            p.update({"online": True, "searchable": True, "seoFlag": True, "dn": "Produto", "fn": "Produto", "sobj": ""})
        state.update({"masters": {}, "child_to_master": {}})
        return state

    def test_lists_details_traz_contagem_por_categoria_de_ritual(self):
        catalog_state = self._catalog_state_completo({"RITUAL-EKOS-LIMPEZA": {"NATBRA-002"}})
        grade_map = {
            "NATBRA-001": {"visible": True, "seal": "", "color": "", "tipo": "RITUAL-EKOS-LIMPEZA"},
            "NATBRA-002": {"visible": True, "seal": "", "color": "", "tipo": "RITUAL-EKOS-LIMPEZA"},
        }
        engine = SyncEngine()
        ritual_targets = engine._compute_ritual_targets(catalog_state, grade_map, "natura")
        _, metrics, _ = engine._execute_rules(catalog_state, grade_map, {}, "natura", None, ritual_targets)

        assert metrics["ritual_categories"] == 12
        rows = {r["id"]: r for r in metrics["lists_details"]}
        assert rows["ritual-ekos-limpeza"] == {"id": "ritual-ekos-limpeza", "excel": 2, "xml": 1, "status": "Delta: +1 / -0"}
        assert rows["ritual-lumina-limpeza"]["status"] == "Lista Vazia"

    def test_sem_regra_de_ritual_nao_gera_linhas(self):
        catalog_state = self._catalog_state_completo({})
        grade_map = {"NATBRA-001": {"visible": True, "seal": "", "color": "", "tipo": "VNP"}}
        _, metrics, _ = SyncEngine()._execute_rules(catalog_state, grade_map, {}, "natura", None, None)
        assert metrics["ritual_categories"] == 0
        assert not any(r["id"].startswith("ritual-") for r in metrics["lists_details"])


class TestParseColunaTipo:
    def _grade(self, tmp_path: Path, header: list, row: list) -> Path:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "GRADE DE ATIVAÇÃO"
        ws.append(header)
        ws.append(row)
        path = tmp_path / "grade.xlsx"
        wb.save(path)
        return path

    def test_le_coluna_tipo_exata_ignorando_tipo_material_e_check(self, tmp_path):
        path = self._grade(
            tmp_path,
            ["SKU", "TIPO MATERIAL", "TIPO", "CHECK COLUNA TIPO"],
            ["NATBRA-001", "ZPAC", "RITUAL-EKOS-NUTRIR", "OK"],
        )
        _, grade_map, _, _ = SyncEngine()._parse_excel_files([str(path)])
        assert grade_map["NATBRA-001"]["tipo"] == "RITUAL-EKOS-NUTRIR"

    def test_celula_tipo_vazia_vira_string_vazia(self, tmp_path):
        path = self._grade(tmp_path, ["SKU", "TIPO"], ["NATBRA-001", None])
        _, grade_map, _, _ = SyncEngine()._parse_excel_files([str(path)])
        assert grade_map["NATBRA-001"]["tipo"] == ""

    def test_grade_sem_coluna_tipo_marca_tipo_none(self, tmp_path):
        path = self._grade(tmp_path, ["SKU", "TIPO MATERIAL"], ["NATBRA-001", "ZPAC"])
        _, grade_map, _, _ = SyncEngine()._parse_excel_files([str(path)])
        assert grade_map["NATBRA-001"]["tipo"] is None
