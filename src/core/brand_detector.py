"""
Brand Detector Utility – Smart Content Identification
Identifies if a file (XML/Excel) belongs to Natura, Avon, or CB (Minha Loja).
Supports multi-brand detection within a single file or across multiple files.
"""

import re
import os
from pathlib import Path
from typing import Optional, Set


class BrandDetector:
    @staticmethod
    def detect_single(file_path: str) -> set[str]:
        """
        Detects all brands within a SINGLE file.

        Parameters
        ----------
        file_path : str
            Path to a single file (XML or Excel)

        Returns
        -------
        set[str]
            Set of brand strings {"natura", "avon", "ml"} found in the file

        Example
        -------
        >>> BrandDetector.detect_single("/path/to/catalog_natura.xml")
        {"natura"}
        """
        if not file_path or not os.path.exists(file_path):
            return set()

        ext = Path(file_path).suffix.lower()

        if ext == ".xml":
            return BrandDetector._detect_xml_set(file_path)
        elif ext in [".xlsx", ".xlsm", ".xls"]:
            return BrandDetector._detect_excel_set(file_path)

        return set()

    @staticmethod
    def detect(file_paths: list[str]) -> set[str]:
        """
        Main entry point. Detects all brands across a list of files.

        Parameters
        ----------
        file_paths : list[str]
            List of file paths to scan

        Returns
        -------
        set[str]
            Union of all brands found across all files {"natura", "avon", "ml"}
        """
        all_brands = set()
        for path in file_paths:
            all_brands.update(BrandDetector.detect_single(path))
        return all_brands

    @staticmethod
    def _detect_xml_set(path: str) -> set[str]:
        """Peeks into an XML to find brand markers via pricebook/catalog IDs."""
        brands = set()
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                # Read entire file to ensure we catch all markers
                content = f.read().lower()

            # Heuristic: Pricebook files are typically larger (>10KB) and contain all 3 brands
            # Catalog files are smaller and usually single-brand
            file_size = os.path.getsize(path)
            is_likely_pricebook = file_size > 10240  # >10KB

            if is_likely_pricebook:
                # PRICEBOOK MODE: Use broad patterns (includes SKU patterns)
                # Natura: pricebook ID or SKU pattern
                if re.search(r"br-natura-brazil|natbra", content):
                    brands.add("natura")
                # Avon: pricebook ID or SKU pattern
                if re.search(r"brl-avon-brazil|br-avon-brazil|avnbra", content):
                    brands.add("avon")
                # CB/Minha Loja: pricebook ID
                if re.search(r"br-cb-brazil|cbbrazil", content):
                    brands.add("ml")
            else:
                # CATALOG MODE: Use strict catalog-specific patterns only
                # Natura: catalog-id pattern (avoid SKU false positives)
                if re.search(r"br-natura-brazil|natura-br[^a-z]", content):
                    brands.add("natura")
                # Avon: catalog-id pattern
                if re.search(r"brl-avon-brazil|avon-br[^a-z]", content):
                    brands.add("avon")
                # CB/Minha Loja: catalog-id pattern
                if re.search(r"br-cb-brazil|cbbrazil|cb-br[^a-z]", content):
                    brands.add("ml")

        except Exception as e:
            import sys
            print(f"Warning: XML detection failed for {path}: {e}", file=sys.stderr)
        return brands

    @staticmethod
    def _detect_excel_set(path: str) -> set[str]:
        """Lightweight scan of an Excel file to find brand signatures."""
        brands = set()
        try:
            import openpyxl

            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

            # Detect by sheet names
            sheet_names_joined = " ".join(wb.sheetnames).upper()
            if "NATURA" in sheet_names_joined:
                brands.add("natura")
            if "AVON" in sheet_names_joined:
                brands.add("avon")

            # Detect by content peeking in the first visible sheet
            sheet = None
            for name in wb.sheetnames:
                try:
                    if wb[name].sheet_state == "visible":
                        sheet = wb[name]
                        break
                except:
                    # Some sheets may not have sheet_state, try anyway
                    sheet = wb[name]
                    break

            if sheet:
                nat = avn = 0
                # Scan first 300 rows (or entire sheet if smaller)
                for row in sheet.iter_rows(max_row=300, values_only=True):
                    for cell in row:
                        if cell:
                            v = str(cell)
                            # Match NATBRA prefix (case-insensitive)
                            if re.search(r"natbra", v, re.IGNORECASE):
                                nat += 1
                            # Match AVNBRA prefix (case-insensitive)
                            if re.search(r"avnbra", v, re.IGNORECASE):
                                avn += 1
                    if nat > 0 and avn > 0:
                        break  # Found both

                if nat > 0:
                    brands.add("natura")
                if avn > 0:
                    brands.add("avon")

            # If no brands found yet, scan ALL visible sheets (not just first)
            if not brands:
                for sheet_name in wb.sheetnames:
                    try:
                        if wb[sheet_name].sheet_state == "visible":
                            sheet = wb[sheet_name]
                            nat = avn = 0
                            for row in sheet.iter_rows(max_row=300, values_only=True):
                                for cell in row:
                                    if cell:
                                        v = str(cell)
                                        if re.search(r"natbra", v, re.IGNORECASE):
                                            nat += 1
                                        if re.search(r"avnbra", v, re.IGNORECASE):
                                            avn += 1
                                if nat > 0 and avn > 0:
                                    break
                            if nat > 0:
                                brands.add("natura")
                            if avn > 0:
                                brands.add("avon")
                            if brands:
                                break
                    except:
                        pass

            wb.close()
        except Exception as e:
            # Log error for debugging, but don't break the app
            import sys
            print(f"Warning: Excel detection failed for {path}: {e}", file=sys.stderr)
        return brands

    @staticmethod
    def get_combined_display_name(brands) -> str:
        if isinstance(brands, str):
            brands = {brands}
        if not brands:
            return "Desconhecida"

        names = []
        if "natura" in brands:
            names.append("Natura")
        if "avon" in brands:
            names.append("Avon")
        if "ml" in brands:
            names.append("Minha Loja")

        return " + ".join(names)

    @staticmethod
    def get_brand_qss_state(brands: set[str]) -> str:
        """Returns a string to be used as 'brand' property in QSS."""
        if not brands:
            return ""
        if len(brands) >= 3:
            return "all"

        # Sort to ensure consistent property values for QSS matching
        sorted_brands = sorted(list(brands))
        return "_".join(sorted_brands)
