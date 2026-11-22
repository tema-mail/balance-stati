import importlib
import os
import sys


def zagruzit(tmp_path, monkeypatch):
    token = tmp_path / "token"
    token.write_text("test")
    monkeypatch.setenv("BALANCE_TILDA_TOKEN", str(token))
    sys.modules.pop("publish_due", None)
    return importlib.import_module("publish_due")


def test_status_v_zavode_blokiruet_povtornyy_vyzov_tilda(tmp_path, monkeypatch):
    p = zagruzit(tmp_path, monkeypatch)
    (tmp_path / "tilda").mkdir()
    (tmp_path / "tilda/raspisanie.tsv").write_text("statya\tuid-1\t2000-01-01 00:00\n")
    p.ROOT = tmp_path
    p.LOG = tmp_path / "tilda/opublikovano.log"
    monkeypatch.setattr(p, "uids", lambda: {"statya": "uid-1"})
    monkeypatch.setattr(p, "uzhe_vylozhena_v_zavode", lambda slug, uid: True)
    monkeypatch.setattr(p, "proverit_live", lambda slug: "https://balance-fit.ru/blog/statya")
    otmetki = []
    monkeypatch.setattr(p, "otmetit_v_zavode", lambda *a: otmetki.append(a))
    monkeypatch.setattr(p, "call", lambda *a: (_ for _ in ()).throw(AssertionError("Tilda вызвана повторно")))
    monkeypatch.setattr(sys, "argv", ["publish_due.py"])
    p.main()
    assert p.LOG.read_text() == "statya\n"
    assert otmetki == [("statya", "uid-1", "https://balance-fit.ru/blog/statya")]


def test_bez_statusa_v_zavode_publikaciya_razreshena(tmp_path, monkeypatch):
    p = zagruzit(tmp_path, monkeypatch)
    monkeypatch.setattr(p, "statya_v_zavode", lambda slug: {"tilda_uid": "uid-1", "status": "gotovo"})
    assert not p.uzhe_vylozhena_v_zavode("statya", "uid-1")
