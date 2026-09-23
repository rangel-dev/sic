"""Rituais — Auditor: categorias de ritual blindadas contra POR < DE em Natura e ML."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from src.core.auditor.parity_rules_v12 import execute_parity_rules
from src.core.auditor_engine import PROHIBITED_CATEGORIES, RITUAL_CATEGORIES, AuditorEngine

RITUAIS = {
    "ritual-lumina-limpeza", "ritual-lumina-condicionamento",
    "ritual-lumina-tratamento", "ritual-lumina-finalizacao",
    "ritual-ekos-limpeza", "ritual-ekos-esfoliacao",
    "ritual-ekos-nutrir", "ritual-ekos-hidratacao",
    "ritual-chronos-derma-limpeza", "ritual-chronos-derma-tratamento-rosto",
    "ritual-chronos-derma-hidratacao", "ritual-chronos-derma-protecao-solar",
}


def _catalog_xml(tmp_path: Path, catalog_id: str, assignments: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<category-assignment category-id="{cat}" product-id="{pid}"/>' for cat, pid in assignments
    )
    path = tmp_path / f"{catalog_id}.xml"
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<catalog xmlns="http://www.demandware.com/xml/impex/catalog/2006-10-31" '
        f'catalog-id="{catalog_id}">{body}</catalog>',
        encoding="utf-8",
    )
    return str(path)


def _margin_errors(sku: str, de: float, por: float, prohibited_state: dict) -> list[dict]:
    brand = "Natura" if sku.startswith("NATBRA-") else "Avon"
    errors = defaultdict(list)
    execute_parity_rules(
        all_skus={sku},
        excel_prices={sku: {"DE": de, "POR": por, "VISIBLE": ""}},
        online_status={sku: True},
        prices_xml={sku: {brand: {"DE": de, "POR": por}}},
        bundles={}, variation_bases={}, searchable_status={},
        technical_skus={}, excel_lists={}, xml_lists={},
        cat_missing_primary={}, prohibited_state=prohibited_state, job_errors={},
        has_nat=True, has_avn=True, errors=errors,
        dump_stats=lambda code, b: None,
    )
    return errors["margin"]


class TestProhibitedCategories:
    def test_as_12_categorias_de_ritual(self):
        assert RITUAL_CATEGORIES == RITUAIS

    def test_natura_e_ml_recebem_os_rituais_sem_perder_as_categorias_antigas(self):
        assert RITUAIS <= PROHIBITED_CATEGORIES["Natura"]
        assert RITUAIS <= PROHIBITED_CATEGORIES["ML"]
        assert {"promocao-da-semana", "LISTA_01", "monte-seu-kit", "LISTA_02"} <= PROHIBITED_CATEGORIES["Natura"]
        assert {"promocao-da-semana", "desconto-progressivo", "monte-seu-kit"} <= PROHIBITED_CATEGORIES["ML"]

    def test_avon_nao_e_impactada(self):
        assert PROHIBITED_CATEGORIES["Avon"] == {"promocoes-desconto-progressivo", "lista-01"}


class TestParseCatalogsRituais:
    def test_sku_em_ritual_entra_no_prohibited_state_de_natura_e_ml(self, tmp_path):
        paths = [
            _catalog_xml(tmp_path, "natura-br-storefront-catalog", [("ritual-ekos-limpeza", "NATBRA-001")]),
            _catalog_xml(tmp_path, "cb-br-storefront-catalog", [("ritual-chronos-derma-protecao-solar", "NATBRA-002")]),
        ]
        prohibited_state = AuditorEngine()._parse_catalogs(paths)[4]
        assert prohibited_state["Natura"] == {"NATBRA-001"}
        assert prohibited_state["ML"] == {"NATBRA-002"}

    def test_ritual_em_catalogo_avon_nao_blinda(self, tmp_path):
        paths = [_catalog_xml(tmp_path, "avon-br-storefront-catalog", [("ritual-ekos-limpeza", "AVNBRA-001")])]
        prohibited_state = AuditorEngine()._parse_catalogs(paths)[4]
        assert prohibited_state["Avon"] == set()


class TestMargemRituais:
    def test_por_menor_que_de_dispara_alerta_em_natura_e_ml(self):
        errors = _margin_errors("NATBRA-001", 100.0, 80.0, {"Natura": {"NATBRA-001"}, "ML": {"NATBRA-001"}})
        assert [e["detail"] for e in errors] == ["CONFLITO PROG (Natura)", "CONFLITO PROG (Minha Loja)"]

    def test_por_igual_ou_maior_que_de_nao_dispara(self):
        state = {"Natura": {"NATBRA-001"}, "ML": {"NATBRA-001"}}
        assert _margin_errors("NATBRA-001", 100.0, 100.0, state) == []
        assert _margin_errors("NATBRA-001", 100.0, 120.0, state) == []

    def test_avon_sem_alerta_indevido(self):
        assert _margin_errors("AVNBRA-001", 100.0, 80.0, {"Avon": set(), "ML": set()}) == []
