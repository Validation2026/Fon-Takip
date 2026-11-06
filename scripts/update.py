"""GitHub Actions'ın iki kez çalıştırdığı korumalı güncelleme."""
import argparse
import json
import sys
from pathlib import Path

from bootstrap import build
from fetch_fonoloji import fetch, parse_csv
from fon_core import apply_updates

ROOT=Path(__file__).resolve().parent.parent
PUBLIC=ROOT/"public"/"index.html"
STATE=ROOT/"state"/"funds.json"
PRICES=ROOT/"public"/"data"/"fund_prices.json"
AUDIT=ROOT/"audit"/"latest.json"

def save(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".tmp")
    temp.write_text(text,encoding="utf8")
    temp.replace(path)

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fixture",type=Path)
    args=parser.parse_args()
    original=build().decode("utf8")
    try:
        incoming=parse_csv(args.fixture.read_bytes()) if args.fixture else fetch()
        previous=json.loads(STATE.read_text("utf8")) if STATE.exists() else {}
        result,updated,report=apply_updates(original,previous,incoming)
        print(json.dumps(report,ensure_ascii=False))
        if not report["publish"]:
            print("Veri kalitesi kontrolünden geçmedi; site değişmeyecek",file=sys.stderr)
            return 1
        out_prices={"as_of":report["dominant_date"],"source":"Fonoloji/TEFAS",
                    "funds":updated,"note":"KAP pozisyon ağırlıkları ve ödendi/ödenmedi statüleri değiştirilmedi"}
        save(PUBLIC,result)
        save(STATE,json.dumps(updated,ensure_ascii=False,indent=2)+"\n")
        save(PRICES,json.dumps(out_prices,ensure_ascii=False,indent=2)+"\n")
        save(AUDIT,json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        print("Doğrulanmış fon verisi yayın için hazır")
        return 0
    except Exception as exc:
        print("Korumalı duruş:",exc,file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(run())
