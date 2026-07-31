"""BRD-010 — Check list_excess não valida lista ausente/oculta da Grade."""
from __future__ import annotations

from collections import defaultdict

from src.core.auditor.parity_rules_v12 import execute_parity_rules


def _run(excel_lists, xml_lists, has_nat=True, has_avn=False, all_skus=None):
    errors = defaultdict(list)
    execute_parity_rules(
        all_skus=all_skus or set(),
        excel_prices={}, online_status={}, prices_xml={},
        bundles={}, variation_bases={}, searchable_status={},
        technical_skus={}, excel_lists=excel_lists, xml_lists=xml_lists,
        cat_missing_primary={}, prohibited_state={}, job_errors={},
        has_nat=has_nat, has_avn=has_avn, errors=errors,
        dump_stats=lambda code, brand: None,
    )
    return errors


class TestListExcessBRD010:
    def test_lista_ausente_da_grade_nao_gera_excesso(self):
        errors = _run(excel_lists={}, xml_lists={"LISTA_01": {"NATBRA-001"}})
        assert errors["list_excess"] == []

    def test_lista_visivel_vazia_gera_excesso_genuino(self):
        errors = _run(excel_lists={"LISTA_01": set()}, xml_lists={"LISTA_01": {"NATBRA-001"}})
        assert len(errors["list_excess"]) == 1
        assert errors["list_excess"][0]["sku"] == "NATBRA-001"

    def test_lista_com_sku_presente_no_excel_nao_gera_excesso(self):
        errors = _run(
            excel_lists={"LISTA_01": {"NATBRA-001"}},
            xml_lists={"LISTA_01": {"NATBRA-001"}},
        )
        assert errors["list_excess"] == []

    def test_marca_sem_grade_carregada_nao_gera_excesso_mesmo_com_lista_ausente(self):
        errors = _run(
            excel_lists={}, xml_lists={"lista-01": {"AVNBRA-001"}},
            has_nat=True, has_avn=False,
        )
        assert errors["list_excess"] == []
