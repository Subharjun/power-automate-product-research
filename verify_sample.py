#!/usr/bin/env python3
"""Refetch five spaced product detail pages and compare scraped fields to the saved CSV."""
import csv,json
from datetime import datetime,timezone
from pathlib import Path
from extract_products import detail

def main():
    out=Path("output"); rows=list(csv.DictReader((out/"products.csv").open(encoding="utf-8-sig")))
    indices=sorted(set([0,len(rows)//4,len(rows)//2,(3*len(rows))//4,len(rows)-1]))
    fields=["title","price_gbp","rating","category","availability","description"]
    checks=[]
    for i in indices:
        expected=rows[i]; actual=detail(expected["product_url"],"")
        mismatches=[f for f in fields if str(expected.get(f,""))!=str(actual.get(f,""))]
        checks.append({"record_id":expected["record_id"],"product_url":expected["product_url"],"fields_compared":fields,"result":"PASS" if not mismatches else "MISMATCH","mismatches":mismatches})
    report={"verified_at":datetime.now(timezone.utc).isoformat(),"method":"Refetched source detail pages and compared parsed values with CSV rows.","sample_size":len(checks),"pass_count":sum(x["result"]=="PASS" for x in checks),"checks":checks}
    (out/"verification.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"Verified {report['pass_count']}/{len(checks)} sample detail pages; see output/verification.json")
    if report["pass_count"]!=len(checks):raise SystemExit(1)
if __name__=="__main__":main()
