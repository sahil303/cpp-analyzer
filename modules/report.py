"""
modules/report.py
Generates a professional PDF report using reportlab.
"""

import os
from datetime import datetime
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
            "The following refactoring suggestions were generated by an AI agent (Groq / LLaMA 3) "
            "based on detected smells and metrics.",
            styles["body"]
        ),
        Spacer(1, 0.3*cm),
    ]

    for filename, suggestion in suggestions.items():
        story.append(Paragraph(f"File: {filename}", styles["subheading"]))
        # Split suggestion into paragraphs
        for para in suggestion.split("\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, styles["body_small"]))
        story.append(Spacer(1, 0.4*cm))

    return story


def _appendix_section(metrics: dict, styles: dict) -> list:
    files = metrics.get("files", {})

    story = [
        Paragraph("Appendix: File Metrics", styles["section_title"]),
        HRFlowable(width="100%", thickness=1, color=MID_BLUE),
        Spacer(1, 0.3*cm),
    ]

    table_data = [["File", "Total Lines", "Functions", "Max CCN"]]
    for filename, data in sorted(files.items()):
        table_data.append([
            Paragraph(filename, styles["table_cell_small"]),
            str(data.get("total_nloc", 0)),
            str(len(data.get("functions", []))),
            str(data.get("max_ccn", 0)),
        ])

    t = Table(table_data, colWidths=[9*cm, 3*cm, 3*cm, 2*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
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
        "table_cell_small": s("tcs",         fontSize=8,  textColor=DARK_GRAY, leading=10),
    }
