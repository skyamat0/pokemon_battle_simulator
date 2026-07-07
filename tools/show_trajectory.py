"""パース済み軌跡を人間可読な形で表示する(抜き打ち検証用)。

公式リプレイビューア(https://replay.pokemonshowdown.com/<id>)と並べて、
各ターンの盤面・選択行動が正しく再構成されているかを目視確認する。

使い方:
    python tools/show_trajectory.py <trajectory.json.lz4>
"""

import json
import sys

import lz4.frame

from metamon.interface import consistent_move_order, consistent_pokemon_order


def decode_action(idx, state):
    if idx == -1:
        return "(不明: ログから確定できず)"
    # 行動インデックスは consistent order(名前の正規化ソート)で振られているため、
    # 保存された公開順のリストをソートし直してから引く
    move_names = consistent_move_order(
        [m["name"] for m in state["player_active_pokemon"]["moves"]]
    )
    if 0 <= idx <= 3:
        return f"技: {move_names[idx]}" if idx < len(move_names) else f"技スロット{idx}(範囲外)"
    if 4 <= idx <= 8:
        switches = consistent_pokemon_order(
            [p["name"] for p in state["available_switches"]]
        )
        s = idx - 4
        return f"交代: {switches[s]}" if s < len(switches) else f"交代スロット{s}(範囲外)"
    if 9 <= idx <= 12:
        m = idx - 9
        return f"メガシンカ + 技: {move_names[m]}" if m < len(move_names) else f"メガ+技スロット{m}"
    return f"不明なインデックス {idx}"


def main():
    path = sys.argv[1]
    with lz4.frame.open(path) as f:
        data = json.load(f)

    fname = path.split("/")[-1]
    replay_id = fname.split("_")[0]
    print(f"ファイル: {fname}")
    print(f"リプレイ: https://replay.pokemonshowdown.com/{replay_id}")
    print(f"視点: {fname.split('_vs_')[0].split('_', 2)[-1]} / 結果: {'勝ち' if 'WIN' in fname else '負け'}")
    print(f"相手のプレビュー: {', '.join(data['states'][0].get('opponent_teampreview', []))}")
    print("=" * 72)

    for i, (state, action) in enumerate(zip(data["states"], data["actions"])):
        me = state["player_active_pokemon"]
        opp = state["opponent_active_pokemon"]
        can_mega = "残" if state.get("can_tera") else "済/不可"
        print(f"ターン{i+1:>2}: 自分 {me['name']:<14} HP{me['hp_pct']:>5.0%} "
              f"| 相手 {opp['name']:<14} HP{opp['hp_pct']:>5.0%} | メガ権:{can_mega}")
        print(f"   └ 選択 → {decode_action(action, state)}")
    print("=" * 72)
    print("確認ポイント: 各ターンの場のポケモン/HP%/選択した技・交代/メガのタイミングが")
    print("リプレイビューアの表示と一致するか。")


if __name__ == "__main__":
    main()
