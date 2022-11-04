# tampon VAT effect evaluator

# (c) Dan Neidle of Tax Policy Associates Ltd
# licensed under the GNU General Public License, version 2

# all ONS data from https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/consumerpriceindicescpiandretailpricesindexrpiitemindicesandpricequotes
# note data can't be scraped from website, as filename changes unpredictably, so instead files should be downloaded
# and names conformed

import os
import statistics
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import datetime
from PIL import Image


dates = []
prices_on_date = {}

# these can be taken from column C of the spreadsheet
# I have added cotton products and toiletries
items_to_find = ["TISSUES-LARGE SIZE BOX", "DISP NAPPIES, SPEC TYPE, 20-60",
                  "PLASTERS-20-40 PACK", "BABY WIPES 50-85", "WOMENS BASIC PLAIN T-SHIRT", "TOILET ROLLS",
                  "KITCHEN ROLL PK OF 2-4 SPECIFY", "SHEET OF WRAPPING PAPER", "MEN'S T-SHIRT SHORT SLEEVED",
                  "BOYS T-SHIRT 3-13 YEARS", "TOOTHPASTE (SPECIFY SIZE)", "RAZOR CARTRIDGE BLADES", "TOOTHBRUSH"]

items_to_find.sort()  # nice to put them in alphabetical order
items_to_find.insert(0,"TAMPONS-PACK OF 10-20") # and then put tampons first

# create lists for each item
for x in items_to_find:
    prices_on_date[x] = []

# get list of all available dates - scraping all "upload-itemindices" csv files in ONS_data directory
for filename in os.listdir('ONS_data'):
    if "upload-itemindices" not in filename:
        continue
    date = filename.replace("upload-itemindices","").replace(".csv","")
    month = int(date[4:])
    year = int(date[:-2])
    dates.append(datetime.datetime(year=year, month=month, day=1))

# now sort the dates
dates.sort()

# extract CPI data
print("Reading CPI data")
cpi_data = pd.read_csv(f"ONS_data/CPI.csv")

cpi = []
for x in dates:
    for cpi_index, cpi_row in cpi_data.iterrows():
        if cpi_row["Month"] == (str(x.year) + " " + x.strftime("%b").upper()):
            cpi.append(cpi_row["Index"])
            break

# check that we found CPI data for each date
if len (dates) != len (cpi):
    print("Error - missing CPI")
    exit()

print(f"CPI data: {cpi}")

# now reading all the ONS data in
for x in dates:
    print(f"Reading ONS data for {x.month}/{x.year}...")

    df = pd.read_csv(f"ONS_data/upload-itemindices{x.year}{x.month:02d}.csv")

    prices_found = {}
    for index, row in df.iterrows():
        # search for each of the specific items
        for target in prices_on_date:
            if row["ITEM_DESC"] == target:
                prices_found[target] = row["ALL_GM_INDEX"]
                prices_on_date[target].append(row["ALL_GM_INDEX"])    # this is CPI
                break

    print(f"{x.month}/{x.year}:  {prices_found}")

# normalise data to Jan 2021
normalising_target_date = datetime.datetime(year=2020, month=12, day=1)
index_for_31_dec_2020 = dates.index(normalising_target_date)

cpi = [float(i)/cpi[index_for_31_dec_2020] for i in cpi]
for x in prices_on_date:
    prices_on_date[x] = [float(i) / prices_on_date[x][index_for_31_dec_2020] for i in prices_on_date[x]]

# Print out tampon data for e.g. import into excel
human_dates = []
for x in dates:
    human_dates.append(x.strftime("%d/%m/%Y"))

print("")
print("Final data for export to Excel:")
print('Date, ' + str(human_dates).replace("\'", "").replace("[", "").replace("]", ""))

for x in prices_on_date:
    print(x.replace(",", "").replace(" ", "_") + ", " + str(prices_on_date[x]).replace("[", "").replace("]", ""))


# for each item, calculate change in average price before/after 1 Jan
change_in_average_price = []
for item in prices_on_date:
    prior_average = statistics.mean(prices_on_date[item][:index_for_31_dec_2020 + 1])
    subsequent_average = statistics.mean(prices_on_date[item][index_for_31_dec_2020 + 1:])
    change_in_average_price.append(subsequent_average - prior_average)

# sort in order of price change
sorted_items = [x for _,x in sorted(zip(change_in_average_price, items_to_find))]
change_in_average_price.sort()

# grab logo
logo_jpg = Image.open("logo_full_white_on_blue.jpg")
logo_layout = [dict(
        source=logo_jpg,
        xref="paper", yref="paper",
        x=1, y=1.03,
        sizex=0.1, sizey=0.1,
        xanchor="right", yanchor="bottom"
    )]


# now plot it

fig_change = make_subplots(specs=[[{"secondary_y": False}]])

fig_change.update_layout(
    images=logo_layout,
    title="The 5% tampon VAT cut - change in average price of items from September 2019 to March 2022",
    yaxis=dict(
        title="% change",
        tickformat='.0%',  # so we get nice percentages
    ),

    )

fig_change.add_trace(go.Bar(
        x=[x.capitalize() for x in sorted_items],
        y=change_in_average_price
    ))

fig_change.show()

# now plot price movements

fig_prices = make_subplots(specs=[[{"secondary_y": False}]])
fig_prices.update_layout(
    images=logo_layout,
    title="The 5% tampon VAT cut - ONS index changes for tampons and related consumer goods, normalised to Dec 2020",
    yaxis=dict(
        title="Relative prices",
        tickformat='.0%',  # so we get nice percentages
    ),
    xaxis=dict(
            range=(min(dates), max(dates)),
            tick0=min(dates),
            dtick="M1",  # monthly x axis ticks
            tickformat='%b %Y'
        ),

    )

# plot a scatter for cpi and then each specified item
plots = [[cpi, "CPI"]]
for x in prices_on_date:
    plots.append([prices_on_date[x], x.capitalize()])

for plot in plots:

    # make the tampon plot visible immediately. the others only visible if clicked on
    if "tampon" in plot[1].lower():
        visibility = True
    else:
        visibility = 'legendonly'

    # dashed lines for tampon and cpi plots
    if "tampon" in plot[1].lower() or "CPI" in plot[1].lower():
        dash = "dash"
    else:
        dash = None

    fig_prices.add_trace(go.Scatter(
        x=dates,
        y=plot[0],
        mode="lines+text+markers",  # no markers
        line=dict(dash=dash),
        name=plot[1],
        showlegend=True,
        visible=visibility
    ),
        secondary_y=False)

    # now add line and annotation showing moment VAT was removed
    fig_prices.add_vline(x=datetime.datetime.strptime("2021-01-01", "%Y-%m-%d").timestamp() * 1000, line_dash="dot",
                  annotation_text="5% VAT on tampons abolished",
                  annotation_position="top right")

fig_prices.show()
