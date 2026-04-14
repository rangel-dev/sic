import sys
import os
sys.path.append('src/core')
from auditor_engine import AuditorEngine

engine = AuditorEngine()
paths_xl = ["test_audit/grade_natura.xlsx", "test_audit/grade_avon.xlsx"]
paths_pb = "test_audit/pricebook.xml"
paths_xml = [f for f in os.listdir("test_audit") if f.endswith(".xml") and "price" not in f]
paths_xml = [os.path.join("test_audit", f) for f in paths_xml]
paths_xl = [p for p in paths_xl if os.path.exists(p)]
paths_xml = [p for p in paths_xml if os.path.exists(p)]
if paths_xl and paths_xml:
    res = engine.run(paths_xl, paths_pb, paths_xml)
    print("STATS:", res.stats)
    print("ERRORS:", res.errors.get("price"))
