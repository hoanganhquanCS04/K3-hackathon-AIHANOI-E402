from flow1.atomic import atomic_chunks, build_code_map
from flow1.chunk import chunk_all
from flow1.models import Chunk


def test_moi_seg_thanh_dung_mot_chunk(sample_segs):
    assert len(atomic_chunks(sample_segs)) == len(sample_segs)


def test_chunk_id_chinh_la_ma_doan(sample_segs):
    atomics = atomic_chunks(sample_segs)
    assert [c.chunk_id for c in atomics] == [s.code for s in sample_segs]


def test_moi_atomic_chi_co_dung_mot_ma(sample_segs):
    for chunk in atomic_chunks(sample_segs):
        assert len(chunk.seg_codes) == 1


def test_atomic_giu_nguyen_van_va_co_prefix_heading(sample_segs):
    atomic = atomic_chunks(sample_segs)[0]
    assert atomic.text == sample_segs[0].text
    assert sample_segs[0].section_title in atomic.index_text


def test_atomic_giu_co_has_gap(sample_segs):
    atomics = atomic_chunks(sample_segs)
    assert [c.has_gap for c in atomics] == [s.has_gap for s in sample_segs]


def test_map_tro_moi_ma_ve_it_nhat_mot_context(sample_segs):
    code_map = build_code_map(chunk_all(sample_segs))
    for seg in sample_segs:
        assert seg.code in code_map
        assert len(code_map[seg.code]) >= 1


def test_map_bat_duoc_ma_nam_trong_hai_context_do_overlap():
    """Overlap 1 doan nghia la mot ma co the thuoc 2 chunk lien ke."""
    contexts = [
        Chunk("c0", "01", "B1", 1, "S", [("T01-001", "a"), ("T01-002", "b")], False),
        Chunk("c1", "01", "B1", 1, "S", [("T01-002", "b"), ("T01-003", "c")], False),
    ]
    code_map = build_code_map(contexts)
    assert code_map["T01-001"] == (0,)
    assert code_map["T01-002"] == (0, 1)
    assert code_map["T01-003"] == (1,)


def test_map_giu_moi_manh_cua_doan_khong_lo():
    """split_giant tach 1 ma thanh #a/#b — ca hai manh phai vao map."""
    contexts = [
        Chunk("T06-123#a", "06", "B6", 1, "S", [("T06-123", "phan dau")], False),
        Chunk("T06-123#b", "06", "B6", 1, "S", [("T06-123", "phan sau")], False),
    ]
    assert build_code_map(contexts)["T06-123"] == (0, 1)


def test_chi_so_trong_map_luon_hop_le(sample_segs):
    contexts = chunk_all(sample_segs)
    for indices in build_code_map(contexts).values():
        for i in indices:
            assert 0 <= i < len(contexts)


def test_build_store_gom_du_bon_thu(sample_segs):
    from flow1.index import build_store

    store = build_store(sample_segs)
    assert len(store.atomics) == len(sample_segs)
    assert len(store.contexts) >= 1
    assert set(store.code_to_contexts) == {s.code for s in sample_segs}
    assert store.bm25 is not None


def test_load_index_dinh_dang_cu_bao_loi_ro_rang(tmp_path):
    """Pickle cu chi co chunk gop — nap tiep se gay KeyError kho hieu o tan retrieve."""
    import pickle

    from flow1.index import IndexMissing, load

    path = tmp_path / "bm25.pkl"
    with path.open("wb") as handle:
        pickle.dump({"chunks": [], "bm25": None}, handle)

    try:
        load(path)
    except IndexMissing as exc:
        assert "python -m flow1 index" in str(exc)
    else:
        raise AssertionError("phai nem IndexMissing cho index dinh dang cu")
