from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
from typing import Dict, Any

def generate_pdf_report(report_data: Dict[str, Any]) -> BytesIO:
    """Generate PDF grading report"""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph("SUPPLIES BUDGET GRADING REPORT", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Header information
    header_data = [
        ["Student Name:", report_data.get('student_name', 'Unknown')],
        ["Department:", report_data.get('department', 'Unknown')],
        ["Date:", datetime.now().strftime("%B %d, %Y")],
        ["", ""]
    ]
    
    header_table = Table(header_data, colWidths=[2*inch, 4.5*inch])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Score box
    score = report_data.get('correct_count', 0)
    total = report_data.get('total_calculations', 1)
    percentage = report_data.get('percentage', 0)
    
    score_data = [[
        Paragraph(f"<b>SCORE</b>", ParagraphStyle('center', alignment=TA_CENTER, fontSize=14)),
        Paragraph(f"<b>{score}/{total}</b>", ParagraphStyle('center', alignment=TA_CENTER, fontSize=20, textColor=colors.HexColor('#27ae60') if percentage >= 70 else colors.HexColor('#e74c3c'))),
        Paragraph(f"<b>{percentage:.1f}%</b>", ParagraphStyle('center', alignment=TA_CENTER, fontSize=20, textColor=colors.HexColor('#27ae60') if percentage >= 70 else colors.HexColor('#e74c3c')))
    ]]
    
    score_table = Table(score_data, colWidths=[2*inch, 2*inch, 2*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecf0f1')),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#34495e')),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Fixed Expenses Results
    elements.append(Paragraph("FIXED EXPENSES", heading_style))
    
    for item_result in report_data.get('fixed_expenses_results', []):
        elements.append(Paragraph(f"<b>{item_result['description']}</b>", subheading_style))
        
        validations = item_result.get('validations', {})
        if validations:
            validation_data = [["Field", "Status", "Expected", "Actual"]]
            
            for field_name, validation in validations.items():
                status = validation.get('status', '')
                expected = validation.get('expected', 'N/A')
                actual = validation.get('actual', 'N/A')
                
                # Format numbers
                if isinstance(expected, (int, float)):
                    expected = f"${expected:,.2f}" if expected > 100 else f"{expected:.2f}"
                if isinstance(actual, (int, float)):
                    actual = f"${actual:,.2f}" if actual > 100 else f"{actual:.2f}"
                
                # Clean field name
                field_display = field_name.replace('_', ' ').title()
                
                validation_data.append([
                    field_display,
                    status,
                    str(expected),
                    str(actual)
                ])
            
            validation_table = Table(validation_data, colWidths=[2.2*inch, 1.8*inch, 1.3*inch, 1.3*inch])
            validation_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            elements.append(validation_table)
        
        elements.append(Spacer(1, 0.15*inch))
    
    # Variable Expenses Results
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("VARIABLE EXPENSES", heading_style))
    
    for item_result in report_data.get('variable_expenses_results', []):
        elements.append(Paragraph(f"<b>{item_result['description']}</b>", subheading_style))
        
        validations = item_result.get('validations', {})
        if validations:
            validation_data = [["Field", "Status", "Expected", "Actual"]]
            
            for field_name, validation in validations.items():
                status = validation.get('status', '')
                expected = validation.get('expected', 'N/A')
                actual = validation.get('actual', 'N/A')
                
                if isinstance(expected, (int, float)):
                    expected = f"${expected:,.2f}" if expected > 100 else f"{expected:.2f}"
                if isinstance(actual, (int, float)):
                    actual = f"${actual:,.2f}" if actual > 100 else f"{actual:.2f}"
                
                field_display = field_name.replace('_', ' ').title()
                
                validation_data.append([
                    field_display,
                    status,
                    str(expected),
                    str(actual)
                ])
            
            validation_table = Table(validation_data, colWidths=[2.2*inch, 1.8*inch, 1.3*inch, 1.3*inch])
            validation_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            elements.append(validation_table)
        
        elements.append(Spacer(1, 0.15*inch))
    
    # Total Expenses Results
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("TOTAL EXPENSES", heading_style))
    
    total_validations = report_data.get('total_expenses_results', {})
    if total_validations:
        validation_data = [["Field", "Status", "Expected", "Actual"]]
        
        for field_name, validation in total_validations.items():
            status = validation.get('status', '')
            expected = validation.get('expected', 'N/A')
            actual = validation.get('actual', 'N/A')
            
            if isinstance(expected, (int, float)):
                expected = f"${expected:,.2f}"
            if isinstance(actual, (int, float)):
                actual = f"${actual:,.2f}"
            
            field_display = field_name.replace('_', ' ').title()
            
            validation_data.append([
                field_display,
                status,
                str(expected),
                str(actual)
            ])
        
        validation_table = Table(validation_data, colWidths=[2.2*inch, 1.8*inch, 1.3*inch, 1.3*inch])
        validation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(validation_table)
    
    # Summary
    if report_data.get('summary'):
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("SUMMARY", heading_style))
        elements.append(Paragraph(report_data['summary'], normal_style))
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle('footer', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    elements.append(Paragraph(f"Generated by LAU Nursing Budget Grader | {datetime.now().strftime('%Y-%m-%d %H:%M')}", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    return buffer