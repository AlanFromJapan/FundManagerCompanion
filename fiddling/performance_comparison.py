from datetime import datetime, timedelta
import sqlite3
import matplotlib.pyplot as plt


def absolute_perf_comparison():
    conn = sqlite3.connect("./../data/data.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
SELECT 
    NAV.*, F.name
FROM 
    FUND_NAV as NAV 
    JOIN FUND as F ON F.FundId = NAV.FundId

WHERE 
    1=1 

    ORDER BY AtDate DESC LIMIT 6000;
""")
        rows = cursor.fetchall()

        navs = {}
        for row in rows:
            date = row[1]

            if date not in navs:
                navs[date] = {}

            #fund_code = int(row[0])
            fund_code = str(row[4])
            nav = int(row[3])

            navs[date][fund_code] = {"NAV": nav}


        latest_date = min(navs.keys()) if navs else None

        #remove oldest date, may be incomplete due to arbitrary LIMIT in SQL query
        if latest_date:
            navs.pop(latest_date)

        #latest date after removing the oldest date
        latest_date = min(navs.keys()) if navs else None
        next_date = min((date for date in navs if date > latest_date), default=None) if latest_date else None

        while next_date:
            if latest_date not in navs or next_date not in navs:
                break

            for fund_code in navs[next_date]:
                nav_next = navs[next_date][fund_code]["NAV"]
                nav_latest = navs[latest_date].get(fund_code, {}).get("NAV")
                if nav_latest is not None:
                    navs[next_date][fund_code]["PerfAbs"] = nav_next - nav_latest

                    perf = (nav_next - nav_latest) / nav_latest  if nav_latest != 0 else None
                    navs[next_date][fund_code]["Perf%"] = perf

            # process the data for latest_date and next_date
            # update latest_date and next_date for the next iteration
            latest_date = next_date
            next_date = min((date for date in navs if date > latest_date), default=None) if latest_date else None
        

        #print
        # for date in sorted(navs.keys()):
        #     print(f"Date: {date}")
        #     for fund_code, data in navs[date].items():
        #         print(f"  Fund Code: {fund_code}, Data: {data}")


    finally:
        conn.close()

    return navs



def plot_absolute_perf_comparison(navs):

    values = {}

    for date in sorted(navs.keys()):
        for fund_code, data in navs[date].items():
            if "Perf%" in data:
                if fund_code not in values:
                    values[fund_code] = []
                values[fund_code].append((date, data["Perf%"]))

    for fund_code, perf_data in values.items():
        dates, perfs = zip(*perf_data)
        plt.plot(dates, perfs, label=f"Fund {fund_code}", linewidth=1)

    plt.xlabel("Date")
    plt.ylabel("Performance %")
    plt.title("Absolute Performance Comparison")
    #plt.legend()
    #plt.savefig("absolute_performance_comparison.png")
    plt.show()


def plot_normalized_perf_comparison(navs):

    values = {}

    for date in sorted(navs.keys()):
        for fund_code, data in navs[date].items():
            if "Perf%" in data:
                if fund_code not in values:
                    #add like started from 1
                    values[fund_code] = [(date, 1 + data["Perf%"])]
                else:
                    #find previous day value for this fund and add the current day's performance to it
                    prev_value = values[fund_code][-1][1]
                    values[fund_code].append((date, prev_value + data["Perf%"]))

    for fund_code in values:
        min_date = min(date for date, _ in values[fund_code])
        #previous date from a date as string
        min_date = datetime.strptime(min_date, "%Y-%m-%d")

        values[fund_code].insert(0, ((min_date - timedelta(days=1)).strftime("%Y-%m-%d"), 1.0))

    for fund_code, perf_data in values.items():
        dates, perfs = zip(*perf_data)
        plt.plot(dates, perfs, label=f"Fund {fund_code}", linewidth=1)

    #add a line for the 1.0
    plt.axhline(y=1.0, color='gray', linestyle='--', linewidth=1)

    plt.xlabel("Date")
    plt.ylabel("Normalized Performance")
    plt.title("Normalized Performance Comparison")
    plt.legend( loc="best", prop={'size': 6} )
    #plt.savefig("normalized_performance_comparison.png")
    plt.show()


if __name__ == "__main__":

    plt.rc("font", family="Noto Sans CJK JP")
    navs = absolute_perf_comparison()
    #plot_absolute_perf_comparison(navs)
    plot_normalized_perf_comparison(navs)