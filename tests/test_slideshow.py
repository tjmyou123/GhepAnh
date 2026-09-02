"""Kiem tra trinh chieu tu dong (Ken Burns): HTML va PPTX.

    python tests/test_slideshow.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_images(folder: Path, n: int = 5):
    from PIL import Image
    for i in range(n):
        Image.new("RGB", (400 + 60 * i, 300 + 40 * i),
                  (30 * i % 255, 120, 180)).save(folder / f"anh_{i}.jpg")


def test_html():
    from smart_collage.slideshow import export_slideshow_html

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _make_images(td)
        out, warns = export_slideshow_html(
            td, title="Ky niem", subtitle="He 2026", duration=4,
            captions=True, overwrite=True)
        assert out.exists() and out.suffix == ".html"
        html = out.read_text(encoding="utf-8")
        # 1 title + 1 collage intro (>=4 anh) + 5 anh
        assert html.count('class="ph') == 7, html.count('class="ph')
        assert "kb-in" in html and "kb-out" in html and "kb-pan" in html
        assert "data:image/jpeg;base64," in html
        assert "__DUR=4" in html and "__LOOP=true" in html
        assert 'class="cap"' in html, "thieu chu thich ten file"
        assert "Ky niem" in html

        # khong intro, khong loop, khong title
        out2, _ = export_slideshow_html(
            td, intro=False, loop=False, overwrite=True,
            out=td / "khac.html")
        h2 = out2.read_text(encoding="utf-8")
        assert h2.count('class="ph') == 5
        assert "__LOOP=false" in h2
    print("OK: slideshow HTML (title + intro collage + Ken Burns + caption)")


def test_pptx():
    try:
        import pptx  # noqa: F401
    except ImportError:
        print("Bo qua: chua cai python-pptx")
        return
    from pptx import Presentation

    from smart_collage.slideshow import export_slideshow_pptx

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _make_images(td)
        out, warns = export_slideshow_pptx(
            td, title="Ky niem", duration=3, overwrite=True)
        assert out.exists() and out.suffix == ".pptx"
        prs = Presentation(str(out))
        slides = list(prs.slides)
        assert len(slides) == 7          # title + intro + 5 anh
        # slide anh phai co transition fade + timing zoom
        xml = slides[2]._element.xml
        assert "transition" in xml and "fade" in xml, "thieu chuyen canh fade"
        assert 'advTm="3000"' in xml, "thieu tu dong chuyen slide"
        assert "animScale" in xml and "spTgt" in xml, "thieu hieu ung zoom"
        # slide tieu de: co transition, khong can animScale
        xml0 = slides[0]._element.xml
        assert "transition" in xml0
        # khong bao loi chen XML
        assert not any("Khong chen duoc" in w for w in warns), warns
    print("OK: slideshow PPTX (7 slide, fade + advTm + animScale)")


def main():
    test_html()
    test_pptx()
    print("OK: tat ca kiem tra trinh chieu deu dat.")


if __name__ == "__main__":
    main()
