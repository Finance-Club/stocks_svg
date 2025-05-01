#!/usr/bin/env python3
import sys
import os
import time
import random
import yfinance as yf
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timedelta

def create_svg(data, symbol):
    """Create the SVG with animations and styling."""
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

    prices = data['Close'].values
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

    # Add stock symbol and current price
    current_price = prices[-1]
    previous_price = prices[0]
    percent_change = ((current_price - previous_price) / previous_price) * 100
    
    # Symbol text
    symbol_text = SubElement(svg, 'text',
                          x=str(margin), y=str(margin / 2),
                          fill="white",
                          opacity="0",
                          **{'font-size': "16", 'font-weight': 'bold', 'text-anchor': 'start', 'font-family': 'Arial'})
    symbol_text.text = symbol
    SubElement(symbol_text, 'animate',
               attributeName="opacity",
               from_="0", to="1",
               dur="0.5s",
               begin="0.5s",
               fill="freeze")
               
    # Price text
    price_color = "rgb(46, 213, 115)" if percent_change >= 0 else "rgb(255, 71, 87)"
    price_text = SubElement(svg, 'text',
                         x=str(size - margin), y=str(margin / 2),
                         fill=price_color,
                         opacity="0",
                         **{'font-size': "14", 'font-weight': 'bold', 'text-anchor': 'end', 'font-family': 'Arial'})
    price_text.text = f"{current_price:.2f} ({percent_change:+.2f}%)"
    SubElement(price_text, 'animate',
              attributeName="opacity",
              from_="0", to="1",
              dur="0.5s",
              begin="1s",
              fill="freeze")

    # Pretty print SVG
    rough_string = tostring(svg, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def create_error_svg(symbol, error_message):
    """Create a fallback SVG with error message when data fetching fails."""
    size = 500
    
    svg = Element('svg',
                  width=str(size),
                  height=str(size),
                  xmlns="http://www.w3.org/2000/svg",
                  style="background-color: #111111")
    
    # Add symbol text
    symbol_text = SubElement(svg, 'text',
                          x=str(size//2), y="100",
                          fill="white",
                          **{'font-size': "24", 'font-weight': 'bold', 'text-anchor': 'middle', 'font-family': 'Arial'})
    symbol_text.text = symbol
    
    # Error message
    error_text = SubElement(svg, 'text',
                         x=str(size//2), y="150",
                         fill="rgb(255, 71, 87)",
                         **{'font-size': "16", 'text-anchor': 'middle', 'font-family': 'Arial'})
    error_text.text = "Error: Unable to fetch data"
    
    # Additional info
    info_text = SubElement(svg, 'text',
                        x=str(size//2), y="180",
                        fill="rgba(255,255,255,0.5)",
                        **{'font-size': "12", 'text-anchor': 'middle', 'font-family': 'Arial'})
    info_text.text = str(error_message)
    
    # Placeholder dash line in the center
    dashed_line = SubElement(svg, 'path',
                           d=f"M 100,{size//2} L {size-100},{size//2}",
                           stroke="rgba(255,255,255,0.2)",
                           fill="none",
                           **{'stroke-width': "2", 'stroke-dasharray': "10,10"})
    
    # Pretty print SVG
    rough_string = tostring(svg, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def generate_stock_svg(ticker_symbol):
    """Generate an SVG chart for the given stock ticker."""
    
    print(f"📈 Fetching data for {ticker_symbol}...")
    
    # Add retry mechanism for rate limiting
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            # Download stock data (5-day period, 1-day interval)
            data = yf.download(ticker_symbol, period="5d", interval="1d", progress=False)
            
            if data.empty or len(data) < 2:  # Ensure we have at least 2 data points
                print(f"❌ Error for {ticker_symbol}: Not enough data points to plot {ticker_symbol}")
                create_fallback = True
                error_msg = "Not enough data points"
                break
                
            print(f"🎨 Generating SVG for {ticker_symbol}...")
            # Create SVG
            svg_content = create_svg(data, ticker_symbol)
            create_fallback = False
            break  # Success, exit retry loop
            
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1}/{max_retries} failed for {ticker_symbol}: {str(e)}")
            if attempt < max_retries - 1:
                # Add some jitter to the delay to avoid synchronized retries
                jitter = random.uniform(0.5, 1.5)
                sleep_time = retry_delay * jitter
                print(f"⏱️ Waiting {sleep_time:.1f} seconds before retrying...")
                time.sleep(sleep_time)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"❌ Failed download:\n['{ticker_symbol}']: {str(e)}")
                create_fallback = True
                error_msg = str(e)
    
    # Create output directory if it doesn't exist
    os.makedirs("svgs", exist_ok=True)
    
    # Save the SVG file
    svg_file = f"svgs/{ticker_symbol}.svg"
    
    if create_fallback:
        # Create error SVG if needed
        svg_content = create_error_svg(ticker_symbol, error_msg)
        print(f"⚠️ Generated error SVG for {ticker_symbol} at {svg_file}")
    else:
        print(f"✅ Generated SVG for {ticker_symbol} at {svg_file}")
    
    with open(svg_file, "w") as f:
        f.write(svg_content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_svgs.py TICKER_SYMBOL")
        
        # Alternative: Read from stocks.txt if it exists
        if os.path.exists("stocks.txt"):
            print("🔄 Reading stock symbols from stocks.txt...")
            with open("stocks.txt") as f:
                stocks = f.readlines()
            stocks = [stock.strip() for stock in stocks if stock.strip()]
            
            # Process each stock symbol
            for stock in stocks:
                generate_stock_svg(stock)
                time.sleep(5)  # Wait between requests to avoid rate limiting
        
        sys.exit(1)
    
    ticker_symbol = sys.argv[1]
    
    # Add delay between job runs to avoid rate limiting
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        # Only sleep if we're running in GitHub Actions
        random_delay = random.uniform(1, 5)
        print(f"⏱️ Adding initial delay of {random_delay:.1f}s to avoid rate limiting...")
        time.sleep(random_delay)
    
    generate_stock_svg(ticker_symbol)
