# FundManagerCompanion
A web app to help you keep track of your funds investments and performance

## Concept
I want to be able to keep track of when I invested on funds, and see the compound performance of the funds. Today my fund management site gives me a number and that's it.

# Quotations API
Mutual Funds have a price daily (NAV Net Asset Value) published at market closure at end of day (except ETF I know). Getting consistently prices from all of them will be a chore since I don't plan to pay for an API provider. 

## MUFG Funds
Bravo guys, you have a free API that does not require registration!😍 WOW. Just WOW.
- RTFM https://www.am.mufg.jp/tool/webapi/
- Sample: `https://developer.am.mufg.jp/fund_information_latest/association_fund_cd/03311112` returns a nice JSON with latest details for their 三菱ＵＦＪ 純金ファンド
- You have latest NAV, ISIN, etc.

To find the "association fund code", search by name on Yahoo Finance (https://finance.yahoo.co.jp), that's the number.

## The rest of the Asset managers
... do rarely have an API, always a page (regulatory) but not the easiest to parse.

Seems that the Nikkei Journal has a page with all needed, no paywall, and parseable (in beautitulSoup we trust).
See `https://www.nikkei.com/nkd/fund/?fcode=0131106B` or `https://www.nikkei.com/nkd/fund/?fcode=03311112` (same fund as above) BUT THE PRICES ARE DELAYED (now 21:30 and still D-1 prices)

Also Yahoo Finance is similar with `https://finance.yahoo.co.jp/quote/0131106B` and `https://finance.yahoo.co.jp/quote/03311112` (same fund as above) AND PRICES SEEM LATEST (at 21:30 I'm seeing day D closure prices)

# Financial indicators

## Fund NAV return
Simplest performance calculation:

(NAV end - NAV start) / Nav Start * 100%

## Fund NAV Total return
Better, including the dividends paid by fund:

((NAV end - NAV start) + Dividends paid over period) / Nav Start * 100%

## Fund NAV Total Excess return
Even better, including the dividends paid by fund minus the risk free interest rate:

(((NAV end - NAV start) + Dividends paid over period) / Nav Start * 100%) - Risk Free Interest rate

