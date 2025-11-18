"""
Result parsers for converting query results to HTML.
Port of Express.js parsing logic to Python.
"""

import re
import html
import logging
from typing import Dict, List, Optional, Tuple

try:
    from . import query_engine, text_formatter
except ImportError:
    import query_engine
    import text_formatter

logger = logging.getLogger(__name__)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ''
    return html.escape(str(text))


async def parse_query_results(results: str, query: str) -> Dict:
    """
    Parse query results and determine response type.

    Args:
        results: Raw results from scratchpad
        query: Original query string

    Returns:
        Dict with header, summary, structuredData, autoSelectProgram
    """
    query_lower = query.lower()

    # Detect query type based on content
    if 'PRIME PROGRAMS:' in results or 'LOANSTREAM PROGRAMS:' in results:
        return await parse_program_list(results, query_lower)
    elif 'MATCHING PROGRAMS' in results or 'PROGRAM MATCHING RESULTS' in results:
        return await parse_matching_programs(results, query_lower)
    elif 'ALL PARAMETERS AND VALUES' in results:
        return parse_parameter_list(results, query_lower)
    elif 'PARAMETER:' in results:
        return parse_parameter_value(results, query_lower)
    else:
        return parse_generic_results(results, query_lower)


async def parse_program_list(results: str, query: str) -> Dict:
    """Parse program list results."""
    lines = [line for line in results.split('\n') if line.strip()]
    programs = []
    servicer = 'Prime'

    # Determine servicer from header
    if 'LOANSTREAM' in results:
        servicer = 'LoanStream'

    # Extract program names (lines starting with numbers)
    for line in lines:
        match = re.match(r'^\d+\.\s+(.+)$', line)
        if match:
            programs.append(match.group(1).strip())

    # Extract total count
    total_match = re.search(r'Total:\s+(\d+)\s+programs?', results, re.IGNORECASE)
    total = total_match.group(1) if total_match else len(programs)

    # Fetch program details from database
    engine = query_engine.get_query_engine()
    program_details = engine.fetch_program_details(programs, servicer)

    # Generate summary
    preview = ', '.join(programs[:3])
    if len(programs) > 3:
        preview += '...'
    summary = f"Found {total} loan programs in {servicer}" + (f": {preview}" if programs else "")

    # Generate program cards with redesigned layout
    program_cards = []
    for program in programs:
        details = program_details.get(program, {})
        program_key = f"{servicer}::{program}"
        # Pre-escape values to avoid backslash in f-string
        program_escaped = escape_html(program).replace("'", "\\'")
        servicer_escaped = escape_html(servicer).replace("'", "\\'")

        # Generate chips for key metrics - extract only relevant single thresholds
        # Order: Loan Amount, Credit, LTV, DTI
        chips_html = []

        # Loan Amount - extract maximum value (FIRST)
        if details.get('loan_amount'):
            loan = details['loan_amount']
            amounts = re.findall(r'\$?[\d,]+', loan)
            if amounts:
                max_amount = max([int(a.replace('$', '').replace(',', '')) for a in amounts if a.replace('$', '').replace(',', '').isdigit()])
                chips_html.append(f'<span class="badge badge-sm bg-green-100 text-green-800 border-0">Max Loan: ${max_amount:,}</span>')

        # Credit Score - extract minimum value (SECOND)
        if details.get('borrower_credit_score'):
            credit = details['borrower_credit_score']
            match = re.search(r'\d{3}', credit)
            if match:
                chips_html.append(f'<span class="badge badge-sm bg-blue-100 text-blue-800 border-0">Min Credit: {match.group()}</span>')

        # LTV - extract maximum percentage (THIRD)
        if details.get('ltv'):
            ltv = details['ltv']
            percentages = re.findall(r'(\d+)%', ltv)
            if percentages:
                max_ltv = max([int(p) for p in percentages])
                chips_html.append(f'<span class="badge badge-sm bg-purple-100 text-purple-800 border-0">Max LTV: {max_ltv}%</span>')

        # DTI - extract maximum percentage (FOURTH)
        if details.get('dti'):
            dti = details['dti']
            percentages = re.findall(r'(\d+)%', dti)
            if percentages:
                max_dti = max([int(p) for p in percentages])
                chips_html.append(f'<span class="badge badge-sm bg-orange-100 text-orange-800 border-0">Max DTI: {max_dti}%</span>')

        # Get program summary
        summary = details.get('program_summary', 'No summary available for this program.')

        card_html = f'''
    <div class="card bg-base-100 border border-base-300 mb-3 hover:shadow-lg transition-all cursor-pointer h-48"
         data-program-key="{escape_html(program_key)}"
         onclick="window.appFunctions.toggleProgramSelection('{program_escaped}', '{servicer_escaped}')">
      <div class="card-body p-3 flex flex-col">
        <!-- Metrics Row (ABOVE program name) -->
        <div class="flex justify-between items-center mb-2">
          <div class="flex flex-wrap gap-1">
            {''.join(chips_html)}
          </div>
          <input type="checkbox" class="checkbox checkbox-sm checkbox-primary pointer-events-none" />
        </div>

        <!-- Program Name Row -->
        <div class="mb-2">
          <h3 class="text-sm font-bold mb-0.5">{escape_html(program)}</h3>
          <div class="text-[10px] text-base-content/60">Servicer: {servicer}</div>
        </div>

        <!-- Program Summary -->
        <p class="text-xs text-base-content/70 leading-relaxed mb-2 flex-1 overflow-hidden">{escape_html(summary)}</p>

        <!-- Icons for additional parameters -->
        <div class="flex gap-1.5 mt-auto border-t border-base-300 pt-1.5">
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'occupancy')"
                title="Occupancy">home</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'transaction')"
                title="Transaction Type">sync_alt</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'reserves')"
                title="Reserves">account_balance</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'documentation')"
                title="Documentation">description</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'citizenship')"
                title="Citizenship">flag</span>
        </div>
      </div>
    </div>'''

        program_cards.append(card_html)

    structured_data = ''.join(program_cards) if program_cards else \
        '<div class="text-center text-base-content/60 py-8">No programs found</div>'

    return {
        "header": f"{servicer} Programs ({total})",
        "summary": summary,
        "structuredData": structured_data
    }


async def parse_matching_programs(results: str, query: str) -> Dict:
    """Parse matching program results."""
    # Handle escaped newlines
    cleaned_results = results.replace('\\n', '\n')
    lines = [line for line in cleaned_results.split('\n') if line.strip()]
    eligible_programs = []

    # Parse eligible programs
    in_eligible_section = False
    for line in lines:
        if 'ELIGIBLE PROGRAMS' in line:
            in_eligible_section = True
            continue
        if 'NOT ELIGIBLE' in line:
            in_eligible_section = False
            break

        if in_eligible_section:
            # Match pattern: "Program Name (Servicer) - XX.X% match"
            match = re.match(r'^(.+?)\s+\((.+?)\)\s+-\s+([\d.]+)%\s+match', line)
            if match:
                eligible_programs.append({
                    'name': match.group(1).strip(),
                    'servicer': match.group(2).strip(),
                    'matchScore': float(match.group(3))
                })

    # Extract summary info
    eligible_count = len(eligible_programs)
    summary_match = re.search(r'Eligible:\s+(\d+)', results, re.IGNORECASE)
    total_eligible = summary_match.group(1) if summary_match else eligible_count

    # Fetch program details
    engine = query_engine.get_query_engine()
    all_programs = {}
    for prog in eligible_programs:
        details = engine.fetch_program_details([prog['name']], prog['servicer'])
        if prog['name'] in details:
            all_programs[prog['name']] = {**details[prog['name']], **prog}
        else:
            all_programs[prog['name']] = prog

    # Generate summary
    preview = ', '.join([p['name'] for p in eligible_programs[:3]])
    if len(eligible_programs) > 3:
        preview += '...'
    summary = f"Found {total_eligible} matching programs" + (f": {preview}" if eligible_programs else "")

    # Generate program cards with match scores (redesigned)
    program_cards = []
    for program in eligible_programs:
        details = all_programs.get(program['name'], {})
        program_key = f"{program['servicer']}::{program['name']}"
        # Pre-escape values to avoid backslash in f-string
        program_name_escaped = escape_html(program['name']).replace("'", "\\'")
        program_servicer_escaped = escape_html(program['servicer']).replace("'", "\\'")

        # Generate chips for key metrics - extract only relevant single thresholds
        # Order: Loan Amount, Credit, LTV, DTI
        chips_html = []

        # Loan Amount - extract maximum value (FIRST)
        if details.get('loan_amount'):
            loan = details['loan_amount']
            amounts = re.findall(r'\$?[\d,]+', loan)
            if amounts:
                max_amount = max([int(a.replace('$', '').replace(',', '')) for a in amounts if a.replace('$', '').replace(',', '').isdigit()])
                chips_html.append(f'<span class="badge badge-sm bg-green-100 text-green-800 border-0">Max Loan: ${max_amount:,}</span>')

        # Credit Score - extract minimum value (SECOND)
        if details.get('borrower_credit_score'):
            credit = details['borrower_credit_score']
            match = re.search(r'\d{3}', credit)
            if match:
                chips_html.append(f'<span class="badge badge-sm bg-blue-100 text-blue-800 border-0">Min Credit: {match.group()}</span>')

        # LTV - extract maximum percentage (THIRD)
        if details.get('ltv'):
            ltv = details['ltv']
            percentages = re.findall(r'(\d+)%', ltv)
            if percentages:
                max_ltv = max([int(p) for p in percentages])
                chips_html.append(f'<span class="badge badge-sm bg-purple-100 text-purple-800 border-0">Max LTV: {max_ltv}%</span>')

        # DTI - extract maximum percentage (FOURTH)
        if details.get('dti'):
            dti = details['dti']
            percentages = re.findall(r'(\d+)%', dti)
            if percentages:
                max_dti = max([int(p) for p in percentages])
                chips_html.append(f'<span class="badge badge-sm bg-orange-100 text-orange-800 border-0">Max DTI: {max_dti}%</span>')

        # Get program summary
        summary = details.get('program_summary', 'No summary available for this program.')

        card_html = f'''
    <div class="card bg-base-100 border border-base-300 mb-3 hover:shadow-lg transition-all cursor-pointer h-48"
         data-program-key="{escape_html(program_key)}"
         onclick="window.appFunctions.toggleProgramSelection('{program_name_escaped}', '{program_servicer_escaped}')">
      <div class="card-body p-3 flex flex-col">
        <!-- Metrics Row (ABOVE program name) -->
        <div class="flex justify-between items-center mb-2">
          <div class="flex flex-wrap gap-1">
            {''.join(chips_html)}
          </div>
          <input type="checkbox" class="checkbox checkbox-sm checkbox-primary pointer-events-none" />
        </div>

        <!-- Program Name Row with match badge -->
        <div class="mb-2">
          <div class="flex items-center gap-2 mb-0.5">
            <h3 class="text-sm font-bold">{escape_html(program['name'])}</h3>
            <span class="badge badge-sm bg-green-500 text-white border-0">{program['matchScore']}% match</span>
          </div>
          <div class="text-[10px] text-base-content/60">Servicer: {program['servicer']}</div>
        </div>

        <!-- Program Summary -->
        <p class="text-xs text-base-content/70 leading-relaxed mb-2 flex-1 overflow-hidden">{escape_html(summary)}</p>

        <!-- Icons for additional parameters -->
        <div class="flex gap-1.5 mt-auto border-t border-base-300 pt-1.5">
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_name_escaped}', 'occupancy')"
                title="Occupancy">home</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_name_escaped}', 'transaction')"
                title="Transaction Type">sync_alt</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_name_escaped}', 'reserves')"
                title="Reserves">account_balance</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_name_escaped}', 'documentation')"
                title="Documentation">description</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_name_escaped}', 'citizenship')"
                title="Citizenship">flag</span>
        </div>
      </div>
    </div>'''

        program_cards.append(card_html)

    structured_data = ''.join(program_cards) if program_cards else \
        '<div class="text-center text-base-content/60 py-8">No matching programs found</div>'

    return {
        "header": f"Matching Programs ({total_eligible})",
        "summary": summary,
        "structuredData": structured_data
    }


def parse_parameter_list(results: str, query: str) -> Dict:
    """Parse parameter list results."""
    lines = [line for line in results.split('\n') if line.strip()]
    program_name = ''
    servicer = ''
    parameters = []

    # Extract program name and servicer
    for line in lines:
        if 'Program:' in line:
            program_name = line.split('Program:')[1].strip()
        if 'Loan Servicer:' in line:
            servicer = line.split('Loan Servicer:')[1].strip()

        # Extract parameters (lines ending with :)
        if ':' in line and '=' not in line and 'Program:' not in line and 'Loan Servicer:' not in line:
            param_name = line.split(':')[0].strip()
            if param_name and len(param_name) > 0 and '-' not in param_name:
                parameters.append({'name': param_name, 'hasValue': True})

    summary = f"Found {len(parameters)} parameters for {program_name}"

    # Generate table
    param_rows = []
    for idx, param in enumerate(parameters[:50]):
        param_rows.append(f'''
            <tr>
              <td class="text-xs">{idx + 1}</td>
              <td class="text-xs font-mono">{escape_html(param['name'])}</td>
            </tr>''')

    table_html = f'''
    <div class="overflow-x-auto">
      <table class="table table-zebra table-sm w-full">
        <thead>
          <tr>
            <th class="text-xs">#</th>
            <th class="text-xs">Parameter Name</th>
          </tr>
        </thead>
        <tbody>
          {''.join(param_rows)}
        </tbody>
      </table>
      {f'<div class="text-xs text-center text-base-content/60 mt-2">Showing first 50 of {len(parameters)} parameters</div>' if len(parameters) > 50 else ''}
    </div>'''

    return {
        "header": f"{program_name} - Parameters",
        "summary": summary,
        "structuredData": table_html,
        "autoSelectProgram": {"programName": program_name, "servicer": servicer} if program_name and servicer else None
    }


def parse_parameter_value(results: str, query: str) -> Dict:
    """Parse parameter value results and generate cards with formatted text."""
    lines = results.split('\n')

    # Extract parameter name and servicer
    param_name = ''
    servicer = ''
    selected_count = 0

    for line in lines:
        if 'PARAMETER:' in line:
            param_name = line.split('PARAMETER:')[1].strip()
        if 'Loan Servicer:' in line:
            servicer = line.split('Loan Servicer:')[1].strip()
        if 'Filtered by Selected Programs:' in line:
            selected_count = int(line.split(':')[1].strip())

    # Parse program-value pairs
    program_values = []
    current_program = ''

    for i, line in enumerate(lines):
        trimmed_line = line.strip()

        # Skip headers and separators
        if not trimmed_line or trimmed_line.startswith('=') or 'PARAMETER:' in trimmed_line or \
           'Loan Servicer:' in trimmed_line or 'Filtered by' in trimmed_line:
            continue

        # Check if this is a program name (not indented)
        if not line.startswith(' ') and not line.startswith('\t') and not trimmed_line.startswith('>') and ':' not in trimmed_line:
            current_program = trimmed_line
        # Check if this is a value (indented or starts with >)
        elif current_program and (line.startswith(' ') or line.startswith('\t') or trimmed_line.startswith('>')):
            value = trimmed_line
            if value and value != '(not specified)':
                program_values.append({
                    'program': current_program,
                    'value': value
                })
            elif value == '(not specified)':
                program_values.append({
                    'program': current_program,
                    'value': 'Not specified'
                })
            current_program = ''

    # Generate summary
    display_param = param_name.replace('_', ' ').title()
    context_msg = f" (filtered by {selected_count} selected)" if selected_count > 0 else ""
    summary = f"Found {display_param} values for {len(program_values)} programs in {servicer}{context_msg}"

    # Fetch program details from database to get metrics
    engine = query_engine.get_query_engine()
    program_names = [item['program'] for item in program_values]
    program_details = engine.fetch_program_details(program_names, servicer)

    # Get formatter for converting technical expressions to English
    formatter = text_formatter.get_formatter()

    # Generate program cards with formatted parameter values
    program_cards = []
    for item in program_values:
        program_name = item['program']
        raw_value = item['value']
        details = program_details.get(program_name, {})

        # Pre-escape values for JavaScript
        program_escaped = escape_html(program_name).replace("'", "\\'")
        servicer_escaped = escape_html(servicer).replace("'", "\\'")
        program_key = f"{servicer}::{program_name}"

        # Format the parameter value using Anthropic API
        if raw_value and raw_value != 'Not specified':
            formatted_value = formatter.format_parameter_value(raw_value, param_name, program_name)
        else:
            formatted_value = 'Not specified'

        # Generate chips for key metrics - Order: Loan Amount, Credit, LTV, DTI
        chips_html = []

        # Loan Amount - extract maximum value (FIRST)
        if details.get('loan_amount'):
            loan = details['loan_amount']
            amounts = re.findall(r'\$?[\d,]+', loan)
            if amounts:
                max_amount = max([int(a.replace('$', '').replace(',', '')) for a in amounts if a.replace('$', '').replace(',', '').isdigit()])
                chips_html.append(f'<span class="badge badge-sm bg-green-100 text-green-800 border-0">Max Loan: ${max_amount:,}</span>')

        # Credit Score - extract minimum value (SECOND)
        if details.get('borrower_credit_score'):
            credit = details['borrower_credit_score']
            match = re.search(r'\d{3}', credit)
            if match:
                chips_html.append(f'<span class="badge badge-sm bg-blue-100 text-blue-800 border-0">Min Credit: {match.group()}</span>')

        # LTV - extract maximum percentage (THIRD)
        if details.get('ltv'):
            ltv = details['ltv']
            percentages = re.findall(r'(\d+)%', ltv)
            if percentages:
                max_ltv = max([int(p) for p in percentages])
                chips_html.append(f'<span class="badge badge-sm bg-purple-100 text-purple-800 border-0">Max LTV: {max_ltv}%</span>')

        # DTI - extract maximum percentage (FOURTH)
        if details.get('dti'):
            dti = details['dti']
            percentages = re.findall(r'(\d+)%', dti)
            if percentages:
                max_dti = max([int(p) for p in percentages])
                chips_html.append(f'<span class="badge badge-sm bg-orange-100 text-orange-800 border-0">Max DTI: {max_dti}%</span>')

        # Add parameter badge as well
        chips_html.insert(0, f'<span class="badge badge-sm bg-indigo-100 text-indigo-800 border-0">{escape_html(display_param)}</span>')

        card_html = f'''
    <div class="card bg-base-100 border border-base-300 mb-3 hover:shadow-lg transition-all cursor-pointer"
         data-program-key="{escape_html(program_key)}"
         onclick="window.appFunctions.toggleProgramSelection('{program_escaped}', '{servicer_escaped}')">
      <div class="card-body p-3 flex flex-col">
        <!-- Metrics Row (ABOVE program name) -->
        <div class="flex justify-between items-center mb-2">
          <div class="flex flex-wrap gap-1">
            {''.join(chips_html)}
          </div>
          <input type="checkbox" class="checkbox checkbox-sm checkbox-primary pointer-events-none" />
        </div>

        <!-- Program Name Row -->
        <div class="mb-2">
          <h3 class="text-sm font-bold mb-0.5">{escape_html(program_name)}</h3>
          <div class="text-[10px] text-base-content/60">Servicer: {servicer}</div>
        </div>

        <!-- Formatted Parameter Value -->
        <div class="text-xs text-base-content/70 leading-relaxed mb-2 flex-1 overflow-auto" style="max-height: 120px;">
          {escape_html(formatted_value)}
        </div>

        <!-- Icons for additional parameters -->
        <div class="flex gap-1.5 mt-auto border-t border-base-300 pt-1.5">
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'occupancy')"
                title="Occupancy">home</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'transaction')"
                title="Transaction Type">sync_alt</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'reserves')"
                title="Reserves">account_balance</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'documentation')"
                title="Documentation">description</span>
          <span class="material-icons-outlined text-base-content/40 hover:text-primary cursor-help text-xs"
                onclick="event.stopPropagation(); showParamDetail('{program_escaped}', 'citizenship')"
                title="Citizenship">flag</span>
        </div>
      </div>
    </div>'''

        program_cards.append(card_html)

    structured_data = ''.join(program_cards) if program_cards else \
        '<div class="text-center text-base-content/60 py-8">No parameter values found</div>'

    return {
        "header": f"{display_param} - {servicer}",
        "summary": summary,
        "structuredData": structured_data
    }


def parse_generic_results(results: str, query: str) -> Dict:
    """Parse generic results as pre-formatted text."""
    lines = [line for line in results.split('\n') if line.strip()]
    summary = ' '.join(lines[:3])[:200]
    if len(results) > 200:
        summary += '...'

    return {
        "header": "Query Results",
        "summary": summary,
        "structuredData": f'<pre class="text-xs font-mono overflow-x-auto bg-base-200 p-4 rounded">{escape_html(results)}</pre>'
    }
