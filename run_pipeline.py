#!/usr/bin/env python3
"""Single entry point intended to be called by the PAD parent flow."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def run(script,*args): subprocess.run([sys.executable,str(ROOT/script),*args],cwd=ROOT,check=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--extract",action="store_true");ap.add_argument("--prepare",action="store_true");ap.add_argument("--delivery",action="store_true");ap.add_argument("--send",action="store_true");ap.add_argument("--sample",default="C001");a=ap.parse_args()
 if a.extract:run("extract_products.py","--config","config.json")
 if a.prepare:
  run("match_and_message.py","--config","config.json");run("deliver.py","--config","config.json")
 if a.delivery:run("deliver.py","--config","config.json",*( ["--send","--sample",a.sample] if a.send else []))
if __name__=="__main__":main()
