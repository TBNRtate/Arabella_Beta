from __future__ import annotations

from collections import defaultdict


class Collection:
    def __init__(self):
        self._docs = {}

    def add(self, documents, ids, metadatas):
        for doc, item_id, metadata in zip(documents, ids, metadatas, strict=False):
            self._docs[item_id] = {"document": doc, "metadata": metadata}

    def query(self, query_texts, n_results=5):
        q = (query_texts or [""])[0].lower()
        scored = []
        for item_id, payload in self._docs.items():
            doc = payload["document"]
            score = 1 if q in doc.lower() else 0
            scored.append((score, item_id, doc, payload["metadata"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:n_results]
        return {
            "ids": [[item[1] for item in top]],
            "documents": [[item[2] for item in top]],
            "metadatas": [[item[3] for item in top]],
        }

    def delete(self, ids):
        for item_id in ids:
            self._docs.pop(item_id, None)

    def count(self):
        return len(self._docs)

    def get(self, include=None, where=None):
        ids = list(self._docs.keys())
        return {
            "ids": ids,
            "documents": [self._docs[item_id]["document"] for item_id in ids],
            "metadatas": [self._docs[item_id]["metadata"] for item_id in ids],
        }


class PersistentClient:
    _stores = defaultdict(dict)

    def __init__(self, path: str):
        self.path = path

    def get_or_create_collection(self, name: str, embedding_function=None):
        if name not in self._stores[self.path]:
            self._stores[self.path][name] = Collection()
        return self._stores[self.path][name]
