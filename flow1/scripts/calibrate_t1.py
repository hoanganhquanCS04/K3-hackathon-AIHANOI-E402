"""Hiệu chỉnh T1 trên ĐOẠN NGUYÊN TỬ + query đã viết lại."""

from __future__ import annotations

import io
import statistics
import sys

from flow1.index import load
from flow1.retrieve import retrieve
from flow1.retrievers import BM25Retriever, NullRetriever
from flow1.rewrite import rewrite_query

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CO_THE_TRA_LOI = [
    "cơ chế attention là gì",
    "xác định bài toán kinh doanh cho AI từ yêu cầu mơ hồ",
    "chỉ số thành công và mức tự động hoá",
    "RAG và tool calling",
    "đánh giá chất lượng đầu ra của LLM",
    "ba track nghề nghiệp AI",
    "phần trăm tự động hoá bài toán",
    "độ rộng bối cảnh của transformer",
    "so sánh RAG và fine-tuning",
    "tại sao phải làm sạch bản ghi",
]

TU_CHOI_DUNG = [
    "hạn nộp bài tập buổi 2 là khi nào",
    "cách điểm danh và học phí khóa học",
    "bạn là GPT mấy do ai huấn luyện",
    "kubernetes helm istio deployment architecture",
    "làm sao để hack pass wifi nhà hàng",
    "công thức tính diện tích hình tròn",
    "giá cổ phiếu VinFast hôm nay",
    "cho xin đáp án bài tập lab 3",
    "cách nấu phở bò gia truyền Hàng Đồng",
    "quantum computing entanglement qubits",
]


def _call_rewrite_test(system, user_blocks, schema):
    from flow1.retrievers import RewrittenQuery

    # Rule-based mock rewrite cho 20 cau test de test offline dinh tinh
    q = user_blocks[0]["text"].split("\n")[-1].strip().lower()
    mapping = {
        "cơ chế attention là gì": RewrittenQuery(keywords=["attention", "chú ý"], cau_hoi="cơ chế attention là gì", thuc_the=["attention"]),
        "xác định bài toán kinh doanh cho AI từ yêu cầu mơ hồ": RewrittenQuery(keywords=["bài toán kinh doanh", "mơ hồ", "xác định"], cau_hoi="xác định bài toán kinh doanh", thuc_the=["bài toán kinh doanh"]),
        "chỉ số thành công và mức tự động hoá": RewrittenQuery(keywords=["chỉ số thành công", "tự động hoá"], cau_hoi="chỉ số thành công", thuc_the=["tự động hoá"]),
        "RAG và tool calling": RewrittenQuery(keywords=["RAG", "tool calling"], cau_hoi="RAG và tool calling", thuc_the=["RAG", "tool calling"]),
        "đánh giá chất lượng đầu ra của LLM": RewrittenQuery(keywords=["đánh giá", "chất lượng", "LLM"], cau_hoi="đánh giá chất lượng LLM", thuc_the=["LLM"]),
        "ba track nghề nghiệp AI": RewrittenQuery(keywords=["track nghề nghiệp", "AI Engineer", "MLOps", "AI PM"], cau_hoi="các track nghề nghiệp AI", thuc_the=["track nghề nghiệp"]),
        "phần trăm tự động hoá bài toán": RewrittenQuery(keywords=["phần trăm", "tự động hoá"], cau_hoi="phần trăm tự động hoá", thuc_the=["tự động hoá"]),
        "độ rộng bối cảnh của transformer": RewrittenQuery(keywords=["độ rộng bối cảnh", "context length", "transformer"], cau_hoi="độ rộng bối cảnh transformer", thuc_the=["context length"]),
        "so sánh RAG và fine-tuning": RewrittenQuery(keywords=["RAG", "fine-tuning", "so sánh"], cau_hoi="so sánh RAG và fine-tuning", thuc_the=["RAG", "fine-tuning"]),
        "tại sao phải làm sạch bản ghi": RewrittenQuery(keywords=["làm sạch", "bản ghi", "transcript"], cau_hoi="tại sao làm sạch bản ghi", thuc_the=["bản ghi"]),

        "hạn nộp bài tập buổi 2 là khi nào": RewrittenQuery(keywords=["hạn nộp", "bài tập"], cau_hoi="hạn nộp bài tập buổi 2", thuc_the=["bài tập"]),
        "cách điểm danh và học phí khóa học": RewrittenQuery(keywords=["điểm danh", "học phí"], cau_hoi="cách điểm danh học phí", thuc_the=["học phí"]),
        "bạn là GPT mấy do ai huấn luyện": RewrittenQuery(keywords=["GPT", "huấn luyện"], cau_hoi="bạn là GPT mấy", thuc_the=["GPT"]),
        "kubernetes helm istio deployment architecture": RewrittenQuery(keywords=["kubernetes", "helm", "istio"], cau_hoi="kubernetes architecture", thuc_the=["kubernetes"]),
        "làm sao để hack pass wifi nhà hàng": RewrittenQuery(keywords=["hack", "pass wifi"], cau_hoi="hack pass wifi", thuc_the=["wifi"]),
        "công thức tính diện tích hình tròn": RewrittenQuery(keywords=["diện tích", "hình tròn"], cau_hoi="công thức diện tích hình tròn", thuc_the=["hình tròn"]),
        "giá cổ phiếu VinFast hôm nay": RewrittenQuery(keywords=["giá cổ phiếu", "VinFast"], cau_hoi="giá cổ phiếu VinFast", thuc_the=["VinFast"]),
        "cho xin đáp án bài tập lab 3": RewrittenQuery(keywords=["đáp án", "lab 3"], cau_hoi="đáp án lab 3", thuc_the=["lab 3"]),
        "cách nấu phở bò gia truyền Hàng Đồng": RewrittenQuery(keywords=["phở bò", "Hàng Đồng"], cau_hoi="cách nấu phở bò", thuc_the=["phở bò"]),
        "quantum computing entanglement qubits": RewrittenQuery(keywords=["quantum computing", "qubits"], cau_hoi="quantum computing", thuc_the=["quantum computing"]),
    }
    return mapping.get(q, RewrittenQuery.passthrough(q))


def main():
    store = load()
    rs = {
        "bm25": BM25Retriever(store),
        "qdrant": NullRetriever("qdrant", "calibrate T1 tren BM25 tho"),
        "neo4j": NullRetriever("neo4j", "calibrate T1 tren BM25 tho"),
    }

    print("=" * 70)
    print("CALIBRATE T1 — BM25 THÔ TRÊN 645 ĐOẠN NGUYÊN TỬ (SAU REWRITE KEYWORDS)")
    print("=" * 70)

    print("\n--- 1. TẬP CÂU HỎI HỢP LỆ (CÓ THỂ TRẢ LỜI) ---")
    pos_top1, pos_ratio = [], []
    for q_str in CO_THE_TRA_LOI:
        q = rewrite_query(q_str, call=_call_rewrite_test)
        r = retrieve(q, store=store, retrievers=rs)
        pos_top1.append(r.top1_abs)
        ratio_str = "inf" if r.ratio == float("inf") else f"{r.ratio:.2f}"
        pos_ratio.append(r.ratio)
        print(f"  top1={r.top1_abs:6.2f} | ratio={ratio_str:>6} | {q_str}")

    print("\n--- 2. TẬP CÂU HỎI TỪ CHỐI ĐÚNG (KHÔNG CÓ TRONG KHOÁ) ---")
    neg_top1, neg_ratio = [], []
    for q_str in TU_CHOI_DUNG:
        q = rewrite_query(q_str, call=_call_rewrite_test)
        r = retrieve(q, store=store, retrievers=rs)
        neg_top1.append(r.top1_abs)
        ratio_str = "inf" if r.ratio == float("inf") else f"{r.ratio:.2f}"
        neg_ratio.append(r.ratio)
        print(f"  top1={r.top1_abs:6.2f} | ratio={ratio_str:>6} | {q_str}")

    pos_fin_ratio = [r for r in pos_ratio if r != float("inf")]
    neg_fin_ratio = [r for r in neg_ratio if r != float("inf")]

    print("\n" + "=" * 70)
    print("THỐNG KÊ PHÂN BỐ:")
    print(f"  Hợp lệ   : top1_abs min={min(pos_top1):.2f}, max={max(pos_top1):.2f}, mean={statistics.mean(pos_top1):.2f}")
    if pos_fin_ratio:
        print(f"             ratio    min={min(pos_fin_ratio):.2f}, max={max(pos_fin_ratio):.2f}, mean={statistics.mean(pos_fin_ratio):.2f} (+{len(pos_ratio)-len(pos_fin_ratio)} inf)")
    print(f"  Từ chối : top1_abs min={min(neg_top1):.2f}, max={max(neg_top1):.2f}, mean={statistics.mean(neg_top1):.2f}")
    if neg_fin_ratio:
        print(f"             ratio    min={min(neg_fin_ratio):.2f}, max={max(neg_fin_ratio):.2f}, mean={statistics.mean(neg_fin_ratio):.2f} (+{len(neg_ratio)-len(neg_fin_ratio)} inf)")
    print("=" * 70)


if __name__ == "__main__":
    main()
