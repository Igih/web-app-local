from PIL import Image

from routers import asset_quality


class CandidateCursor:
    def __init__(self, source_path):
        self.source_path = source_path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params):
        pass

    def fetchone(self):
        return {"source_path": str(self.source_path), "decode_status": "ok"}


class CandidateConnection:
    def __init__(self, source_path):
        self.source_path = source_path

    def cursor(self, **kwargs):
        return CandidateCursor(self.source_path)


def test_candidate_preview_uses_larger_image_for_zoom(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    Image.new("RGB", (2000, 1000), "blue").save(source)
    monkeypatch.setattr(asset_quality, "ASSET_QUALITY_PREVIEWS_DIR", tmp_path / "previews")
    conn = CandidateConnection(source)

    thumbnail = asset_quality._generate_candidate_preview(conn, 1, 320)
    enlarged = asset_quality._generate_candidate_preview(conn, 1, 1600)

    with Image.open(thumbnail) as image:
        assert image.size == (320, 160)
    with Image.open(enlarged) as image:
        assert image.size == (1600, 800)
