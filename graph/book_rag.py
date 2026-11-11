"""
Book RAG & Daily Content Queue (`graph/book_rag.py`).

Hỗ trợ nạp sách (.epub, .txt, .md, .docx, .pdf) 1 lần vào SQLite + FTS5:
  1. Tách thông minh theo ranh giới Chương / Mục & Đoạn văn (không cắt ngang câu).
  2. Mỗi chunk ~800-1200 từ có overlap 1-2 đoạn cuối để không đứt mạch truyện.
  3. Chế độ RAG truy xuất 1-2 chunk liên quan nhất cho topic (`--book <id> "<topic>"`).
  4. Chế độ đăng hằng ngày (`--book <id> --daily`): tự lấy chunk `pending` kế tiếp,
     sinh topic tập trung vào đúng đoạn sách đó rồi đánh dấu `done` sau khi render.
"""

from __future__ import annotations

import os
import re
import sqlite3
import time
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from config.settings import WORKSPACE_DIR

BOOK_RAG_DB_PATH: Path = WORKSPACE_DIR / "book_rag.sqlite"
EMBED_MODEL_ID: str = os.getenv("RAG_EMBED_MODEL", "intfloat/multilingual-e5-small").strip()
_EMBED_CACHE: Dict[str, Any] = {}

_SECTION_RE = re.compile(
    r"^(?:"
    r"lời giới thiệu|lời mở đầu|lời tựa|mở đầu|vào truyện|bạt|kết thúc|phần kết|"
    r"(?:chương|phần|hồi|tập|mục|chapter|part)\s+[\divxlcdm]+(?:\s*[-–—]\s*[\divxlcdm]+)?(?:\s*[:.\-–].*)?|"
    r"chương\s+kết|"
    r"\*{3,}"
    r")$",
    re.IGNORECASE,
)

_BOILERPLATE_RE = re.compile(
    r"^(?:cover|mục lục|chia\s*s[ẽẻ]\s*ebook|http[s]?://|www\.|ebook miễn phí)",
    re.IGNORECASE,
)


def _slugify(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_").lower()
    return slug[:48] or "book"


class _HTMLParagraphParser(HTMLParser):
    """Tách văn bản sạch theo thẻ block (<p>, <h1>..<h6>, <li>, <div>) trong EPUB."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: List[str] = []
        self._buf: List[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        t = tag.lower()
        if t in ("script", "style", "head", "title"):
            self._skip = True
        elif t in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "div"):
            self._flush()
        elif t == "br":
            self._buf.append(" ")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("script", "style", "head", "title"):
            self._skip = False
        elif t in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "div"):
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._buf.append(data)

    def _flush(self) -> None:
        raw = "".join(self._buf).replace("\xa0", " ")
        self._buf.clear()
        clean = re.sub(r"\s+", " ", raw).strip()
        if clean:
            self.blocks.append(clean)


def _extract_epub(path: Path) -> Tuple[str, List[str]]:
    title = path.stem
    paragraphs: List[str] = []

    with zipfile.ZipFile(path, "r") as zf:
        names = set(zf.namelist())
        opf_files = [n for n in names if n.lower().endswith(".opf")]
        spine_files: List[str] = []

        if opf_files:
            opf_name = opf_files[0]
            base_dir = opf_name.rsplit("/", 1)[0] + "/" if "/" in opf_name else ""
            root = ET.fromstring(zf.read(opf_name))

            for el in root.iter():
                if el.tag.endswith("}title") and (el.text or "").strip():
                    title = el.text.strip()
                    break

            ns = {"opf": "http://www.idpf.org/2007/opf"}
            manifest = {
                el.attrib["id"]: el.attrib["href"]
                for el in root.findall(".//opf:manifest/opf:item", ns)
                if "id" in el.attrib and "href" in el.attrib
            }
            for el in root.findall(".//opf:spine/opf:itemref", ns):
                href = manifest.get(el.attrib.get("idref", ""), "")
                full = base_dir + href
                if full in names:
                    spine_files.append(full)

        if not spine_files:
            spine_files = sorted(n for n in names if n.lower().endswith((".html", ".xhtml", ".htm")))

        for sf in spine_files:
            raw_html = zf.read(sf).decode("utf-8", errors="ignore")
            parser = _HTMLParagraphParser()
            parser.feed(raw_html)
            parser._flush()
            paragraphs.extend(parser.blocks)

    return title, paragraphs


def _extract_docx(path: Path) -> Tuple[str, List[str]]:
    paragraphs: List[str] = []
    with zipfile.ZipFile(path, "r") as zf:
        if "word/document.xml" not in zf.namelist():
            return path.stem, []
        root = ET.fromstring(zf.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for p in root.findall(".//w:p", ns):
            texts = [t.text for t in p.findall(".//w:t", ns) if t.text]
            line = re.sub(r"\s+", " ", "".join(texts)).strip()
            if line:
                paragraphs.append(line)
    return path.stem, paragraphs


def _extract_txt(path: Path) -> Tuple[str, List[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    blocks = [re.sub(r"\s+", " ", b).strip() for b in re.split(r"\n\s*\n+", text)]
    return path.stem, [b for b in blocks if b]


def _extract_pdf(path: Path) -> Tuple[str, List[str]]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Cần cài `pypdf` để đọc PDF (khuyến nghị dùng .epub hoặc .txt cho nhẹ và sạch).") from exc

    reader = PdfReader(str(path))
    paragraphs: List[str] = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        for block in re.split(r"\n\s*\n+", txt):
            clean = re.sub(r"\s+", " ", block).strip()
            if clean:
                paragraphs.append(clean)
    return path.stem, paragraphs


def extract_book_paragraphs(file_path: str | Path) -> Tuple[str, List[str]]:
    """Đọc sách thành (tiêu_đề, danh_sách_đoạn_văn) hỗ trợ .epub, .txt, .md, .docx, .pdf."""
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file sách: {path}")

    ext = path.suffix.lower()
    if ext == ".epub":
        return _extract_epub(path)
    if ext in (".txt", ".md"):
        return _extract_txt(path)
    if ext == ".docx":
        return _extract_docx(path)
    if ext == ".pdf":
        return _extract_pdf(path)
    raise ValueError(f"Định dạng chưa hỗ trợ: {ext} (hỗ trợ .epub, .txt, .md, .docx, .pdf)")


def _is_section_heading(para: str) -> bool:
    if len(para) > 85 or len(para.split()) > 14:
        return False
    return bool(_SECTION_RE.match(para.strip()))


def chunk_book_paragraphs(
    paragraphs: List[str],
    target_words: int = 900,
    max_words: int = 1250,
    overlap_paragraphs: int = 2,
) -> List[Dict[str, Any]]:
    """
    Gom các đoạn văn thành chunk theo ranh giới chương/mục & đoạn văn:
      - Không bao giờ cắt ngang câu/đoạn.
      - Khi một chương dài vượt `max_words`, tách thành nhiều phần có gối đầu `overlap_paragraphs`.
    """
    sections: List[Tuple[str, List[str]]] = []
    current_title = "Mở đầu"
    current_paras: List[str] = []

    for raw_p in paragraphs:
        p = raw_p.strip()
        if not p or _BOILERPLATE_RE.match(p):
            continue
        if _is_section_heading(p):
            if current_paras:
                sections.append((current_title, current_paras))
                current_paras = []
            if p.strip("*") != "":
                current_title = p.lstrip("#").strip()
            continue
        current_paras.append(p)

    if current_paras:
        sections.append((current_title, current_paras))

    chunks: List[Dict[str, Any]] = []
    for sec_title, sec_paras in sections:
        sec_words = sum(len(p.split()) for p in sec_paras)
        if sec_words < 45:
            continue

        buf: List[str] = []
        buf_words = 0
        part_num = 1

        for p in sec_paras:
            pw = len(p.split())
            if buf and (buf_words + pw > max_words or (buf_words >= target_words and buf_words + pw > target_words + 150)):
                chunks.append(
                    {
                        "section_title": sec_title if part_num == 1 else f"{sec_title} (tiếp {part_num})",
                        "content": "\n\n".join(buf),
                        "word_count": buf_words,
                    }
                )
                part_num += 1
                tail = buf[-overlap_paragraphs:] if overlap_paragraphs > 0 else []
                tail_words = sum(len(x.split()) for x in tail)
                if tail_words > 260 and len(tail) > 1:
                    tail = tail[-1:]
                    tail_words = len(tail[0].split())
                buf = list(tail)
                buf_words = tail_words

            buf.append(p)
            buf_words += pw

        if buf and buf_words >= 45:
            chunks.append(
                {
                    "section_title": sec_title if part_num == 1 else f"{sec_title} (tiếp {part_num})",
                    "content": "\n\n".join(buf),
                    "word_count": buf_words,
                }
            )

    for idx, ch in enumerate(chunks, start=1):
        ch["chunk_idx"] = idx
    return chunks


def _connect_db(db_path: Path = BOOK_RAG_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            book_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            total_chunks INTEGER NOT NULL,
            total_words INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            chunk_idx INTEGER NOT NULL,
            section_title TEXT NOT NULL,
            content TEXT NOT NULL,
            word_count INTEGER NOT NULL,
            topic_suggestion TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            last_video_path TEXT NOT NULL DEFAULT '',
            embedding BLOB DEFAULT NULL
        )
        """
    )
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(chunks)").fetchall()}
    if "embedding" not in cols:
        conn.execute("ALTER TABLE chunks ADD COLUMN embedding BLOB DEFAULT NULL")
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_id UNINDEXED,
            book_id UNINDEXED,
            section_title,
            content,
            tokenize='unicode61'
        )
        """
    )
    return conn


def _fallback_topic_from_chunk(book_title: str, section_title: str, content: str) -> str:
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", content.replace("\n", " ")) if len(s.split()) >= 5]
    snippet = sentences[0] if sentences else section_title
    if len(snippet) > 90:
        snippet = " ".join(snippet.split()[:14]) + "..."
    return f"Review sách {book_title} ({section_title}): {snippet}"


def _get_embedder() -> Tuple[Any, Any]:
    """Tải model embedding đa ngôn ngữ/tiếng Việt chạy local CPU (0 token API)."""
    if "ready" in _EMBED_CACHE:
        return _EMBED_CACHE.get("tok"), _EMBED_CACHE.get("mod")
    try:
        from transformers import AutoModel, AutoTokenizer

        try:
            tok = AutoTokenizer.from_pretrained(EMBED_MODEL_ID, local_files_only=True)
            mod = AutoModel.from_pretrained(EMBED_MODEL_ID, local_files_only=True)
        except Exception:
            tok = AutoTokenizer.from_pretrained(EMBED_MODEL_ID)
            mod = AutoModel.from_pretrained(EMBED_MODEL_ID)
        mod.eval()
        _EMBED_CACHE.update({"ready": True, "tok": tok, "mod": mod})
        return tok, mod
    except Exception as e:
        print(f" [Book RAG] Chưa nạp được model embedding local ({e}) -> Dùng BM25/FTS5 thuần.")
        _EMBED_CACHE.update({"ready": False, "tok": None, "mod": None})
        return None, None


def embed_texts(texts: Sequence[str], is_query: bool = False, batch_size: int = 16) -> Optional[np.ndarray]:
    """Mã hóa danh sách văn bản sang vector chuẩn hóa L2 (float32)."""
    if not texts:
        return None
    tok, mod = _get_embedder()
    if tok is None or mod is None:
        return None
    import torch

    prefix = "query: " if (is_query and "e5" in EMBED_MODEL_ID.lower()) else ("passage: " if "e5" in EMBED_MODEL_ID.lower() else "")
    vecs: List[np.ndarray] = []
    for i in range(0, len(texts), batch_size):
        batch = [prefix + t.strip() for t in texts[i : i + batch_size]]
        enc = tok(batch, padding=True, truncation=True, max_length=384, return_tensors="pt")
        with torch.no_grad():
            out = mod(**enc)
            mask = enc["attention_mask"].unsqueeze(-1).expand(out.last_hidden_state.size()).float()
            emb = (out.last_hidden_state * mask).sum(1) / torch.clamp(mask.sum(1), min=1e-9)
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
        vecs.append(emb.cpu().numpy().astype(np.float32))
    return np.vstack(vecs)


def _embed_chunk_text(section_title: str, content: str) -> Optional[bytes]:
    """Chia chunk dài thành 2-3 cửa sổ gối đầu rồi lấy trung bình vector để đại diện trọn vẹn cả đoạn."""
    words = content.split()
    if not words:
        return None
    windows: List[str] = []
    step, win_size = 240, 300
    for start in range(0, len(words), step):
        seg = " ".join(words[start : start + win_size])
        windows.append(f"{section_title}: {seg}")
        if start + win_size >= len(words) or len(windows) >= 4:
            break
    embs = embed_texts(windows, is_query=False)
    if embs is None:
        return None
    avg = embs.mean(axis=0)
    norm = float(np.linalg.norm(avg))
    if norm > 1e-9:
        avg = avg / norm
    return avg.astype(np.float32).tobytes()


def ensure_book_embeddings(book_id: str, db_path: Path = BOOK_RAG_DB_PATH) -> int:
    """Tính & lưu embedding local cho các chunk còn thiếu (chỉ chạy 1 lần mỗi sách)."""
    if not db_path.exists():
        return 0
    conn = _connect_db(db_path)
    try:
        rows = conn.execute(
            "SELECT chunk_id, section_title, content FROM chunks WHERE book_id = ? AND embedding IS NULL ORDER BY chunk_idx",
            (book_id,),
        ).fetchall()
        if not rows:
            return 0
        tok, mod = _get_embedder()
        if tok is None or mod is None:
            return 0
        print(f"[Book RAG] Đang tạo vector ngữ nghĩa local cho {len(rows)} chunks của '{book_id}' (0 token API)...")
        updated = 0
        for r in rows:
            blob = _embed_chunk_text(r["section_title"], r["content"])
            if blob is not None:
                conn.execute("UPDATE chunks SET embedding = ? WHERE chunk_id = ?", (blob, r["chunk_id"]))
                updated += 1
        conn.commit()
        return updated
    finally:
        conn.close()


def ingest_book(
    file_path: str | Path,
    book_id: Optional[str] = None,
    target_words: int = 900,
    db_path: Path = BOOK_RAG_DB_PATH,
    build_embeddings: bool = True,
) -> Dict[str, Any]:
    """Nạp toàn bộ sách vào SQLite FTS5 + Vector Embedding local + hàng đợi topic hằng ngày."""
    t0 = time.perf_counter()
    title, paragraphs = extract_book_paragraphs(file_path)
    chunks = chunk_book_paragraphs(paragraphs, target_words=target_words)
    if not chunks:
        raise ValueError(f"Không trích xuất được nội dung từ {file_path}")

    resolved_id = _slugify(book_id or title or Path(file_path).stem)
    total_words = sum(c["word_count"] for c in chunks)

    conn = _connect_db(db_path)
    try:
        conn.execute("DELETE FROM chunks_fts WHERE book_id = ?", (resolved_id,))
        conn.execute("DELETE FROM chunks WHERE book_id = ?", (resolved_id,))
        conn.execute(
            """
            INSERT OR REPLACE INTO books (book_id, title, file_path, total_chunks, total_words, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (resolved_id, title, str(Path(file_path).resolve()), len(chunks), total_words, time.strftime("%Y-%m-%d %H:%M:%S")),
        )
        for ch in chunks:
            topic_sug = _fallback_topic_from_chunk(title, ch["section_title"], ch["content"])
            cur = conn.execute(
                """
                INSERT INTO chunks (book_id, chunk_idx, section_title, content, word_count, topic_suggestion, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """,
                (resolved_id, ch["chunk_idx"], ch["section_title"], ch["content"], ch["word_count"], topic_sug),
            )
            conn.execute(
                "INSERT INTO chunks_fts (chunk_id, book_id, section_title, content) VALUES (?, ?, ?, ?)",
                (cur.lastrowid, resolved_id, ch["section_title"], ch["content"]),
            )
        conn.commit()
    finally:
        conn.close()

    embedded_cnt = ensure_book_embeddings(resolved_id, db_path) if build_embeddings else 0
    elapsed = round(time.perf_counter() - t0, 3)
    print(
        f"[Book RAG] Đã nạp '{title}' (book_id={resolved_id}) | {len(chunks)} chunks | {total_words} từ "
        f"| vectors={embedded_cnt} | {elapsed}s"
    )
    return {
        "book_id": resolved_id,
        "title": title,
        "total_chunks": len(chunks),
        "total_words": total_words,
        "embedded_chunks": embedded_cnt,
        "elapsed_sec": elapsed,
        "db_path": str(db_path),
    }


def _query_tokens(query: str) -> List[str]:
    tokens = re.findall(r"[^\W_]{2,}", query.lower(), flags=re.UNICODE)
    stop = {
        "review", "sách", "sach", "cuốn", "cuon", "tập", "tap", "phần", "phan",
        "về", "của", "và", "là", "những", "cái", "này", "trong", "cho", "với", "một",
    }
    kept = [t for t in tokens if t not in stop]
    return kept or tokens


def _fts_query_terms(query: str) -> str:
    kept = _query_tokens(query)[:12]
    return " OR ".join(f'"{t}"' for t in kept)


def _lexical_scores(query: str, rows: List[Dict[str, Any]], fts_ranks: Dict[int, float]) -> Dict[int, float]:
    """Tính điểm khớp từ khóa BM25 + bigram coverage chuẩn hóa về [0.0, 1.0]."""
    q_tokens = _query_tokens(query)
    bigrams = [f"{q_tokens[i]} {q_tokens[i + 1]}" for i in range(len(q_tokens) - 1)]
    raw_scores: Dict[int, float] = {}
    max_s = 0.0
    for row in rows:
        cid = int(row["chunk_id"])
        hay = f"{row.get('section_title', '')} {row.get('content', '')}".lower()
        uniq_hits = sum(1 for t in set(q_tokens) if re.search(rf"\b{re.escape(t)}\b", hay)) if q_tokens else 0
        bigram_hits = sum(1 for bg in bigrams if bg in hay) if bigrams else 0
        fts_bonus = fts_ranks.get(cid, 0.0)
        sc = uniq_hits * 2.0 + bigram_hits * 4.5 + fts_bonus
        raw_scores[cid] = sc
        if sc > max_s:
            max_s = sc
    if max_s <= 0:
        return {int(r["chunk_id"]): 0.0 for r in rows}
    return {cid: val / max_s for cid, val in raw_scores.items()}


def format_chunks_for_prompt(book_title: str, chunks: List[Dict[str, Any]], max_words: int = 1600) -> str:
    """Đóng gói các chunk RAG thành khối ngữ cảnh sạch đưa cho Architect/Scorer."""
    blocks: List[str] = []
    used_words = 0
    for ch in chunks:
        header = f"[Sách: {book_title} | Chunk #{ch['chunk_idx']} — {ch['section_title']}]"
        body = ch["content"].strip()
        words = body.split()
        if used_words + len(words) > max_words and blocks:
            break
        if len(words) > max_words:
            body = " ".join(words[:max_words]) + "..."
            words = body.split()
        blocks.append(f"{header}\n{body}")
        used_words += len(words)
    return "\n\n---\n\n".join(blocks)


def retrieve_chunks(
    query: str,
    book_id: Optional[str] = None,
    top_k: int = 2,
    exclude_chunk_ids: Optional[Sequence[int]] = None,
    db_path: Path = BOOK_RAG_DB_PATH,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Hybrid Search (Từ khóa SQLite FTS5 BM25 + Vector Ngữ nghĩa local multilingual-e5-small).
    Trả về `(context_str, results)` trong đó mỗi chunk đính kèm `s_rag`, `dense_score`, `lexical_score`.
    """
    if not db_path.exists():
        return "", []

    conn = _connect_db(db_path)
    try:
        resolved_book = book_id
        if not resolved_book:
            row = conn.execute("SELECT book_id FROM books ORDER BY rowid DESC LIMIT 1").fetchone()
            if not row:
                return "", []
            resolved_book = row["book_id"]

        book_row = conn.execute("SELECT title FROM books WHERE book_id = ?", (resolved_book,)).fetchone()
        book_title = book_row["title"] if book_row else resolved_book
    finally:
        conn.close()

    ensure_book_embeddings(resolved_book, db_path)

    conn = _connect_db(db_path)
    try:
        fts_ranks: Dict[int, float] = {}
        fts_q = _fts_query_terms(query)
        if fts_q:
            try:
                fts_rows = conn.execute(
                    """
                    SELECT c.chunk_id
                    FROM chunks_fts
                    JOIN chunks c ON chunks_fts.chunk_id = c.chunk_id
                    WHERE chunks_fts MATCH ? AND c.book_id = ?
                    ORDER BY bm25(chunks_fts)
                    LIMIT 20
                    """,
                    (fts_q, resolved_book),
                ).fetchall()
                for idx, fr in enumerate(fts_rows):
                    fts_ranks[int(fr["chunk_id"])] = max(0.2, 2.5 - idx * 0.12)
            except sqlite3.OperationalError:
                pass

        all_rows = conn.execute(
            """
            SELECT chunk_id, book_id, chunk_idx, section_title, content, word_count, topic_suggestion, status, embedding
            FROM chunks
            WHERE book_id = ?
            ORDER BY chunk_idx ASC
            """,
            (resolved_book,),
        ).fetchall()
    finally:
        conn.close()

    excluded = set(int(x) for x in (exclude_chunk_ids or []))
    candidates = [dict(r) for r in all_rows if int(r["chunk_id"]) not in excluded]
    if not candidates:
        candidates = [dict(r) for r in all_rows]
    if not candidates:
        return "", []

    lex_map = _lexical_scores(query, candidates, fts_ranks)

    q_vec = embed_texts([query], is_query=True)
    dense_raw: Dict[int, float] = {}
    if q_vec is not None:
        valid_vecs: List[np.ndarray] = []
        valid_cids: List[int] = []
        for c in candidates:
            blob = c.get("embedding")
            if blob:
                vec = np.frombuffer(blob, dtype=np.float32)
                if vec.shape[0] == q_vec.shape[1]:
                    valid_vecs.append(vec)
                    valid_cids.append(int(c["chunk_id"]))
        if valid_vecs:
            mat = np.vstack(valid_vecs)
            sims = (mat @ q_vec[0]).tolist()
            for cid, sim in zip(valid_cids, sims):
                dense_raw[cid] = float(sim)

    max_d = max(dense_raw.values()) if dense_raw else 1.0
    min_d = min(dense_raw.values()) if dense_raw else 0.0
    span_d = max(1e-5, max_d - min_d)

    scored_rows: List[Tuple[float, Dict[str, Any]]] = []
    for c in candidates:
        cid = int(c["chunk_id"])
        c.pop("embedding", None)
        lex_s = lex_map.get(cid, 0.0)
        if cid in dense_raw:
            d_raw = dense_raw[cid]
            d_norm = (d_raw - min_d) / span_d
            hybrid = 0.62 * d_norm + 0.38 * lex_s
            s_rag = round(min(1.0, max(0.0, 0.72 * d_raw + 0.28 * lex_s)), 4)
        else:
            d_raw = 0.0
            hybrid = lex_s
            s_rag = round(lex_s, 4)

        c["dense_score"] = round(d_raw, 4)
        c["lexical_score"] = round(lex_s, 4)
        c["s_rag"] = s_rag
        scored_rows.append((hybrid, c))

    scored_rows.sort(key=lambda x: x[0], reverse=True)
    results = [row for _, row in scored_rows[:top_k]]
    context = format_chunks_for_prompt(book_title, results)
    return context, results


def compute_groundedness_local(scenes: List[Dict[str, Any]], source_text: str) -> Tuple[float, List[int]]:
    """
    Chấm độ bám sát đoạn sách (Groundedness) hoàn toàn LOCAL (0 token API):
    So sánh từng câu `narration_vn` với các cửa sổ câu trong `source_text` bằng Vector Cosine + Khớp từ nội dung.
    Trả về `(groundedness_score [0..1], danh_sách_cảnh_yếu)`.
    """
    if not scenes or not source_text or not source_text.strip():
        return 1.0, []

    body_lines = [ln for ln in source_text.splitlines() if not ln.startswith("[Sách:") and ln.strip() != "---"]
    words = " ".join(body_lines).split()
    if len(words) < 20:
        return 1.0, []

    passages = [" ".join(words[i : i + 65]) for i in range(0, len(words), 40)]
    narrations = [str(s.get("narration_vn", "")).strip() for s in scenes]

    full_low = " ".join(words).lower()
    s_vecs = embed_texts(narrations, is_query=True)
    p_vecs = embed_texts(passages, is_query=False)

    sim_matrix = (s_vecs @ p_vecs.T) if (s_vecs is not None and p_vecs is not None) else None
    scene_scores: List[float] = []
    weak_scenes: List[int] = []

    for idx, narr in enumerate(narrations):
        tokens = [t for t in _query_tokens(narr) if len(t) >= 3]
        overlap = (sum(1 for t in set(tokens) if t in full_low) / max(1, len(set(tokens)))) if tokens else 0.5
        if sim_matrix is not None:
            raw_sem = float(sim_matrix[idx].max())
            sem_norm = min(1.0, max(0.0, (raw_sem - 0.71) / 0.17))
            sc = 0.72 * sem_norm + 0.28 * overlap
        else:
            sc = overlap
        scene_scores.append(sc)
        if sc < 0.50:
            weak_scenes.append(idx + 1)

    avg = float(sum(scene_scores) / max(1, len(scene_scores)))
    return round(min(1.0, max(0.0, avg)), 4), weak_scenes


def get_chunk_by_idx(
    book_id: str,
    chunk_idx: int,
    db_path: Path = BOOK_RAG_DB_PATH,
) -> Optional[Dict[str, Any]]:
    if not db_path.exists():
        return None
    conn = _connect_db(db_path)
    try:
        row = conn.execute(
            """
            SELECT c.*, b.title AS book_title
            FROM chunks c
            JOIN books b ON c.book_id = b.book_id
            WHERE c.book_id = ? AND c.chunk_idx = ?
            """,
            (book_id, chunk_idx),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_next_pending_chunk(book_id: Optional[str] = None, db_path: Path = BOOK_RAG_DB_PATH) -> Optional[Dict[str, Any]]:
    """Lấy chunk `pending` tiếp theo theo thứ tự từ đầu đến cuối sách để đăng hằng ngày."""
    if not db_path.exists():
        return None
    conn = _connect_db(db_path)
    try:
        if not book_id:
            b = conn.execute("SELECT book_id FROM books ORDER BY rowid DESC LIMIT 1").fetchone()
            if not b:
                return None
            book_id = b["book_id"]

        row = conn.execute(
            """
            SELECT c.*, b.title AS book_title
            FROM chunks c
            JOIN books b ON c.book_id = b.book_id
            WHERE c.book_id = ? AND c.status = 'pending'
            ORDER BY c.chunk_idx ASC
            LIMIT 1
            """,
            (book_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def mark_chunk_done(chunk_id: int, video_path: str = "", db_path: Path = BOOK_RAG_DB_PATH) -> None:
    if not db_path.exists() or not chunk_id:
        return
    conn = _connect_db(db_path)
    try:
        conn.execute(
            "UPDATE chunks SET status = 'done', last_video_path = ? WHERE chunk_id = ?",
            (video_path, chunk_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_book_chunks(book_id: Optional[str] = None, db_path: Path = BOOK_RAG_DB_PATH) -> List[Dict[str, Any]]:
    if not db_path.exists():
        return []
    conn = _connect_db(db_path)
    try:
        if not book_id:
            b = conn.execute("SELECT book_id FROM books ORDER BY rowid DESC LIMIT 1").fetchone()
            if not b:
                return []
            book_id = b["book_id"]
        rows = conn.execute(
            """
            SELECT chunk_id, book_id, chunk_idx, section_title, word_count, topic_suggestion, status, last_video_path
            FROM chunks
            WHERE book_id = ?
            ORDER BY chunk_idx ASC
            """,
            (book_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
