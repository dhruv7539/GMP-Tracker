from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from jinja2 import Template
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

app = FastAPI()

# Scrape GMP data
def scrape_gmp_data():
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
        return pd.DataFrame(columns=["IPO", "Est Listing (%)", "IPO Size", "Open", "Close", "BoA Dt", "Listing", "GMP Updated"])

    rows = table.find_all("tr")
    data = []
    headers = [header.text.strip() for header in rows[0].find_all("th")]
    
    for row in rows[1:]:
        cells = row.find_all("td")
        row_data = []
        for cell in cells:
            if cell.get("data-label") == "IPO":
                ipo_name = cell.find("a").contents[0].strip()
                row_data.append(ipo_name)
            else:
                row_data.append(cell.text.strip())
        data.append(row_data)

    df = pd.DataFrame(data, columns=headers)
    df = df.drop(columns=["GMP(â¹)", "Lot", "Price", "Fire Rating"], errors='ignore')
    df["Est Listing"] = df["Est Listing"].str.extract(r'\((.*?)\)')
    df = df.rename(columns={"Est Listing": "Est Listing (%)"})

    def convert_date_format(date_str):
        match = re.match(r'([0-9]{1,2})-([A-Za-z]{3})', date_str)
        if match:
            day = match.group(1).zfill(2)
            month = str(pd.to_datetime(match.group(2), format='%b').month).zfill(2)
            return f"{day}/{month}"
        return date_str

    date_columns = ["Open", "Close", "BoA Dt", "Listing"]
    for col in date_columns:
        df[col] = df[col].apply(convert_date_format)
    df["GMP Updated"] = df["GMP Updated"].str.replace(r'([0-9]{1,2})-([A-Za-z]{3})\s[0-9]{2}:[0-9]{2}', lambda m: convert_date_format(m.group(0).split()[0]), regex=True)

    def format_est_listing(val):
        try:
            percentage = float(val.replace('%', ''))
            return f'<div class="est-listing" style="width: {percentage}%; background-color: #76c893; color: black; padding: 5px; border-radius: 4px; text-align: center;">{percentage}%</div>'
        except:
            return val

    df["Est Listing (%)"] = df["Est Listing (%)"].apply(format_est_listing)

    return df

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h1>Test Page - It works!</h1>"


# def home():
    ipo_df = scrape_gmp_data()
    ipo_html_table = ipo_df.to_html(classes='table table-hover table-custom w-100', index=False, escape=False)

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/5.1.3/css/bootstrap.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600&display=swap" rel="stylesheet">
        <title>Current IPO GMP</title>
        <style>
            body {
                background: linear-gradient(135deg, #d3d6df, #e6e9ef);
                font-family: 'Nunito', sans-serif;
            }
            .container {
                max-width: 100%;
                margin-top: 50px;
                padding: 30px;
                background: linear-gradient(135deg, #f7f8fa, #e9ebf0);
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            }
            h1 {
                font-size: 2.5rem;
                font-weight: 600;
                color: #4a4a4a;
                margin-bottom: 30px;
                text-align: center;
            }
            .table-custom {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                border-radius: 12px;
                overflow: hidden;
            }
            .table-custom thead th {
                background-color: #b0b3b8;
                color: #ffffff;
                font-weight: 500;
                padding: 20px;
                text-align: left;
            }
            .table-custom tbody td {
                padding: 15px;
                font-size: 1rem;
                color: #5a5a5a;
            }
            .table-custom tbody tr:nth-child(even) {
                background-color: #f0f1f3;
            }
            .table-custom tbody tr:hover {
                background-color: #e2e4e8;
            }
            .est-listing {
                display: inline-block;
                height: 20px;
                border-radius: 4px;
                background-color: #76c893;
                color: black;
                text-align: center;
                padding: 5px;
                font-weight: bold;
            }
            @media (max-width: 768px) {
                h1 {
                    font-size: 2rem;
                }
                .container {
                    padding: 20px;
                }
                .table-custom tbody td {
                    padding: 10px;
                    font-size: 0.9rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Current & Upcoming IPO GMP</h1>
            <div class="table-container">
                {{ table|safe }}
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

    # Using Jinja2 templating with FastAPI
    template = Template(html_template)
    rendered_html = template.render(table=ipo_html_table)
    
    return HTMLResponse(content=rendered_html)

