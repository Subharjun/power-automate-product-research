#!/usr/bin/env python3
"""Clean product data, strictly match preferences, and prepare per-customer messages."""
import argparse,csv,json,re
from pathlib import Path

def read_csv(path):
    with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--config",default="config.json");args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text());out=Path(cfg["output_dir"]);out.mkdir(exist_ok=True,parents=True)
    products=read_csv(out/"products.csv"); customer_path=Path("customers.csv"); customers=read_csv(customer_path)
    (out/"customers.csv").write_bytes(customer_path.read_bytes())
    clean=[]; seen=set()
    for p in products:
        p={k:(v or "").strip() for k,v in p.items()}; key=p.get("product_url","")
        if not key or key in seen:continue
        seen.add(key)
        try:p["price_gbp"]=float(p["price_gbp"])
        except (ValueError,TypeError):p["price_gbp"]=None
        try:p["rating"]=int(p["rating"])
        except (ValueError,TypeError):p["rating"]=None
        p["category_clean"]=re.sub(r"\s+"," ",p.get("category","")).strip().casefold()
        clean.append(p)
    cap=int(cfg.get("matching",{}).get("max_recommendations",3)); result_rows=[]; drafts=[]
    for c in customers:
        wanted=[re.sub(r"\s+"," ",x).strip().casefold() for x in c["preferred_categories"].split("|") if x.strip()]
        budget=float(c["max_budget_gbp"]); minimum=int(c["min_rating"])
        matches=[p for p in clean if p["category_clean"] in wanted and p["price_gbp"] is not None and p["rating"] is not None and p["price_gbp"]<=budget and p["rating"]>=minimum]
        matches.sort(key=lambda p:(-p["rating"],p["price_gbp"],p["title"].casefold()))
        selected=matches[:cap]
        for rank,p in enumerate(selected,1):
            reason=f"{p['category']} matches your preference; £{p['price_gbp']:.2f} is within your £{budget:.2f} budget; {p['rating']}/5 meets your {minimum}/5 minimum rating."
            result_rows.append({"customer_id":c["customer_id"],"customer_name":c["name"],"rank":rank,"record_id":p["record_id"],"title":p["title"],"product_url":p["product_url"],"price_gbp":f"{p['price_gbp']:.2f}","rating":p["rating"],"category":p["category"],"reason":reason})
        lines=[f"{i+1}. {p['title']} — £{p['price_gbp']:.2f}\n   {p['product_url']}\n   {p['category']}, rated {p['rating']}/5: matches your category and meets your budget and rating limits." for i,p in enumerate(selected)]
        email_body=(f"Hi {c['name']},\n\nHere are {len(selected)} book pick(s) based on your preferences:\n\n"+("\n\n".join(lines) if lines else "No books in the collected catalogue met all your stated category, budget, and rating requirements." )+"\n\nHappy reading!")
        short=(f"Hi {c['name']}! Your book picks:\n"+"\n".join(f"{p['title']} (£{p['price_gbp']:.2f}) {p['product_url']} — {p['category']}, {p['rating']}/5 fits your limits." for p in selected) if selected else f"Hi {c['name']}! No books in this catalogue sample met all your selected category, budget and rating limits.")
        drafts.append({"customer_id":c["customer_id"],"name":c["name"],"email_subject":f"Book picks selected for you, {c['name']}","email_body":email_body,"whatsapp_message":short,"match_count":len(selected),"mode":"draft"})
    with (out/"matching_results.csv").open("w",newline="",encoding="utf-8") as f:
        fields=["customer_id","customer_name","rank","record_id","title","product_url","price_gbp","rating","category","reason"];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(result_rows)
    (out/"messages.json").write_text(json.dumps(drafts,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"Prepared {len(drafts)} customer message sets; {len(result_rows)} qualifying recommendations.")
if __name__=="__main__":main()
