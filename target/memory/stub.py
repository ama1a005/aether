from typing import Any, Optional

class MemoryStub:
    def __init__(self):
        self._store = {}
        
    def store(self, key: str, value: Any) -> None:
        self._store[key] = value
        
    def retrieve(self, key: str) -> Optional[Any]:
        return self._store.get(key)
        
    def clear(self) -> None:
        self._store.clear()
