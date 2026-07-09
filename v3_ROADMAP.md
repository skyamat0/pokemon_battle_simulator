## v3 開発計画: 選出・観測空間・価値関数を分離した学習型AI

v2(模倣学習 + オフラインRL)で十分な勝率改善が得られない場合、v3では単にモデルサイズや学習時間を増やすのではなく、以下の構造変更を行う。

目的は、チャンピオンズ仕様(6匹見せ・3匹選出・メガシンカあり・テラスなし)において、最終的に高レート帯(2000+)で安定して勝てるAIを作ること。運負けは避けられないため、選出・プレイング・メガ判断・交代判断の期待勝率を高めることを目標にする。

### v3 の基本方針

v2までは、Metamon/PokéChamp 系の既存パイプラインを Champions 仕様に改造し、そのターン時点で確定している情報を埋め込んで方策を出力する方針を取る。

v3では、以下のように役割を分離する。

```
[選出モデル]
  P(selected_3 | self_6, opp_6, self_sets)
      ↓
[選出結果に基づく観測空間 v3]
  active / bench / opponent known info / field info
      ↓
[Transformer 方策・価値モデル]
  policy head + Q head + value head
      ↓
[policy 候補 + Q rerank]
  最終行動を選択
```

### v3 で導入する主な変更点

* 選出モデルをバトル中方策モデルから分離する

  * 入力: 自分6匹、相手6匹、自分側の型情報(持ち物・技・性格・ステータスポイント等)
  * 出力: 選出3匹の確率分布
  * 初手は別headまたは別モデルで扱う

* 観測空間 v3 を作る

  * 見せ合い6匹: 順序なし
  * 選出済み控え2匹: 順序なし
  * 場のポケモン: active token として明示
  * ゾロアーク/イリュージョンは例外的に専用フラグで扱う
  * 相手情報は known / unknown / impossible を分ける
  * 未来情報リークを防ぐため、各ターン時点でプレイヤーから見えている情報のみを使う

* 埋め込み表現を学習対象にする

  * species / item / move / ability / nature / type などは learnable embedding とする
  * 例: species embedding 64次元、item embedding 32〜64次元
  * 各カテゴリのembeddingを結合し、Linear/MLPでTransformerの d_model に射影する
  * embedding、射影層、Transformer、policy/Q/value head はすべて学習対象

* 手作り特徴量を追加する

  * ダメージ計算
  * 自分から相手への最大打点
  * 相手から自分への推定最大打点
  * 確定数/乱数圏内
  * 素早さ関係
  * ステルスロック等の設置技の影響
  * 天候・フィールド・壁・状態異常による環境変化
  * メガ前後の素早さ・耐性・火力変化

* 報酬設計は勝敗中心にする

  * 基本報酬: 勝ち +1 / 負け -1
  * shaped reward は必要最小限にする
  * ダメージ計算や最大打点は報酬ではなく、まず特徴量として入力する
  * 「ステロを撒くこと自体が偉い」などの報酬ハックを避ける

* Q関数を行動選択に使う

  * policy は候補行動を出す
  * Q は候補行動を勝率的に再評価する
  * 初期段階では argmax Q ではなく、policy 上位候補を Q で rerank する

### Phase 0: v2 の評価と失敗原因の切り分け

目的: v2が本当に構造変更を必要としているのかを確認する。

評価項目:

* 検証 accuracy
* top-k accuracy
* 対 heuristic bot 勝率
* 対過去モデル勝率
* 不合法行動率
* メガ可能ターンでのメガ判断
* 有利対面での取りこぼし率
* 不利対面での交代率
* Q値と実勝率/報酬の相関
* policy entropy
* 負け試合の原因分類

成果物:

* `EXPERIMENTS.md` に v2 の評価結果を記録
* v3 に入れるべき変更点を確定
* v2継続 / v3着手 の判断

判断基準の例:

* BC accuracy は改善しているが対戦勝率が伸びない
* 対bot勝率が低いまま
* Qが不安定で、明らかな悪手に高い値を出す
* 選出負けが多い
* メガ判断・交代判断が弱い
* ダメージ/素早さ/確定数を理解できていない挙動が多い

### Phase 1: 観測空間 v3 の実装

目的: battle policy が盤面価値を判断しやすい入力表現を作る。

実装予定:

* `ChampionsObservationSpaceV3` を追加
* active / bench / preview / opponent known info を分離
* known / unknown / impossible flag を追加
* メガ前後の species / ability / type / stats を扱う
* item / move / ability の未判明状態を明示
* ダメージ計算特徴量を追加
* 素早さ関係・確定数・最大打点特徴量を追加
* field/weather/hazard/screen/status の特徴量を追加

観測空間の概念:

```
self_preview_6: set encoding
self_active: active token
self_bench_2: set encoding
opp_preview_6: set encoding
opp_active_known: known-info token
opp_back_known: known/unknown tokens
field_state: field token
action_context: legal action mask + mega availability
```

テスト項目:

* 各ターン時点で未来情報が混入していないこと
* リプレイの進行に従って known 情報が増えること
* unknown と impossible が区別されていること
* メガ前後の状態遷移が正しいこと
* 合法手maskが正しく作られること

### Phase 2: 選出モデルの実装

目的: 6匹見せの段階で、勝率の高い3匹を選べるようにする。

モデル:

```
P(selected_3 | self_6, opp_6, self_sets)
```

入力:

* 自分6匹
* 相手6匹
* 自分側の持ち物
* 自分側の技構成
* 自分側の性格
* 自分側のステータスポイント
* メガ可能ポケモン
* ルール/レギュレーションID

出力:

* 20通りの選出集合 C(6, 3) の確率分布
* 必要なら、初手3択の確率分布

学習:

* まずは高レート/勝ち試合中心の模倣学習
* 次に勝敗両方を使った selection value を学習
* 最終的には `score = V_select + λ log π_select` で選出候補を評価する

注意:

* 勝ち試合の選出だけを正解とみなすと、プレイング勝ちや相手ミスも混ざる
* 負け試合も「選出が悪かった」とは限らない
* 可能なら、選出直後の `V_battle(s0)` を使って選出品質と試合結果を分離する

成果物:

* `select_model_v1`
* 選出一致率
* 初手一致率
* 選出別勝率
* 選出モデルあり/なしでの対bot勝率比較

### Phase 2.1: 選出モデル特徴量の段階的スコープ

目的: 最初からすべての相互作用を作り込まず、最小ベースラインから段階的に特徴量を増やす。

方針:

* v3.0では、技効果・特性効果・持ち物効果の詳細な手作り特徴量は入れない
* species / type / ability / item / move は key として渡し、モデル側の embedding に任せる
* 実数値ステータス、体重、メガ可能フラグなど、すでに安定して計算できる数値特徴は入れる
* 複雑な相互作用は、学習パイプラインが一周してから追加する
* 各段階で選出一致率・選出別勝率・対bot勝率を比較し、どの特徴量が効いたかを確認する

#### v3.0: minimal selection baseline

自分ポケモン:

* species_key
* types
* stats
* ability_key
* item_key
* is_mega
* form_key
* move_keys
* weight

相手ポケモン:

* species_key
* types
* base_stats
* has_mega_form
* weight

入れないもの:

* 技威力・命中・PP・優先度
* 状態異常・積み・回復・ピボット等の技フラグ
* 特性による技威力/耐性/素早さ補正
* 持ち物による技威力/耐久/素早さ補正
* 自分6匹と相手6匹の pairwise 相性特徴
* 概算ダメージ・確定数・最大打点

狙い:

* まず学習データ作成、tokenizer、モデル、評価まで一周させる
* embedding だけでどこまで選出を学習できるか確認する
* 以降の特徴量追加による改善幅を測るための基準にする

#### v3.1: move basics

追加するもの:

* base_power
* accuracy
* pp
* priority
* is_status_move
* has_priority
* is_pivot
* is_setup
* is_recovery
* is_hazard
* is_screen
* inflicts_status
* has_boost
* has_debuff

狙い:

* 技名 embedding だけでは拾いにくい基本性能を明示する
* 回復技、設置技、壁、積み技、先制技など、選出判断に効きやすい役割をモデルに渡す

#### v3.2: ability interactions

追加するもの:

* ability × species
* ability × type
* ability × move
* ability × stats
* ability による無効耐性・火力補正・素早さ補正の概算特徴

例:

* Levitate による Ground 無効
* Technician × 低威力技
* Adaptability × STAB
* Swift Swim / Chlorophyll 等の天候下素早さ補正

#### v3.3: item interactions

追加するもの:

* item × species
* item × stats
* item × move
* item × category
* item による火力・耐久・素早さ補正の概算特徴

例:

* Choice Band / Choice Specs による火力補正
* Choice Scarf による素早さ補正
* Assault Vest による特殊耐久補正
* Life Orb による火力補正
* Mega Stone によるメガ後 species / stats / type / ability

#### v3.4: move interactions

追加するもの:

* move × type
* move × stats
* move × ability
* move × item
* move × opponent type
* STAB
* 打点有無
* 概算火力
* 素早さ関係

狙い:

* 自分の技が相手6匹にどれくらい通るかを表現する
* 選出段階で「誰が誰に打点を持つか」を明示する

#### v3.5: full pairwise/team interactions

追加するもの:

* 自分6匹 × 相手6匹の pairwise 相性特徴
* 選出3匹の組み合わせ補完
* 一貫して重い相手
* 受け先の有無
* 崩し役・詰め役・初手要員の分担
* 可能なら概算ダメージ/耐久ライン

狙い:

* 個体ごとの強さだけでなく、3匹選出全体としての勝ち筋を評価する
* 方策モデルに渡す前の段階で、勝ちやすい盤面を作る

### Phase 3: Transformer 方策モデル v3 の実装

目的: 観測空間 v3 を入力として、方策・Q・状態価値を同時に学習する。

モデル構造:

```
learnable embeddings
    ↓
token builder
    ↓
Linear/MLP → d_model
    ↓
Transformer encoder
    ↓
policy head
Q head
value head
auxiliary heads
```

学習対象:

* species embedding
* item embedding
* move embedding
* ability embedding
* nature embedding
* type embedding
* projection Linear/MLP
* Transformer
* policy head
* Q head
* value head
* auxiliary heads

補助タスク候補:

* 次ターン相手行動予測
* 相手持ち物予測
* 相手技構成予測
* 現在状態の勝率予測
* 次に倒れるポケモン予測
* メガ使用判断予測

行動選択:

```
legal actions
    ↓
policy で上位k個を抽出
    ↓
Qでrerank
    ↓
最終行動
```

初期設定:

* k = 3〜5
* Q単独 argmax は使わない
* policy の確率が極端に低い行動は除外する

### Phase 4: v3 模倣学習

目的: v3 観測空間とモデル構造で、人間リプレイの行動を再現できるか確認する。

学習:

* 人間リプレイから BC
* 時間分割で train/validation を作る
* v1/v2 と同じデータ分割でも比較する
* 最新レギュレーションのリプレイを優先する

評価:

* top-1 accuracy
* top-2/top-3 accuracy
* legal action accuracy
* メガ判断 accuracy
* 交代判断 accuracy
* 不利対面での交代率
* 有利対面での攻撃選択率
* 対 heuristic bot 勝率

判断:

* BC精度が伸びても勝率が伸びない場合、policy単体ではなくQ/value側を重視する
* BC精度が伸びない場合、観測空間・行動エンコード・データ品質を疑う

### Phase 5: オフラインRL / Q学習

目的: 人間の平均行動を真似るだけでなく、勝ちに繋がる行動を高く評価できるようにする。

方針:

* v3 BCモデルを初期値にする
* 勝敗報酬を中心にQ/valueを学習する
* shaped reward は弱く入れる
* policy は急激に崩さない
* OOD行動のQ過大評価を避ける

報酬:

```
win: +1
lose: -1
```

必要に応じて:

```
faint opponent: small +
faint self: small -
HP advantage: small shaped reward
```

注意:

* 最大打点・確定数・設置技はまず特徴量として入れる
* 報酬に入れすぎると中間指標を最適化する危険がある
* Q値が実際の勝率と対応しているか必ず確認する

評価:

* Q値と勝敗の相関
* Q値とn-step returnの相関
* policyのみ vs policy+Q rerank
* v2 vs v3
* 対 heuristic bot
* 対過去モデル
* 対固定構築群

### Phase 6: self-play リーグ

目的: 固定botや人間平均への過適応を避ける。

相手プール:

* heuristic bot
* v1
* v2
* v3 BC
* v3 RL
* 過去checkpoint
* 固定メタ構築
* 受け構築
* 対面構築
* 積み構築
* 雨/砂/晴れ等の天候構築

方針:

* 固定相手だけでRLしない
* checkpoint pool を使う
* 勝ちやすい相手だけを狩るモデルを避ける
* 構築ジャンケンに過適応しないように複数構築で評価する

評価:

* 全体勝率
* 相手別勝率
* 構築タイプ別勝率
* 選出段階の勝率
* 初手別勝率
* メガ使用ターン別勝率
* 不利構築への耐性
* 有利構築の取りこぼし率

### Phase 7: 実戦評価・レート2000+想定評価

目的: 最終目標である高レート帯勝率を意識した評価に移る。

評価項目:

* 2000+相当の構築群への勝率
* 高レートリプレイに対する選出一致率
* 高レートリプレイに対する行動 top-k accuracy
* 高レート構築に対する対戦勝率
* 不利構築での最低勝率
* 運負けを除いた期待勝率
* 読み負け・選出負け・メガ判断ミスの分析

目標:

* 短期: heuristic bot を安定して上回る
* 中期: v2 を安定して上回る
* 長期: 高レート構築群に対して高勝率
* 最終: レート2000+帯で勝率7割を目指す

## v3 実験管理

実験名の例:

```
champions_v3_obs_bc_001
champions_v3_select_001
champions_v3_qrerank_001
champions_v3_offlinerl_001
champions_v3_selfplay_001
```

記録するもの:

* git commit hash
* 使用データ期間
* レギュレーション
* tokenizer version
* observation space version
* model config
* reward config
* train/validation split
* accuracy
* top-k accuracy
* 対bot勝率
* 対過去モデル勝率
* 備考

## v3 の優先順位

最初にやること:

1. v2の評価と失敗原因の確認
2. 観測空間 v3 の実装
3. 未来情報リークテスト
4. ダメージ/素早さ/最大打点特徴量の追加
5. v3 BCモデルの学習
6. policy + Q rerank の実装
7. 選出モデルの実装
8. self-play リーグ化

最初からやらないこと:

* 選出モデルとバトル方策モデルの完全end-to-end学習
* 全ポケモン・全持ち物・全技を対象にした大規模化
* Q単独argmaxでの行動選択
* shaped reward の過剰導入
* LLMによる直接行動選択

将来的にやること:

* 選出モデルを上位方策、バトル方策を下位方策とする階層型RL
* Gumbel-Softmax / policy gradient による選出まで含めたend-to-end更新
* 構築選択モデル
* 高レート対戦ログに基づくメタ追従
* 対戦後の敗因自動分類
