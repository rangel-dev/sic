"""BRD-010 — searchable-if-unavailable-flag sempre true, modo idempotente."""
from __future__ import annotations

from lxml import etree

from src.core.sync_engine import SyncEngine, CATALOG_NS


def _product(pid, seo_flag, online=False, searchable=False, is_master=False, dn="", fn="", sobj=""):
    return {
        "id": pid, "isMaster": is_master, "online": online, "searchable": searchable,
        "seoFlag": seo_flag, "dn": dn, "fn": fn, "sobj": sobj,
    }


def _catalog(products, masters=None, child_to_master=None, assignments=None):
    return {
        "products": products,
        "masters": masters or {},
        "child_to_master": child_to_master or {},
        "assignments": assignments or {},
    }


class TestSeoFlagIdempotenteProdutoNormal:
    def test_flag_ausente_no_xml_entra_no_delta_como_true(self):
        engine = SyncEngine()
        catalog_state = _catalog({"NATBRA-001": _product("NATBRA-001", seo_flag=False)})
        delta, _, _ = engine._execute_rules(catalog_state, grade_map={}, excel_lists={}, brand="natura", presente_targets=None)
        up = next(d["up"] for d in delta["products"] if d["id"] == "NATBRA-001")
        assert up["searchable-if-unavailable-flag"] == "true"

    def test_flag_ja_true_nao_reentra_no_delta_por_causa_dela(self):
        engine = SyncEngine()
        catalog_state = _catalog({"NATBRA-001": _product("NATBRA-001", seo_flag=True)})
        delta, _, _ = engine._execute_rules(catalog_state, grade_map={}, excel_lists={}, brand="natura", presente_targets=None)
        assert delta["products"] == []

    def test_avon_tambem_recebe_a_regra_sem_excecao(self):
        engine = SyncEngine()
        catalog_state = _catalog({"AVNBRA-001": _product("AVNBRA-001", seo_flag=False)})
        delta, _, _ = engine._execute_rules(catalog_state, grade_map={}, excel_lists={}, brand="avon", presente_targets=None)
        up = next(d["up"] for d in delta["products"] if d["id"] == "AVNBRA-001")
        assert up["searchable-if-unavailable-flag"] == "true"

    def test_flag_false_e_outras_mudancas_coexistem_no_mesmo_delta(self):
        engine = SyncEngine()
        catalog_state = _catalog({"NATBRA-001": _product("NATBRA-001", seo_flag=False, online=False)})
        grade_map = {"NATBRA-001": {"visible": True, "seal": "", "color": "", "price": 10.0, "planning_cat": ""}}
        delta, _, _ = engine._execute_rules(catalog_state, grade_map, excel_lists={}, brand="natura", presente_targets=None)
        up = next(d["up"] for d in delta["products"] if d["id"] == "NATBRA-001")
        assert up["online-flag"] == "true"
        assert up["searchable-if-unavailable-flag"] == "true"


class TestSeoFlagIdempotenteMestre:
    def test_mestre_com_flag_ausente_entra_no_delta(self):
        engine = SyncEngine()
        catalog_state = _catalog(
            products={"NATBRA-001M": _product("NATBRA-001M", seo_flag=False, is_master=True)},
            masters={"NATBRA-001M": set()},
        )
        delta, _, _ = engine._execute_rules(catalog_state, grade_map={}, excel_lists={}, brand="natura", presente_targets=None)
        up = next(d["up"] for d in delta["products"] if d["id"] == "NATBRA-001M")
        assert up["searchable-if-unavailable-flag"] == "true"

    def test_mestre_com_flag_ja_true_nao_reentra_no_delta(self):
        engine = SyncEngine()
        catalog_state = _catalog(
            products={"NATBRA-001M": _product("NATBRA-001M", seo_flag=True, is_master=True)},
            masters={"NATBRA-001M": set()},
        )
        delta, _, _ = engine._execute_rules(catalog_state, grade_map={}, excel_lists={}, brand="natura", presente_targets=None)
        assert delta["products"] == []


class TestGeracaoXmlEmiteSeoFlag:
    def test_geracao_xml_emite_flag_do_delta(self):
        engine = SyncEngine()
        delta = {"products": [{"id": "NATBRA-001", "up": {"searchable-if-unavailable-flag": "true"}}]}
        xml_bytes = engine._generate_catalog_xml(
            delta, catalog_id="natura-br-storefront-catalog", excel_lists={},
            catalog_state=_catalog({}), brand="natura", presente_targets=None,
        )
        root = etree.fromstring(xml_bytes)
        ns = {"c": CATALOG_NS}
        prod_el = root.find("c:product[@product-id='NATBRA-001']", ns)
        assert prod_el is not None
        flag_el = prod_el.find("c:searchable-if-unavailable-flag", ns)
        assert flag_el is not None
        assert flag_el.text == "true"
