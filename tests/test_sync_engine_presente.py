"""BRD-008 — categorização de presentes por faixa de preço (CA-01 a CA-08)."""
from __future__ import annotations

from lxml import etree

from src.core.sync_engine import SyncEngine, _price_bucket


def _catalog(pid: str, is_master: bool = False, assignments: dict | None = None) -> dict:
    return {
        "products": {pid: {"id": pid, "isMaster": is_master}},
        "assignments": assignments or {},
    }


class TestPriceBucket:
    def test_agradecer_limite_inferior_e_superior(self):
        assert _price_bucket(0.01) == "presentes-faixa-de-preco-agradecer"
        assert _price_bucket(50.00) == "presentes-faixa-de-preco-agradecer"

    def test_encantar(self):
        assert _price_bucket(50.01) == "presentes-faixa-de-preco-encantar"
        assert _price_bucket(100.00) == "presentes-faixa-de-preco-encantar"

    def test_surpreender(self):
        assert _price_bucket(100.01) == "presentes-faixa-de-preco-surpreender"
        assert _price_bucket(150.00) == "presentes-faixa-de-preco-surpreender"

    def test_impressionar(self):
        assert _price_bucket(150.01) == "presentes-faixa-de-preco-impressionar"
        assert _price_bucket(999999) == "presentes-faixa-de-preco-impressionar"


class TestComputePresenteTargets:
    def test_ca01_ca02_presente_faixa_correta(self):
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001")
        grade_map = {"NATBRA-001": {"planning_cat": "Presente", "price": 30.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura")
        assert targets["presentes-faixa-de-preco-agradecer"] == {"NATBRA-001"}
        assert all(len(v) == 0 for k, v in targets.items() if k != "presentes-faixa-de-preco-agradecer")

    def test_ca04_preco_zero_nao_categoriza(self):
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001")
        grade_map = {"NATBRA-001": {"planning_cat": "Presente", "price": 0.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura")
        assert all(len(v) == 0 for v in targets.values())

    def test_ca04_preco_none_nao_categoriza(self):
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001")
        grade_map = {"NATBRA-001": {"planning_cat": "Presente", "price": None}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura")
        assert all(len(v) == 0 for v in targets.values())

    def test_ca05_avon_nunca_categoriza(self):
        engine = SyncEngine()
        catalog_state = _catalog("AVNBRA-001")
        grade_map = {"AVNBRA-001": {"planning_cat": "Presente", "price": 30.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "avon")
        assert all(len(v) == 0 for v in targets.values())

    def test_ca06_master_nunca_categoriza(self):
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001M", is_master=True)
        grade_map = {"NATBRA-001M": {"planning_cat": "Presente", "price": 30.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura")
        assert all(len(v) == 0 for v in targets.values())

    def test_nao_presente_ignorado(self):
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001")
        grade_map = {"NATBRA-001": {"planning_cat": "Kit Especial", "price": 30.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura")
        assert all(len(v) == 0 for v in targets.values())

    def test_sempre_retorna_as_4_chaves(self):
        engine = SyncEngine()
        targets = engine._compute_presente_targets(_catalog("NATBRA-001"), {}, "natura")
        assert set(targets.keys()) == {
            "presentes-faixa-de-preco-agradecer",
            "presentes-faixa-de-preco-encantar",
            "presentes-faixa-de-preco-surpreender",
            "presentes-faixa-de-preco-impressionar",
        }


class TestGenerateCatalogXmlPresente:
    def _assignments(self, xml_bytes: bytes) -> list[dict]:
        root = etree.fromstring(xml_bytes)
        ns = {"c": "http://www.demandware.com/xml/impex/catalog/2006-10-31"}
        return [
            {
                "category-id": ca.get("category-id"),
                "product-id": ca.get("product-id"),
                "mode": ca.get("mode"),
            }
            for ca in root.findall("c:category-assignment", ns)
        ]

    def test_ca03_migracao_de_faixa_gera_add_e_remove(self):
        engine = SyncEngine()
        catalog_state = _catalog(
            "NATBRA-001",
            assignments={
                "PRESENTES-FAIXA-DE-PRECO-AGRADECER": {"NATBRA-001"},
            },
        )
        # SKU migrou de "agradecer" (preço antigo) para "encantar" (preço novo)
        presente_targets = {
            "presentes-faixa-de-preco-agradecer": set(),
            "presentes-faixa-de-preco-encantar": {"NATBRA-001"},
            "presentes-faixa-de-preco-surpreender": set(),
            "presentes-faixa-de-preco-impressionar": set(),
        }
        xml = engine._generate_catalog_xml(
            {"products": []}, "cat-id", {}, catalog_state, "natura", presente_targets
        )
        cas = self._assignments(xml)

        added = [c for c in cas if c["category-id"] == "presentes-faixa-de-preco-encantar"]
        removed = [c for c in cas if c["category-id"] == "presentes-faixa-de-preco-agradecer"]
        assert added == [{"category-id": "presentes-faixa-de-preco-encantar", "product-id": "NATBRA-001", "mode": None}]
        assert removed == [{"category-id": "presentes-faixa-de-preco-agradecer", "product-id": "NATBRA-001", "mode": "delete"}]

    def test_ca07_nao_toca_outras_categorias(self):
        engine = SyncEngine()
        catalog_state = _catalog(
            "NATBRA-001",
            assignments={
                "CATEGORIA-PRIMARIA-X": {"NATBRA-001"},
                "PRESENTES-FAIXA-DE-PRECO-AGRADECER": {"NATBRA-001"},
            },
        )
        # Continua na mesma faixa — nenhuma mudança de presente
        presente_targets = {
            "presentes-faixa-de-preco-agradecer": {"NATBRA-001"},
            "presentes-faixa-de-preco-encantar": set(),
            "presentes-faixa-de-preco-surpreender": set(),
            "presentes-faixa-de-preco-impressionar": set(),
        }
        xml = engine._generate_catalog_xml(
            {"products": []}, "cat-id", {}, catalog_state, "natura", presente_targets
        )
        cas = self._assignments(xml)
        assert all(c["category-id"] != "CATEGORIA-PRIMARIA-X" for c in cas)

    def test_ca08_removido_ao_deixar_de_ser_presente(self):
        engine = SyncEngine()
        catalog_state = _catalog(
            "NATBRA-001",
            assignments={"PRESENTES-FAIXA-DE-PRECO-AGRADECER": {"NATBRA-001"}},
        )
        presente_targets = {
            "presentes-faixa-de-preco-agradecer": set(),
            "presentes-faixa-de-preco-encantar": set(),
            "presentes-faixa-de-preco-surpreender": set(),
            "presentes-faixa-de-preco-impressionar": set(),
        }
        xml = engine._generate_catalog_xml(
            {"products": []}, "cat-id", {}, catalog_state, "natura", presente_targets
        )
        cas = self._assignments(xml)
        assert cas == [{"category-id": "presentes-faixa-de-preco-agradecer", "product-id": "NATBRA-001", "mode": "delete"}]
