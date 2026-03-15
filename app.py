import streamlit as st
import re
from datetime import datetime, timedelta
from statistics import mean, median

# ────────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────────

def calculate_net(price: float) -> float:
    """Calculate net payout after fees based on sold price (StockX)."""
    if price < 57:
        return price * 0.97 - 8.5
    else:
        return price * 0.89 - 4


def get_target_roi(avg_days: float | None, num_sales: int, quick_roi: float, jogging_roi: float, slow_roi: float) -> float:
    """Determine target ROI % based on average days between sales and number of sales."""
    if avg_days is None:
        return slow_roi
    if num_sales >= 15 and avg_days <= 15:
        return quick_roi
    elif avg_days <= 15:
        return jogging_roi
    elif num_sales < 5 and avg_days > 15:
        return slow_roi
    else:
        return slow_roi


def parse_sales(raw_text: str) -> list[dict]:
    """Parse StockX-style sales data (mm/dd/yy)."""
    sales = []
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        date_time_match = re.search(r'(\d{2}/\d{2}/\d{2}), (\d{1,2}:\d{2} (?:AM|PM))', line)
        if date_time_match:
            try:
                date_str = date_time_match.group(1)
                time_str = date_time_match.group(2)
                dt_str = f"{date_str}, {time_str}"
                dt = datetime.strptime(dt_str, '%m/%d/%y, %I:%M %p')
                if dt > datetime.now():
                    dt = dt.replace(year=dt.year - 100)
                price = None
                for j in range(i, min(i + 6, len(lines))):
                    price_match = re.search(r'£\s*([\d,]+(?:\.\d{1,2})?)', lines[j])
                    if price_match:
                        price_str = price_match.group(1).replace(',', '')
                        price = float(price_str)
                        i = j
                        break
                if price is not None:
                    sales.append({'date': dt, 'price': price})
            except ValueError:
                pass
        i += 1
    return sales


def parse_uk_sales(raw_text: str) -> list[dict]:
    """Parse eBay / Alias sales (dd/mm/yy format)."""
    sales = []
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        date_match = re.search(r'(\d{2}/\d{2}/\d{2})', line)
        if date_match:
            try:
                date_str = date_match.group(1)
                dt = datetime.strptime(date_str, '%d/%m/%y')
                if dt > datetime.now():
                    dt = dt.replace(year=dt.year - 100)
                price = None
                for j in range(i, min(i + 6, len(lines))):
                    price_match = re.search(r'£\s*([\d,]+(?:\.\d{1,2})?)', lines[j])
                    if price_match:
                        price_str = price_match.group(1).replace(',', '')
                        price = float(price_str)
                        i = j
                        break
                if price is not None:
                    sales.append({'date': dt, 'price': price})
            except ValueError:
                pass
        i += 1
    return sales


def calculate_avg_days(sales_list: list[dict]) -> float | None:
    """Calculate average days between consecutive sales."""
    if len(sales_list) < 2:
        return None
    sorted_sales = sorted(sales_list, key=lambda x: x['date'])
    intervals = [(sorted_sales[i]['date'] - sorted_sales[i - 1]['date']).days for i in range(1, len(sorted_sales))]
    return round(sum(intervals) / len(intervals), 1)


def format_net(net: float | None) -> str:
    """Safely format net payout value for display."""
    return f"£{net:.2f}" if net is not None else "N/A"


# ── NEW NET CALCULATORS FOR OTHER PLATFORMS ──
def calculate_ebay_net(price: float, fee_rate: float) -> float:
    """eBay net after promoted listing fee %."""
    return price * (1 - fee_rate)


def calculate_laced_net(price: float) -> float:
    """Laced net: 12% handling + 3% payment + £6.99 shipping."""
    if price <= 0:
        return 0.0
    return price * (1 - 0.12) * (1 - 0.03) - 6.99


def calculate_alias_net(price: float) -> float:
    """Alias net: 9.5% platform fee + £3.78 seller fee."""
    if price <= 0:
        return 0.0
    return price * (1 - 0.095) - 3.78


# ────────────────────────────────────────────────
# STREAMLIT APP
# ────────────────────────────────────────────────

st.set_page_config(page_title="Sneaker Sales Analyzer", layout="wide")
st.title("Sneaker Sales Analyzer")
st.caption("StockX + eBay + Laced + Alias → blended ROI recommendation")

# Session state
if "sales_input" not in st.session_state:
    st.session_state.sales_input = ""
if "ebay_input" not in st.session_state:
    st.session_state.ebay_input = ""
if "alias_region_input" not in st.session_state:
    st.session_state.alias_region_input = ""
if "alias_worldwide_input" not in st.session_state:
    st.session_state.alias_worldwide_input = ""


def clear_data():
    st.session_state.sales_input = ""
    st.session_state.ebay_input = ""
    st.session_state.alias_region_input = ""
    st.session_state.alias_worldwide_input = ""
    st.rerun()


# ── Sidebar ───────────────────────────────────────
st.sidebar.header("Settings")
use_price_filter = st.sidebar.checkbox("Apply minimum price filter", value=False)
show_last_10 = st.sidebar.checkbox("Show Last 10 sales stats", value=True)

st.sidebar.header("ROI Parameters")
instant_roi = st.sidebar.number_input("Instant Sellers ROI (%)", min_value=0.0, max_value=100.0, value=25.0, step=1.0) / 100.0
quick_roi = st.sidebar.number_input("Quick Sellers ROI (%) (15+ sales, <=15 days)", min_value=0.0, max_value=100.0, value=30.0, step=1.0) / 100.0
jogging_roi = st.sidebar.number_input("Jogging Sellers ROI (%) (<15 sales, <=15 days)", min_value=0.0, max_value=100.0, value=35.0, step=1.0) / 100.0
slow_roi = st.sidebar.number_input("Slow Sellers ROI (%) (<5 sales, >15 days or fallback)", min_value=0.0, max_value=100.0, value=45.0, step=1.0) / 100.0
manual_roi = st.sidebar.slider("Manual ROI Override (%) (0 = auto)", min_value=0, max_value=100, value=0, step=1) / 100.0

# ── Platform toggles & settings ──
st.sidebar.header("Platform Guides")
ebay_enabled = st.sidebar.checkbox("Enable eBay Price Guide", value=False)
laced_enabled = st.sidebar.checkbox("Enable Laced Price Guide", value=False)
alias_enabled = st.sidebar.checkbox("Enable Alias Price Guide", value=False)

st.sidebar.header("eBay Fee")
ebay_fee_rate = st.sidebar.number_input("Promoted Listings Fee %", min_value=5.0, max_value=9.0, value=7.0, step=0.1) / 100.0

st.sidebar.header("Blended Recommendation")
blended_roi = st.sidebar.slider("Target ROI % (Multi-Platform)", min_value=0, max_value=100, value=30, step=1) / 100.0

# ── Main Area ─────────────────────────────────────
data = st.text_area(
    "Paste your StockX sales data here (multi-line)",
    value=st.session_state.sales_input,
    height=300,
    key="sales_input",
    placeholder="Example:\n02/10/25, 1:47 AM UK 7.5\n£109\n..."
)

st.subheader("Filter Options")
min_price = st.number_input("Minimum sale price to include (£)", value=0, step=5, min_value=0, disabled=not use_price_filter)

st.subheader("Instant Sell Options (StockX)")
sell_now_price = st.number_input("Sell Now Price (£) - Optional", value=0.0, min_value=0.0, step=1.0)

# ── Platform input sections (appear only when toggled) ──
if ebay_enabled:
    st.subheader("eBay Data")
    st.number_input("Lowest Listing Price (£)", value=0.0, min_value=0.0, step=1.0, key="lowest_ebay")
    st.text_area(
        "Paste up to 25 eBay sold sales (dd/mm/yy format)",
        value=st.session_state.ebay_input,
        height=200,
        key="ebay_input",
        placeholder="15/03/26\n£120\n16/03/26\n£125\n..."
    )

if laced_enabled:
    st.subheader("Laced Data")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.number_input("Total Sold This Week", value=0, min_value=0, step=1, key="total_laced")
    with c2:
        st.number_input("Last Sold Price (£)", value=0.0, min_value=0.0, step=1.0, key="last_laced")
    with c3:
        st.number_input("Sell Faster Price (£)", value=0.0, min_value=0.0, step=1.0, key="faster_laced")

if alias_enabled:
    st.subheader("Alias Data")
    st.text_area(
        "Region Sales (last 10, dd/mm/yy)",
        value=st.session_state.alias_region_input,
        height=150,
        key="alias_region_input",
        placeholder="15/03/26\n£130\n..."
    )
    st.text_area(
        "Worldwide Sales (last 10, dd/mm/yy)",
        value=st.session_state.alias_worldwide_input,
        height=150,
        key="alias_worldwide_input",
        placeholder="15/03/26\n£128\n..."
    )

col_clear, col_analyze = st.columns([1, 3])
with col_clear:
    if st.button("Clear All Data", use_container_width=True):
        clear_data()
with col_analyze:
    analyze_clicked = st.button("Analyze All Platforms", type="primary", use_container_width=True)

# ── ANALYSIS LOGIC ────────────────────────────────
if analyze_clicked:
    if not any([st.session_state.sales_input.strip(), ebay_enabled, laced_enabled, alias_enabled]):
        st.warning("Please add data or enable at least one platform!")
    else:
        with st.spinner("Parsing and analyzing all platforms..."):
            # === STOCKX ===
            stockx_avg_price = stockx_avg_net = stockx_max_buy = None
            stockx_n = 0
            all_sales = parse_sales(st.session_state.sales_input)
            if use_price_filter:
                filtered_sales = [s for s in all_sales if s['price'] >= min_price]
            else:
                filtered_sales = all_sales

            if len(filtered_sales) >= 2:
                cutoff_120 = datetime.now() - timedelta(days=120)
                recent_sales = [s for s in filtered_sales if s['date'] >= cutoff_120]
                n = len(recent_sales)
                if n >= 2:
                    prices = [s['price'] for s in recent_sales]
                    avg_price = mean(prices)
                    med_price = median(prices)
                    min_p = min(prices)
                    max_p = max(prices)

                    sorted_recent = sorted(recent_sales, key=lambda x: x['date'])
                    mid = n // 2
                    first_half = mean([s['price'] for s in sorted_recent[:mid]]) if mid > 0 else avg_price
                    second_half = mean([s['price'] for s in sorted_recent[mid:]]) if mid < n else avg_price
                    trend = "↑ rising" if second_half > first_half + 2 else "↓ falling" if second_half < first_half - 2 else "→ stable"

                    avg_net = mean(calculate_net(p) for p in prices)
                    last_10_sales = sorted(recent_sales, key=lambda x: x['date'], reverse=True)[:10]
                    avg_net_last10 = mean(calculate_net(s['price']) for s in last_10_sales) if last_10_sales else None
                    avg_days_all = calculate_avg_days(recent_sales)
                    avg_days_10 = calculate_avg_days(last_10_sales) if show_last_10 and len(last_10_sales) >= 2 else None

                    target_roi = get_target_roi(avg_days_all, n, quick_roi, jogging_roi, slow_roi)
                    if manual_roi > 0:
                        target_roi = manual_roi
                    max_pay = round(avg_net / (1 + target_roi), 2)

                    # Instant sell
                    instant_max_buy = None
                    if sell_now_price > 0:
                        sell_now_net = calculate_net(sell_now_price)
                        instant_max_buy = round(sell_now_net / (1 + instant_roi), 2)

                    # Store for blended
                    stockx_avg_price = avg_price
                    stockx_avg_net = avg_net
                    stockx_max_buy = max_pay
                    stockx_n = n

                    st.success("StockX Analysis Complete")
                    st.markdown(f"""
**120-Day Summary**  
**Valid Sales**: {n}  
**Avg Sold Price**: £{avg_price:.2f}  
**Median**: £{med_price:.2f}  
**Range**: £{min_p:.0f} – £{max_p:.0f}  
**Trend**: {trend}  
**Avg Net**: {format_net(avg_net)}  
**Avg Days Between Sales**: **{avg_days_all if avg_days_all is not None else 'N/A'} days**
""")
                    if show_last_10 and avg_days_10 is not None:
                        st.markdown(f"- Last 10 → **{avg_days_10} days**")
                    st.markdown(f"**Target ROI**: {target_roi:.0%}  \n**Recommended Max Buy (StockX)**: £{max_pay}")

                    if instant_max_buy:
                        st.markdown(f"**Instant Sell Max Buy**: £{instant_max_buy}")

            # === eBay ===
            ebay_avg_price = ebay_avg_net = ebay_avg_days = None
            ebay_sales_count = 0
            if ebay_enabled:
                ebay_sales = parse_uk_sales(st.session_state.ebay_input)
                ebay_sales_count = len(ebay_sales)
                lowest_ebay = st.session_state.get("lowest_ebay", 0.0)
                all_ebay_prices = ([lowest_ebay] if lowest_ebay > 0 else []) + [s['price'] for s in ebay_sales]
                if all_ebay_prices:
                    ebay_avg_price = mean(all_ebay_prices)
                    ebay_avg_net = mean(calculate_ebay_net(p, ebay_fee_rate) for p in all_ebay_prices)
                ebay_avg_days = calculate_avg_days(ebay_sales) if ebay_sales_count >= 2 else None

                st.subheader("eBay Analysis")
                st.markdown(f"""
**Sales Parsed**: {ebay_sales_count}  
**Avg Days Between Sales**: {ebay_avg_days if ebay_avg_days is not None else 'N/A'}  
**Avg Price (Lowest + Solds)**: £{ebay_avg_price:.2f if ebay_avg_price else 0:.2f}  
**Avg Net (after {ebay_fee_rate*100:.1f}% fee)**: {format_net(ebay_avg_net)}
""")

            # === Laced ===
            laced_avg_gross = laced_avg_net = None
            total_laced = 0
            if laced_enabled:
                total_laced = st.session_state.get("total_laced", 0)
                last_laced = st.session_state.get("last_laced", 0.0)
                faster_laced = st.session_state.get("faster_laced", 0.0)
                laced_prices = [p for p in [last_laced, faster_laced] if p > 0]
                if laced_prices:
                    laced_avg_gross = mean(laced_prices)
                    laced_avg_net = mean(calculate_laced_net(p) for p in laced_prices)

                st.subheader("Laced Analysis")
                st.markdown(f"""
**Total Sold This Week**: {total_laced}  
**Avg (Last Sold + Sell Faster)**: £{laced_avg_gross:.2f if laced_avg_gross else 0:.2f}  
**Avg Net (12% + 3% + £6.99)**: {format_net(laced_avg_net)}
""")

            # === Alias ===
            alias_avg_price = alias_avg_net = alias_avg_days = None
            alias_sales_count = 0
            if alias_enabled:
                region_sales = parse_uk_sales(st.session_state.alias_region_input)
                world_sales = parse_uk_sales(st.session_state.alias_worldwide_input)
                all_alias_sales = region_sales + world_sales
                alias_sales_count = len(all_alias_sales)
                alias_prices = [s['price'] for s in all_alias_sales]
                if alias_prices:
                    alias_avg_price = mean(alias_prices)
                    alias_avg_net = mean(calculate_alias_net(p) for p in alias_prices)
                alias_avg_days = calculate_avg_days(all_alias_sales) if alias_sales_count >= 2 else None

                st.subheader("Alias Analysis")
                st.markdown(f"""
**Sales Parsed**: {alias_sales_count}  
**Avg Days Between Sales**: {alias_avg_days if alias_avg_days is not None else 'N/A'}  
**Average Sale Price**: £{alias_avg_price:.2f if alias_avg_price else 0:.2f}  
**Avg Net (9.5% + £3.78)**: {format_net(alias_avg_net)}
""")

            # === BLENDED ACROSS ALL ENABLED PLATFORMS ===
            platform_nets = []
            platform_gross = []
            if stockx_avg_net is not None:
                platform_nets.append(stockx_avg_net)
                platform_gross.append(stockx_avg_price)
            if ebay_enabled and ebay_avg_net is not None:
                platform_nets.append(ebay_avg_net)
                platform_gross.append(ebay_avg_price)
            if laced_enabled and laced_avg_net is not None:
                platform_nets.append(laced_avg_net)
                platform_gross.append(laced_avg_gross)
            if alias_enabled and alias_avg_net is not None:
                platform_nets.append(alias_avg_net)
                platform_gross.append(alias_avg_price)

            if platform_nets:
                overall_avg_net = mean(platform_nets)
                overall_avg_sold = mean(platform_gross)
                blended_max_buy = round(overall_avg_net / (1 + blended_roi), 2)

                st.subheader("Blended Multi-Platform Recommendation")
                st.markdown(f"""
**Average Sold Price (gross across {len(platform_nets)} platforms)**: £{overall_avg_sold:.2f}  
**Blended Avg Net Payout**: {format_net(overall_avg_net)}  
**Recommended Max Buy Price**: £{blended_max_buy}  
*(at {blended_roi:.0%} ROI – based on blended net payouts)*
""")
            else:
                st.info("Add data to at least one platform for blended recommendation.")
