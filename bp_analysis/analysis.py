from flask import  flash, render_template, request, Blueprint, send_file, redirect, url_for
from shared import get_all_funds, get_overall_stats
from datetime import datetime
from fund import Fund

from config import conf

bp_analysis = Blueprint('bp_analysis', __name__)


def get_ai_prompt():
    prompt = """Below is a table with the name of the funds I invested in. 
First column is the name of the fund, second column is the ISIN, third column is the Yahoo Finance (also 投資信託協会) code, the fourth column is the number of units I hold, and the fifth is the latest NAV for 10,000 units.
My investment strategy is long term investment with a yearly target return of 10%. I can tolerate a loss of 5% yearly exceptionally.
I prefer to limit my exposure to the US market, and prefer to focus on Europe or Asia (Japan and Korea as preferences). This is a general guideline and not a hard rule.

First, what can you tell me about my investment? 
Secondly, what adjustments should I make to my current portfolio to better align with my investment goals and risk tolerance? Highlight me the 3 funds you'd recommend me to close and why.
Then, considering my investment goal and risk appetite, suggest me 3 funds that are available on Monex.co.jp platform and NISA eligible that I should consider investing in.


"""

    for fund in get_all_funds():
        if fund.latest_units == 0:
            continue
        prompt += f"{fund.name}\t{fund.codes['ISIN'] if 'ISIN' in fund.codes else ''}\t{fund.codes['yahoo_finance'] if 'yahoo_finance' in fund.codes else ''}\t{fund.latest_units}\t{int(fund.latest_nav) if fund.latest_nav else 'n/a'}\n"

    return prompt

@bp_analysis.route('/analysis', methods=['GET'])
def analysis_page():
    funds = get_all_funds()
    stats = get_overall_stats()

    for fund in funds:
        fund.get_fund_nav(5)  # Fetch only the latest NAV for each fund


    # Filter out funds without holdings
    funds = [f for f in funds if f.latest_units > 0]

    #sort by 1Y return, with those missing the stat at the bottom
    funds = sorted(funds, key=lambda f: f.stats["return_1y"] if "return_1y" in f.stats else float('-inf'), reverse=True) 

    return render_template('analysis.html', funds=funds, stats=stats, conf=conf, ai_prompt=get_ai_prompt())