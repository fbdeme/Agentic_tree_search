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
    def browse(self, doc_id: str = None, node_id: str = None,
               depth: int = 1) -> list[dict]:
        """
        List children of a node with configurable depth.
        Like `ls` (depth=1) or `tree` (depth=2+) in a file system.

        Args:
            depth: How many levels deep to show (1=children, 2=grandchildren too)

        Returns:
            [{"doc_id", "node_id", "title", "page_index", "n_children", "depth"}, ...]
        """
        if doc_id is None:
            results = []
            for did, doc in self.documents.items():
                for node in doc["tree"]:
                    results.extend(self._browse_recursive(did, node, depth, 0))
            return results

        if doc_id not in self.documents:
            return []

        if node_id is None:
            results = []
            for n in self.documents[doc_id]["tree"]:
                results.extend(self._browse_recursive(doc_id, n, depth, 0))
            return results

        cache_key = f"{doc_id}::{node_id}"
        if cache_key not in self.node_cache:
            return []

        node = self.node_cache[cache_key]
        results = []
        for child in node.get("nodes", []):
            results.extend(self._browse_recursive(doc_id, child, depth, 0))
        return results

    def _browse_recursive(self, doc_id: str, node: dict,
                          max_depth: int, current_depth: int) -> list[dict]:
        """Recursively collect node listings up to max_depth."""
        results = [self._node_listing(doc_id, node, current_depth)]
        if current_depth < max_depth - 1:
            for child in node.get("nodes", []):
                results.extend(self._browse_recursive(
                    doc_id, child, max_depth, current_depth + 1))
        return results

    def _node_listing(self, doc_id: str, node: dict, depth: int = 0) -> dict:
        return {
            "doc_id": doc_id,
            "node_id": node.get("node_id", ""),
            "title": node.get("title", "Untitled"),
            "page_index": node.get("page_index", 0),
            "n_children": len(node.get("nodes", [])),
            "depth": depth,
        }

    def get_document_overview(self, depth: int = 2) -> str:
        """
        Generate a compact document structure overview for agent's first hop.
        Shows all documents with their sections up to specified depth.
        """
        lines = ["=== Document Structure ==="]
        for doc_id, doc in self.documents.items():
            lines.append(f"\n📄 {doc['name']} (id={doc_id})")
            items = self.browse(doc_id, None, depth=depth)
            for item in items:
                indent = "  " * (item["depth"] + 1)
                children_str = f" [{item['n_children']} subsections]" if item["n_children"] > 0 else ""
                lines.append(f"{indent}[{item['node_id']}] {item['title'][:60]}{children_str}")
        return "\n".join(lines)

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

        content = node.get("text", node.get("summary", ""))

        # Append structured table data from references so LLM can read
        # table values that are corrupted in raw PDF text extraction
        table_sections = []
        for ref in node.get("references", []):
            if ref.get("structured_text"):
                table_sections.append(
                    f"\n[{ref['id']}: {ref.get('caption', '')}]\n{ref['structured_text']}"
                )
        if table_sections:
            content += "\n\n--- Referenced Tables (structured) ---" + "".join(table_sections)

        return {
            "doc_id": doc_id,
            "node_id": node_id,
            "title": node.get("title", ""),
            "content": content,
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
               max_results: int = 5, prf: bool = True) -> list[dict]:
        """
        BM25-ranked search with Pseudo-Relevance Feedback (RM3).

        1. Initial BM25 search with original query
        2. PRF: Extract top terms from top-K results, expand query
        3. Re-score with expanded query

        Returns:
            [{"doc_id", "node_id", "title", "page_index", "score", "snippet"}, ...]
        """
        if self._bm25_index is None:
            self._build_bm25_index()

        query_tokens = keyword.lower().split()
        scores = self._bm25_index.get_scores(query_tokens)

        # PRF: Pseudo-Relevance Feedback (RM3)
        if prf:
            # Get top-3 documents from initial search
            top_k_prf = 3
            alpha = 0.4  # weight of feedback terms
            n_expand = 5  # number of expansion terms

            initial_top = sorted(enumerate(scores), key=lambda x: -x[1])[:top_k_prf]
            if initial_top and initial_top[0][1] > 0:
                # Collect term frequencies from top docs
                term_freq = {}
                for idx, _ in initial_top:
                    for token in self._bm25_corpus[idx]:
                        if len(token) > 2 and token not in query_tokens:
                            term_freq[token] = term_freq.get(token, 0) + 1

                # Select top expansion terms (most frequent in top docs)
                expansion = sorted(term_freq.items(), key=lambda x: -x[1])[:n_expand]
                expand_tokens = [t for t, _ in expansion]

                if expand_tokens:
                    # Re-score: combine original + expansion scores
                    expand_scores = self._bm25_index.get_scores(expand_tokens)
                    scores = [(1 - alpha) * s + alpha * e
                              for s, e in zip(scores, expand_scores)]

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
1. browse(doc_id, node_id, depth)
   - Lists children of a node (like `ls` or `tree`)
   - depth=1 (default): immediate children only
   - depth=2: children + grandchildren (table of contents view)
   - Use to drill down into a specific section and see its structure

2. read(doc_id, node_id)
   - Returns the full content of a specific node (like `cat`)
   - Use when you've identified a relevant section and want to read it

3. search(keyword)
   - BM25-ranked keyword search across all nodes (like `grep`)
   - Use when you know a specific term, value, or concept to find"""

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
