import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import frontmatter


@dataclass
class PromptEntry:
    identifier: str
    name: str
    description: str
    body: str
    path: Path


@dataclass
class PromptManager:
    prompts_dir: Path
    _entries: dict[str, PromptEntry] = field(default_factory=dict)
    _enabled: set[str] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.prompts_dir = Path(self.prompts_dir)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _load_all(self) -> None:
        entries: dict[str, PromptEntry] = {}
        for md_path in sorted(self.prompts_dir.glob("*.md")):
            identifier = md_path.stem
            try:
                post = frontmatter.load(md_path)
            except Exception as exc:  # noqa: BLE001
                print(f"Failed to parse prompt '{md_path.name}': {exc}")
                continue
            name = str(post.metadata.get("name") or identifier)
            description = str(post.metadata.get("description") or "")
            body = (post.content or "").strip()
            entries[identifier] = PromptEntry(
                identifier=identifier,
                name=name,
                description=description,
                body=body,
                path=md_path,
            )
        with self._lock:
            self._entries = entries
            self._enabled = {i for i in self._enabled if i in entries}

    def reload(self) -> None:
        self._load_all()

    def list_entries(self) -> list[PromptEntry]:
        with self._lock:
            return [self._entries[k] for k in sorted(self._entries.keys())]

    def is_enabled(self, identifier: str) -> bool:
        with self._lock:
            return identifier in self._enabled

    def set_enabled(self, identifier: str, enabled: bool) -> None:
        with self._lock:
            if identifier not in self._entries:
                print(f"[manager] set_enabled: unknown identifier '{identifier}'")
                return
            if enabled:
                self._enabled.add(identifier)
            else:
                self._enabled.discard(identifier)
            current = sorted(self._enabled)
        print(f"[manager] set_enabled({identifier}, {enabled}) -> enabled={current}")

    def enable_many(self, identifiers: Iterable[str]) -> None:
        with self._lock:
            for ident in identifiers:
                if ident in self._entries:
                    self._enabled.add(ident)

    def get_enabled_identifiers(self) -> list[str]:
        with self._lock:
            return sorted(self._enabled)

    def build_merged_prompt(self) -> str:
        with self._lock:
            ordered = [self._entries[k] for k in sorted(self._enabled) if k in self._entries]
        bodies = [e.body for e in ordered if e.body]
        return "\n\n".join(bodies)
