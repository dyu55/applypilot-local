"""Optional agent helper: render editable resume text and check text preservation."""

import argparse
import json
import re
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from batch_lib import pdf_quality, require


def render(source, output):
    import reportlab
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    source, output = Path(source), Path(output)
    require(not output.exists(), "Output already exists; choose a new staging path.")
    content = source.read_text(encoding="utf-8-sig")
    require(len(content.split()) >= 40, "Resume must contain substantive source text.")
    name = "ApplyPilotSans"
    if name not in pdfmetrics.getRegisteredFontNames():
        font = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
        pdfmetrics.registerFont(TTFont(name, str(font)))
    supported = pdfmetrics.getFont(name).face.charToGlyph
    require(
        all(char.isspace() or ord(char) in supported for char in content),
        "Unsupported glyphs: use a suitable font/document tool; do not drop source characters.",
    )
    body = ParagraphStyle("Body", fontName=name, fontSize=9.5, leading=13, spaceAfter=5)
    heading = ParagraphStyle(
        "Heading", parent=body, fontSize=12, leading=16, spaceBefore=9, keepWithNext=True
    )
    title = ParagraphStyle("Title", parent=heading, fontSize=21, leading=26)
    story = []
    for line in content.splitlines():
        clean = re.sub(r"^#{1,6}\s+", "", line).strip()
        if not clean:
            story.append(Spacer(1, 4))
            continue
        style = title if not story else heading if line.startswith("#") else body
        story.append(Paragraph(escape(clean), style))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="resume-", dir=output.parent) as temp:
        staged = Path(temp) / "resume.pdf"
        SimpleDocTemplate(
            str(staged),
            pagesize=(595.28, 841.89),
            leftMargin=43,
            rightMargin=43,
            topMargin=38,
            bottomMargin=38,
            title="Resume",
            author="",
        ).build(story)
        quality = pdf_quality(staged, content)
        # Exclusive creation preserves a concurrent writer's output as well.
        with output.open("xb") as target:
            target.write(staged.read_bytes())
    return quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(render(args.source, args.output)))
    except (OSError, ValueError, ImportError) as exc:
        parser.exit(1, f"Resume rendering failed: {exc}\n")


if __name__ == "__main__":
    main()
