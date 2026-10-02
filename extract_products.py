#!/usr/bin/env python3
"""Resume-capable extractor for Books to Scrape; fetches catalogue and detail pages."""
import argparse, csv, json, logging, os, re, time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

FIELDS = ["record_id", "title", "product_url", "price_gbp", "rating", "category", "availability", "description", "upc"]

class Node:
    def __init__(self, tag, attrs): self.tag, self.attrs, self.children, self.parts, self.sequence = tag, dict(attrs), [], [], []
    def text(self): return " ".join(part if isinstance(part, str) else part.text() for part in self.sequence).strip()
    def walk(self):
        yield self
        for child in self.children: yield from child.walk()

class TreeParser(HTMLParser):
    VOID = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
    def __init__(self): super().__init__(convert_charrefs=True); self.root=Node("root",{}); self.stack=[self.root]
    def handle_starttag(self, tag, attrs):
        n=Node(tag,attrs); self.stack[-1].children.append(n); self.stack[-1].sequence.append(n)
        if tag not in self.VOID: self.stack.append(n)
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag,attrs); self.handle_endtag(tag)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag: del self.stack[i:]; break
    def handle_data(self, data): self.stack[-1].parts.append(data); self.stack[-1].sequence.append(data)

def parse(html):
    p=TreeParser(); p.feed(html); return p.root
def cls(n, name): return name in n.attrs.get("class", "").split()
def first(nodes, pred): return next((n for n in nodes if pred(n)), None)
def allnodes(root, tag=None): return [n for n in root.walk() if tag is None or n.tag==tag]
def fetch(url, timeout=30):
    req=Request(url, headers={"User-Agent":"ProductResearchInternAssignment/1.0 (educational; contact: example@example.invalid)"})
    with urlopen(req, timeout=timeout) as r: return r.read().decode("utf-8", "replace")
def rating_from(product):
    n=first(allnodes(product), lambda x: x.tag=="p" and "star-rating" in x.attrs.get("class", "").split())
    names={"One":1,"Two":2,"Three":3,"Four":4,"Five":5}
    return names.get(next((c for c in n.attrs.get("class","").split() if c in names), "")) if n else ""
def category_from(root):
    crumb=first(allnodes(root), lambda x: x.tag=="ul" and cls(x,"breadcrumb"))
    if not crumb: return ""
    links=[n for n in allnodes(crumb,"a")]
    return links[-1].text() if links else ""
def description_from(root):
    marker=first(allnodes(root), lambda x: x.tag=="div" and x.attrs.get("id")=="product_description")
    if not marker: return ""
    parent=next((p for p in root.walk() if marker in p.children), None)
    if not parent: return ""
    siblings=parent.children; i=siblings.index(marker)
    for n in siblings[i+1:]:
        if n.tag=="p" and n.text(): return re.sub(r"\s+", " ", n.text()).strip()
    return ""
def table_value(root, label):
    for row in (n for n in root.walk() if n.tag=="tr"):
        cells=[c.text() for c in row.children if c.tag in ("th","td")]
        if len(cells)>1 and cells[0].strip()==label: return cells[1].strip()
    return ""
def detail(url, category_fallback):
    root=parse(fetch(url)); main=first(allnodes(root),lambda x:x.tag=="div" and cls(x,"product_main")) or root
    h=first(allnodes(main,"h1"),lambda _:True); price=first(allnodes(main,"p"),lambda x:cls(x,"price_color"))
    stock=first(allnodes(main,"p"),lambda x:cls(x,"instock"))
    availability=re.sub(r"\s+"," ",stock.text()).strip() if stock else ""
    rawprice=price.text() if price else ""
    pm=re.search(r"([0-9]+(?:\.[0-9]+)?)",rawprice)
    title=h.text() if h else ""
    category=category_from(root) or category_fallback
    upc=table_value(root,"UPC")
    record_id=upc or re.sub(r"[^a-zA-Z0-9]+","-",url.rsplit("/",2)[-2]).strip("-").lower()
    return {"record_id":record_id,"title":title,"product_url":url,"price_gbp":float(pm.group(1)) if pm else "","rating":rating_from(main),"category":category,"availability":availability,"description":description_from(root),"upc":upc}
def save_csv(path, rows):
    tmp=path.with_suffix(".tmp")
    with tmp.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    tmp.replace(path)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="config.json"); ap.add_argument("--pages",type=int); args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text()); out=Path(cfg["output_dir"]); out.mkdir(parents=True,exist_ok=True)
    log=logging.getLogger("extract"); log.setLevel(logging.INFO); fh=logging.FileHandler(out/"processing.log",encoding="utf-8"); fh.setFormatter(logging.Formatter("%(asctime)sZ %(levelname)s %(message)s")); log.addHandler(fh)
    csvpath=out/"products.csv"; cp_path=out/"checkpoint.json"
    checkpoint=json.loads(cp_path.read_text()) if cp_path.exists() else {"completed_pages":[],"products":{}}
    rows=list(checkpoint["products"].values()); by_url={r["product_url"]:r for r in rows}
    pages=args.pages or int(cfg.get("catalogue_pages",5)); maxp=int(cfg.get("max_products",100)); base=cfg["base_url"].rstrip("/")
    for page in range(1,pages+1):
        if page in checkpoint["completed_pages"]: continue
        url=base+("/catalogue/page-1.html" if page==1 else f"/catalogue/page-{page}.html")
        try:
            root=parse(fetch(url)); articles=[n for n in allnodes(root,"article") if cls(n,"product_pod")]
            page_errors=0
            for art in articles:
                a=first(allnodes(art,"a"),lambda n:n.attrs.get("href") is not None)
                if not a: continue
                product_url=urljoin(url,a.attrs["href"])
                if product_url in by_url or len(by_url)>=maxp: continue
                log.info("detail_start url=%s",product_url)
                try:
                    title=first(allnodes(art,"h3"),lambda _:True)
                    rec=detail(product_url,"")
                    if not rec["title"] and title: rec["title"]=title.text()
                    by_url[product_url]=rec
                    checkpoint["products"]={r["product_url"]:r for r in by_url.values()}
                    checkpoint["last_product_url"]=product_url
                    cp_path.write_text(json.dumps(checkpoint,indent=2),encoding="utf-8")
                    save_csv(csvpath,list(by_url.values()))
                    log.info("product_saved record_id=%s url=%s",rec["record_id"],product_url)
                except Exception as e:
                    page_errors+=1; log.exception("detail_failed url=%s error=%s",product_url,e)
                time.sleep(float(cfg.get("request_delay_seconds",0.2)))
                if len(by_url)>=maxp: break
            if page_errors==0:
                checkpoint["completed_pages"].append(page); checkpoint["completed_pages"]=sorted(set(checkpoint["completed_pages"]))
            else:
                log.warning("page_incomplete page=%s detail_failures=%s; rerun will retry missing URLs",page,page_errors)
            checkpoint["current_page"]=page; cp_path.write_text(json.dumps(checkpoint,indent=2),encoding="utf-8")
            save_csv(csvpath,list(by_url.values())); log.info("page_completed page=%s records=%s",page,len(by_url))
            if len(by_url)>=maxp: break
        except Exception as e:
            log.exception("catalogue_page_failed page=%s error=%s",page,e); raise
    print(f"Saved {len(by_url)} unique products to {csvpath}; checkpoint {cp_path}")
if __name__=="__main__": main()
