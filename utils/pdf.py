
from typing import List
from typing_extensions import Literal
from models.report import Report
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle, StyleSheet1
from reportlab.lib import colors
import io
from datetime import datetime

from scanner.accessibility.ace import AxeNode, AxeResult
from reportlab.graphics import renderPDF
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

def getStyleSheet() -> StyleSheet1:
    stylesheet = StyleSheet1()

    # Rutgers Scarlet color
    rutgers_red = colors.HexColor("#cc0033")
    rutgers_gray = colors.HexColor("#5f6062")
    rutgers_dark = colors.HexColor("#222222")
    rutgers_light_gray = colors.HexColor("#f5f5f5")

    # Title: Large, bold, Rutgers red, centered
    stylesheet.add(ParagraphStyle(
        name='Title',
        fontSize=28,
        leading=34,
        spaceAfter=20,
        alignment=1,  # Center
        fontName='Helvetica-Bold',
        textColor=rutgers_red,
    ))

    # Heading1: Bold, left, Rutgers red
    stylesheet.add(ParagraphStyle(
        name='Heading1',
        fontSize=20,
        leading=26,
        spaceAfter=14,
        fontName='Helvetica-Bold',
        textColor=rutgers_red,
    ))

    # Heading2: Bold, left, dark gray
    stylesheet.add(ParagraphStyle(
        name='Heading2',
        fontSize=15,
        leading=21,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        textColor=rutgers_dark,
    ))

    # Heading3: Semi-bold, left, Rutgers gray
    stylesheet.add(ParagraphStyle(
        name='Heading3',
        fontSize=12,
        leading=16,
        spaceAfter=8,
        fontName='Helvetica-BoldOblique',
        textColor=rutgers_gray,
    ))

    # Normal: Standard body text, dark gray
    stylesheet.add(ParagraphStyle(
        name='Normal',
        fontSize=10,
        leading=12,
        spaceAfter=6,
        fontName='Helvetica',
        textColor=rutgers_dark,
    ))

    # Small: For footnotes or less important info, Rutgers gray
    stylesheet.add(ParagraphStyle(
        name='Small',
        fontSize=9,
        leading=11,
        spaceAfter=4,
        fontName='Helvetica',
        textColor=rutgers_gray,
    ))

    # NormalSmall: Slightly smaller than normal, gray
    stylesheet.add(ParagraphStyle(
        name='NormalSmall',
        fontSize=9,
        leading=11,
        spaceAfter=5,
        fontName='Helvetica',
        textColor=colors.HexColor("#757575"),
    ))

    # NormalXSmall: For code, node details, etc., monospaced, dark gray
    stylesheet.add(ParagraphStyle(
        name='NormalXSmall',
        fontSize=8,
        leading=10,
        spaceAfter=4,
        fontName='Courier',
        textColor=rutgers_dark,
    ))

    # Caption: Centered, gray, for images/tables
    stylesheet.add(ParagraphStyle(
        name='Caption',
        fontSize=9,
        leading=11,
        spaceAfter=4,
        alignment=1,
        fontName='Helvetica-Oblique',
        textColor=rutgers_gray,
    ))

    # BodyText: Slightly larger, for main content, dark gray
    stylesheet.add(ParagraphStyle(
        name='BodyText',
        fontSize=12,
        leading=16,
        spaceAfter=7,
        fontName='Helvetica',
        textColor=rutgers_dark,
    ))

    # Code: Monospaced, light background, dark gray text
    stylesheet.add(ParagraphStyle(
        name='Code',
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        spaceAfter=6,
        backColor=rutgers_light_gray,
        textColor=rutgers_dark,
        leftIndent=6,
        rightIndent=6,
    ))

    return stylesheet
    
    
    
    
def escape_html(text: str) -> str:
    """Escape HTML special characters in a string."""
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#39;",
        ">": "&gt;",
        "<": "&lt;",
    }
    return "".join(html_escape_table.get(c, c) for c in text)


def generate_pdf(report:Report) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getStyleSheet()
    elements = []



    # Add Header and Metadata
    
    # add Rutgers Logo (SVG)
    try:
        logo_path = "static/Rutgers_Primary_Mark_Horizontal_Red_and_Black_RGB.svg"
        drawing = svg2rlg(logo_path)
        # Scale drawing to fit width
        desired_width = 150
        scale = desired_width / drawing.width
        drawing.scale(scale, scale)
        drawing.hAlign = 'CENTER'
        elements.append(drawing)  # If using Platypus, wrap in a Drawing flowable
        elements.append(Spacer(1, 6))
    except Exception:
        pass


    # create TableStyles
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])


    # Title
    title = Paragraph(f"Accessibility Report for {report.url}", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Report Metadata
    metadata = [
        ['Report ID:', report.id],
        ['Site ID:', report.site_id],
        ['Base URL:', report.base_url],
        ['URL:', report.url],
        ['Response Status:', report.response_code],
        ['Timestamp:', report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")],
        ['Tags:', ', '.join(report.tags) if report.tags else 'None']
    ]
    table = Table(metadata, hAlign='CENTER', colWidths=[150, 350])
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 12))
    # Caption
    caption = Paragraph("This table provides key metadata about the accessibility report, including identifiers, URLs, response status, timestamp, and associated tags used for the rule sets. More info here https://www.deque.com/axe/core-documentation/api-documentation/#axecore-tags", styles['Caption'])
    elements.append(caption)
    elements.append(Spacer(1, 12))


    statement = Paragraph("This report provides an overview of the accessibility issues found on the specified URL. It includes counts of rule violations, inaccessible elements, incomplete rules, and passed rules. Rules are categories which the axe-core engine uses to evaluate the accessibility of web content. Once a rule is determined to be run by a matching function, it is executed and the results are reported. Each rule has an associated impact level (e.g. critical, serious, moderate, minor), and checks which determine if a rule passes. Checks include functions give back a boolean based what its testing. Checks are categorized into three types, All checks (all functions must pass), Any (at least one function must pass), and None (no functions must pass) and are part of the rule. Checks might not be exhaustive and Rules may or may not cover all edge cases.", styles['Normal'])
    elements.append(statement)
    
    elements.append(Spacer(1, 12))

    # Report Counts
    counts_data = [['Category', 'Total', 'Critical', 'Serious', 'Moderate', 'Minor']]
    for category, counts in report.report_counts.items():
        counts_data.append([
            category.capitalize(),
            counts['total'],
            counts['critical'],
            counts['serious'],
            counts['moderate'],
            counts['minor']
        ])
    counts_table = Table(counts_data, hAlign='CENTER', colWidths=[100, 80, 80, 80, 80, 80])
    counts_table.setStyle(table_style)
    elements.append(Paragraph("Report Counts:", styles['Heading2']))
    elements.append(counts_table)
    elements.append(Paragraph("This table summarizes the counts of accessibility issues found in the report, categorized by type and impact level.", styles['Caption']))
    
    elements.append(Spacer(1, 12))
    # Add Images if available
    
    
    if report.photo:
        # put on new page

        img_stream = io.BytesIO(report.photo)
        try:
            elements.append(Paragraph("Screenshot:", styles["Heading2"]))
            elements.append(Image(img_stream , width=500, height=600))
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("This screenshot captures the full page as it appeared during the accessibility scan. It provides visual context for the issues identified in the report. There are different colors highlighting the elements based on the impact of the violations. Darkred indicates critical issues, Red indicates serious issues, Orange indicates moderate issues, and Yellow indicates minor issues.", styles["Caption"]))
            elements.append(Spacer(1, 12))
        except Exception:
            elements.append(Paragraph("⚠ Could not load embedded image", styles["Normal"]))
   
    
    
    # Detailed Violations
    elements.append(Paragraph("Detailed Violations:", styles['Heading2']))


    def create_result_section(result:AxeResult, type:Literal["violation","incomplete","pass","inaccessible"] = "violation") -> list:
        
        elements.append(Paragraph(f"{type.capitalize()}: {result.get('id', 'N/A')}", styles['Heading3']))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"Impact: {result.get('impact', 'N/A')}", styles['Normal']))
        description = escape_html(result.get('description', 'N/A'))
        elements.append(Paragraph(f"Description: {description}", styles['Normal']))
        help = escape_html(result.get('help', 'N/A'))
        elements.append(Paragraph(f"Help: {help}", styles['Normal']))
        elements.append(Paragraph(f"Help URL: {result.get('helpUrl', 'N/A')}", styles['Normal']))
        elements.append(Spacer(1, 6))
        
        
        # Node Details Table
        return elements

    def create_nodes_table(nodes:List[AxeNode], type:Literal["violation","incomplete","pass","inaccessible"] = "violation") -> Table:
        node_data = [[f'HTML ({len(nodes)})', 'Target']]
        
        if type in ["violation", "incomplete"]:
            node_data[0].append('Failure Summary')

        for node in nodes:
            # escape html in node details
            html = escape_html(node.get('html', 'N/A'))
            target = ', '.join(escape_html(t) for t in node.get('target', []))
            failure_summary = escape_html(node.get('failureSummary', 'N/A'))
            
            # Use Paragraph for HTML and Target to enable wrapping
            html_paragraph = Paragraph(html if html.strip() else "⚠ No HTML content available", styles['NormalXSmall'])
            target_paragraph = Paragraph(target, styles['NormalXSmall'])
            failure_paragraph = Paragraph(failure_summary, styles['NormalSmall'])
            node_data.append([html_paragraph, target_paragraph])
            
            if type in ["violation", "incomplete"]:
                node_data[-1].append(failure_paragraph)
            
        node_table = Table(node_data, hAlign='LEFT', colWidths=[200, 120, 180])
        node_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        return node_table
        

    violations = report.report.get('violations', [])
    if violations and len(violations) > 0:
        for violation in violations:
            create_result_section(violation, type="violation")
            elements.append(Spacer(1, 6))
            elements.append(Paragraph("Affected Nodes Details:", styles['Small']))
            elements.append(Spacer(1, 6))
            # Node Details Table
            elements.append(create_nodes_table(violation.get('nodes', [])))
            elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph("No violations found.", styles['Heading2']))
    
    elements.append(Spacer(1, 14))

    
    incomplete = report.report.get('incomplete', [])
    if incomplete and len(incomplete) > 0:
        elements.append(Paragraph("Incomplete Checks:", styles['Heading2']))
        for check in incomplete:
            create_result_section(check, type="incomplete")
            elements.append(create_nodes_table(check.get('nodes', []), type="incomplete"))
            elements.append(Spacer(1, 6))
            
            
            
    else:
        elements.append(Paragraph("No incomplete checks found.", styles['Heading2']))
    
    
    elements.append(Spacer(1, 14))
    
    passes = report.report.get('passes', [])
    if passes and len(passes) > 0:
        elements.append(Paragraph("Passed Checks:", styles['Heading2']))
        for check in passes:
            create_result_section(check, type="pass")
            elements.append(create_nodes_table(check.get('nodes', []), type="pass"))
            elements.append(Spacer(1, 6))
            
    else:
        elements.append(Paragraph("No passed checks found.", styles['Heading2']))
    
    elements.append(Spacer(1, 14))
    
    inaccessible = report.report.get('inaccessible', [])
    if inaccessible and len(inaccessible) > 0:
        elements.append(Paragraph("Inaccessible Elements:", styles['Heading2']))
        for check in inaccessible:
            create_result_section(check, type="inaccessible")
            elements.append(create_nodes_table(check.get('nodes', []), type="inaccessible"))
            elements.append(Spacer(1, 6))
            
    else:
        elements.append(Paragraph("No inaccessible elements found.", styles['Heading3']))
    
    elements.append(Spacer(1, 14))

    
    # Add Links if available
    if report.links:
        elements.append(Paragraph("Links found on the page:", styles['Heading2']))
        elements.append(Paragraph(f"The following are links on the page as found by the scanner. Some links may not be found by the scanner due to dynamic content or other factors.", styles['Normal']))
        for link in report.links:
            elements.append(Paragraph(link, styles['NormalSmall']))
        elements.append(Spacer(1, 12))
    # # Add Videos if available
    if report.videos:
        elements.append(Paragraph("Video Content found:", styles['Heading2']))
        elements.append(Paragraph(f"Video content on a page might indicate potential accessibility issues. Videos are recommended to have other accessibility features such as captions or transcripts.", styles['Normal']))
        for video in report.videos:
            elements.append(Paragraph(video, styles['NormalSmall']))
        elements.append(Spacer(1, 12))


   
    # Add Rutgers Logo (SVG)
    try:
        logo_path = "static/Rutgers_Primary_Mark_Horizontal_Red_and_Black_RGB.svg"
        
        drawing = svg2rlg(logo_path)
        # Scale drawing to fit width
        desired_width = 200
        scale = desired_width / drawing.width
        drawing.scale(scale, scale)
        elements.append(drawing)  # If using Platypus, wrap in a Drawing flow

        elements.append(Paragraph("Powered by Laboratory of Computer Science Research, Rutgers University", styles["Small"]))
        elements.append(Spacer(1, 6))

    except Exception:
        elements.append(Paragraph("⚠ Could not load Rutgers logo", styles["Normal"]))

    # Add Statement
    elements.append(Paragraph("This PDF was generated by Laboratory of Computer Science Research Accessibility Scanner. The purpose of this tool is to assist in identifying accessibility issues in web applications. This report provides an overview of the accessibility checks performed on the specified web application. Focusing on WCAG 2.1 guidelines, it aims to highlight potential areas for improvement. This scanner is automated and may not catch all issues. Manual review is recommended.", styles['Small']))


    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Rutgers is an equal access/equal opportunity institution. Individuals with disabilities are encouraged to direct suggestions, comments, or complaints concerning any accessibility issues with Rutgers web sites to: accessibility@rutgers.edu or complete the Report Accessibility Barrier or Provide Feedback Form.", styles['Small']))

    elements.append(Paragraph("For more information on Rutgers University and its commitment to accessibility, visit https://accessibility.rutgers.edu", styles['Small']))
    elements.append(Spacer(1, 12))
 


    # build PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data