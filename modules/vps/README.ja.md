# Claude Network Guide · VPS

> Independent source reference for the advanced VPS component. No tutorial site is currently hosted by this repository. Start with the [main tutorial and local workbench](../../README.md); source attribution is preserved in [NOTICE](../../NOTICE.md).

[中文](./README.md) · [English](./README.en.md) · [한국어](./README.ko.md) · **日本語** · [العربية](./README.ar.md) · [Español](./README.es.md) · [Français](./README.fr.md) · [Русский](./README.ru.md) · [Deutsch](./README.de.md) · [Português](./README.pt.md)

ネットが使いにくい国へ出張しても、いつものウェブサイトや AI ツールをそのまま使えます。

未公開のチュートリアルサイトのソース：[中国語](site/src/pages/) · [英語](site/src/pages/en/) · [ローカルプレビュー](site/README.md)。GitHub のディレクトリ表示ではサイトは実行されません。

やり方はシンプルです。海外サーバーを自分で 1 台買い、このプロジェクトどおりに AI に設定してもらい、スマホとパソコンに購読を読み込むだけ。回線は自分専用で、知らない人とは共有しません。

## 設定が終わると

- **自分だけの回線**：パソコン、スマホ、ルーターで使えます。メインと予備の 2 つのノードがあり、片方がつながらないと自動で切り替わります。
- **読み込めばすぐ使える**：よく使うサイトと AI ツールの振り分けルールは設定済み。中国本土のサイトは直接つながり、それ以外は自分のサーバーを経由します。
- **CLIProxyAPI**：自分専用の API と管理画面。最新版へ自動で更新されます。
  - ⚠️ **Claude のアカウントを CLIProxyAPI につながないでください**：Anthropic のポリシーで認められていません。ChatGPT などは OpenAI が公式に問題ないとしていて、私は画像作りによく使っています。
- **安全**：サーバーにはこのパソコンの鍵でしかログインできません。正式な HTTPS 証明書を使うので「保護されていない通信」の警告も出ません。
- **ほぼ手間なし**：証明書、ルール、CLIProxyAPI は自動で更新され、設定は毎日自動でバックアップされます。

## 3 ステップで使い始める

### 1. サーバーを買う

いまは **BandwagonHost** をそのまま買うのがおすすめです。回線が安定していて、私自身も使い続けています。

**[BandwagonHost を購入する](https://bandwagonhost.com/)**

このリンクのプランは**毎月 1TB の転送量**付きで、家族で使っても十分です。

[DMIT](https://www.dmit.io/) も良いのですが、現在は在庫切れです。待つ必要はありません。

> どちらも私の紹介リンクです。リンク経由で購入されると私に紹介料が入る場合があり、その収入は慈善活動に使います。価格と在庫は公式サイトをご確認ください。

OS は **Ubuntu 24.04** を選んでください。開通したら管理画面で 3 つをメモします：**サーバー IP、root パスワード（または鍵ファイル）、SSH ポート**。

### 2. AI に設定してもらう

パソコンでコマンドを実行できる AI ツールを開きます。たとえば [Codex](https://github.com/openai/codex) や [Claude Code](https://claude.com/claude-code)（Windows は WSL 内で使用）。下の文章をコピーし、埋めてから送ってください。

```text
「claude-network-guide」方式で、新しく買ったサーバーを設定してください。

方式：https://github.com/clm031102-source/claude-network-guide
まずこのプロジェクトを私のパソコンにダウンロードし、
modules/vps/skills/claude-network-guide/SKILL.md を最後まで読んでください。
その手順とルールに厳密に従い、プロジェクトのスクリプトで設定と検証を行ってください。
やり取りは日本語でお願いします。

私のサーバー：
- IP：
- ログイン方法：初期パスワード（ターミナルで私が自分で入力します）
- SSH ユーザーとポート：デフォルト
- 今後ログインに使う名前：bwg
```

変えるのは 3 か所だけです。

- **IP**：管理画面に表示されているサーバー IP。
- **ログイン方法**：業者から鍵ファイルをもらった場合は `鍵ファイル：ファイルのパス` に変えてください（zip でも可）。
- **名前**：`bwg` を好きな名前に。以後は `ssh その名前` と打つだけでサーバーに入れます。

ユーザーとポートが root / 22 でない場合は、「デフォルト」を実際の値に変えてください。

あとは AI が終わるのを待つだけで、通常 10〜20 分です。途中で一度、ターミナルにサーバーのパスワードを入力するよう求められます。**パスワードはチャットに貼らないでください。** 設定が終わるとパスワードでのログインは無効になり、このパソコンからしかログインできなくなります。

AI がプロジェクトをダウンロードできない場合は、自分で [ZIP をダウンロード](https://github.com/clm031102-source/claude-network-guide/archive/refs/heads/main.zip)して解凍し、上の文章に「プロジェクトはここにあります：フォルダのパス」と一行足してください。

完了すると、デスクトップに `my-server-名前-subscriptions-and-accounts-ja.md` というファイルができます。中身は：

- パソコン・ルーター用の **Clash 購読 URL**、iPhone 用の **Shadowrocket 購読 URL**
- 3x-ui パネルの URL、ユーザー名、パスワード
- CLIProxyAPI 管理画面の URL、管理用ログインキー、API の URL と API キー

<details>
<summary>よくサーバーを設定する方へ：skill としてインストールすれば一言で呼び出せます</summary>

ターミナルで一度だけ実行します。

```bash
git clone https://github.com/clm031102-source/claude-network-guide.git
mkdir -p ~/.claude/skills ~/.codex/skills
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.claude/skills/
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.codex/skills/
```

以後は AI に「claude-network-guide で新しいサーバーを設定して」と言うだけで、必要な情報を AI が聞いてきます。

</details>

### 3. 購読を読み込む

- **パソコン（おすすめは Clash Verge Rev）**：[Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev/releases) をインストールして Clash 購読 URL を読み込み、**ルール**モードを選び、**TUN モード**（仮想ネットワークアダプター。求められたらサービスをインストール）をオンにします。システムプロキシだけだと、ブラウザの WebRTC から実際の IP が漏れることがあります。[WebRTC 漏洩の修正ガイド](./docs/Clash-Verge-WebRTC泄露修复手册.md)（中国語。AI アシスタントがそのまま手順どおりに進められるように書かれています）を参照してください。
- **iPhone**：Shadowrocket で Shadowrocket 購読 URL を読み込みます。
- **ルーター（OpenClash）**：同じ Clash 購読 URL がそのまま使え、家中の端末がこの回線を通ります。「設定の購読」に URL を追加してください（YAML ファイルをアップロードすると、通信量が表示されずルールも自動更新されません）。「オンライン購読変換」はオフ、コアは Meta を選びます。
- **すでに v2rayN を使っている場合（Windows / Mac / Linux）**：使えますが、あくまで代替です。「Shadowrocket（iPhone）」の行の購読 URL を読み込み（Clash の行ではありません）、ルーティングは「中国本土をバイパス」を選び、WebRTC 漏洩対策に TUN をオンにします。この購読はノードだけで、AI の振り分けや WeChat 直結のルールは入っていないため、パソコンでは引き続き Clash Verge Rev をおすすめします。詳しくは [v2rayN ガイド](https://github.com/clm031102-source/claude-network-guide/blob/main/modules/vps/site/src/pages/en/howto/v2rayn.mdx)（英語）。

最後に <https://ip.net.coffee/claude/> を開き、自分のサーバーの IP が表示されればつながっています。

## 出張の前に

- **出発前に設定して、一度テストしておきましょう。** 制限のあるネットワークに着いてからでは、プロジェクトのダウンロードや AI ツールを開くことさえ難しくなることがあります。
- スマホとパソコンの両方にクライアントを入れて購読を読み込み、2 つのノードがどちらもつながるか確認してください。
- 現地のあるネットワークでサーバーにつながらないときは、まず別のネットワークを試します（ホテルの Wi-Fi、モバイルデータ、別の通信会社）。どれもだめなら、その地域でサーバーの IP がブロックされている可能性が高く、設定では直りません。業者に IP の変更を依頼してください。
- 回線は自分と家族だけで使い、人とは共有しないでください。

## あとでサーバーを点検する

下の文章を AI に送ります（`bwg` は自分の名前に）。

```text
「claude-network-guide」方式で私のサーバーを点検してください：ssh bwg

方式：https://github.com/clm031102-source/claude-network-guide
プロジェクトをダウンロードし、modules/vps/skills/claude-network-guide/SKILL.md の
「以后的复核和维护」（その後の点検とメンテナンス）の部分を読んでください。
まず点検だけを行い、失敗した項目と原因を教えてください。修正は私が同意してからにしてください。
パスワード、購読 URL、キーはチャットに表示しないでください。やり取りは日本語でお願いします。
```

詳しい資料（[トラブルシューティング](./skills/claude-network-guide/references/troubleshooting.md)、[設計の説明](./skills/claude-network-guide/references/design.md)）は現在中国語のみです。AI に読んでもらえます。

## フィードバック・ご提案



## プライバシー

- このプロジェクトには、実在するサーバーの情報は一切含まれていません。
- サーバーごとのパスワード、鍵、購読 URL、API キーは設定時に新しく生成され、サーバーと自分のパソコンにだけ保存されます。AI がチャットに表示することはありません。
- ログイン情報のファイル、購読 URL、キーは、どこにも投稿したりスクリーンショットを撮ったりしないでください。
- セキュリティ上の問題は [SECURITY.md](./SECURITY.md) をご覧ください。

つながるかどうか、速度がどうかは、現地のネットワークとサーバーの回線にも左右されます。このプロジェクトはサーバーが正しく設定されることを保証しますが、どの国のどの通信会社からも同じ IP につながることまでは保証できません。

## ライセンス

[MIT](./LICENSE)
