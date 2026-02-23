import streamlit as st
import re
from datetime import datetime, timedelta
from statistics import mean, median

# ────────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────────

def calculate_net(price: float) -> float:
    """Calculate net payout after fees based on sold price."""
    if price < 57:
        return price * 0.97 - 8.5
    else:
        return price * 0.89 - 4


def get_target_roi(avg_days: float | None) -> float:
    """Determine target ROI % based on average days between sales."""
    if avg_days is None:
        return 0.45
    if avg_days < 5:
        return 0.30
    elif 10 <= avg_days <= 15:
        return 0.40
    else:
        return 0.45


def parse_sales(raw_text: str) -> list[dict]:
    """Parse StockX-style sales data from pasted text."""
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

                # Handle future dates (likely typo → previous century)
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
    intervals = []
    for i in range(1, len(sorted_sales)):
        delta = (sorted_sales[i]['date'] - sorted_sales[i - 1]['date']).days
        intervals.append(delta)

    if not intervals:
        return None
    return round(sum(intervals) / len(intervals), 1)


def format_net(net: float | None) -> str:
    """Safely format net payout value for display."""
    return f"£{net:.2f}" if net is not None else "N/A"


# ────────────────────────────────────────────────
# STREAMLIT APP
# ────────────────────────────────────────────────

st.set_page_config(page_title="Sneaker Sales Analyzer", layout="wide")
st.title("Sneaker Sales Analyzer")
st.caption("Paste StockX / GOAT / similar sales data → filter → analyze")

# Session state for persistent input
if "sales_input" not in st.session_state:
    st.session_state.sales_input = ""


def clear_data():
    st.session_state.sales_input = ""


# ── Sidebar ───────────────────────────────────────
st.sidebar.header("Settings")
use_price_filter = st.sidebar.checkbox("Apply minimum price filter", value=False)
show_last_10 = st.sidebar.checkbox("Show Last 10 sales stats", value=True)

# ── Main Area ─────────────────────────────────────
data = st.text_area(
    "Paste your sales data here (multi-line)",
    value=st.session_state.sales_input,
    height=520,
    key="sales_input",
    placeholder="Example format:\n02/10/25, 1:47 AM UK 7.5\n£109\n02/12/25, 3:22 PM UK 8\n£115\n..."
)

st.subheader("Filter Options")
min_price = st.number_input(
    "Minimum sale price to include (£)",
    value=0,
    step=5,
    min_value=0,
    disabled=not use_price_filter,
    help="Only sales ≥ this price will be used (if filter enabled)"
)

col_clear, col_analyze = st.columns([1, 3])
with col_clear:
    if st.button("Clear Data", use_container_width=True):
        clear_data()
        st.rerun()

with col_analyze:
    analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)

# ── Analysis Logic ────────────────────────────────
if analyze_clicked:
    if not st.session_state.sales_input.strip():
        st.warning("Please paste some sales data first!")
    else:
        with st.spinner("Parsing and analyzing sales..."):
            all_sales = parse_sales(st.session_state.sales_input)

            # Apply price filter if enabled
            if use_price_filter:
                filtered_sales = [s for s in all_sales if s['price'] >= min_price]
            else:
                filtered_sales = all_sales

            if len(filtered_sales) < 2:
                st.error("Not enough valid sales after filtering (need at least 2).")
            else:
                # Last 120 days
                cutoff_120 = datetime.now() - timedelta(days=120)
                recent_sales = [s for s in filtered_sales if s['date'] >= cutoff_120]

                n = len(recent_sales)
                if n < 2:
                    st.warning("No / too few sales in the last 120 days.")
                else:
                    prices = [s['price'] for s in recent_sales]

                    avg_price = mean(prices)
                    med_price = median(prices)
                    min_p = min(prices)
                    max_p = max(prices)

                    # Trend detection (simple half-split)
                    sorted_recent = sorted(recent_sales, key=lambda x: x['date'])
                    mid = n // 2
                    first_half_avg = mean([s['price'] for s in sorted_recent[:mid]]) if mid > 0 else avg_price
                    second_half_avg = mean([s['price'] for s in sorted_recent[mid:]]) if mid < n else avg_price

                    if second_half_avg > first_half_avg + 2:
                        trend = "↑ rising"
                    elif second_half_avg < first_half_avg - 2:
                        trend = "↓ falling"
                    else:
                        trend = "→ stable"

                    avg_net = mean(calculate_net(p) for p in prices)

                    # Last 10
                    last_10_sales = sorted(recent_sales, key=lambda x: x['date'], reverse=True)[:10]
                    avg_net_last10 = mean(calculate_net(s['price']) for s in last_10_sales) if last_10_sales else None

                    avg_days_all = calculate_avg_days(recent_sales)
                    avg_days_10 = calculate_avg_days(last_10_sales) if show_last_10 and len(last_10_sales) >= 2 else None

                    target_roi = get_target_roi(avg_days_all)

                    # Use overall 120-day avg net for recommendation
                    max_pay = round(avg_net / (1 + target_roi), 2) if avg_net is not None else "N/A"

                    # Warnings
                    if n < 10:
                        st.warning(f"Only {n} sales in last 120 days — results may be less reliable.")
                    if n < 5:
                        st.warning("Very low volume in last 120 days — consider a longer period or different filter.")

                    st.success("Analysis Complete")

                    # ── Results Display ───────────────────────
                    st.markdown(f"""
**120-Day Summary**

**Valid Sales**: {n}  
**Avg Sold Price**: £{avg_price:.2f}  
**Median Sold Price**: £{med_price:.2f}  
**Price Range**: £{min_p:.0f} – £{max_p:.0f}  
**Trend**: {trend}  
**Avg Net Payout**: {format_net(avg_net)}  
**Avg Net (Last 10)**: {format_net(avg_net_last10)}  
**Average Days Between Sales**:  
- All in last 120 days → **{avg_days_all if avg_days_all is not None else 'N/A'} days** (used for ROI)
                    """.strip())

                    if show_last_10 and avg_days_10 is not None:
                        st.markdown(f"- Last 10 sales → **{avg_days_10} days**")

                    st.markdown(f"""
**Target ROI**: {target_roi:.0%}  
**Recommended Max Buy Price**: £{max_pay}  
*(based on 120-day Avg Net Payout)*
                    """.strip())
