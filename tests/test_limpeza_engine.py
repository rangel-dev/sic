"""
Testes do motor da Limpeza de Campanhas (BRD-015).

Todos os XMLs são inventados — dados reais nunca entram no repositório
(BRD-015, trava 7.4). Os nomes CA-xx remetem aos critérios de aceite.
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.core import limpeza_engine as le
from src.core.limpeza_engine import (
    ELEGIVEL, PROTEGIDO, REVISAR,
    ENT_CAMPAIGNS, ENT_COUPONS, ENT_GROUPS, ENT_PROMOTIONS,
    KIND_COUPONS, KIND_CUSTOMER_GROUPS, KIND_PROMOTIONS,
    LimpezaEngine, LimpezaError,
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _promotions_xml(campaigns=(), promotions=(), assignments=(), catalog="natura-br-storefront-catalog",
                    skus=("NATBRA-1001",)):
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<promotions xmlns="{le.PROMOTIONS_NS}">']
    for c in campaigns:
        out.append(f'<campaign campaign-id="{c["id"]}">')
        out.append(f'<enabled-flag>{"true" if c.get("enabled", True) else "false"}</enabled-flag>')
        out.append('<campaign-scope><applicable-online/></campaign-scope>')
        if "start" in c:
            out.append(f'<start-date>{c["start"]}</start-date>')
        if "end" in c:
            out.append(f'<end-date>{c["end"]}</end-date>')
        groups = c.get("groups", ["Everyone"])
        out.append('<customer-groups match-mode="any">'
                   + "".join(f'<customer-group group-id="{g}"/>' for g in groups) + "</customer-groups>")
        if c.get("coupons"):
            out.append("<coupons>" + "".join(f'<coupon coupon-id="{x}"/>' for x in c["coupons"]) + "</coupons>")
        out.append("</campaign>")
    for p in promotions:
        out.append(f'<promotion promotion-id="{p}"><enabled-flag>true</enabled-flag>'
                   f'<name xml:lang="x-default">{p}</name>'
                   '<product-promotion-rule><discounted-products><included-products><condition-group>'
                   f'<product-id-condition catalog-id="{catalog}">'
                   + "".join(f"<product-id>{k}</product-id>" for k in skus)
                   + '</product-id-condition></condition-group></included-products></discounted-products>'
                   '</product-promotion-rule></promotion>')
    for a in assignments:
        out.append(f'<promotion-campaign-assignment promotion-id="{a["promo"]}" campaign-id="{a["camp"]}">'
                   '<qualifiers match-mode="any"/>')
        if a.get("coupons"):
            out.append("<coupons>" + "".join(f'<coupon coupon-id="{x}"/>' for x in a["coupons"]) + "</coupons>")
        if a.get("groups"):
            out.append('<customer-groups match-mode="any">'
                       + "".join(f'<customer-group group-id="{g}"/>' for g in a["groups"]) + "</customer-groups>")
        out.append("</promotion-campaign-assignment>")
    out.append("</promotions>")
    return "\n".join(out)


def _coupons_xml(coupons=()):
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<coupons xmlns="{le.COUPONS_NS}">']
    for c in coupons:
        out.append(f'<coupon coupon-id="{c["id"]}"><description>{c["id"]} desc</description>'
                   f'<enabled-flag>{"true" if c.get("enabled", True) else "false"}</enabled-flag>'
                   '<case-insensitive>true</case-insensitive><redemption-limits/>')
        if c.get("codes"):
            out.append('<multiple-codes><code-prefix>X</code-prefix></multiple-codes>')
        else:
            out.append(f'<single-code>{c["id"].upper()}</single-code>')
        out.append("</coupon>")
    for c in coupons:
        if c.get("codes"):
            out.append(f'<coupon-codes coupon-id="{c["id"]}">'
                       + "".join(f"<code>{c['id']}-{i}</code>" for i in range(c["codes"])) + "</coupon-codes>")
    out.append("</coupons>")
    return "\n".join(out)


def _groups_xml(groups=()):
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<customer-groups xmlns="{le.CUSTOMER_GROUPS_NS}">']
    for g in groups:
        out.append(f'<customer-group group-id="{g["id"]}">')
        if g.get("desc"):
            out.append(f'<description>{g["desc"]}</description>')
        if g.get("dynamic", True):
            out.append("<membership-rule><included-customers/></membership-rule>")
        out.append("<custom-attributes/></customer-group>")
    for g in groups:
        for i in range(g.get("members", 0)):
            out.append(f'<group-assignment group-id="{g["id"]}" customer-no="{i:08d}"/>')
    out.append("</customer-groups>")
    return "\n".join(out)


def _write(tmp_path: Path, promotions="", coupons="", groups="", names=("p.xml", "c.xml", "g.xml")):
    paths = {}
    for kind, content, name in ((KIND_PROMOTIONS, promotions, names[0]),
                                (KIND_COUPONS, coupons, names[1]),
                                (KIND_CUSTOMER_GROUPS, groups, names[2])):
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        paths[kind] = str(p)
    return paths


SYSTEM = [{"id": "Everyone"}, {"id": "Registered"}]
OLD = _iso(NOW - timedelta(days=60))


BASE_CAMP = {"id": "BASE-PERENE"}
BASE_PROMO = "BASE-PROMO"


def _run(tmp_path, campaigns=({"id": "QUALQUER"},), promotions=(), assignments=(), coupons=(),
         groups=SYSTEM, now=NOW, catalog="natura-br-storefront-catalog", skus=("NATBRA-1001",), **kw):
    """Sempre inclui uma campanha perene com uma promoção que cita o catálogo
    da loja — é a impressão digital que identifica a loja (ficam Protegidas)."""
    files = _write(tmp_path,
                   _promotions_xml([BASE_CAMP, *campaigns], [BASE_PROMO, *promotions],
                                   [{"camp": BASE_CAMP["id"], "promo": BASE_PROMO}, *assignments],
                                   catalog=catalog, skus=skus),
                   _coupons_xml(coupons), _groups_xml(groups))
    eng = LimpezaEngine(files, now=now, **kw)
    return eng, eng.simulate()


def _status(res, entity, item_id):
    return res.items[entity][item_id].status


# ── Reconhecimento dos arquivos ──────────────────────────────────────────────
def test_ca19_reconhece_pelo_namespace_mesmo_com_nomes_trocados(tmp_path):
    files = _write(tmp_path, _promotions_xml(), _coupons_xml(), _groups_xml(),
                   names=("CUPONS.xml", "PROMOTIONS.xml", "GRUPOS.xml"))
    assert le.detect_kind(files[KIND_PROMOTIONS]) == KIND_PROMOTIONS
    assert le.detect_kind(files[KIND_COUPONS]) == KIND_COUPONS
    sel = le.classify_files(list(files.values()))
    assert sel.complete and sel.paths == files


def test_classificacao_recusa_desconhecido_e_repetido(tmp_path):
    files = _write(tmp_path, _promotions_xml(), _coupons_xml(), _groups_xml())
    other = tmp_path / "outro_cupons.xml"
    other.write_text(_coupons_xml(), encoding="utf-8")
    junk = tmp_path / "catalogo.xml"
    junk.write_text('<catalog xmlns="http://www.demandware.com/xml/impex/catalog/2006-10-31"/>', encoding="utf-8")
    sel = le.classify_files([*files.values(), str(other), str(junk)])
    assert sel.complete
    assert {Path(p).name for p, _ in sel.rejected} == {"outro_cupons.xml", "catalogo.xml"}


def test_motor_recusa_arquivo_no_tipo_errado(tmp_path):
    files = _write(tmp_path, _promotions_xml(), _coupons_xml(), _groups_xml())
    files[KIND_COUPONS], files[KIND_PROMOTIONS] = files[KIND_PROMOTIONS], files[KIND_COUPONS]
    with pytest.raises(LimpezaError):
        LimpezaEngine(files, now=NOW)


# ── Datas ────────────────────────────────────────────────────────────────────
def test_data_sem_fuso_e_tratada_como_utc_e_ilegivel_sinalizada():
    dt, bad = le.parse_sfcc_date("2026-10-01T10:00:00")
    assert dt is not None and dt.tzinfo is not None and not bad
    assert le.parse_sfcc_date("31/02/2026") == (None, True)
    assert le.parse_sfcc_date("") == (None, False)


# ── Campanhas ────────────────────────────────────────────────────────────────
def test_ca01_vencida_ha_mais_que_a_carencia_e_elegivel(tmp_path):
    _, res = _run(tmp_path, campaigns=[
        {"id": "VELHA", "end": _iso(NOW - timedelta(days=30))},
        {"id": "RECENTE", "end": _iso(NOW - timedelta(days=29))},
        {"id": "VIGENTE", "end": _iso(NOW + timedelta(days=5))},
    ])
    assert _status(res, ENT_CAMPAIGNS, "VELHA") == ELEGIVEL
    assert _status(res, ENT_CAMPAIGNS, "RECENTE") == PROTEGIDO
    assert _status(res, ENT_CAMPAIGNS, "VIGENTE") == PROTEGIDO


def test_ca02_perene_habilitada_e_protegida(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "PERENE"}])
    assert _status(res, ENT_CAMPAIGNS, "PERENE") == PROTEGIDO


def test_ca03_perene_desativada_e_elegivel_ja_na_primeira_rodada(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "PAUSADA", "enabled": False}])
    assert _status(res, ENT_CAMPAIGNS, "PAUSADA") == ELEGIVEL


def test_ca04_data_ilegivel_vai_para_revisar_mesmo_desativada(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "QUEBRADA", "enabled": False, "end": "não-é-data"}])
    assert _status(res, ENT_CAMPAIGNS, "QUEBRADA") == REVISAR


def test_regua_de_carencia_vale_para_campanhas_vencidas(tmp_path):
    camp = [{"id": "VENCIDA-10D", "end": _iso(NOW - timedelta(days=10))}]
    _, r30 = _run(tmp_path, campaigns=camp)
    assert _status(r30, ENT_CAMPAIGNS, "VENCIDA-10D") == PROTEGIDO
    _, r7 = _run(tmp_path, campaigns=camp, grace_days=7)
    assert _status(r7, ENT_CAMPAIGNS, "VENCIDA-10D") == ELEGIVEL


def test_regua_fora_dos_limites_e_recusada(tmp_path):
    files = _write(tmp_path, _promotions_xml(), _coupons_xml(), _groups_xml())
    for bad in (le.GRACE_MIN_DAYS - 1, le.GRACE_MAX_DAYS + 1):
        with pytest.raises(LimpezaError):
            LimpezaEngine(files, grace_days=bad, now=NOW)


# ── Itens sem campanha: saem já na primeira rodada (regra do negócio) ────────
def test_ca06_itens_sem_campanha_sao_elegiveis_na_primeira_rodada(tmp_path):
    _, res = _run(tmp_path, promotions=["PROMO-ORFA"], coupons=[{"id": "CUP-ORFAO"}],
                  groups=SYSTEM + [{"id": "Grupo Sem Campanha"}])
    assert _status(res, ENT_PROMOTIONS, "PROMO-ORFA") == ELEGIVEL
    assert _status(res, ENT_COUPONS, "CUP-ORFAO") == ELEGIVEL
    assert _status(res, ENT_GROUPS, "Grupo Sem Campanha") == ELEGIVEL
    assert res.items[ENT_COUPONS]["CUP-ORFAO"].reason == "Sem campanha"


def test_cupom_desativado_sem_campanha_tambem_sai(tmp_path):
    _, res = _run(tmp_path, coupons=[{"id": "CUP-OFF", "enabled": False}])
    assert _status(res, ENT_COUPONS, "CUP-OFF") == ELEGIVEL


def test_resultado_nao_depende_de_execucoes_anteriores(tmp_path):
    kw = dict(promotions=["P"], coupons=[{"id": "C"}])
    _, r1 = _run(tmp_path, **kw)
    _, r2 = _run(tmp_path, **kw)
    assert {e: dict(r1.counts(e)) for e in le.ENTITIES} == {e: dict(r2.counts(e)) for e in le.ENTITIES}


# ── Cascata ──────────────────────────────────────────────────────────────────
def test_ca05_item_ligado_a_campanha_que_fica_e_protegido(tmp_path):
    _, res = _run(
        tmp_path,
        campaigns=[
            {"id": "VELHA", "end": OLD, "coupons": ["CUP-COMP"], "groups": ["NAT-RR100"]},
            {"id": "ATIVA", "end": _iso(NOW + timedelta(days=10)), "coupons": ["CUP-COMP"],
             "groups": ["NAT-RR100"]},
        ],
        promotions=["PROMO-COMP"],
        assignments=[{"camp": "VELHA", "promo": "PROMO-COMP"}, {"camp": "ATIVA", "promo": "PROMO-COMP"}],
        coupons=[{"id": "CUP-COMP"}],
        groups=SYSTEM + [{"id": "NAT-RR100"}],
    )
    assert _status(res, ENT_CAMPAIGNS, "VELHA") == ELEGIVEL
    assert _status(res, ENT_PROMOTIONS, "PROMO-COMP") == PROTEGIDO
    assert _status(res, ENT_COUPONS, "CUP-COMP") == PROTEGIDO
    assert _status(res, ENT_GROUPS, "NAT-RR100") == PROTEGIDO


def test_item_de_campanha_na_carencia_fica(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "RECENTE", "end": _iso(NOW - timedelta(days=3)),
                                        "coupons": ["CUP-R"], "groups": ["Grupo R"]}],
                  coupons=[{"id": "CUP-R"}], groups=SYSTEM + [{"id": "Grupo R"}])
    assert _status(res, ENT_COUPONS, "CUP-R") == PROTEGIDO
    assert _status(res, ENT_GROUPS, "Grupo R") == PROTEGIDO


def test_itens_de_campanha_excluida_saem_juntos(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "VELHA", "end": OLD, "coupons": ["CUP-V"],
                                        "groups": ["Segunda Compra"]}],
                  promotions=["PROMO-V"], assignments=[{"camp": "VELHA", "promo": "PROMO-V"}],
                  coupons=[{"id": "CUP-V"}], groups=SYSTEM + [{"id": "Segunda Compra"}])
    assert _status(res, ENT_PROMOTIONS, "PROMO-V") == ELEGIVEL
    assert _status(res, ENT_COUPONS, "CUP-V") == ELEGIVEL
    assert _status(res, ENT_GROUPS, "Segunda Compra") == ELEGIVEL


def test_vinculo_com_campanha_fora_do_arquivo_vai_para_revisar(tmp_path):
    _, res = _run(tmp_path, promotions=["PROMO-X"],
                  assignments=[{"camp": "NAO-EXISTE", "promo": "PROMO-X", "coupons": ["CUP-X"]}],
                  coupons=[{"id": "CUP-X"}])
    assert _status(res, ENT_PROMOTIONS, "PROMO-X") == REVISAR
    assert _status(res, ENT_COUPONS, "CUP-X") == REVISAR


def test_cupom_desativado_mas_em_uso_fica_e_avisa(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "ATIVA", "coupons": ["CUP-OFF"]}],
                  coupons=[{"id": "CUP-OFF", "enabled": False}])
    item = res.items[ENT_COUPONS]["CUP-OFF"]
    assert item.status == PROTEGIDO and "reative" in item.reason


# ── Customer groups: só os padrão do SFCC e DONT_REMOVE são protegidos ──────
def test_ca08_grupos_padrao_e_dont_remove_ficam(tmp_path):
    _, res = _run(tmp_path, groups=[
        {"id": "Everyone"}, {"id": "Registered"}, {"id": "Unregistered"},
        {"id": "DONATION_ORDER_DONT_REMOVE"}, {"id": "Grupo X", "desc": "dontremove — usado pelo checkout"},
    ])
    assert all(_status(res, ENT_GROUPS, g) == PROTEGIDO for g in res.items[ENT_GROUPS])


def test_termos_antigos_de_infraestrutura_nao_protegem(tmp_path):
    _, res = _run(tmp_path, groups=SYSTEM + [{"id": "System_Team"}, {"id": "productNotFoundLogged"}])
    assert _status(res, ENT_GROUPS, "System_Team") == ELEGIVEL
    assert _status(res, ENT_GROUPS, "productNotFoundLogged") == ELEGIVEL


def test_lista_protegida_vazia_por_padrao_e_opcional(tmp_path):
    assert le.DEFAULT_PROTECTED_TERMS == ()
    _, res = _run(tmp_path, groups=SYSTEM + [{"id": "crm-vip"}], coupons=[{"id": "crm-boas-vindas"}],
                  protected_terms=["crm"])
    assert _status(res, ENT_GROUPS, "crm-vip") == PROTEGIDO
    assert _status(res, ENT_COUPONS, "crm-boas-vindas") == PROTEGIDO


# ── Identificação da loja (regra 3 — incidente do Chile) ────────────────────
def test_loja_identificada_pelo_catalogo(tmp_path):
    _, res = _run(tmp_path)
    assert res.detection.ok and res.store.key == "natura-br" and res.store.name == "Natura Brasil"
    _, avon_mx = _run(tmp_path, catalog="avon-mx-storefront-catalog", skus=("AVNMEX-197114",))
    assert avon_mx.detection.ok and avon_mx.store.name == "Avon México"


def test_export_de_outra_loja_e_identificado_como_ela(tmp_path):
    _, res = _run(tmp_path, catalog="natura-cl-storefront-catalog", skus=("NATCHL-218971",))
    assert res.detection.ok and res.store.key == "natura-cl"


def test_produto_de_outro_pais_bloqueia(tmp_path):
    _, res = _run(tmp_path, skus=("NATBRA-1001", "NATCHL-48863"))
    assert not res.detection.ok and "Chile" in res.blocked_msg and not res.can_export


def test_produto_de_outro_pais_no_arquivo_de_cupons_bloqueia(tmp_path):
    _, res = _run(tmp_path, coupons=[{"id": "NATPER-14168"}])
    assert not res.detection.ok and "Peru" in res.blocked_msg


def test_catalogo_desconhecido_bloqueia(tmp_path):
    _, res = _run(tmp_path, catalog="tbs-chile-storefront-catalog", skus=())
    assert not res.detection.ok and "tbs-chile-storefront-catalog" in res.blocked_msg


def test_sem_catalogo_nenhum_bloqueia(tmp_path):
    files = _write(tmp_path, _promotions_xml([{"id": "C"}]), _coupons_xml(), _groups_xml(SYSTEM))
    res = LimpezaEngine(files, now=NOW).simulate()
    assert not res.detection.ok and res.store is None and "nenhum catálogo" in res.blocked_msg


def test_catalogos_de_duas_lojas_bloqueiam(tmp_path):
    promos = _promotions_xml([{"id": "C"}], ["P1"]).replace(
        "</promotions>",
        '<promotion promotion-id="P2"><x catalog-id="avon-br-storefront-catalog"/></promotion></promotions>')
    files = _write(tmp_path, promos, _coupons_xml(), _groups_xml(SYSTEM))
    res = LimpezaEngine(files, now=NOW).simulate()
    assert not res.detection.ok and "mais de uma loja" in res.blocked_msg


def test_catalogo_compartilhado_nao_conta(tmp_path):
    promos = _promotions_xml([{"id": "C"}], ["P1"]).replace(
        "</promotions>",
        '<promotion promotion-id="P2"><x catalog-id="nat-master-catalog"/></promotion></promotions>')
    files = _write(tmp_path, promos, _coupons_xml(), _groups_xml(SYSTEM))
    res = LimpezaEngine(files, now=NOW).simulate()
    assert res.detection.ok and res.store.key == "natura-br"


def test_loja_bloqueada_nao_exporta(tmp_path):
    eng, res = _run(tmp_path, campaigns=[{"id": "VELHA", "end": OLD}], skus=("NATBRA-1", "NATMEX-50212"))
    assert res.affected_total > 0 and not res.can_export
    with pytest.raises(LimpezaError):
        eng.export(res, str(tmp_path))


def test_arquivos_gerados_levam_a_loja_no_nome_e_no_topo(tmp_path):
    eng, res = _run(tmp_path, campaigns=[{"id": "VELHA", "end": OLD}])
    out = eng.export(res, str(tmp_path))
    assert Path(out.folder).name.startswith("LIMPEZA_NATURA-BR_")
    for f in out.files:
        assert "NATURA-BR" in Path(f).name
        if f.endswith(".xml"):
            head = Path(f).read_text(encoding="utf-8")[:400]
            assert "Importe SOMENTE no site Natura Brasil" in head


def test_emoji_exportado_em_par_de_referencias_nao_derruba_e_volta_no_rollback(tmp_path):
    # O SFCC exporta 📝 como "&#55357;&#56541;" (inválido em XML) — caso real do Chile
    eng, res = _run(tmp_path, campaigns=[{"id": "VELHA", "end": OLD}], promotions=["PROMO-EMOJI"],
                    assignments=[{"camp": "VELHA", "promo": "PROMO-EMOJI"}])
    promo_path = Path(eng.files[KIND_PROMOTIONS])
    promo_path.write_text(promo_path.read_text(encoding="utf-8").replace(
        ">PROMO-EMOJI</name>", ">Oferta &#55357;&#56541; &#1; fim</name>"), encoding="utf-8")
    eng = LimpezaEngine(eng.files, now=NOW)
    res = eng.simulate()
    assert res.items[ENT_PROMOTIONS]["PROMO-EMOJI"].info["Nome"] == "Oferta \U0001F4DD  fim"
    out = eng.export(res, str(tmp_path))
    rb = Path(out.folder, le.file_name(le.FILE_PROMO_ROLLBACK, res.store)).read_text(encoding="utf-8")
    assert "Oferta \U0001F4DD  fim" in rb


def test_leitor_corrige_par_cortado_entre_blocos(tmp_path):
    p = tmp_path / "x.xml"
    p.write_bytes(b"<a>" + b"y" * 20 + b"&#55357;&#56541;</a>")
    reader = le._CleanXmlReader(str(p))
    data = b""
    while chunk := reader.read(26):   # corta no meio do par
        data += chunk
    reader.close()
    assert data == b"<a>" + b"y" * 20 + b"&#128221;</a>"


def test_varredura_nao_perde_sinal_na_divisa_dos_blocos(tmp_path):
    p = tmp_path / "grande.xml"
    filler = b"x" * ((4 << 20) - 10)
    p.write_bytes(filler + b' catalog-id="natura-cl-storefront-catalog" NATCHL-1 ' + filler)
    cats, countries = le._scan_signals(str(p))
    assert cats == {"natura-cl-storefront-catalog": 1} and countries == {"cl": 1}


# ── Exportação e conferência do rollback ─────────────────────────────────────
def _cenario_completo(tmp_path):
    return _run(
        tmp_path,
        campaigns=[{"id": "VELHA", "end": OLD, "coupons": ["CUP-MULTI"], "groups": ["NAT-RR42"]},
                   {"id": "ATIVA", "coupons": ["CUP-OK"]}],
        promotions=["PROMO-VELHA"],
        assignments=[{"camp": "VELHA", "promo": "PROMO-VELHA"}],
        coupons=[{"id": "CUP-MULTI", "codes": 25}, {"id": "CUP-OK", "codes": 4}, {"id": "CUP-ORFAO"}],
        groups=SYSTEM + [{"id": "NAT-RR42", "dynamic": False, "members": 3}],
    )


def test_ca13_rollback_completo_com_codigos_e_membros(tmp_path):
    eng, res = _cenario_completo(tmp_path)
    assert res.ids(ENT_COUPONS, ELEGIVEL) == {"CUP-MULTI", "CUP-ORFAO"}
    out = eng.export(res, str(tmp_path))
    delete = ET.parse(Path(out.folder, le.file_name(le.FILE_COUPON_DELETE, res.store))).getroot()
    assert {c.attrib["coupon-id"] for c in delete} == {"CUP-MULTI", "CUP-ORFAO"}
    assert all(c.attrib["mode"] == "delete" for c in delete)
    rb = ET.parse(Path(out.folder, le.file_name(le.FILE_COUPON_ROLLBACK, res.store))).getroot()
    blocks = rb.findall("{*}coupon-codes")
    assert [b.attrib["coupon-id"] for b in blocks] == ["CUP-MULTI"]
    assert len(blocks[0]) == 25
    tags = [le._local(e.tag) for e in rb]
    assert tags.index("coupon-codes") > max(i for i, t in enumerate(tags) if t == "coupon")
    grb = ET.parse(Path(out.folder, le.file_name(le.FILE_GROUP_ROLLBACK, res.store))).getroot()
    assert len(grb.findall("{*}group-assignment")) == 3
    prb = ET.parse(Path(out.folder, le.file_name(le.FILE_PROMO_ROLLBACK, res.store))).getroot()
    assert [le._local(e.tag) for e in prb] == ["campaign", "promotion", "promotion-campaign-assignment"]
    name = prb.find("{*}promotion/{*}name")
    assert name is not None and name.attrib   # xml:lang preservado
    names = {Path(f).name for f in out.files}
    assert names == {le.file_name(t, res.store) for t in (
        le.FILE_PROMO_DELETE, le.FILE_COUPON_DELETE, le.FILE_GROUP_DELETE, le.FILE_GROUP_ROLLBACK,
        le.FILE_COUPON_ROLLBACK, le.FILE_PROMO_ROLLBACK, le.FILE_SHEET)}


def test_ca13_divergencia_na_conferencia_nao_gera_nada(tmp_path):
    eng, res = _cenario_completo(tmp_path)
    eng.coupons["CUP-MULTI"]["codes"] += 1   # simula rollback incompleto
    out_dir = tmp_path / "saida"
    out_dir.mkdir()
    with pytest.raises(LimpezaError, match="conferência"):
        eng.export(res, str(out_dir))
    assert list(out_dir.iterdir()) == []


def test_os_3_rollbacks_sao_gerados_mesmo_vazios(tmp_path):
    eng, res = _run(tmp_path, campaigns=[{"id": "VELHA", "end": OLD}])
    out = eng.export(res, str(tmp_path))
    for t in (le.FILE_GROUP_ROLLBACK, le.FILE_COUPON_ROLLBACK, le.file_name(le.FILE_PROMO_ROLLBACK, res.store)):
        path = Path(out.folder, le.file_name(t, res.store))
        assert path.exists()
        ET.parse(path)   # XML válido


# ── Travas ───────────────────────────────────────────────────────────────────
def test_ca15_arquivos_incoerentes_bloqueiam(tmp_path):
    campaigns = [{"id": f"C{i}", "coupons": [f"CUP{i}"]} for i in range(10)]
    eng, res = _run(tmp_path, campaigns=campaigns,
                    coupons=[{"id": "OUTRA-LOJA-1"}, {"id": "OUTRA-LOJA-2"}])
    assert not res.coherence_ok
    with pytest.raises(LimpezaError):
        eng.export(res, str(tmp_path))


def test_ca16_freio_de_volume(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "A", "end": OLD}, {"id": "B", "end": OLD}, {"id": "C"}])
    assert res.volume_alerts and "Campanhas" in res.volume_alerts[0]


def test_planilha_tem_resumo_e_uma_aba_por_entidade(tmp_path):
    _, res = _cenario_completo(tmp_path)
    wb = le.build_workbook(res)
    assert wb.sheetnames == ["Resumo", "Campanhas", "Promoções", "Cupons", "Customer groups"]
