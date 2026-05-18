import time
from typing import Optional

from openai import OpenAI


SYSTEM_INSTRUCTIONS = """\
あなたは音声書き起こし結果を整形するアシスタントです。

絶対遵守:
- 入力テキストの意味内容を変えない（要約・言い換え・情報の追加や削除を禁止）
- ユーザー指示に書かれたルールは、入力の長さに関わらず必ず適用する
- ルールに該当する語があれば必ず変換する。例示リストに無くても、ルールの意図に沿って判断する
- 整形済みテキストのみを出力（前置き・後書き・コードフェンス・説明文を一切付けない）
"""


class TextFormatter:
    """
    Two-stage pipeline helper: takes a raw transcription and a user
    instruction text, returns a formatted version using a GPT-5 family
    reasoning model. Falls back to the raw input on any error.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.4-mini",
        reasoning_effort: str = "low",
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.reasoning_effort = reasoning_effort

    def format_text(self, text: str, user_instructions: str) -> str:
        if not text:
            print("[formatter] skipped: empty input text")
            return text
        if not user_instructions:
            print("[formatter] skipped: no user instructions")
            return text
        print(
            f"[formatter] calling model={self.model} effort={self.reasoning_effort} "
            f"(instructions={len(user_instructions)} chars, input={len(text)} chars)"
        )
        start = time.monotonic()
        try:
            instructions = (
                f"{SYSTEM_INSTRUCTIONS}\n"
                f"--- USER INSTRUCTIONS BELOW ---\n"
                f"{user_instructions}"
            )
            response = self._client.responses.create(
                model=self.model,
                reasoning={"effort": self.reasoning_effort},
                instructions=instructions,
                input=text,
            )
            elapsed = time.monotonic() - start
            output: Optional[str] = getattr(response, "output_text", None)
            if not output:
                print(f"[formatter] returned empty output in {elapsed:.2f}s, falling back to raw")
                return text
            changed = "changed" if output != text else "unchanged"
            print(
                f"[formatter] returned {len(output)} chars in {elapsed:.2f}s ({changed})"
            )
            return output
        except Exception as exc:  # noqa: BLE001
            elapsed = time.monotonic() - start
            print(f"[formatter] failed after {elapsed:.2f}s, falling back to raw: {exc}")
            return text
