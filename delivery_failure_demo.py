#!/usr/bin/env python3
"""Create an explicitly simulated provider-failure/no-retry artifact; makes no network call."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path

def now():return datetime.now(timezone.utc).isoformat()
def main():
    out=Path("output");state_path=out/"delivery_failure_demo_state.json";log_path=out/"delivery_failure_demo.log"
    state=json.loads(state_path.read_text()) if state_path.exists() else {"attempts":{}}
    key=hashlib.sha256(b"SIMULATED|DEMO-FAILURE|email|one-shot-provider-error").hexdigest(); rows=[]
    if key not in state["attempts"]:
        row={"timestamp":now(),"record_id":"DEMO-FAILURE","channel":"email","result":"FAILED_SIMULATED","detail":"Injected local demo error; no network request, no message sent, no automatic retry."}
        state["attempts"][key]=row;rows.append(row)
    else:
        rows.append({"timestamp":now(),"record_id":"DEMO-FAILURE","channel":"email","result":"DUPLICATE_BLOCKED","detail":"Prior simulated attempt exists; no retry."})
    with log_path.open("a",encoding="utf-8") as f:
        for row in rows:f.write(json.dumps(row)+"\n")
    state_path.write_text(json.dumps(state,indent=2),encoding="utf-8")
    print(rows[-1]["result"]+" (simulation only)")
if __name__=="__main__":main()
