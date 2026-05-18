"""
Dev-only script. Generates a multi-clause employment contract PDF for testing
context-window chunking. Approx 18,000 characters / 4,500 tokens.
Run once: python sample_docs/create_sample_employment.py
"""
from fpdf import FPDF

SECTIONS = [
    ("EMPLOYMENT AGREEMENT", True, """
This Employment Agreement ("Agreement") is entered into as of March 1, 2024 ("Effective Date")
by and between NovaTech Systems Inc., a Delaware corporation with its principal place of business
at 789 Silicon Boulevard, San Jose, CA 95110 ("Company"), and Dr. Emily R. Hartwell, an individual
residing at 42 Oakwood Lane, Palo Alto, CA 94301 ("Employee").
"""),
    ("1. POSITION AND DUTIES", True, """
1.1 Position. The Company hereby employs Employee as Vice President of Engineering, reporting
directly to the Chief Technology Officer. Employee accepts such employment on the terms and
conditions set forth herein.

1.2 Duties. Employee shall perform the following duties and responsibilities: (a) Lead and manage
the engineering department, including a team of 45 engineers across four product verticals;
(b) Define and execute the technical roadmap in alignment with company objectives; (c) Collaborate
with product management, design, and sales to deliver high-quality software products; (d) Establish
engineering best practices, coding standards, and quality assurance processes; (e) Recruit, mentor,
and retain top engineering talent; (f) Manage departmental budget of approximately $8.2 million
annually; (g) Report weekly on engineering progress, blockers, and resource needs; and (h) Represent
the engineering organization in executive leadership meetings.

1.3 Exclusive Service. During the term of this Agreement, Employee shall devote substantially all
of Employee's business time and attention to the performance of Employee's duties hereunder. Employee
shall not, without the prior written consent of the Company, directly or indirectly engage in any
other business activity that would interfere with the performance of Employee's duties.
"""),
    ("2. COMPENSATION", True, """
2.1 Base Salary. The Company shall pay Employee a base salary of $285,000 per year ("Base Salary"),
payable in accordance with the Company's standard payroll practices, subject to applicable tax
withholdings and deductions. The Base Salary shall be reviewed annually.

2.2 Annual Bonus. Employee shall be eligible to receive an annual performance bonus of up to 25%
of Base Salary based on achievement of performance objectives established by the Board of Directors.
Bonus payments, if any, shall be made within 90 days following the end of each fiscal year. Employee
must be employed on the bonus payment date to receive any bonus.

2.3 Equity Compensation. Subject to approval by the Company's Board of Directors, Employee shall
be granted options to purchase 85,000 shares of the Company's common stock at a per share exercise
price equal to the fair market value of the Company's common stock on the date of grant. Such options
shall vest over a four-year period, with 25% vesting after the first year of continuous service and
the remaining 75% vesting monthly over the following 36 months, subject to the terms of the Company's
Equity Incentive Plan.

2.4 Benefits. Employee shall be entitled to participate in all benefit plans and programs that the
Company generally makes available to its full-time employees, including health, dental, vision, and
life insurance; 401(k) plan with 4% company match; unlimited paid time off policy; $2,000 annual
professional development allowance; and monthly home office stipend of $150.
"""),
    ("3. TERM AND TERMINATION", True, """
3.1 Term. This Agreement shall commence on the Effective Date and shall continue until terminated
in accordance with this Section 3.

3.2 Termination Without Cause. The Company may terminate Employee's employment at any time without
Cause upon thirty (30) days written notice to Employee, or at the Company's option, payment of
thirty (30) days Base Salary in lieu of notice.

3.3 Termination for Cause. The Company may terminate Employee's employment immediately for Cause.
For purposes of this Agreement, "Cause" means: (a) Employee's material breach of this Agreement;
(b) Employee's conviction of, or plea of guilty or nolo contendere to, any felony or crime involving
moral turpitude; (c) Employee's willful misconduct or gross negligence in the performance of duties;
(d) Employee's repeated failure to perform duties after written notice and reasonable opportunity
to cure; (e) Employee's theft, fraud, or embezzlement; or (f) Employee's material violation of
Company policies.

3.4 Resignation. Employee may resign from employment upon sixty (60) days written notice to the
Company. The Company may waive all or part of this notice period.

3.5 Severance. If the Company terminates Employee's employment without Cause, Employee shall be
entitled to receive: (a) continuation of Base Salary for six (6) months following the termination
date; (b) payment of COBRA premiums for up to six (6) months; and (c) acceleration of any unvested
equity awards that would have vested in the twelve (12) months following termination. Receipt of
severance is conditioned upon Employee's execution of a general release of claims.
"""),
    ("4. CONFIDENTIALITY", True, """
4.1 Confidential Information. Employee acknowledges that, in the course of employment, Employee
will have access to and become acquainted with proprietary and confidential information including
but not limited to: technical information such as software code, algorithms, architectures, and
technical specifications; business information such as strategic plans, financial data, customer
lists, pricing, and vendor agreements; and personnel information such as compensation, performance
reviews, and organizational plans (collectively, "Confidential Information").

4.2 Non-Disclosure Obligation. Employee agrees to hold all Confidential Information in strict
confidence and not to disclose any Confidential Information to any third party without the prior
written consent of the Company. This obligation shall survive the termination of employment for
a period of five (5) years.

4.3 Return of Materials. Upon termination of employment, or upon request by the Company, Employee
shall promptly return all documents, records, and materials in any form containing or reflecting
Confidential Information.
"""),
    ("5. INTELLECTUAL PROPERTY", True, """
5.1 Assignment of Inventions. Employee agrees that all inventions, discoveries, improvements,
works of authorship, and other intellectual property (collectively, "Inventions") that Employee
conceives, creates, or develops during the period of employment that: (a) relate to the Company's
business or anticipated business; (b) are developed using Company resources; or (c) result from
work performed for the Company, shall be the sole and exclusive property of the Company.

5.2 Moral Rights Waiver. To the extent permitted by applicable law, Employee hereby irrevocably
waives all moral rights with respect to any Inventions assigned to the Company.

5.3 Prior Inventions. Employee has disclosed to the Company, on Exhibit A attached hereto, any and
all inventions or improvements that Employee has made prior to employment and that Employee desires
to exclude from this Agreement. Employee represents that Exhibit A is a complete list of all such
prior inventions.
"""),
    ("6. NON-COMPETE AND NON-SOLICITATION", True, """
6.1 Non-Compete. During employment and for a period of twelve (12) months following termination,
Employee shall not, directly or indirectly: (a) engage in, own, manage, operate, control, be employed
by, consult with, or participate in any business that competes with the Company in the enterprise
software infrastructure market within the United States; or (b) use Confidential Information to
compete with the Company.

6.2 Non-Solicitation of Employees. During employment and for a period of twenty-four (24) months
following termination, Employee shall not, directly or indirectly, solicit, recruit, induce, or
attempt to solicit any employee of the Company to leave their employment.

6.3 Non-Solicitation of Customers. During employment and for a period of twelve (12) months
following termination, Employee shall not, directly or indirectly, solicit or attempt to solicit
any customer of the Company with whom Employee had material contact during the last twelve (12)
months of employment.

6.4 Enforceability. Employee acknowledges that the restrictions in this Section 6 are reasonable
and necessary to protect the Company's legitimate business interests. If any restriction is deemed
unenforceable, the parties agree that a court may modify the restriction to the minimum extent
necessary to render it enforceable.

RISKY NOTE: The non-compete clause in Section 6.1 may be unenforceable in California under
Business and Professions Code Section 16600, which broadly prohibits non-compete agreements.
Employees in California should seek independent legal advice.
"""),
    ("7. DISPUTE RESOLUTION", True, """
7.1 Mandatory Arbitration. Any dispute, claim, or controversy arising out of or relating to this
Agreement, or the breach, termination, enforcement, interpretation, or validity thereof, including
the determination of the scope or applicability of this Agreement to arbitrate, shall be determined
by binding arbitration before a single arbitrator in San Jose, California, administered by JAMS
pursuant to its Employment Arbitration Rules. Judgment on the award may be entered in any court
having jurisdiction.

7.2 Class Action Waiver. TO THE FULLEST EXTENT PERMITTED BY LAW, EMPLOYEE WAIVES ANY RIGHT TO
BRING OR PARTICIPATE IN A CLASS ACTION, COLLECTIVE ACTION, OR REPRESENTATIVE ACTION AGAINST THE
COMPANY. All claims must be brought on an individual basis only.

7.3 Attorneys Fees. In any arbitration or legal proceeding arising under this Agreement, the
prevailing party shall be entitled to recover its reasonable attorneys fees and costs.

RISKY NOTE: The mandatory arbitration clause and class action waiver in Sections 7.1-7.2
significantly limit Employee's ability to pursue legal remedies and join with other employees
in collective legal action.
"""),
    ("8. GENERAL PROVISIONS", True, """
8.1 Governing Law. This Agreement shall be governed by and construed in accordance with the laws
of the State of California, without regard to its conflict of law provisions.

8.2 Entire Agreement. This Agreement, together with all exhibits attached hereto, constitutes the
entire agreement between the parties with respect to the subject matter hereof and supersedes all
prior agreements, whether written or oral.

8.3 Amendments. This Agreement may not be amended or modified except by a written instrument
signed by both parties.

8.4 Severability. If any provision of this Agreement is held to be invalid or unenforceable, the
remaining provisions shall continue in full force and effect.

8.5 Waiver. No waiver of any provision of this Agreement shall be effective unless made in writing
and signed by the waiving party.

8.6 Counterparts. This Agreement may be executed in counterparts, each of which shall be deemed
an original. Electronic signatures shall be deemed valid.
"""),
    ("SIGNATURES", True, """
IN WITNESS WHEREOF, the parties have executed this Employment Agreement as of the date first
written above.

NovaTech Systems Inc.                         Dr. Emily R. Hartwell

Signature: ____________________               Signature: ____________________
Name:      Marcus T. Webb                     Name:      Dr. Emily R. Hartwell
Title:     Chief Executive Officer            Date:      March 1, 2024
Date:      March 1, 2024
"""),
]


def create_employment_contract():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)

    for heading, is_heading, body in SECTIONS:
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.multi_cell(0, 6, heading)
        pdf.ln(2)

        pdf.set_font("Helvetica", size=10)
        # Write each paragraph (blank-line separated) as its own multi_cell
        for para in body.strip().split("\n\n"):
            cleaned = " ".join(line.strip() for line in para.splitlines() if line.strip())
            if cleaned:
                pdf.multi_cell(0, 6, cleaned)
                pdf.ln(2)
        pdf.ln(4)

    output = "sample_docs/sample_employment.pdf"
    pdf.output(output)
    print(f"Created: {output}")


if __name__ == "__main__":
    create_employment_contract()
