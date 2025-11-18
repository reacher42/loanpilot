#!/usr/bin/env python3
"""
Populate parameter_metadata table with all database columns and their metadata.
"""

import sqlite3
import json

# Parameter metadata: column_name -> (display_name, common_terms, description, category)
PARAMETERS = {
    # Core identifiers
    'loan_servicer': ('Loan Servicer', ['servicer', 'lender', 'loan provider'], 'The loan servicing company (Prime or LoanStream)', 'identifier'),
    'program_name': ('Program Name', ['program', 'product name'], 'Name of the loan program', 'identifier'),
    'program_summary': ('Program Summary', ['summary', 'overview', 'description'], 'Brief description of the loan program', 'identifier'),

    # Financial parameters
    'loan_amount': ('Loan Amount', ['loan size', 'loan value', 'amount', 'principal'], 'Loan amount range or limit', 'financial'),
    'loan_type': ('Loan Type', ['mortgage type', 'loan product type'], 'Type of loan (conforming, non-conforming, jumbo, etc.)', 'financial'),
    'dti': ('DTI', ['debt to income', 'debt to income ratio', 'debt ratio'], 'Maximum debt-to-income ratio allowed', 'financial'),
    'ltv': ('LTV', ['loan to value', 'loan to value ratio'], 'Maximum loan-to-value ratio', 'financial'),
    'cltv': ('CLTV', ['combined loan to value', 'combined ltv'], 'Combined loan-to-value ratio (includes all liens)', 'financial'),
    'cash_out': ('Cash Out', ['cash out amount', 'cash out limit'], 'Cash-out refinance limitations', 'financial'),
    'reserves': ('Reserves', ['reserve requirements', 'cash reserves', 'reserve months'], 'Required cash reserves in months', 'financial'),

    # Credit parameters
    'borrower_credit_score': ('Borrower Credit Score', ['credit score', 'fico', 'minimum credit score', 'credit requirement'], 'Minimum credit score for primary borrower', 'credit'),
    'co-borrower_credit_score': ('Co-Borrower Credit Score', ['coborrower credit', 'secondary borrower credit'], 'Minimum credit score for co-borrower', 'credit'),
    'qualifying_credit_score': ('Qualifying Credit Score', ['qualifying score', 'qualifying fico'], 'Qualifying credit score methodology', 'credit'),

    # Late payment history
    '30day_mortgage_lates_in_06_months': ('30-Day Lates (6 Months)', ['30 day late payments', 'mortgage lates 6 months'], 'Allowed 30-day late payments in last 6 months', 'credit'),
    '30day_mortgage_lates_in_12_months': ('30-Day Lates (12 Months)', ['30 day late payments', 'mortgage lates 12 months', 'mortgage lates 1 year'], 'Allowed 30-day late payments in last 12 months', 'credit'),
    '30day_mortgage_lates_in_24_months': ('30-Day Lates (24 Months)', ['30 day late payments', 'mortgage lates 24 months', 'mortgage lates 2 years'], 'Allowed 30-day late payments in last 24 months', 'credit'),
    '60day_mortgage_lates_in_12_months': ('60-Day Lates (12 Months)', ['60 day late payments', 'mortgage lates 12 months'], 'Allowed 60-day late payments in last 12 months', 'credit'),
    '60day_mortgage_lates_in_24_months': ('60-Day Lates (24 Months)', ['60 day late payments', 'mortgage lates 24 months'], 'Allowed 60-day late payments in last 24 months', 'credit'),
    '90day_mortgage_lates_in_24_months': ('90-Day Lates (24 Months)', ['90 day late payments', 'mortgage lates 24 months'], 'Allowed 90-day late payments in last 24 months', 'credit'),
    '120day_mortgage_lates_in_12_months': ('120-Day Lates (12 Months)', ['120 day late payments', 'mortgage lates 12 months'], 'Allowed 120-day late payments in last 12 months', 'credit'),
    'lates_in_last_12_months': ('Lates in Last 12 Months', ['late payments', 'payment history'], 'Total late payments in last 12 months', 'credit'),

    # Credit events and seasoning
    'credit_event_major': ('Major Credit Event', ['bankruptcy', 'foreclosure', 'short sale', 'deed in lieu'], 'Major credit events allowed', 'credit'),
    'credit_event_type': ('Credit Event Type', ['type of credit event'], 'Type of credit event allowed', 'credit'),
    'credit_event_seasoning': ('Credit Event Seasoning', ['time since credit event', 'seasoning period'], 'Required time since major credit event', 'credit'),
    'fc_seasoning': ('Foreclosure Seasoning', ['foreclosure waiting period', 'time since foreclosure'], 'Required time since foreclosure', 'credit'),
    'ss_seasoning': ('Short Sale Seasoning', ['short sale waiting period', 'time since short sale'], 'Required time since short sale', 'credit'),
    'dil_seasoning': ('Deed in Lieu Seasoning', ['dil waiting period', 'time since deed in lieu'], 'Required time since deed in lieu', 'credit'),
    'bk_seasoning': ('Bankruptcy Seasoning', ['bankruptcy waiting period', 'time since bankruptcy'], 'Required time since bankruptcy', 'credit'),

    # Appraisal parameters
    'appraisal_review_required': ('Appraisal Review Required', ['appraisal review', 'desk review', 'field review'], 'When appraisal review is required', 'appraisal'),
    'number_of_appraisals': ('Number of Appraisals', ['appraisal count', 'how many appraisals'], 'Number of appraisals required', 'appraisal'),
    'appraisal_transfer_allowed': ('Appraisal Transfer Allowed', ['appraisal transfer', 'transferred appraisals', 'transfer appraisal'], 'Whether appraisal transfers are permitted', 'appraisal'),
    'cu_score': ('CU Score', ['collateral underwriter', 'collateral underwriter score'], 'Collateral Underwriter (CU) score requirements', 'appraisal'),

    # Property parameters
    'property_type': ('Property Type', ['property', 'home type', 'property classification'], 'Eligible property types (SFR, condo, townhome, etc.)', 'property'),
    'property_value': ('Property Value', ['home value', 'property price'], 'Property value limits or requirements', 'property'),
    'property_state': ('Property State', ['state', 'location', 'geography'], 'Eligible property states', 'property'),
    'property_address': ('Property Address', ['address', 'location'], 'Property address requirements', 'property'),
    'occupancy': ('Occupancy', ['occupancy type', 'owner occupied', 'primary residence', 'second home', 'investment'], 'Property occupancy type', 'property'),
    'non-warrantable_condos_allowed': ('Non-Warrantable Condos', ['non warrantable', 'condo requirements'], 'Whether non-warrantable condos are allowed', 'property'),
    'condotels_allowed': ('Condotels Allowed', ['condotel', 'hotel condos'], 'Whether condotels are permitted', 'property'),
    'length_of_ownership': ('Length of Ownership', ['ownership period', 'time owned'], 'Required length of property ownership', 'property'),

    # Borrower parameters
    'borrower_contribution': ('Borrower Contribution', ['down payment contribution', 'borrower funds'], 'Required borrower contribution to down payment', 'borrower'),
    'eligible_borrowers': ('Eligible Borrowers', ['borrower eligibility', 'who can borrow'], 'Types of eligible borrowers', 'borrower'),
    'ineligible_borrowers': ('Ineligible Borrowers', ['borrower restrictions', 'who cannot borrow'], 'Types of ineligible borrowers', 'borrower'),
    'first_time_homebuyer': ('First Time Homebuyer', ['fthb', 'first time buyer'], 'First-time homebuyer requirements or benefits', 'borrower'),
    'first_time_investor': ('First Time Investor', ['first time investor requirements'], 'First-time investor requirements', 'borrower'),
    'citizenship': ('Citizenship', ['citizenship requirements', 'permanent resident', 'foreign national'], 'Citizenship and residency requirements', 'borrower'),
    'entities_allowed_to_title': ('Entities Allowed to Title', ['entity ownership', 'llc', 'trust', 'corporate'], 'Legal entities allowed to hold title', 'borrower'),

    # Funds and contributions
    'gifts_for_down_payment': ('Gifts for Down Payment', ['gift funds', 'gifted down payment'], 'Gift fund allowances for down payment', 'funds'),
    'gift_funds_for_reserves': ('Gift Funds for Reserves', ['gift funds for reserves', 'gifted reserves'], 'Gift fund allowances for reserves', 'funds'),
    'business_funds_for_down_payment (or reserves?)': ('Business Funds', ['business funds', 'business assets'], 'Business fund usage for down payment or reserves', 'funds'),

    # Income parameters
    'income': ('Income', ['income requirements', 'income documentation'], 'Income requirements and documentation', 'income'),
    'channel': ('Channel', ['origination channel', 'broker', 'retail'], 'Origination channel (retail, broker, correspondent)', 'distribution'),

    # Loan terms and features
    'temp_buydown_allowed': ('Temporary Buydown', ['buydown', 'temp buydown', 'rate buydown'], 'Temporary interest rate buydown allowances', 'loan_terms'),
    'interest_only_period': ('Interest Only Period', ['io period', 'interest only', 'io'], 'Interest-only period duration', 'loan_terms'),
    'prepayment_penalty': ('Prepayment Penalty', ['prepay penalty', 'early payoff penalty'], 'Prepayment penalty terms', 'loan_terms'),
    'prepayment_penalty_investment_properties': ('Prepayment Penalty (Investment)', ['prepay penalty investment', 'investment prepay'], 'Prepayment penalty for investment properties', 'loan_terms'),
    'lien_position': ('Lien Position', ['first lien', 'second lien', 'subordinate lien'], 'Allowed lien positions', 'loan_terms'),
    'products': ('Products', ['loan products', 'available products'], 'Available loan products and options', 'loan_terms'),

    # AUS and underwriting
    'aus_required': ('AUS Required', ['automated underwriting', 'aus', 'underwriting system'], 'Automated Underwriting System (AUS) requirements', 'underwriting'),
    'aus_used': ('AUS Used', ['which aus', 'aus system'], 'Which AUS system is used', 'underwriting'),

    # Other
    'time_since_last_cash_out': ('Time Since Last Cash Out', ['cash out seasoning', 'time since cash out'], 'Required time since last cash-out refinance', 'timing'),
}

def populate_metadata():
    """Populate parameter_metadata table with all parameters."""
    conn = sqlite3.connect('loanpilot.db')
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM parameter_metadata")

    # Insert all parameters
    for column_name, (display_name, common_terms, description, category) in PARAMETERS.items():
        cursor.execute('''
            INSERT INTO parameter_metadata (column_name, display_name, common_terms, description, category)
            VALUES (?, ?, ?, ?, ?)
        ''', (column_name, display_name, json.dumps(common_terms), description, category))

    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM parameter_metadata")
    count = cursor.fetchone()[0]
    print(f"✅ Successfully populated {count} parameters in parameter_metadata table")

    # Show sample
    cursor.execute("SELECT column_name, display_name, category FROM parameter_metadata LIMIT 10")
    print("\nSample parameters:")
    for row in cursor.fetchall():
        print(f"  • {row[1]} ({row[0]}) - {row[2]}")

    conn.close()

if __name__ == '__main__':
    populate_metadata()
