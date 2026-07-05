"""Champions データセットからトークナイザ語彙を構築する。

本家語彙(allreplaysv3)を土台に、パース済み軌跡の観測テキストに現れる
未知語(新メガ種族・Champions 技など)を追加して championsv1.json を作る。

使い方(metamon venv で実行):
    python tools/build_champions_vocab.py --sample 100   # 時間見積もり用
    python tools/build_champions_vocab.py                # 全件
"""

import argparse
import glob
import json
import os
import time

import lz4.frame

from metamon.interface import (
    TeamPreviewObservationSpace,
    TokenizedObservationSpace,
    UniversalState,
)
from metamon.tokenizer import PokemonTokenizer

VOCAB_BASE = os.path.join(
    os.path.dirname(__import__("metamon").__file__), "tokenizer", "allreplaysv3.json"
)
PARSED_DIR = os.path.expanduser("~/dev/metamon_cache/parsed_champions")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=None, help="先頭N軌跡のみ(見積もり用)")
    parser.add_argument("--out", default=None, help="語彙の保存先(省略時は保存しない)")
    args = parser.parse_args()

    tokenizer = PokemonTokenizer().load_tokens_from_disk(VOCAB_BASE)
    base_vocab_size = len(tokenizer)
    tokenizer.unfreeze()
    obs_space = TokenizedObservationSpace(
        base_obs_space=TeamPreviewObservationSpace(), tokenizer=tokenizer
    )

    files = sorted(glob.glob(f"{PARSED_DIR}/*/*.lz4"))
    if args.sample:
        files = files[: args.sample]
    print(f"対象軌跡: {len(files)}件 / 基礎語彙: {base_vocab_size}")

    t0 = time.time()
    for i, f in enumerate(files):
        with lz4.frame.open(f) as fh:
            data = json.load(fh)
        for state_dict in data["states"]:
            if isinstance(state_dict, str):
                state_dict = json.loads(state_dict)
            state = UniversalState.from_dict(state_dict)
            obs_space.state_to_obs(state)
        if (i + 1) % 2000 == 0:
            print(f"{i+1}件... ({time.time()-t0:.0f}秒)", flush=True)
    elapsed = time.time() - t0

    tokenizer.sort_tokens()
    new_tokens = len(tokenizer) - base_vocab_size
    print(f"\n処理時間: {elapsed:.1f}秒 ({elapsed/max(len(files),1)*1000:.1f}ms/軌跡)")
    print(f"追加された語彙: {new_tokens} / 合計: {len(tokenizer)}")
    if args.out:
        tokenizer.save_tokens_to_disk(args.out)
        print(f"保存: {args.out}")


if __name__ == "__main__":
    main()
