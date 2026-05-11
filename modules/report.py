"""
modules/report.py
Generates a professional PDF report using reportlab.
"""

import os
import re
from datetime import datetime
import markdown
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# ─── Color Palette ────────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1a237e")
MID_BLUE    = colors.HexColor("#1565c0")
LIGHT_BLUE  = colors.HexColor("#e3f2fd")
RED         = colors.HexColor("#c62828")
ORANGE      = colors.HexColor("#e65100")
GREEN       = colors.HexColor("#2e7d32")
LIGHT_GRAY  = colors.HexColor("#f5f5f5")
DARK_GRAY   = colors.HexColor("#424242")


def generate_report(project_name: str, metrics: dict, suggestions: dict, output_dir: str) -> str:
    """Generate a PDF analysis report. Returns path to PDF."""

    report_path = os.path.join(output_dir, f"{project_name}_analysis_report.pdf")

    doc = SimpleDocTemplate(
        report_path,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = _build_styles()
    story = []

    # ── Cover Page ──
    story += _cover_page(project_name, metrics, styles)
    story.append(PageBreak())

    # ── Executive Summary ──
    story += _executive_summary(metrics, styles)
    story.append(PageBreak())

    # ── Smell Analysis ──
    story += _smell_section(metrics, styles)
    story.append(PageBreak())

    # ── Principle Violations ──
    story += _principle_violations_section(metrics, styles)

    # ── AI Suggestions ──
    if suggestions:
        story.append(PageBreak())
        story += _ai_suggestions_section(suggestions, styles)

    # ── Appendix: All Files ──
    story.append(PageBreak())
    story += _appendix_section(metrics, styles)

    doc.build(story)
    return report_path


# ─── Page Sections ────────────────────────────────────────────────────────────

def _cover_page(project_name: str, metrics: dict, styles: dict) -> list:
    summary = metrics.get("summary", {})
    date_str = datetime.now().strftime("%B %d, %Y")

    return [
        Spacer(1, 3*cm),
        Paragraph("C++ Object-Oriented Analysis Report", styles["cover_title"]),
        Spacer(1, 0.5*cm),
        HRFlowable(width="100%", thickness=2, color=MID_BLUE),
        Spacer(1, 0.5*cm),
        Paragraph(project_name, styles["cover_project"]),
        Spacer(1, 2*cm),
        _summary_box(summary, styles),
        Spacer(1, 3*cm),
        Paragraph(f"Generated: {date_str}", styles["cover_date"]),
        Paragraph("Automated OO Smell Detection &amp; Refactoring Advisor", styles["cover_date"]),
    ]


def _summary_box(summary: dict, styles: dict) -> Table:
    data = [
        ["Metric", "Value"],
        ["Total Files Analyzed",   str(summary.get("total_files", 0))],
        ["Files With Smells",      str(summary.get("files_with_smells", 0))],
        ["Total Smells Detected",  str(summary.get("total_smells", 0))],
    ]
    t = Table(data, colWidths=[9*cm, 6*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 11),
        ("BACKGROUND",  (0, 1), (-1, -1), LIGHT_BLUE),
        ("FONTSIZE",    (0, 1), (-1, -1), 10),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN",       (1, 0), (1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _executive_summary(metrics: dict, styles: dict) -> list:
    summary = metrics.get("summary", {})
    violations = metrics.get("principle_violations", {})

    total = summary.get("total_files", 0)
    with_smells = summary.get("files_with_smells", 0)
    pct = round((with_smells / total * 100) if total > 0 else 0, 1)

    story = [
        Paragraph("Executive Summary", styles["section_title"]),
        HRFlowable(width="100%", thickness=1, color=MID_BLUE),
        Spacer(1, 0.3*cm),
        Paragraph(
            f"This report presents an automated Object-Oriented quality analysis of the "
            f"<b>{total}</b> C++ source files in the project. "
            f"<b>{with_smells}</b> files ({pct}%) exhibit one or more code or design smells "
            f"that violate OO principles.",
            styles["body"]
        ),
        Spacer(1, 0.3*cm),
    ]

    if violations:
        story.append(Paragraph("OO Principles Violated:", styles["subheading"]))
        for principle, issues in violations.items():
            story.append(Paragraph(
                f"• <b>{principle}</b> — {len(issues)} occurrence(s)",
                styles["body"]
            ))

    return story


def _smell_section(metrics: dict, styles: dict) -> list:
    smells_data = metrics.get("smells", {})

    story = [
        Paragraph("Detected Code Smells", styles["section_title"]),
        HRFlowable(width="100%", thickness=1, color=MID_BLUE),
        Spacer(1, 0.3*cm),
    ]

    if not smells_data:
        story.append(Paragraph("No significant smells detected.", styles["body"]))
        return story

    # Table of smells
    table_data = [["File", "Smell Type", "Severity", "Detail"]]
    for filename, smells in smells_data.items():
        for smell in smells:
            sev = smell["severity"].upper()
            table_data.append([
                Paragraph(filename, styles["table_cell_small"]),
                Paragraph(smell["type"].replace("_", " ").title(), styles["table_cell_small"]),
                Paragraph(sev, styles["table_cell_small"]),
                Paragraph(smell["detail"][:80] + ("..." if len(smell["detail"]) > 80 else ""), styles["table_cell_small"]),
            ])

    t = Table(table_data, colWidths=[4*cm, 3.5*cm, 2*cm, 7*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    return story


def _principle_violations_section(metrics: dict, styles: dict) -> list:
    violations = metrics.get("principle_violations", {})

    story = [
        Paragraph("OO Principle Violations", styles["section_title"]),
        HRFlowable(width="100%", thickness=1, color=MID_BLUE),
        Spacer(1, 0.3*cm),
    ]

    if not violations:
        story.append(Paragraph("No principle violations detected.", styles["body"]))
        return story

    for principle, issues in violations.items():
        story.append(Paragraph(principle, styles["subheading"]))
        story.append(Paragraph(
            f"Affected files: {len(issues)}",
            styles["body"]
        ))
        for issue in issues[:5]:  # Show max 5 per principle
            story.append(Paragraph(
                f"• <b>{issue['file']}</b>: {issue['smell'].replace('_', ' ').title()} — {issue['detail'][:60]}",
                styles["body_small"]
            ))
        if len(issues) > 5:
            story.append(Paragraph(f"  ... and {len(issues)-5} more.", styles["body_small"]))
        story.append(Spacer(1, 0.2*cm))

    return story


def _ai_suggestions_section(suggestions: dict, styles: dict) -> list:
    story = [
        Paragraph("AI Refactoring Suggestions", styles["section_title"]),
        HRFlowable(width="100%", thickness=1, color=MID_BLUE),
        Spacer(1, 0.3*cm),
        Paragraph(
            "The following refactoring suggestions were generated by an AI agent (Groq / Gemini) "
            "based on detected smells and metrics.",
            styles["body"]
        ),
        Spacer(1, 0.3*cm),
    ]

    for filename, suggestion in suggestions.items():
        story.append(Paragraph(f"File: {filename}", styles["subheading"]))
        story.extend(_markdown_to_flowables(suggestion, styles))
        story.append(Spacer(1, 0.4*cm))

    return story


def _md_inline(text: str) -> str:
    """Convert inline markdown (**bold**, *italic*, `code`) to ReportLab XML tags."""
    # Escape existing XML special chars first (except & already escaped)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold+italic ***text***
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Italic *text* (not bullet markers)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    # Inline code `text`
    text = re.sub(r'`([^`]+)`', r'<font face="Courier">\1</font>', text)
    return text


def _markdown_to_flowables(markdown_text: str, styles: dict) -> list:
    """
    Robustly convert AI markdown response to ReportLab flowables.
    Handles: ### headings, bullet lists, numbered lists,
             fenced code blocks, inline bold/italic/code, paragraphs.
    """
    flowables = []
    lines     = markdown_text.splitlines()
    i         = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ── Skip blank lines
        if not stripped:
            i += 1
            continue

        # ── Horizontal rule
        if stripped in ("---", "***", "___"):
            flowables.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY))
            flowables.append(Spacer(1, 0.1 * cm))
            i += 1
            continue

        # ── Fenced code block  ```...```
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_text = "\n".join(code_lines)
            # Escape XML in code
            code_text = (code_text
                         .replace("&", "&amp;")
                         .replace("<", "&lt;")
                         .replace(">", "&gt;"))
            flowables.append(
                Paragraph(
                    f'<font face="Courier" size="7">{code_text}</font>',
                    styles["code"]
                )
            )
            flowables.append(Spacer(1, 0.15 * cm))
            continue

        # ── Headings  # / ## / ###
        heading_match = re.match(r'^(#{1,6})\s+(.*)', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text  = _md_inline(heading_match.group(2).strip())
            style = styles["subheading"] if level >= 2 else styles["section_title"]
            flowables.append(Spacer(1, 0.15 * cm))
            flowables.append(Paragraph(text, style))
            flowables.append(Spacer(1, 0.05 * cm))
            i += 1
            continue

        # ── Bullet list  - / * / +
        if re.match(r'^[\*\-\+]\s+', stripped):
            while i < len(lines) and re.match(r'^[\*\-\+]\s+', lines[i].strip()):
                item = re.sub(r'^[\*\-\+]\s+', '', lines[i].strip())
                flowables.append(
                    Paragraph(f"&bull;&nbsp;&nbsp;{_md_inline(item)}", styles["bullet"])
                )
                i += 1
            flowables.append(Spacer(1, 0.05 * cm))
            continue

        # ── Numbered list  1. / 2. etc.
        if re.match(r'^\d+\.\s+', stripped):
            num = 1
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i].strip()):
                item = re.sub(r'^\d+\.\s+', '', lines[i].strip())
                flowables.append(
                    Paragraph(f"<b>{num}.</b>&nbsp;&nbsp;{_md_inline(item)}", styles["numbered"])
                )
                num += 1
                i += 1
            flowables.append(Spacer(1, 0.05 * cm))
            continue

        # ── Regular paragraph (collect consecutive non-special lines)
        para_lines = []
        while i < len(lines):
            l = lines[i].strip()
            if (not l or
                l.startswith("#") or
                l.startswith("```") or
                re.match(r'^[\*\-\+]\s+', l) or
                re.match(r'^\d+\.\s+', l) or
                l in ("---", "***", "___")):
                break
            para_lines.append(l)
            i += 1

        text = " ".join(para_lines).strip()
        if text:
            flowables.append(Paragraph(_md_inline(text), styles["body_small"]))
            flowables.append(Spacer(1, 0.08 * cm))

    return flowables


def _appendix_section(metrics: dict, styles: dict) -> list:
    files      = metrics.get("files", {})
    ck_metrics = metrics.get("ck_metrics", {})
    avgs       = metrics.get("summary", {}).get("ck_averages", {})

    story = [
        Paragraph("Appendix A: Full CK Metrics per File", styles["section_title"]),
        HRFlowable(width="100%", thickness=1, color=MID_BLUE),
        Spacer(1, 0.2*cm),
        Paragraph(
            "The Chidamber &amp; Kemerer (CK) metric suite provides quantitative indicators "
            "of object-oriented design quality. Values above threshold indicate design issues "
            "mapped to SOLID principle violations.",
            styles["body"]
        ),
        Spacer(1, 0.2*cm),
    ]

    # CK Averages summary row
    avg_table = [
        ["Metric", "Avg Value", "Description", "Threshold (High)", "SOLID Principle"],
        ["WMC",  str(avgs.get("avg_WMC", 0)),  "Weighted Methods per Class",  "> 20",   "S — SRP"],
        ["CBO",  str(avgs.get("avg_CBO", 0)),  "Coupling Between Objects",    "> 10",   "D — DIP, O — OCP"],
        ["RFC",  str(avgs.get("avg_RFC", 0)),  "Response for a Class",        "> 50",   "S — SRP, D — DIP"],
        ["LCOM", str(avgs.get("avg_LCOM", 0)), "Lack of Cohesion in Methods", "> 0.7",  "S — SRP"],
        ["DIT",  str(avgs.get("avg_DIT", 0)),  "Depth of Inheritance Tree",   "> 3",    "L — LSP"],
        ["NOC",  str(avgs.get("avg_NOC", 0)),  "Number of Children",          "> 10",   "L — LSP, O — OCP"],
        ["CCN",  str(avgs.get("avg_CCN_max", 0)), "Max Cyclomatic Complexity","> 10",   "S — SRP, O — OCP"],
        ["NLOC", str(avgs.get("avg_NLOC", 0)), "Avg Lines of Code per file",  "> 500",  "S — SRP"],
    ]
    at = Table(avg_table, colWidths=[1.5*cm, 1.8*cm, 4*cm, 3*cm, 4.2*cm])
    at.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("ALIGN",         (1, 0), (1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(at)
    story.append(Spacer(1, 0.4*cm))

    # Per-file CK metrics table
    story.append(Paragraph("Per-File CK Metrics", styles["subheading"]))
    table_data = [["File", "WMC", "CBO", "RFC", "LCOM", "DIT", "NOC", "CCN", "NLOC"]]
    for filename in sorted(files.keys()):
        ck = ck_metrics.get(filename, {})
        table_data.append([
            Paragraph(filename, styles["table_cell_small"]),
            str(ck.get("WMC", 0)),
            str(ck.get("CBO", 0)),
            str(ck.get("RFC", 0)),
            str(round(ck.get("LCOM", 0.0), 2)),
            str(ck.get("DIT", 0)),
            str(ck.get("NOC", 0)),
            str(ck.get("CCN_max", 0)),
            str(ck.get("NLOC_total", 0)),
        ])

    col_w = [5*cm, 1.2*cm, 1.2*cm, 1.2*cm, 1.4*cm, 1.2*cm, 1.2*cm, 1.2*cm, 1.4*cm]
    t = Table(table_data, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("FONTSIZE",      (0, 1), (-1, -1), 7),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    # SOLID violation summary
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("Appendix B: SOLID Principle Violation Summary", styles["section_title"]))
    story.append(HRFlowable(width="100%", thickness=1, color=MID_BLUE))
    story.append(Spacer(1, 0.2*cm))

    solid_table = [["SOLID Principle", "Occurrences", "Most Violated By"]]
    violations = metrics.get("principle_violations", {})
    for principle, issues in sorted(violations.items(), key=lambda x: -len(x[1])):
        top_smell = max(set(i["smell"] for i in issues), key=lambda s: sum(1 for i in issues if i["smell"] == s))
        solid_table.append([
            Paragraph(principle, styles["table_cell_small"]),
            str(len(issues)),
            top_smell.replace("_", " ").title(),
        ])

    if len(solid_table) > 1:
        st = Table(solid_table, colWidths=[8*cm, 2.5*cm, 4*cm])
        st.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.grey),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("ALIGN",         (1, 0), (1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(st)
    else:
        story.append(Paragraph("No SOLID violations detected.", styles["body"]))

    return story


# ─── Styles ───────────────────────────────────────────────────────────────────

def _build_styles() -> dict:
    base = getSampleStyleSheet()

    def s(name, **kwargs):
        return ParagraphStyle(name, parent=base["Normal"], **kwargs)

    return {
        "cover_title":    s("cover_title",   fontSize=22, textColor=DARK_BLUE,
                             alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=10),
        "cover_project":  s("cover_project", fontSize=16, textColor=MID_BLUE,
                             alignment=TA_CENTER, spaceAfter=6),
        "cover_date":     s("cover_date",    fontSize=10, textColor=DARK_GRAY,
                             alignment=TA_CENTER, spaceAfter=4),
        "section_title":  s("section_title", fontSize=14, textColor=DARK_BLUE,
                             fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4),
        "subheading":     s("subheading",    fontSize=11, textColor=MID_BLUE,
                             fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3),
        "body":           s("body",          fontSize=10, textColor=DARK_GRAY,
                             spaceAfter=4, leading=14),
        "body_small":     s("body_small",    fontSize=9,  textColor=DARK_GRAY,
                             spaceAfter=3, leading=12),
        "code":           s("code",          fontName="Courier", fontSize=8, textColor=DARK_GRAY,
                             backColor=LIGHT_GRAY, leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=4, leading=12),
        "table_cell_small": s("tcs",         fontSize=8,  textColor=DARK_GRAY, leading=10),
        "bullet":           s("bullet",       fontSize=9,  textColor=DARK_GRAY,
                             leftIndent=14, spaceAfter=3, leading=13),
        "numbered":         s("numbered",     fontSize=9,  textColor=DARK_GRAY,
                             leftIndent=14, spaceAfter=3, leading=13),
    }
