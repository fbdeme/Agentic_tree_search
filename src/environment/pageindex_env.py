"""
PageIndexEnvironment: Document exploration environment using PageIndex tree index.
Provides file-system-like tools for agent navigation:
  - browse(node_id): list children of a node (like `ls`)
  - read(node_id): get full content of a node (like `cat`)
  - search(keyword): find nodes containing keyword (like `grep`)
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_PATH = Path(__file__).parent.parent.parent / "pageindex_core"
sys.path.insert(0, str(PAGEINDEX_PATH))


class PageIndexEnvironment:
    """
    PageIndex-based document exploration environment.
    Serves as GWM's World, providing tools for agent Actions.
    """

    def __init__(self, model: str = "gpt-4.1"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.documents: dict[str, dict] = {}    # doc_id -> {tree, name, pdf_path}
        self.node_cache: dict[str, dict] = {}   # "doc_id::node_id" -> node dict
        self.parent_map: dict[str, str] = {}    # "doc_id::node_id" -> "doc_id::parent_node_id"
        self._bm25_index = None                 # Built lazily on first search

    # -----------------------------------------------------------
    # Document registration
    # -----------------------------------------------------------
    def register_tree(self, doc_id: str, tree: list, doc_name: str = "",
                      pdf_path: str = "") -> None:
        self.documents[doc_id] = {
            "tree": tree,
            "name": doc_name or doc_id,
            "pdf_path": pdf_path,
        }
        self._cache_nodes(doc_id, tree)
        print(f"[Environment] Registered: {doc_id} ({len(self.node_cache)} nodes cached)")

    def _cache_nodes(self, doc_id: str, nodes: list, depth: int = 0,
                     parent_key: str = "") -> None:
        for node in nodes:
            nid = node.get("node_id", "")
            if nid:
                cache_key = f"{doc_id}::{nid}"
                self.node_cache[cache_key] = {
                    **node,
                    "doc_id": doc_id,
                    "depth": depth,
                }
                if parent_key:
                    self.parent_map[cache_key] = parent_key
            sub = node.get("nodes", [])
            if sub:
                self._cache_nodes(doc_id, sub, depth + 1,
                                  parent_key=f"{doc_id}::{nid}" if nid else parent_key)

    # -----------------------------------------------------------
    # Tool 1: browse — list children of a node (like `ls`)
    # -----------------------------------------------------------
    def browse(self, doc_id: str = None, node_id: str = None) -> list[dict]:
        """
        List children of a node. If node_id is None, returns root-level nodes.
        Like `ls` in a file system.

        Returns:
            [{"doc_id", "node_id", "title", "page_index", "summary", "n_children"}, ...]
        """
        if doc_id is None:
            # List all documents and their root nodes
            results = []
            for did, doc in self.documents.items():
                for node in doc["tree"]:
                    results.append(self._node_listing(did, node))
            return results

        if doc_id not in self.documents:
            return []

        if node_id is None:
            # Root level of this document
            return [self._node_listing(doc_id, n)
                    for n in self.documents[doc_id]["tree"]]

        # Children of specific node
        cache_key = f"{doc_id}::{node_id}"
        if cache_key not in self.node_cache:
            return []

        node = self.node_cache[cache_key]
        children = node.get("nodes", [])
        return [self._node_listing(doc_id, c) for c in children]

    def _node_listing(self, doc_id: str, node: dict) -> dict:
        return {
            "doc_id": doc_id,
            "node_id": node.get("node_id", ""),
            "title": node.get("title", "Untitled"),
            "page_index": node.get("page_index", 0),
            "summary": (node.get("summary", "") or "")[:150],
            "n_children": len(node.get("nodes", [])),
        }

    # -----------------------------------------------------------
    # Tool 2: read — get full content of a node (like `cat`)
    # -----------------------------------------------------------
    def read(self, doc_id: str, node_id: str) -> Optional[dict]:
        """
        Get full content of a specific node.
        Like `cat` in a file system.

        Returns:
            {"doc_id", "node_id", "title", "content", "summary",
             "page_range", "references", "n_children"}
        """
        cache_key = f"{doc_id}::{node_id}"
        node = self.node_cache.get(cache_key)
        if not node:
            return None

        return {
            "doc_id": doc_id,
            "node_id": node_id,
            "title": node.get("title", ""),
            "content": node.get("text", node.get("summary", "")),
            "summary": node.get("summary", ""),
            "page_range": str(node.get("start_index", node.get("page_index", "?"))),
            "references": node.get("references", []),
            "n_children": len(node.get("nodes", [])),
        }

    # -----------------------------------------------------------
    # Tool 3: search — BM25-ranked keyword search (like `grep | sort`)
    # -----------------------------------------------------------
    def _build_bm25_index(self) -> None:
        """Build BM25 index over all cached nodes. Called lazily on first search."""
        from rank_bm25 import BM25Okapi

        self._bm25_keys = []     # cache_keys in index order
        self._bm25_corpus = []   # tokenized documents

        for cache_key, node in self.node_cache.items():
            title = node.get("title", "")
            summary = node.get("summary", "") or ""
            text = node.get("text", "") or ""
            # Include reference captions + structured table data in searchable text
            ref_parts = []
            for ref in node.get("references", []):
                ref_parts.append(ref.get("caption", ""))
                if ref.get("structured_text"):
                    ref_parts.append(ref["structured_text"])
            ref_text = " ".join(ref_parts)
            # Combine all searchable text, weight title higher by repeating
            combined = f"{title} {title} {title} {summary} {ref_text} {text}"
            tokens = combined.lower().split()
            self._bm25_keys.append(cache_key)
            self._bm25_corpus.append(tokens)

        self._bm25_index = BM25Okapi(self._bm25_corpus)

    def search(self, keyword: str, doc_ids: Optional[list[str]] = None,
               max_results: int = 5) -> list[dict]:
        """
        BM25-ranked search across all node titles, summaries, and text.

        BM25 naturally handles:
        - Term frequency: nodes mentioning the keyword more often score higher
        - Document length normalization: shorter, focused nodes score higher
          than long parent nodes with the same keyword count
        - IDF: rare terms across the corpus get higher weight

        Returns:
            [{"doc_id", "node_id", "title", "page_index", "score", "snippet"}, ...]
        """
        if self._bm25_index is None:
            self._build_bm25_index()

        query_tokens = keyword.lower().split()
        scores = self._bm25_index.get_scores(query_tokens)

        # Pair scores with cache keys and sort descending
        scored = sorted(zip(scores, self._bm25_keys), reverse=True)

        results = []
        for score, cache_key in scored:
            if score <= 0:
                break
            if len(results) >= max_results:
                break

            node = self.node_cache[cache_key]
            doc_id = node.get("doc_id", "")
            if doc_ids and doc_id not in doc_ids:
                continue

            # Extract snippet around keyword
            title = node.get("title", "")
            summary = node.get("summary", "") or ""
            text = node.get("text", "") or ""
            keyword_lower = keyword.lower()

            snippet = ""
            if keyword_lower in title.lower():
                snippet = title
            elif keyword_lower in summary.lower():
                idx = summary.lower().find(keyword_lower)
                start = max(0, idx - 50)
                snippet = summary[start:idx + len(keyword) + 50]
            elif keyword_lower in text.lower():
                idx = text.lower().find(keyword_lower)
                start = max(0, idx - 50)
                snippet = text[start:idx + len(keyword) + 50]
            else:
                snippet = title  # BM25 matched on tokenized terms

            results.append({
                "doc_id": doc_id,
                "node_id": node.get("node_id", ""),
                "title": title,
                "page_index": node.get("page_index", 0),
                "score": round(float(score), 2),
                "snippet": snippet.strip(),
            })

        return results

    # -----------------------------------------------------------
    # Tool descriptions for LLM tool-use
    # -----------------------------------------------------------
    def get_tool_descriptions(self) -> str:
        """Return tool descriptions for the LLM to choose from."""
        docs = []
        for did, doc in self.documents.items():
            docs.append(f"  - {did}: {doc['name']}")

        return f"""You have access to three tools for exploring regulatory documents:

Available documents:
{chr(10).join(docs)}

Tools:
1. browse(doc_id, node_id)
   - Lists the children of a node (like `ls` in a file system)
   - Use doc_id=null, node_id=null to see root-level nodes of all documents
   - Use node_id=null to see root-level nodes of a specific document
   - Use both to drill down into a specific section

2. read(doc_id, node_id)
   - Returns the full content of a specific node (like `cat`)
   - Use this when you've identified a relevant section and want to read it

3. search(keyword)
   - Searches for a keyword across all node titles, summaries, and text (like `grep`)
   - Use this when you know a specific term, value, or concept to find"""

    # -----------------------------------------------------------
    # Legacy: search_relevant_nodes (for backward compatibility)
    # -----------------------------------------------------------
    def search_relevant_nodes(
        self,
        query: str,
        doc_ids: Optional[list[str]] = None,
        top_k: int = 3,
        exclude_node_ids: Optional[set[str]] = None,
    ) -> list[dict]:
        """Legacy method — kept for backward compatibility."""
        if doc_ids is None:
            doc_ids = list(self.documents.keys())

        tree_summary = self.get_tree_summary(doc_ids)

        exclude_instruction = ""
        if exclude_node_ids:
            exclude_list = ", ".join(sorted(exclude_node_ids))
            exclude_instruction = (
                f"\n\n⚠️ The following nodes have already been explored and MUST be excluded:\n{exclude_list}\n"
                f"Select only NEW nodes not in the above list."
            )

        prompt = (
            f"Below is the hierarchical tree structure of the document:\n{tree_summary}\n\n"
            f"Search query: {query}\n\n"
            f"Select up to {top_k} nodes most relevant to the query above.{exclude_instruction}\n"
            f"Respond ONLY as a JSON array:\n"
            f'[{{"doc_id": "...", "node_id": "...", "reason": "reason for selection"}}]'
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical document exploration expert. Select the sections most relevant to the query accurately.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()

        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            selections = json.loads(cleaned)
        except Exception:
            return []

        results = []
        for sel in selections:
            doc_id = sel.get("doc_id", "")
            node_id = sel.get("node_id", "")
            cache_key = f"{doc_id}::{node_id}"
            if cache_key in self.node_cache:
                node = self.node_cache[cache_key]
                results.append(
                    {
                        "doc_id": doc_id,
                        "node_id": node_id,
                        "title": node.get("title", ""),
                        "content": node.get("text", node.get("summary", "")),
                        "page_range": f"{node.get('start_index', node.get('page_index', '?'))}",
                        "references": node.get("references", []),
                        "reason": sel.get("reason", ""),
                    }
                )
        return results

    def get_tree_summary(self, doc_ids: Optional[list[str]] = None) -> str:
        """Legacy: full tree summary text."""
        if doc_ids is None:
            doc_ids = list(self.documents.keys())
        lines = []
        for doc_id in doc_ids:
            if doc_id not in self.documents:
                continue
            doc = self.documents[doc_id]
            lines.append(f"\n📄 {doc['name']} (id={doc_id})")
            lines.append(self._tree_to_text(doc["tree"], indent=0))
        return "\n".join(lines)

    def _tree_to_text(self, nodes: list, indent: int = 0) -> str:
        lines = []
        prefix = "  " * indent
        for node in nodes:
            nid = node.get("node_id", "?")
            title = node.get("title", "Untitled")
            summary = node.get("summary", "")[:100]
            page = node.get("page_index") or node.get("start_index", "?")
            lines.append(f"{prefix}[{nid}] p.{page} {title}")
            if summary:
                lines.append(f"{prefix}    → {summary}")
            sub = node.get("nodes", [])
            if sub:
                lines.append(self._tree_to_text(sub, indent + 1))
        return "\n".join(lines)

    @property
    def doc_count(self) -> int:
        return len(self.documents)

    @property
    def node_count(self) -> int:
        return len(self.node_cache)
