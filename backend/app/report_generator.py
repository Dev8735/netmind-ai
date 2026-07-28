import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


CONFIDENCE_COLORS = {
    "high": colors.HexColor('#22c55e'),
    "medium": colors.HexColor('#eab308'),
    "low": colors.HexColor('#ef4444'),
}


def generate_pdf_report(incident, diagnosis, alert_text, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"incident_{incident.id}_report.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=18)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], spaceBefore=14)
    normal = styles['Normal']
    evidence_style = ParagraphStyle('EvidenceStyle', parent=normal, fontSize=9, textColor=colors.HexColor('#475569'))

    elements = []
    elements.append(Paragraph("NetMind AI — Incident Diagnosis Report", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal))
    elements.append(Spacer(1, 12))

    summary_data = [
        ["Device", incident.device_type],
        ["Severity", incident.priority],
        ["Status", incident.status],
        ["Category", incident.category],
    ]
    summary_table = Table(summary_data, colWidths=[4*cm, 10*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Issue Description", heading_style))
    elements.append(Paragraph(incident.incident_description, normal))

    if diagnosis and diagnosis.get("matched"):
        confidence = diagnosis.get("confidence", "unknown")
        confidence_score = diagnosis.get("confidence_score", "")
        conf_color = CONFIDENCE_COLORS.get(confidence, colors.grey)
        conf_style = ParagraphStyle('ConfStyle', parent=normal, textColor=conf_color, fontSize=11)

        elements.append(Paragraph("Diagnosed Cause(s)", heading_style))
        elements.append(Paragraph(
            f"<b>Confidence: {confidence.upper()}</b> (score: {confidence_score})", conf_style))
        elements.append(Spacer(1, 8))

        for idx, c in enumerate(diagnosis["causes"], 1):
            elements.append(Paragraph(
                f"<b>{idx}. {c['cause']}</b> — {c['probability']}% likely", normal))

            matched_kw = c.get('matched_keywords') or []
            if matched_kw:
                match_text = f"Matched keywords: {', '.join(matched_kw)}"
            else:
                match_text = "Matched: semantic similarity (no exact keyword overlap)"
            evidence_text = f"Similarity: {c.get('similarity_score', 'n/a')} &nbsp;|&nbsp; {match_text}"
            elements.append(Paragraph(evidence_text, evidence_style))

            if c.get('business_impact'):
                elements.append(Paragraph(f"<b>Business Impact:</b> {c['business_impact']}", evidence_style))

            elements.append(Paragraph(f"Verify: {c['verification_command']}", normal))
            elements.append(Paragraph(f"Steps: {c['troubleshooting_steps']}", normal))
            elements.append(Spacer(1, 10))

        rejected = diagnosis.get("rejected_causes") or []
        if rejected:
            elements.append(Paragraph("Other Causes Considered and Ruled Out", heading_style))
            for r in rejected:
                elements.append(Paragraph(f"<b>{r['cause']}</b> — {r['reason']}", evidence_style))
                elements.append(Spacer(1, 4))
    else:
        elements.append(Paragraph("Diagnosed Cause(s)", heading_style))
        elements.append(Paragraph("No confident match found — manual review required.", normal))

    if getattr(incident, 'remediation_log', None):
        elements.append(Paragraph("Automated Remediation", heading_style))
        for line in incident.remediation_log.split("\n"):
            elements.append(Paragraph(line if line.strip() else "&nbsp;", normal))

    elements.append(Paragraph("Admin Alert", heading_style))
    for line in alert_text.split("\n"):
        elements.append(Paragraph(line if line.strip() else "&nbsp;", normal))

    doc.build(elements)
    return filepath