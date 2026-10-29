"""Command line:

    python -m eshop_ai popisky data/produkty.csv     -> vystup/popisky.csv + vystup/popisky.html
    python -m eshop_ai dotazy  data/dotazy           -> vystup/dotazy.json + vystup/dotazy.html
"""
import argparse
import os
import sys
from pathlib import Path

from eshop_ai import descriptions, inbox, report


def load_env(path=Path(".env")):
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.strip().startswith("#") and value.strip():
                os.environ.setdefault(key.strip(), value.strip())


def main(argv=None):
    parser = argparse.ArgumentParser(prog="eshop_ai", description="AI automatizace pro e-shop")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("popisky", help="popisky produktů z CSV")
    p.add_argument("csv")
    d = sub.add_parser("dotazy", help="třídění e-mailů zákazníků")
    d.add_argument("slozka")
    for sp in (p, d):
        sp.add_argument("--out", default="vystup", help="složka pro výstupy (výchozí: vystup)")
    args = parser.parse_args(argv)

    load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Chybí ANTHROPIC_API_KEY: zkopíruj .env.example do .env a vlož klíč.")
    from anthropic import Anthropic  # imported late so --help works without the SDK configured
    client = Anthropic()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.cmd == "popisky":
        rows = descriptions.read_products(args.csv)
        results = descriptions.run(client, rows)
        descriptions.write_csv(results, out / "popisky.csv")
        report.save(report.products_html(results), out / "popisky.html")
        done = sum("copy" in r for r in results)
        print(f"Hotovo: {done}/{len(results)} produktů -> {out / 'popisky.csv'}, {out / 'popisky.html'}")
    else:
        emails = inbox.read_emails(args.slozka)
        results = inbox.run(client, emails)
        inbox.write_json(results, out / "dotazy.json")
        report.save(report.inbox_html(results), out / "dotazy.html")
        done = sum("triage" in r for r in results)
        print(f"Hotovo: {done}/{len(results)} e-mailů -> {out / 'dotazy.json'}, {out / 'dotazy.html'}")
    failed = [r for r in results if "error" in r]
    for r in failed:
        print(f"  chyba: {r['error']}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
