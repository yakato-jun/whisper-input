from pathlib import Path
from typing import Optional

from openai import OpenAI


class Transcriber:
    def __init__(self, api_key: str, model: str = "whisper-1"):
        self._client = OpenAI(api_key=api_key)
        self.model = model

    def transcribe(self, audio_path: Path) -> Optional[str]:
        with audio_path.open("rb") as f:
            response = self._client.audio.transcriptions.create(
                model=self.model,
                file=f,
            )
        return getattr(response, "text", None)
