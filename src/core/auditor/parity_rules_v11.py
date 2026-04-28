"""
🔒 DO NOT MODIFY THIS FILE 🔒
=========================================
This file contains the certified legacy logic (v11.6 Parity).
Any changes made to this file will break functional parity with the original Pricing Master Suite.
An integrity hash checks this file at runtime. Any modification will trigger a critical integrity alert.
=========================================
"""
import re

SKU_RE = re.compile(r"^(NAT|AVN)BRA-", re.IGNORECASE)

def execute_parity_rules(
    all_skus, excel_prices, online_status, prices_xml,
    bundles, variation_bases, searchable_status, technical_skus,
    excel_lists, xml_lists, cat_missing_primary, prohibited_state,
    job_errors, has_nat, has_avn, errors, dump_stats
):
    for sku in all_skus:
        if not SKU_RE.match(sku):
            continue

        brand = "Natura" if sku.startswith("NATBRA-") else "Avon"
        pE = excel_prices.get(sku)
        is_offline      = online_status.get(sku) is not True
        is_on_grade     = pE is not None

        if is_offline and not is_on_grade:
            continue

        px     = (prices_xml.get(sku) or {}).get(brand, {})
        px_ml  = (prices_xml.get(sku) or {}).get("ML", {})
        px_nat = (prices_xml.get(sku) or {}).get("Natura", {})
        px_avn = (prices_xml.get(sku) or {}).get("Avon", {})

        px_de  = px.get("DE", 0) or 0
        px_por = px.get("POR", 0) or 0

        sf_ml_de  = px_ml["DE"]  if "DE"  in px_ml else px_de
        sf_ml_por = px_ml["POR"] if "POR" in px_ml else px_por

        row_base = {"sku": sku, "brand": brand}

        # ── Check #1: PRODUTO OFFLINE (estava no Excel) ───────────────
        if is_offline and is_on_grade:
            errors["offline"].append({**row_base, "detail": "PRODUTO OFFLINE (Ação Comercial Exigida)"})
            dump_stats("offline", brand)

        if not is_offline:
            # ── Check #2: BUNDLE QUEBRADO ─────────────────────────────
            if sku in bundles:
                offline_comps = []
                missing_price_comps = []
                for comp in bundles[sku]:
                    if variation_bases.get(comp):
                        continue
                    if online_status.get(comp) is not True:
                        offline_comps.append(comp)
                    comp_px = (prices_xml.get(comp) or {}).get(brand, {})
                    if (comp_px.get("DE") or 0) <= 0 or (comp_px.get("POR") or 0) <= 0:
                        missing_price_comps.append(comp)

                if offline_comps or missing_price_comps:
                    parts = []
                    if offline_comps:
                        parts.append(f"Comp. Offline: {', '.join(offline_comps)}")
                    if missing_price_comps:
                        parts.append(f"Comp. sem preço: {', '.join(missing_price_comps)}")
                    errors["bundle"].append({**row_base, "detail": f"BUNDLE QUEBRADO ({' ; '.join(parts)})"})
                    dump_stats("bundle", brand)

            # ── Check #3: CROSS-BRAND ─────────────────────────────────
            has_nat_price = bool(px_nat.get("DE") or px_nat.get("POR"))
            has_avn_price = bool(px_avn.get("DE") or px_avn.get("POR"))
            if brand == "Natura" and has_avn_price:
                errors["cross"].append({**row_base, "detail": "MARCA CRUZADA (NAT no Pricebook AVN)"})
                dump_stats("cross", brand)
            if brand == "Avon" and has_nat_price:
                errors["cross"].append({**row_base, "detail": "MARCA CRUZADA (AVN no Pricebook NAT)"})
                dump_stats("cross", brand)

            # Os checks seguintes só correm se temos Excel para esta marca
            should_compare = (brand == "Natura" and has_nat) or (brand == "Avon" and has_avn)
            if should_compare:
                if pE:
                    e_de  = pE.get("DE", 0) or 0
                    e_por = pE.get("POR", 0) or 0

                    # ── Check #4: PREÇO AUSENTE NO SF ────────────────
                    if not px_de and not px_por:
                        errors["price"].append({**row_base, "de_excel": e_de, "de_sf": 0,
                                                "por_excel": e_por, "por_sf": 0,
                                                "detail": "FALTA NO SF (PREÇO)"})
                        dump_stats("price", brand)
                    else:
                        # ── Check #5: DIVERGÊNCIA DE PREÇO ───────────
                        if e_de > 0 and abs(e_de - px_de) > 0.01:
                            errors["price"].append({**row_base, "de_excel": e_de, "de_sf": px_de,
                                                    "por_excel": e_por, "por_sf": px_por,
                                                    "detail": f"DIVERGE SF (DE GRADE: R${e_de:.2f} vs DE SF: R${px_de:.2f})"})
                            dump_stats("price", brand)
                        if e_por > 0 and abs(e_por - px_por) > 0.01:
                            errors["price"].append({**row_base, "de_excel": e_de, "de_sf": px_de,
                                                    "por_excel": e_por, "por_sf": px_por,
                                                    "detail": f"DIVERGE SF (POR GRADE: R${e_por:.2f} vs POR SF: R${px_por:.2f})"})
                            dump_stats("price", brand)

                    # ── Check #6: SEARCHABLE vs VISIBLE ──────────────
                    vis = pE.get("VISIBLE", "")
                    is_visible_excel = (vis == "SIM")
                    is_hidden_excel  = (vis in ("NÃO", "NAO"))
                    is_searchable_sf = searchable_status.get(sku) is True
                    if not technical_skus.get(sku):
                        if is_visible_excel and not is_searchable_sf:
                            errors["searchable"].append({**row_base,
                                "detail": "DIVERGE SEARCHABLE (Excel SIM vs SF false)"})
                            dump_stats("searchable", brand)
                        elif is_hidden_excel and is_searchable_sf:
                            errors["searchable"].append({**row_base,
                                "detail": "DIVERGE SEARCHABLE (Excel NÃO vs SF true)"})
                            dump_stats("searchable", brand)

                    # ── Check #7: LISTAS DE VITRINE ───────────────────
                    for list_id, ex_skus in excel_lists.items():
                        list_is_mine = (
                            (brand == "Natura" and list_id.startswith("LISTA_")) or
                            (brand == "Avon"   and list_id.startswith("lista-"))
                        )
                        if not list_is_mine:
                            continue
                        if sku not in ex_skus:
                            continue
                        if list_id not in xml_lists:
                            errors["list"].append({**row_base,
                                "detail": f"LISTA INEXISTENTE NO SF ({list_id})"})
                            dump_stats("list", brand)
                        elif sku not in xml_lists[list_id]:
                            errors["list"].append({**row_base,
                                "detail": f"FALTA NO SF ({list_id})"})
                            dump_stats("list", brand)

            # Checks que dependem apenas de preços SF (sem obrigar Excel)
            if px_de or px_por or sf_ml_de or sf_ml_por or sku in cat_missing_primary:
                # ── Check #8: FALTA PREÇO DE / POR ───────────────────
                if px_por == 0 and px_de != 0:
                    errors["missing"].append({**row_base, "ausente": "POR",
                                              "detail": "FALTA PREÇO POR"})
                    dump_stats("missing", brand)
                if px_de == 0 and px_por != 0:
                    errors["missing"].append({**row_base, "ausente": "DE",
                                              "detail": "FALTA PREÇO DE"})
                    dump_stats("missing", brand)

                # ── Check #9: POR > DE ────────────────────────────────
                if px_por > px_de > 0:
                    errors["logic"].append({**row_base, "de": px_de, "por": px_por,
                                            "detail": f"POR > DE (R${px_por:.2f} > R${px_de:.2f})"})
                    dump_stats("logic", brand)

                # ── Check #10: CONFLITO DE MARGEM ─────────────────────
                is_promo_brand = px_por < px_de and px_por > 0
                is_promo_ml    = sf_ml_por < sf_ml_de and sf_ml_por > 0
                if is_promo_brand and sku in prohibited_state.get(brand, set()):
                    errors["margin"].append({**row_base,
                        "detail": f"CONFLITO PROG ({brand})"})
                    dump_stats("margin", brand)
                if is_promo_ml and sku in prohibited_state.get("ML", set()):
                    errors["margin"].append({**row_base,
                        "detail": "CONFLITO PROG (Minha Loja)"})
                    dump_stats("margin", brand)

                # ── Check #11: DIVERGÊNCIA ML ─────────────────────────
                if (px_por > 0 or sf_ml_por > 0) and abs(px_por - sf_ml_por) > 0.01:
                    errors["ml"].append({**row_base,
                        "detail": f"DIVERGE ML (POR: Marca R${px_por:.2f} vs ML R${sf_ml_por:.2f})"})
                    dump_stats("ml", brand)
                if (px_de > 0 or sf_ml_de > 0) and abs(px_de - sf_ml_de) > 0.01:
                    errors["ml"].append({**row_base,
                        "detail": f"DIVERGE ML (DE: Marca R${px_de:.2f} vs ML R${sf_ml_de:.2f})"})
                    dump_stats("ml", brand)

                # ── Check #12: CATEGORIA PRIMÁRIA ─────────────────────
                for cat_brand in (cat_missing_primary.get(sku) or []):
                    errors["primary"].append({**row_base,
                        "detail": f"FALTA CAT PRIMÁRIA ({cat_brand})"})
                    dump_stats("primary", brand)

            # ── Check JOB ─────────────────────────────────────────────
            for msg in (job_errors.get(sku) or []):
                errors["job"].append({**row_base, "detail": msg})
                dump_stats("job", brand)
