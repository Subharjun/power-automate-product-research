#!/usr/bin/env python3
"""Draft/simulate by default; explicit test send supports Gmail API and WhatsApp Cloud API."""
import argparse,base64,csv,hashlib,json,os,time
from datetime import datetime,timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

def now():return datetime.now(timezone.utc).isoformat()
def post(url,data,headers):
    req=Request(url,data=data,headers=headers,method="POST")
    try:
        with urlopen(req,timeout=25) as r:return r.status,r.read().decode("utf-8","replace")
    except HTTPError as e:return e.code,e.read().decode("utf-8","replace")
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--config",default="config.json");ap.add_argument("--send",action="store_true",help="required explicit gate for one controlled test send");ap.add_argument("--sample",default="C001");ap.add_argument("--channels",default="email,whatsapp");args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text());d=cfg["delivery"];out=Path(cfg["output_dir"]);messages=json.loads((out/"messages.json").read_text())
    logpath=out/"delivery.log";statepath=out/"delivery_state.json";state=json.loads(statepath.read_text()) if statepath.exists() else {"attempts":{}}
    channels=[x.strip() for x in args.channels.split(",") if x.strip()]
    if args.send and d.get("mode")!="test":raise SystemExit("Refusing to send: set delivery.mode to 'test' AND pass --send explicitly.")
    chosen=[m for m in messages if m["customer_id"]==args.sample] if args.send else messages
    if args.send and len(chosen)!=1:raise SystemExit("Sample customer ID must match exactly one message set.")
    now_s=now(); log=[]
    for m in chosen:
      for ch in channels:
        if ch not in ("email","whatsapp"):continue
        recipient=(d.get("gmail_controlled_test_recipient") if ch=="email" else d.get("whatsapp_controlled_test_recipient")) if args.send else ""
        key=hashlib.sha256(f"{ch}|{recipient}|{m['customer_id']}|{m['email_body'] if ch=='email' else m['whatsapp_message']}".encode()).hexdigest()
        if key in state["attempts"]:
            log.append({"timestamp":now_s,"record_id":m["customer_id"],"channel":ch,"result":"DUPLICATE_BLOCKED","detail":"Prior attempt exists; no retry."});continue
        if not args.send:
            result="DRAFT_PREPARED" if ch=="email" else "SIMULATED_ONLY"
            detail="Local draft payload written; no account or delivery used." if ch=="email" else "WhatsApp draft payload only; no WhatsApp API call or delivery."
        else:
            status="UNCERTAIN"; detail=""
            try:
                if not recipient:raise ValueError(f"Missing controlled {ch} recipient in config")
                if ch=="email":
                    token=os.environ.get("GMAIL_ACCESS_TOKEN",""); sender=d.get("gmail_from","")
                    if not token or not sender:raise ValueError("Set GMAIL_ACCESS_TOKEN (OAuth user access token) and delivery.gmail_from")
                    msg=EmailMessage();msg["To"]=recipient;msg["From"]=sender;msg["Subject"]=m["email_subject"];msg.set_content(m["email_body"])
                    raw=base64.urlsafe_b64encode(msg.as_bytes()).decode().rstrip("=")
                    code,body=post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",json.dumps({"raw":raw}).encode(),{"Authorization":f"Bearer {token}","Content-Type":"application/json"})
                else:
                    token=os.environ.get("WHATSAPP_ACCESS_TOKEN",""); phone_id=d.get("whatsapp_phone_number_id","")
                    if not token or not phone_id:raise ValueError("Set WHATSAPP_ACCESS_TOKEN and delivery.whatsapp_phone_number_id after supported test setup")
                    url=f"https://graph.facebook.com/{d.get('whatsapp_api_version','v22.0')}/{phone_id}/messages"
                    payload={"messaging_product":"whatsapp","to":recipient,"type":"text","text":{"body":m["whatsapp_message"]}}
                    code,body=post(url,json.dumps(payload).encode(),{"Authorization":f"Bearer {token}","Content-Type":"application/json"})
                if 200<=code<300:status="API_ACCEPTED"
                else:status="FAILED" if code>=400 else "UNCERTAIN"
                detail=f"http_status={code}; response={body[:500]}"
            except Exception as e:status="FAILED";detail=str(e)
            result=status
        state["attempts"][key]={"timestamp":now_s,"record_id":m["customer_id"],"channel":ch,"result":result,"recipient_configured":bool(recipient)}
        log.append({"timestamp":now_s,"record_id":m["customer_id"],"channel":ch,"result":result,"detail":detail})
        statepath.write_text(json.dumps(state,indent=2),encoding="utf-8")
    with logpath.open("a",encoding="utf-8") as f:
        for row in log:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    print(f"Processed {len(log)} channel attempts in {d.get('mode','draft')} mode. See {logpath}")
if __name__=="__main__":main()
