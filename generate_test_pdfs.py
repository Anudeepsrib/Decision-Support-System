from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf(filename, title, data):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Subtitle
    elements.append(Paragraph("Commission Order for Financial Year 2024-25", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Table
    table_data = [["Particulars", "Approved (Rs. Cr.)", "Actual (Rs. Cr.)", "Claimed (Rs. Cr.)"]]
    for item, app, act, clm in data:
        table_data.append([item, app, act, clm])
    
    t = Table(table_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(t)
    doc.build(elements)
    print(f"Generated {filename}")

# ARR Order Rows (Approved values matter here)
arr_rows = [
    ("Power Purchase Cost", "4500.00", "0.00", "0.00"),
    ("Employee Cost", "1200.00", "0.00", "0.00"),
    ("Repair & Maintenance", "150.00", "0.00", "0.00"),
    ("A&G Expenses", "80.00", "0.00", "0.00"),
    ("Depreciation", "400.00", "0.00", "0.00"),
    ("Interest & Finance Charges", "350.00", "0.00", "0.00"),
    ("Return on Equity", "250.00", "0.00", "0.00"),
    ("Total ARR", "6930.00", "0.00", "0.00"),
]

# Petition Rows (Actual and Claimed matter here)
petition_rows = [
    ("Power Purchase Cost", "0.00", "4850.50", "4900.00"),
    ("Employee Cost", "0.00", "1250.00", "1300.00"),
    ("Repair & Maintenance", "0.00", "185.00", "190.00"), # High variance ( >15%)
    ("A&G Expenses", "0.00", "82.00", "85.00"),
    ("Depreciation", "0.00", "410.00", "410.00"),
    ("Interest & Finance Charges", "0.00", "360.00", "360.00"),
    ("Return on Equity", "0.00", "250.00", "250.00"),
    ("Total ARR", "0.00", "7387.50", "7495.00"),
]

if __name__ == "__main__":
    generate_pdf("arr_order_test.pdf", "ARR Approval Order for 2024-25", arr_rows)
    generate_pdf("petition_test.pdf", "Truing-Up Petition for 2024-25", petition_rows)
