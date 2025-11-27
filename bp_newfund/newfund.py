from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify
import sqlite3
import openai
from config import conf
from shared import get_coding_systems, get_all_funds, import_whole_nav

bp_newfund = Blueprint('bp_newfund', __name__)


PROMPT_DETAILS_FROM_NAME = f"""
Please provide the ISIN (International Securities Identification Number) and Japanese market code (市場コード) for the following Japanese investment fund:

Fund Name: %%FUND_NAME%%

Please respond in JSON format with the following structure:
{{
    "isin": "the ISIN code if found",
    "market_code": "the Japanese market code (市場コード) if found",
    "confidence": "high/medium/low based on how certain you are",
    "notes": "any additional notes or warnings about the information"
}}

If you cannot find the information, please set the values to null and explain in the notes field.
"""

@bp_newfund.route('/funds/register', methods=['GET'])
def register_fund_form():
    codingsys = get_coding_systems()

    return render_template('register_fund.html', coding_systems=codingsys, prompt=PROMPT_DETAILS_FROM_NAME)

#For the POST method
@bp_newfund.route('/funds/register', methods=['POST'])
def register_fund():
    name = request.form.get('name')
    currency = request.form.get('currency')
    if not name or not name.strip():
        flash('Fund name cannot be empty.', 'error')
        return redirect(url_for('bp_newfund.register_fund_form'))
    if not currency:
        flash('Currency is required to register a fund.', 'error')
        return redirect(url_for('bp_newfund.register_fund_form'))
    

    conn = sqlite3.connect(conf['DB_PATH'])
    cur = conn.cursor()
    try:
        # Check if fund name already exists
        cur.execute('SELECT FundID FROM FUND WHERE Name = ?', (name.strip(),))
        if cur.fetchone():
            flash(f'Fund name "{name}" already exists. Please choose a unique name.', 'error')
            conn.close()
            return redirect(url_for('bp_newfund.register_fund_form'))
        # Insert new fund
        cur.execute('INSERT INTO FUND (Name, Currency) VALUES (?, ?)', (name.strip(), currency.upper()))

        #check that the fund was properly inserted
        cur.execute("SELECT FundID FROM FUND WHERE Name = ? AND Currency = ?", (name.strip(), currency.upper()))
        row = cur.fetchone()
        if row is None:
            flash(f'Error: Fund {name} was not inserted properly.', 'error')
            conn.close()
            return redirect(url_for('bp_newfund.register_fund_form'))
        else:
            fund_id = row[0]

        #register the coding system if provided
        codingsys = get_coding_systems()
        for code in codingsys:
            code_value = request.form.get(f'coding_system_{code[0]}')
            if code_value:
                cur.execute('INSERT INTO FUND_CODE (FundID, System, Code) VALUES (?, ?, ?)', (fund_id, code[0], code_value.strip()))

        #ZA final commit
        conn.commit()

        #fund is registered successfully, get the historical prices
        funds_list = get_all_funds(forced_reload=True)  # Refresh fund list cache

        new_fund = [f for f in funds_list if f.fund_id == int(fund_id)]
        if new_fund:
            #get all the NAV data for this fund from Asset manager assoc
            import_whole_nav(new_fund[0])

        flash(f'Fund {name} (ID: {fund_id}) registered successfully.', 'success')
        
        #redirect to register transaction for this fund
        return redirect(url_for('bp_transactions.register_transaction_form'))
    except Exception as e:
        flash(f'Error registering fund: {e}', 'error')
    finally:
        conn.close()


    return redirect(url_for('show_funds_page'))


@bp_newfund.route('/funds/search_fund_info', methods=['POST'])
def search_fund_info():
    """Search for fund ISIN and market code using ChatGPT"""
    
    fund_name = request.json.get('fund_name', '').strip()
    if not fund_name:
        return jsonify({'error': 'Fund name is required'}), 400
    
    # Check if OpenAI API key is configured
    if not conf.openai_api_key:
        return jsonify({'error': 'OpenAI API key not configured. Please set it in the admin panel.'}), 400
    
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=conf.openai_api_key)
        
        # Create the prompt for ChatGPT
        prompt = PROMPT_DETAILS_FROM_NAME.replace("%%FUND_NAME%%", fund_name)
        
        # Make the API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides accurate financial information about Japanese investment funds. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        # Parse the response
        result_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        import json
        try:
            # Sometimes ChatGPT wraps JSON in code blocks, so we need to extract it
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            
            result = json.loads(result_text)
            return jsonify(result)
            
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw text
            return jsonify({
                'isin': None,
                'market_code': None,
                'confidence': 'low',
                'notes': f'Could not parse ChatGPT response: {result_text}'
            })
            
    except Exception as e:
        return jsonify({'error': f'Error calling ChatGPT: {str(e)}'}), 500
