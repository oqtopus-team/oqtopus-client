# oqtopus-client

OQTOPUS Cloud User API 向けの Python SDK です。

このドキュメントは `src/oqtopus_client` の docstring から API リファレンスを自動生成しています。

## 主な機能

- User API の各エンドポイントを Python メソッドで操作
- ダウンロードした OpenAPI 定義から生成した Pydantic モデルで型安全に入出力を扱う
- API トークンの文字列指定とファイル指定の両方に対応
- コアクライアント利用時は、他の量子ソフトウェア SDK に依存しない
- OpenAPI 生成モデルは内部で利用し、`OqtopusJobSpec` や `run_*` ヘルパーで利用者側の記述を簡潔化
- HTTP 通信は内部で非同期実行しつつ、公開 API は使いやすい同期 API を提供
- 組み込みの retry/backoff 制御と型付き結果ラッパーで運用時の安定性を向上

## クイックリンク

- [Quickstart](quickstart.md)
- [API Reference](api.md)
- [Models](models.md)
- [Examples](examples.md)

## 言語

- [English](../en/index.md)
