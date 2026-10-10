from concurrent.futures import ThreadPoolExecutor

from mcm_solarcheck.infrastructure.sqlite_transfer_fences import SQLiteTransferFences


def test_generation_survives_reopen_and_invalidates_older_worker(tmp_path):
    db = tmp_path / "fences.db"
    first = SQLiteTransferFences(db)
    old = first.advance("transfer-a")
    restarted = SQLiteTransferFences(db)
    new = restarted.advance("transfer-a")
    assert (old, new) == (1, 2)
    assert not first.is_current("transfer-a", old)
    assert restarted.is_current("transfer-a", new)
    assert not restarted.is_current("transfer-b", new)


def test_concurrent_generations_are_unique_and_monotonic(tmp_path):
    db = tmp_path / "fences.db"
    fences = SQLiteTransferFences(db)
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(lambda _: fences.advance("transfer-a"), range(12)))
    assert sorted(values) == list(range(1, 13))
    assert fences.is_current("transfer-a", 12)
