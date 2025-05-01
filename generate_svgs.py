import yfinance as yf
import datetime
import os

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# Configuration
OUTPUT_DIR = "static/img/"
DAYS_TO_FETCH = 7
STOCK_SYMBOLS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "HINDUNILVR.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "ASIANPAINT.NS",
    "BAJFINANCE.NS"
]

def fetch_stock_data(symbol, days):
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days)
    data = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
    return data['Close']

def create_svg(data, symbol):
    size = 500
    margin = 50

    svg = Element('svg',
                  width=str(size),
                  height=str(size),
                  xmlns="http://www.w3.org/2000/svg",
                  style="background-color: #111111")

    # Gradient and filter defs
    defs = SubElement(svg, 'defs')

    gradient = SubElement(defs, 'linearGradient', id='lineGradient', x1='0%', y1='0%', x2='0%', y2='100%')
    SubElement(gradient, 'stop', offset='0%', style='stop-color:rgba(255,255,255,0.5);stop-opacity:1')
    SubElement(gradient, 'stop', offset='100%', style='stop-color:rgba(255,255,255,0.2);stop-opacity:1')

    filter_effect = SubElement(defs, 'filter', id='glow')
    SubElement(filter_effect, 'feGaussianBlur', stdDeviation="3", result="coloredBlur")
    fe_merge = SubElement(filter_effect, 'feMerge')
    SubElement(fe_merge, 'feMergeNode', in_="coloredBlur")
    SubElement(fe_merge, 'feMergeNode', in_="SourceGraphic")

    prices = data.values
    dates = data.index.strftime('%m-%d').tolist()
    n = len(prices)

    if n < 2:
        raise ValueError(f"Not enough data points to plot {symbol}")

    max_price = float(prices.max())
    min_price = float(prices.min())
    padding = (max_price - min_price) * 0.1 or 1
    max_price += padding
    min_price -= padding
    price_range = max_price - min_price

    def scale_x(i):
        return round(margin + i * (size - 2 * margin) / (n - 1))

    def scale_y(p):
        return round(size - margin - ((float(p) - min_price) * (size - 2 * margin) / price_range))

    # Grid lines
    num_grid_lines = 5
    for i in range(num_grid_lines):
        y = margin + i * (size - 2 * margin) / (num_grid_lines - 1)
        price = max_price - (i * price_range / (num_grid_lines - 1))
        SubElement(svg, 'line',
                   x1=str(margin), y1=str(y),
                   x2=str(size - margin), y2=str(y),
                   stroke="rgba(255,255,255,0.1)",
                   **{'stroke-width': "0.5"})

        text = SubElement(svg, 'text',
                          x=str(margin - 10), y=str(y + 4),
                          fill="rgba(255,255,255,0.5)",
                          opacity="0",
                          **{'font-size': "11", 'text-anchor': "end", 'font-family': 'Arial'})
        text.text = f"{price:,.0f}"
        SubElement(text, 'animate',
                   attributeName="opacity",
                   from_="0", to="1",
                   dur="0.5s",
                   begin="2s",
                   fill="freeze")

    # Line path
    points = [(scale_x(i), scale_y(p)) for i, p in enumerate(prices)]
    path_d = f"M {points[0][0]},{points[0][1]}"
    for i in range(1, n):
        x1, y1 = points[i - 1]
        x2, y2 = points[i]
        cx = (x1 + x2) / 2
        path_d += f" C {cx},{y1} {cx},{y2} {x2},{y2}"

    path = SubElement(svg, 'path',
                      d=path_d,
                      fill="none",
                      stroke="url(#lineGradient)",
                      **{'stroke-width': "2", 'stroke-linecap': "round", 'stroke-linejoin': "round"})

    SubElement(path, 'animate',
               attributeName="stroke-dasharray",
               from_=f"{size*3} {size*3}",
               to="0 0",
               dur="2s",
               fill="freeze")

    for i, p in enumerate(prices):
        cx, cy = scale_x(i), scale_y(p)

        ripple = SubElement(svg, 'circle',
                            cx=str(cx), cy=str(cy),
                            r="2",
                            fill="none",
                            stroke="rgba(255,255,255,0.3)",
                            **{'stroke-width': "1"})
        SubElement(ripple, 'animate',
                   attributeName="r",
                   values="2;8",
                   dur="1.5s",
                   begin="2s",
                   repeatCount="indefinite")
        SubElement(ripple, 'animate',
                   attributeName="opacity",
                   values="0.3;0",
                   dur="1.5s",
                   begin="2s",
                   repeatCount="indefinite")

        point = SubElement(svg, 'circle',
                           cx=str(cx), cy=str(cy),
                           r="3",
                           fill="white",
                           opacity="0")
        SubElement(point, 'animate',
                   attributeName="opacity",
                   from_="0", to="1",
                   dur="0.3s",
                   begin="2s",
                   fill="freeze")

    # Date labels
    for i, date in enumerate(dates):
        if i % max(1, n // 5) == 0 or i == n - 1:
            x = scale_x(i)
            y = size - margin / 2
            text = SubElement(svg, 'text',
                              x=str(x), y=str(y),
                              fill="rgba(255,255,255,0.5)",
                              opacity="0",
                              **{'font-size': "11", 'text-anchor': 'middle', 'font-family': 'Arial'})
            text.text = date
            SubElement(text, 'animate',
                       attributeName="opacity",
                       from_="0", to="1",
                       dur="0.5s",
                       begin="2s",
                       fill="freeze")

    # Pretty print SVG
    rough_string = tostring(svg, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def save_svg(content, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w') as f:
        f.write(content)
    print(f"✅ Saved: {path}")

def main():
    for symbol in STOCK_SYMBOLS:
        try:
            print(f"📈 Fetching data for {symbol}...")
            data = fetch_stock_data(symbol, DAYS_TO_FETCH)
            print(f"🎨 Generating SVG for {symbol}...")
            svg_content = create_svg(data, symbol)
            svg_filename = f"{symbol.replace('.NS','').lower()}_stock.svg"
            save_svg(svg_content, svg_filename)
        except Exception as e:
            print(f"❌ Error for {symbol}: {e}")

if __name__ == "__main__":
    main()
