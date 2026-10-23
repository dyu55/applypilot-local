# Truthful material preparation

Use a source resume suitable for the role family. Preserve the original privately with a stable ID and hash. Extract the full text from PDF/DOCX using available document tools; a scanned PDF with little text requires OCR or an editable source before reliable tailoring. Do not build a resume from headings or a truncated preview.

Tailoring may reorder or clarify supported experience, shorten irrelevant detail, and use equivalent wording. Do not add tools, metrics, employers, dates, degrees, authorization, responsibilities, or outcomes absent from the evidence. Keep project/design reconstructions distinct from production experience. Do not copy desired qualifications into the resume as candidate facts.

Save a fact map per job:

```json
{
  "reviewed": true,
  "claims": [
    {
      "text": "Facilitated usability sessions for a mobile prototype.",
      "source": "state/resumes/design-resume.md:18"
    }
  ]
}
```

The agent reviews every substantive tailored claim against its source. The map and `facts_checked` are an agent attestation, not an automated proof of truth. Unsupported claims must be removed or become a pending question.

Each selected job gets editable `resume.md`, `resume.pdf` when possible, a complete saved `job_description.md`, `notes.md` with fit/gaps/questions, and `fact_map.json`. Reuse the original PDF when no tailoring is requested and it passes the same quality checks. Draft cover letters or answers only when requested or required; label them as drafts and cite their factual basis in notes.

The bundled PDF helper uses ReportLab's Latin-script font. For other scripts, use a suitable installed font/document tool and check glyphs, or report that PDF generation is incomplete. Do not transliterate names or silently drop characters. Repository instructions/templates are English; preserve the user's actual names and source facts faithfully.

Before setting materials to `ready`:

1. Compare the complete editable text with the source resume and fact map.
2. Extract PDF text and verify substantive body content, not just contact details/headings. Check that editable source words are preserved. The helper's minimum word count is a corruption check, not a content-quality score.
3. Render the PDF to images using available tools and inspect all pages for clipping, overlap, missing glyphs, whitespace, and readable layout. Record `pdf_visual_checked` only when this happened.
4. Confirm file numbering, job identity, links, source resume ID, and notes agree.

If any check cannot run, save `draft` or `missing` with the reason. A nonempty file, a successful process exit, or a fixed file-size threshold does not prove readiness. Do not squeeze or pad a resume merely to hit an arbitrary page/word target.
