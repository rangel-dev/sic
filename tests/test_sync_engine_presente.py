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
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura", True)
        assert targets["presentes-faixa-de-preco-agradecer"] == {"NATBRA-001"}
        assert all(len(v) == 0 for k, v in targets.items() if k != "presentes-faixa-de-preco-agradecer")

    def test_presentes_plural_tambem_categoriza(self):
        """Dado real da Grade usa "PRESENTES" (plural) — confirmado em arquivos
        reais de maio/junho, Natura e Avon. O BRD-008 documenta "Presente"
        (singular); a regra precisa aceitar as duas formas."""
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001")
        grade_map = {"NATBRA-001": {"planning_cat": "PRESENTES", "price": 30.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura", True)
        assert targets is not None
        assert targets["presentes-faixa-de-preco-agradecer"] == {"NATBRA-001"}

    def test_ca04_preco_zero_nao_categoriza(self):
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001")
        grade_map = {"NATBRA-001": {"planning_cat": "Presente", "price": 0.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura", True)
        assert all(len(v) == 0 for v in targets.values())

    def test_ca04_preco_none_nao_categoriza(self):
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001")
        grade_map = {"NATBRA-001": {"planning_cat": "Presente", "price": None}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura", True)
        assert all(len(v) == 0 for v in targets.values())

    def test_ca05_avon_regra_nunca_roda(self):
        """Avon: a regra não roda (retorna None), em vez de rodar com sets vazios —
        rodar com sets vazios geraria delete de qualquer presente já atribuído."""
        engine = SyncEngine()
        catalog_state = _catalog("AVNBRA-001")
        grade_map = {"AVNBRA-001": {"planning_cat": "Presente", "price": 30.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "avon", True)
        assert targets is None

    def test_grade_sem_colunas_regra_nao_roda(self):
        """Grade sem "CATEGORIA PLANEJAMENTO"/"POR" detectadas -> regra não
        roda (retorna None), mesmo com brand Natura e dados no grade_map."""
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001")
        grade_map = {"NATBRA-001": {"planning_cat": "Presente", "price": 30.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura", False)
        assert targets is None

    def test_ca06_master_nunca_categoriza(self):
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001M", is_master=True)
        grade_map = {"NATBRA-001M": {"planning_cat": "Presente", "price": 30.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura", True)
        assert all(len(v) == 0 for v in targets.values())

    def test_nao_presente_ignorado(self):
        engine = SyncEngine()
        catalog_state = _catalog("NATBRA-001")
        grade_map = {"NATBRA-001": {"planning_cat": "Kit Especial", "price": 30.0}}
        targets = engine._compute_presente_targets(catalog_state, grade_map, "natura", True)
        assert all(len(v) == 0 for v in targets.values())

    def test_sempre_retorna_as_4_chaves(self):
        engine = SyncEngine()
        targets = engine._compute_presente_targets(_catalog("NATBRA-001"), {}, "natura", True)
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

    def test_presente_targets_none_nao_gera_nenhum_delta(self):
        """Grade sem colunas, ou execução Avon: presente_targets=None chega
        até a geração do XML -> nenhum category-assignment de presente é
        emitido, nem add nem delete, mesmo com atribuições prévias no XML."""
        engine = SyncEngine()
        catalog_state = _catalog(
            "NATBRA-001",
            assignments={"PRESENTES-FAIXA-DE-PRECO-AGRADECER": {"NATBRA-001"}},
        )
        xml = engine._generate_catalog_xml(
            {"products": []}, "cat-id", {}, catalog_state, "natura", None
        )
        cas = self._assignments(xml)
        assert cas == []

    def test_avon_com_presente_previo_nao_e_alterado(self):
        """Fim a fim: compute retorna None para Avon -> XML não altera nada
        das categorias de presente já atribuídas nesse catálogo Avon."""
        engine = SyncEngine()
        catalog_state = _catalog(
            "AVNBRA-001",
            assignments={"PRESENTES-FAIXA-DE-PRECO-AGRADECER": {"AVNBRA-001"}},
        )
        grade_map = {"AVNBRA-001": {"planning_cat": "Presente", "price": 30.0}}
        presente_targets = engine._compute_presente_targets(catalog_state, grade_map, "avon", True)
        xml = engine._generate_catalog_xml(
            {"products": []}, "cat-id", {}, catalog_state, "avon", presente_targets
        )
        cas = self._assignments(xml)
        assert cas == []
