import io
import re
import html
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        if self._pageNumber > 1:
            self.drawString(40, letter[1] - 30, "FairScan — Dataset Fairness & Bias Check Report")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(40, letter[1] - 35, letter[0] - 40, letter[1] - 35)

        footer_y = 30
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, footer_y + 12, letter[0] - 40, footer_y + 12)
        
        self.drawString(40, footer_y, "FairScan Plain-English Audit • Pre-Training Fairness Check")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 40, footer_y, page_str)
        self.restoreState()


def generate_pdf_audit_report(
    dataset_meta: Dict[str, Any],
    audit_results: Dict[str, Any],
    findings: Dict[str, Any],
    explanation_text: str = "",
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=45,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()

    C_PRIMARY = colors.HexColor("#18181b")  # Clean dark zinc
    C_ACCENT = colors.HexColor("#ca8a04")   # Warm gold/yellow
    C_TEXT = colors.HexColor("#27272a")     # Slate 800
    C_MUTED = colors.HexColor("#71717a")    # Slate 500
    C_BORDER = colors.HexColor("#e4e4e7")   # Zinc 200
    C_SURFACE = colors.HexColor("#fafafa")  # Zinc 50
    C_PASS = colors.HexColor("#15803d")     # Emerald green
    C_WARN = colors.HexColor("#b45309")     # Amber warning
    C_FAIL = colors.HexColor("#b91c1c")     # Red alert

    title_style = ParagraphStyle(
        "DocTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=C_PRIMARY,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=C_MUTED,
    )
    section_title = ParagraphStyle(
        "SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=C_PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.5,
        textColor=C_TEXT,
    )
    code_style = ParagraphStyle(
        "MonoCode",
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#3f3f46"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=C_TEXT,
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=C_TEXT,
    )

    story = []

    # Header
    header_table_data = [
        [
            Paragraph("<b>FAIRSCAN DATASET AUDIT</b><br/><font size='7' color='#71717a'>PLAIN-ENGLISH FAIRNESS CHECK</font>", subtitle_style),
            Paragraph(f"<b>Audit Date:</b> {datetime.now().strftime('%B %d, %Y')}<br/><b>Status:</b> Completed Automatically", subtitle_style),
        ]
    ]
    t_top = Table(header_table_data, colWidths=[4.0 * inch, 3.2 * inch])
    t_top.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(t_top)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Dataset Fairness & Bias Audit Report", title_style))
    story.append(Paragraph("A clear, easy-to-read check to see if different demographic groups get treated fairly in this dataset.", subtitle_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=C_PRIMARY, spaceBefore=4, spaceAfter=10))

    # Metadata Grid
    target_name = audit_results.get("target_col", "N/A")
    favorable_val = audit_results.get("favorable_outcome", "N/A")
    total_records = dataset_meta.get("total_rows", 0)
    adv_count = findings.get("adverse_impact_count", 0)

    meta_grid = [
        [
            Paragraph("<b>File Name</b>", body_style),
            Paragraph(str(dataset_meta.get("filename", "N/A")), code_style),
            Paragraph("<b>Total Rows</b>", body_style),
            Paragraph(f"{total_records:,} people / records", table_cell_bold),
        ],
        [
            Paragraph("<b>Data Fingerprint (ID)</b>", body_style),
            Paragraph(str(dataset_meta.get("fingerprint", "N/A"))[:32] + "...", code_style),
            Paragraph("<b>Total Columns</b>", body_style),
            Paragraph(f"{dataset_meta.get('total_columns', 0)} columns", body_style),
        ],
        [
            Paragraph("<b>What was Measured</b>", body_style),
            Paragraph(f"<b>{target_name}</b> (Positive Result = '{favorable_val}')", body_style),
            Paragraph("<b>Unfair Gaps Found</b>", body_style),
            Paragraph(
                f"<font color='{C_FAIL.hexval()}'><b>{adv_count} group(s) have unfair gaps</b></font>" if adv_count > 0 else f"<font color='{C_PASS.hexval()}'><b>0 (Everything balanced)</b></font>",
                body_style
            ),
        ]
    ]
    meta_table = Table(meta_grid, colWidths=[1.6 * inch, 2.5 * inch, 1.5 * inch, 1.6 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_SURFACE),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # SECTION 1: SIMPLE FINDINGS
    story.append(Paragraph("1. Summary of What Was Found", section_title))
    findings_list = findings.get("findings", [])
    if not findings_list:
        no_findings_box = Table(
            [[Paragraph("<b>Everything Looks Balanced:</b> No large fairness gaps were detected across the groups in this dataset. Success rates stay within the recommended 80% guideline.", body_style)]],
            colWidths=[7.2 * inch]
        )
        no_findings_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#bbf7d0")),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(no_findings_box)
    else:
        for f in findings_list[:6]:
            ftype = f.get("type")
            bg_color = colors.HexColor("#fef2f2") if ftype == "critical" else (colors.HexColor("#fffbeb") if ftype == "warning" else C_SURFACE)
            border_color = colors.HexColor("#fecaca") if ftype == "critical" else (colors.HexColor("#fef08a") if ftype == "warning" else C_BORDER)
            title_color = C_FAIL if ftype == "critical" else (C_WARN if ftype == "warning" else C_PASS)

            f_box = [
                [
                    Paragraph(f"<font color='{title_color.hexval()}'><b>{f.get('title', '')}</b></font>", body_style),
                ],
                [
                    Paragraph(f.get("summary", ""), body_style),
                ],
                [
                    Paragraph(f"<i>What this means: {f.get('detail', '')}</i>", subtitle_style),
                ]
            ]
            f_table = Table(f_box, colWidths=[7.2 * inch])
            f_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                ('BOX', (0, 0), (-1, -1), 0.5, border_color),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(f_table)
            story.append(Spacer(1, 3))

    story.append(Spacer(1, 8))

    # SECTION 2: PLAIN ENGLISH GROUP SUCCESS RATES
    story.append(Paragraph("2. Group Comparison: Who Got What?", section_title))
    attr_audits = audit_results.get("attribute_audits", {})

    for col, audit in attr_audits.items():
        if audit.get("status") != "completed":
            continue

        ref_group = audit.get("reference_group")
        story.append(Paragraph(f"<b>Category: {col}</b> &nbsp;•&nbsp; <b>Comparison Benchmark:</b> <i>{ref_group}</i>", body_style))
        story.append(Spacer(1, 3))

        headers = ["Group", "Total People", "Positive Decisions", "Success Rate", "Difference from Benchmark", "Ratio to Benchmark", "Verdict"]
        table_rows = [[Paragraph(f"<b>{h}</b>", ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=colors.white)) for h in headers]]

        group_stats = audit.get("group_stats", {})
        spd_comps = audit.get("statistical_parity", {}).get("comparisons", {})
        di_comps = audit.get("disparate_impact", {}).get("comparisons", {})

        for g, s in group_stats.items():
            spd_val = spd_comps.get(g, {}).get("difference")
            spd_str = f"{spd_val:+.1%}" if spd_val is not None else "0.0%"
            di_val = di_comps.get(g, {}).get("ratio")
            zero_den = di_comps.get(g, {}).get("zero_denominator")
            di_str = f"{di_val:.2f}x" if di_val is not None else ("No ratio (0)" if zero_den else "1.00x")

            is_ref = (g == ref_group)
            label = f"{g} (Benchmark)" if is_ref else g

            if is_ref:
                verdict = "<font color='#4f46e5'><b>Benchmark</b></font>"
            elif di_comps.get(g, {}).get("violates_80_rule"):
                verdict = f"<font color='{C_FAIL.hexval()}'><b>Unfair Gap</b></font>"
            elif spd_val and spd_val < -0.10:
                verdict = f"<font color='{C_WARN.hexval()}'><b>Watchlist</b></font>"
            else:
                verdict = f"<font color='{C_PASS.hexval()}'><b>Fair</b></font>"

            table_rows.append([
                Paragraph(label, table_cell_bold if is_ref else table_cell),
                Paragraph(str(s["total_count"]), table_cell),
                Paragraph(str(s["favorable_count"]), table_cell),
                Paragraph(f"<b>{s['selection_rate_pct']}%</b>", table_cell),
                Paragraph(spd_str, table_cell),
                Paragraph(di_str, table_cell),
                Paragraph(verdict, table_cell),
            ])

        m_table = Table(
            table_rows,
            colWidths=[1.5 * inch, 0.9 * inch, 1.0 * inch, 0.9 * inch, 1.1 * inch, 1.0 * inch, 0.8 * inch]
        )
        m_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C_SURFACE]),
        ]))
        story.append(m_table)
        story.append(Spacer(1, 8))

    # SECTION 3: PLAIN-ENGLISH NARRATIVE
    if explanation_text:
        escaped_text = html.escape(explanation_text)
        escaped_text = re.sub(r'###\s*(.*?)(?:\n|$)', r'<b>\1</b><br/>', escaped_text)
        escaped_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', escaped_text)
        escaped_text = escaped_text.replace('\n', '<br/>')

        expl_table = Table(
            [[Paragraph(escaped_text, body_style)]],
            colWidths=[7.2 * inch]
        )
        expl_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), C_SURFACE),
            ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(KeepTogether([
            Paragraph("3. In-Depth Explanation", section_title),
            expl_table,
        ]))
        story.append(Spacer(1, 8))

    # SECTION 4: NEXT STEPS
    story.append(Paragraph("4. Recommended Next Steps", section_title))
    for idx, rec in enumerate(findings.get("investigation_recommendations", []), 1):
        rec_box = Table(
            [[
                Paragraph(f"<b>{idx}.</b>", ParagraphStyle("Num", fontName="Helvetica-Bold", fontSize=9, textColor=C_PRIMARY)),
                Paragraph(rec, body_style),
            ]],
            colWidths=[0.3 * inch, 6.9 * inch]
        )
        rec_box.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(rec_box)
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 8))

    # Disclaimer
    disclaimer_text = (
        "<b>Important Note:</b> This report is an analytical helper tool to assist in discovering data imbalances. "
        "Seeing a gap does not automatically mean illegal discrimination, nor does equal percentages guarantee complete legal immunity. "
        "Always review the context of your decisions with relevant human experts and legal counsel."
    )
    disclaimer_table = Table([[Paragraph(disclaimer_text, subtitle_style)]], colWidths=[7.2 * inch])
    disclaimer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f4f4f5")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e4e4e7")),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(disclaimer_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
