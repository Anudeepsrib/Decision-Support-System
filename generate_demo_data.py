import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def create_pdf(filename, title, content_lines, table_data=None):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    doc = SimpleDocTemplate(filename, pagesize=letter)
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    
    normal_style = styles['Normal']
    normal_style.fontSize = 11
    normal_style.leading = 14
    
    elements = []
    
    # Title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.5 * inch))
    
    # Content
    for line in content_lines:
        elements.append(Paragraph(line, normal_style))
        elements.append(Spacer(1, 0.2 * inch))
        
    # Table (if any)
    if table_data:
        elements.append(Spacer(1, 0.3 * inch))
        t = Table(table_data, colWidths=[2.5*inch, 2*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        
    doc.build(elements)
    print(f"✅ Generated demo PDF: {filename}")

if __name__ == "__main__":
    # Petition 1: SBU-D True-up
    create_pdf(
        "data/demo_files/1_True_Up_Petition_SBU_D_FY25.pdf",
        "KSEB LIMITED - SBU-D TRUING UP PETITION (FY 2024-25)",
        [
            "BEFORE THE KERALA STATE ELECTRICITY REGULATORY COMMISSION",
            "PETITION FOR TRUING UP OF ACCOUNTS FOR STRATEGIC BUSINESS UNIT - DISTRIBUTION (SBU-D)",
            "Financial Year: 2024-25",
            "1. Introduction: This petition is filed under the KSERC MYT Tariff Regulations 2022-27.",
            "2. O&M Expenses: The operational and maintenance expenses have been closely monitored.",
            "Based on our internal audit, below are the final declared values for regulatory approval."
        ],
        table_data=[
            ["Particulars", "Approved (MYT)", "Actual Claimed"],
            ["O&M Cost", "Rs. 180.00 Cr", "Rs. 150.00 Cr (Audited)"],
            ["Depreciation", "Rs. 45.50 Cr", "Rs. 42.10 Cr"],
            ["Interest on Loan", "Rs. 60.00 Cr", "Rs. 65.20 Cr"],
            ["Return on Equity", "Rs. 30.00 Cr", "Rs. 30.00 Cr"]
        ]
    )

    # Petition 2: SBU-G Audited Financials
    create_pdf(
        "data/demo_files/2_Audited_Financials_SBU_G_FY25.pdf",
        "STATUTORY AUDIT REPORT - SBU-G (FY 2024-25)",
        [
            "INDEPENDENT STATUTORY AUDITOR'S REPORT",
            "To the Members of KSEB Limited (SBU-Generation)",
            "We have audited the accompanying financial statements of SBU-G for the year ended March 31, 2025.",
            "In our opinion, the statements give a true and fair view in conformity with the accounting principles.",
            "Key cost components identified during the audit are tabulated below for regulatory truing-up."
        ],
        table_data=[
            ["Expenditure Head", "Previous Year", "Current Year (Actual)"],
            ["Power Purchase Cost", "Rs. 750.00 Cr", "Rs. 850.00 Cr"],
            ["Fuel Cost", "Rs. 110.00 Cr", "Rs. 135.00 Cr"],
            ["Employee Expenses", "Rs. 85.00 Cr", "Rs. 92.50 Cr"],
            ["A&G Expenses", "Rs. 12.00 Cr", "Rs. 14.10 Cr"]
        ]
    )
    
    # Petition 3: Transmission Extract 
    create_pdf(
        "data/demo_files/3_Transmission_Loss_Report_FY25.pdf",
        "KSERC COMPLIANCE REPORT - SYSTEM EFFICIENCY (SBU-T)",
        [
            "ANNUAL LINE LOSS & EFFICIENCY DECLARATION",
            "Financial Year: 2024-25",
            "This report details the technical and commercial losses recorded across the transmission network.",
            "The KSERC normative trajectory mandated a strict compliance target for this fiscal year.",
            "Our automated SCADA systems and subsequent audits have verified the following metrics:"
        ],
        table_data=[
            ["Metric", "Normative Target", "Actual Achieved"],
            ["T&D Line Loss (%)", "11.50 %", "12.20 %"],
            ["Collection Efficiency", "99.00 %", "98.50 %"],
            ["AT&C Loss", "12.00 %", "13.25 %"]
        ]
    )

    print("\nAll demo data has been generated in the 'data/demo_files' directory.")
