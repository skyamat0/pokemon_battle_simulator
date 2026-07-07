# 実験記録

すべての学習・評価実験をここに記録する(2026-07-07 運用開始)。

## 学習

| ID | 日付 | 手法 | モデル | データ | val精度(ベスト) | Top-2 | 備考 |
|---|---|---|---|---|---|---|---|
| il_dryrun_mac | 07-05 | BC | 82k (tiny) | M-B 3,136(ランダム分割) | 22.8%(1ep) | 41.3% | Mac CPU疎通確認 |
| gpu_dryrun2 | 07-07 | BC | 82k (tiny) | M-A+M-B, 時間分割 | 22.8%(1ep) | 43.0% | サーバーGPU疎通・時間分割確認 |
| **champions_il_v1** | 07-07 | BC | 1.4M | 全レート 42,018軌跡 / val=7/4以降454 | **38.1%**(11ep, 早期停止13ep) | 59.5% | eager実行(compile無効時代) |
| champions_il_v15 | 07-07 | BC | 7.3M | **レート1300+** 15,076試合 / val=7/4以降∩1300+ **96試合** | 23.9%(4ep) | — | **失敗(教訓あり)**: val 96試合では accuracy がノイズで暴れ、loss が単調改善中(1.90→1.69)なのに acc 基準の早期停止(patience2)が誤発動。※ v1 の38.1%とは val セットが違うため精度の直接比較は不可 |
| champions_il_v15b | 07-07 | BC | 7.3M | 同上 / **val=7/1以降∩1300+(拡大)** | (実行中) | | 対策: loss 基準の早期停止 + patience 4。--patience/--early_stop_metric を CLI 化 |

## 対戦評価(100戦、選出ランダム、bot=ChampionsHeuristics)

| ID | 日付 | モデル | 手選択 | 自チーム vs 相手チーム | モデル勝率 | 参考 |
|---|---|---|---|---|---|---|
| eval_v1 | 07-07 | v1 | サンプリング | my_party vs top_rain | **21%** | bot同士だと my_party側 40.7% |
| eval_greedy | 07-07 | v1 | **greedy** | my_party vs top_rain | **29%** | greedy化で+8pt |
| eval_mirror | 07-07 | v1 | greedy | my_party ミラー | **15%** | 相性を消すと悪化。原因未解明(次回からturn_log付きで分析可能) |

## 既知の運用ノート

- 評価は greedy を標準とする
- eval_model.py は logs/eval_*.jsonl に全対戦ログを記録(analyze.py 互換)
- 対botはあくまで代理指標。真の評価は対人(ユーザー)とラダー
