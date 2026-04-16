"""
Brand Detector Utility – Smart Content Identification
Identifies if a file (XML/Excel) belongs to Natura, Avon, or CB (Minha Loja).
"""
import re
import os
from pathlib import Path
from typing import Optional

class BrandDetector:
    @staticmethod
    def detect(file_path: str) -> str:
        """
        Main entry point. Detects brand based on file extension and content peeking.
        Returns: "natura", "avon", "ml", or "unknown"
        """
        if not file_path or not os.path.exists(file_path):
            return "unknown"
        
        ext = Path(file_path).suffix.lower()
        
        if ext == ".xml":
            return BrandDetector._detect_xml(file_path)
        elif ext in [".xlsx", ".xls"]:
            return BrandDetector._detect_excel(file_path)
        
        return "unknown"

    @staticmethod
    def _detect_xml(path: str) -> str:
        """Peeks into the first 8KB of an XML to find brand markers."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(8192).lower()
                
                # Check for Minha Loja (CB) IDs first
                if any(x in head for x in ["cb-br", "cbbrazil", "cbcom", "cb_br"]):
                    return "ml"
                
                # Check for Natura/Avon
                if "natura" in head:
                    return "natura"
                if "avon" in head:
                    return "avon"
                    
                # Fallback to looking for SKU patterns in the first chunk
                if "natbra-" in head: return "natura"
                if "avnbra-" in head: return "avon"
        except:
            pass
        return "unknown"

    @staticmethod
    def _detect_excel(path: str) -> str:
        """Lightweight scan of the first few rows/names of an Excel file."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            
            # Detect by sheet names first
            sheet_names_joined = " ".join(wb.sheetnames).upper()
            if "NATURA" in sheet_names_joined: 
                wb.close()
                return "natura"
            if "AVON" in sheet_names_joined:
                wb.close()
                return "avon"

            # Detect by content peeking in the first visible sheet
            sheet = None
            for name in wb.sheetnames:
                if wb[name].sheet_state == 'visible':
                    sheet = wb[name]
                    break
            
            if not sheet:
                wb.close()
                return "unknown"
            
            nat = avn = 0
            # Scan first 100 rows, should be very fast in read_only
            for row in sheet.iter_rows(max_row=100, values_only=True):
                for cell in row:
                    if cell:
                        v = str(cell).upper()
                        if "NATBRA-" in v: nat += 1
                        if "AVNBRA-" in v: avn += 1
            
            wb.close()
            
            if nat > 0 and avn > 0: return "ml" # Multibrand is often ML context
            if nat > 0: return "natura"
            if avn > 0: return "avon"
        except:
            pass
        return "unknown"

    @staticmethod
    def get_brand_display_name(brand: str) -> str:
        return {
            "natura": "Natura",
            "avon":   "Avon",
            "ml":     "Minha Loja",
            "unknown": "Desconhecida"
        }.get(brand, "Desconhecida")

    @staticmethod
    def get_brand_color(brand: str) -> str:
        """Primary brand colors for UI highlighting."""
        return {
            "natura": "#FF8050", # Orange
            "avon":   "#BB88FF", # Purple
            "ml":     "#2196F3", # Blue
            "unknown": "#666666"  # Grey
        }.get(brand, "#666666")
