"""
Dev-only script. Generates a realistic sample NDA PDF for testing the parser.
Run once: python sample_docs/create_sample_nda.py
"""
from fpdf import FPDF

NDA_TEXT = [
    ("NON-DISCLOSURE AGREEMENT", True),
    ("", False),
    (
        "This Non-Disclosure Agreement (\"Agreement\") is entered into as of January 15, 2024 "
        "(\"Effective Date\") by and between Acme Technologies Inc., a Delaware corporation "
        "with its principal place of business at 123 Innovation Drive, San Francisco, CA 94105 "
        "(\"Disclosing Party\"), and Horizon Legal Partners LLP, a California limited liability "
        "partnership with offices at 456 Market Street, Suite 800, San Francisco, CA 94104 "
        "(\"Receiving Party\").",
        False,
    ),
    ("", False),
    ("1. PURPOSE", True),
    (
        "The Receiving Party understands that the Disclosing Party has disclosed or may disclose "
        "information relating to its proprietary software platform, client data, business strategies, "
        "financial projections, and product roadmap (hereinafter referred to as \"Confidential "
        "Information\"). The parties wish to enter into this Agreement to protect such information "
        "in connection with a potential business partnership.",
        False,
    ),
    ("", False),
    ("2. DEFINITION OF CONFIDENTIAL INFORMATION", True),
    (
        "\"Confidential Information\" means any data or information that is proprietary to the "
        "Disclosing Party and not generally known to the public, whether in tangible or intangible "
        "form, whenever and however disclosed, including but not limited to: (a) any marketing "
        "strategies, plans, financial information, or projections, operations, sales estimates, "
        "business plans and performance results; (b) the identity of customers, clients, and "
        "business partners; (c) any scientific or technical information, inventions, design, "
        "process, procedure, formula, improvement, technology, or method; (d) concepts, reports, "
        "data, know-how, works-in-progress, designs, development tools, specifications, and "
        "computer programs; and (e) any other information that should reasonably be recognized "
        "as confidential information of the Disclosing Party.",
        False,
    ),
    ("", False),
    ("3. OBLIGATIONS OF RECEIVING PARTY", True),
    (
        "The Receiving Party agrees to: (a) hold the Confidential Information in strict confidence "
        "and take all reasonable precautions to protect such Confidential Information; (b) not "
        "disclose any Confidential Information to any third parties without prior written consent "
        "of the Disclosing Party; (c) not use any Confidential Information for any purpose except "
        "to evaluate and engage in discussions concerning a potential business relationship between "
        "the parties; and (d) limit access to Confidential Information to those employees, "
        "contractors, and agents who need to know such information for the purpose stated herein "
        "and who are bound by confidentiality obligations no less restrictive than those contained "
        "in this Agreement.",
        False,
    ),
    ("", False),
    ("4. TERM AND TERMINATION", True),
    (
        "This Agreement shall remain in effect for a period of three (3) years from the Effective "
        "Date. Either party may terminate this Agreement upon thirty (30) days written notice to "
        "the other party. Upon termination, the Receiving Party shall promptly return or destroy "
        "all Confidential Information and any copies thereof, and shall certify in writing that "
        "it has done so. Obligations of confidentiality shall survive termination for a period "
        "of two (2) additional years.",
        False,
    ),
    ("", False),
    ("5. PAYMENT TERMS", True),
    (
        "In consideration of the mutual covenants contained herein, each party agrees to pay "
        "any out-of-pocket costs incurred in connection with this Agreement within Net 30 days "
        "of receipt of a valid invoice. Late payments shall accrue interest at the rate of 1.5% "
        "per month.",
        False,
    ),
    ("", False),
    ("6. RISKY CLAUSES -- INDEMNIFICATION", True),
    (
        "Each party (\"Indemnifying Party\") shall indemnify, defend, and hold harmless the "
        "other party and its officers, directors, employees, and agents from and against any "
        "claims, damages, losses, liabilities, costs, and expenses (including reasonable "
        "attorneys' fees) arising out of or resulting from the Indemnifying Party's breach of "
        "this Agreement. This indemnification obligation shall survive the termination of this "
        "Agreement indefinitely.",
        False,
    ),
    ("", False),
    ("7. GOVERNING LAW", True),
    (
        "This Agreement shall be governed by and construed in accordance with the laws of the "
        "State of California, without regard to its conflict of law provisions. Any dispute "
        "arising under this Agreement shall be subject to the exclusive jurisdiction of the "
        "state and federal courts located in San Francisco County, California.",
        False,
    ),
    ("", False),
    ("8. ENTIRE AGREEMENT", True),
    (
        "This Agreement constitutes the entire agreement between the parties with respect to "
        "the subject matter hereof and supersedes all prior agreements and understandings, "
        "whether written or oral. This Agreement may not be amended except by a written "
        "instrument signed by both parties.",
        False,
    ),
    ("", False),
    ("IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.", False),
    ("", False),
    ("Acme Technologies Inc.                    Horizon Legal Partners LLP", False),
    ("", False),
    ("Signature: ___________________            Signature: ___________________", False),
    ("Name:      Sarah Chen                     Name:      Robert Malik", False),
    ("Title:     Chief Executive Officer        Title:     Managing Partner", False),
    ("Date:      January 15, 2024               Date:      January 15, 2024", False),
]


def create_nda():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)

    for text, is_heading in NDA_TEXT:
        if not text:
            pdf.ln(4)
            continue

        if is_heading:
            pdf.set_font("Helvetica", style="B", size=11)
        else:
            pdf.set_font("Helvetica", size=10)

        pdf.multi_cell(0, 6, text)
        pdf.ln(2)

    # Add a page number to the second page to test page-number stripping
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(
        0, 6,
        "EXHIBIT A -- PERMITTED DISCLOSURES\n\n"
        "The following categories of disclosure are expressly permitted under Section 3:\n\n"
        "1. Disclosure to legal counsel retained by the Receiving Party, provided such counsel "
        "is bound by professional confidentiality obligations.\n\n"
        "2. Disclosure required by court order, provided the Receiving Party gives prompt "
        "written notice to the Disclosing Party and cooperates in seeking a protective order.\n\n"
        "3. Disclosure to accountants and financial advisors who are bound by professional "
        "confidentiality obligations and who require access solely for tax or audit purposes.",
    )
    pdf.ln(10)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 5, "2", align="C")  # page number

    output = "sample_docs/sample_nda.pdf"
    pdf.output(output)
    print(f"Created: {output}")


if __name__ == "__main__":
    create_nda()
