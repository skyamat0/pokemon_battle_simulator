"""Showdown 公式サーバーから Champions 系フォーマットのリプレイを収集する。

差分収集: 既に保存済みの ID に当たったページで打ち切る(--full で全ページ走査)。
cron で定期実行し、data/replays/<format>/<id>.json に貯める。

使い方:
    python collect_replays.py            # 差分収集
    python collect_replays.py --full     # 全ページ走査(初回・取りこぼし回収用)
"""

import argparse
import json
import pathlib
import time
import urllib.request

FORMATS = [
    "gen9championsbssregmb",
    "gen9championsbssregma",
    "gen9championsou",
    "gen9championsuu",
    "gen9championsrandombattle",
    "gen9championsvgc2026regmb",
    "gen9championsvgc2026regma",
]

HEADERS = {"User-Agent": "pokemon-battle-simulator replay collector (research use)"}
BASE = "https://replay.pokemonshowdown.com"


def fetch_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def collect_format(fmt: str, out_root: pathlib.Path, full: bool, sleep: float) -> int:
    out = out_root / fmt
    out.mkdir(parents=True, exist_ok=True)
    before = None
    new_count = 0
    while True:
        url = f"{BASE}/search.json?format={fmt}"
        if before:
            url += f"&before={before}"
        try:
            page = fetch_json(url)
        except Exception as e:
            print(f"[{fmt}] search 失敗: {e}")
            break
        if not page:
            break

        page_had_new = False
        for meta in page:
            rid = meta["id"]
            path = out / f"{rid}.json"
            if path.exists() or meta.get("private"):
                continue
            try:
                data = fetch_json(f"{BASE}/{rid}.json")
            except Exception as e:
                print(f"[{fmt}] {rid} 取得失敗: {e}")
                continue
            path.write_text(json.dumps(data, ensure_ascii=False))
            new_count += 1
            page_had_new = True
            time.sleep(sleep)

        if not page_had_new and not full:
            break  # 差分モード: 新規ゼロのページまで来たら終了
        if len(page) < 51:
            break  # 最終ページ
        before = page[-1]["uploadtime"]
        time.sleep(sleep)
    return new_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="全ページ走査")
    parser.add_argument("--out", default="data/replays")
    parser.add_argument("--sleep", type=float, default=0.3, help="リクエスト間隔秒")
    parser.add_argument("--formats", nargs="*", default=FORMATS)
    args = parser.parse_args()

    out_root = pathlib.Path(args.out)
    total = 0
    for fmt in args.formats:
        n = collect_format(fmt, out_root, args.full, args.sleep)
        stored = len(list((out_root / fmt).glob("*.json")))
        print(f"[{fmt}] 新規 {n} 件 / 累計 {stored} 件")
        total += n
    print(f"合計新規: {total} 件")


if __name__ == "__main__":
    main()
