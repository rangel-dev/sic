import os
import openpyxl

os.makedirs('test_audit', exist_ok=True)

# 1. Pricebook
xml_pb = """<?xml version="1.0" encoding="UTF-8"?>
<pricebooks xmlns="http://www.demandware.com/xml/impex/pricebook/2006-10-31">
    <pricebook>
        <header pricebook-id="br-natura-brazil-list-prices"/>
        <price-tables>
            <price-table product-id="NATBRA-EXP1"><amount quantity="1">100.00</amount></price-table>
            <price-table product-id="NATBRA-EXP2"><amount quantity="1">100.00</amount></price-table>
        </price-tables>
    </pricebook>
    <pricebook>
        <header pricebook-id="br-natura-brazil-sale-prices"/>
        <price-tables>
            <price-table product-id="NATBRA-EXP1"><amount quantity="1">50.00</amount></price-table>
            <price-table product-id="NATBRA-EXP2"><amount quantity="1">50.00</amount></price-table>
        </price-tables>
    </pricebook>
    <pricebook>
        <header pricebook-id="br-cb-brazil-list-prices"/>
        <price-tables>
            <price-table product-id="NATBRA-EXP3"><amount quantity="1">100.00</amount></price-table>
        </price-tables>
    </pricebook>
    <pricebook>
        <header pricebook-id="br-cb-brazil-sale-prices"/>
        <price-tables>
            <price-table product-id="NATBRA-EXP3"><amount quantity="1">50.00</amount></price-table>
        </price-tables>
    </pricebook>
</pricebooks>
"""
with open("test_audit/pb_margin_conflict.xml", "w") as f: f.write(xml_pb)

# 2. Natura Catalog
xml_cat_natura = """<?xml version="1.0" encoding="UTF-8"?>
<catalog xmlns="http://www.demandware.com/xml/impex/catalog/2006-10-31" catalog-id="natura-br">
    <product product-id="NATBRA-EXP1"><online-flag>true</online-flag></product>
    <product product-id="NATBRA-EXP2"><online-flag>true</online-flag></product>
    <category-assignment product-id="NATBRA-EXP1" category-id="LISTA_02"><primary-flag>true</primary-flag></category-assignment>
    <category-assignment product-id="NATBRA-EXP2" category-id="monte-seu-kit"><primary-flag>true</primary-flag></category-assignment>
</catalog>
"""
with open("test_audit/cat_natura_margin_conflict.xml", "w") as f: f.write(xml_cat_natura)

# 3. ML Catalog
xml_cat_ml = """<?xml version="1.0" encoding="UTF-8"?>
<catalog xmlns="http://www.demandware.com/xml/impex/catalog/2006-10-31" catalog-id="cb-br">
    <product product-id="NATBRA-EXP3"><online-flag>true</online-flag></product>
    <category-assignment product-id="NATBRA-EXP3" category-id="monte-seu-kit"><primary-flag>true</primary-flag></category-assignment>
</catalog>
"""
with open("test_audit/cat_ml_margin_conflict.xml", "w") as f: f.write(xml_cat_ml)

# 4. Excel Grade
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "GRADE"
ws.append(["SKU", "DE", "POR", "VISIBLE"])
ws.append(["NATBRA-EXP1", 100.0, 50.0, "SIM"])
ws.append(["NATBRA-EXP2", 100.0, 50.0, "SIM"])
ws.append(["NATBRA-EXP3", 100.0, 50.0, "SIM"])
wb.save("test_audit/excel_margin_conflict.xlsx")

print("Files generated!")
