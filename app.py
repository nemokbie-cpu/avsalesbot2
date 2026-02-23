import streamlit as st
import re
from datetime import datetime, timedelta
from statistics import mean, median

def calculate_net(price):
    if price < 57:
        return price * 0.97 - 8.5
    else:
        return price * 0.89 - 4

def get_target_roi(avg_days):
    if avg_days < 5:
        return 0.30
    elif 10 <= avg_days <= 15:
        return 0.40
    else:
        return 0.45

def parse_sales(raw_text):
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
                    price_match = re.search(r'£\s*([\d,]+)', lines[j])
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))
                        i = j
                        break
                
                if price is not None:
                    sales.append({'date': dt, 'price': price})
            except ValueError:
                pass
        i += 1
    return sales

def calculate_avg_days(sales_list):
    if len(sales_list) < 2:
        return None
    
    sorted_sales = sorted(sales_list, key=lambda x: x['date'])  # oldest to newest
    intervals = []
    for i in range(1, len(sorted_sales)):
        delta = (sorted_sales[i]['date'] - sorted_sales[i-1]['date']).days
        intervals.append(delta)
    
    avg = sum(intervals) / len(intervals)
    return round(avg, 1)

# ────────────────────────────────────────────────
# STREAMLIT APP
# ────────────────────────────────────────────────
st.set_page_config(page_title="Sneaker Analyzer", layout="wide")
st.title("Sneaker Sales Analyzer")
st.caption("Paste StockX sales data → filter if needed → analyze")

if "sales_input" not in st.session_state:
    st.session_state.sales_input = ""

def clear_data():
    st.session_state.sales_input = ""

st.sidebar.header("Settings")
use_price_filter = st.sidebar.checkbox("Apply price filter (exclude lower sales)", value=False)
show_last_10 = st.sidebar.checkbox("Also show Last 10 velocity & net", value=True)

data = st.text_area(
    "Paste Sales Data Here",
    height=520,
    key="sales_input",
    placeholder="02/10/26, 1:47 AM UK 7.5\n£109\n..."
)

st.subheader("Filter Options")
min_price = st.number_input(
    "Only include sales at or above this price (£)",
    value=0,
    step=5,
    min_value=0,
    disabled=not use_price_filter,
    help="Ignored if checkbox above is off"
)

col_clear, col_analyze = st.columns([1, 3])
with col_clear:
    st.button("Clear Data", on_click=clear_data, use_container_width=True)
with col_analyze:
    analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)

if analyze_clicked:
    if not data.strip():
        st.warning("Paste your sales data first!")
    else:
        all_sales = parse_sales(data)
        
        # Apply filter only if enabled
        if use_price_filter:
            filtered_sales = [s for s in all_sales if s['price'] >= min_price]
        else:
            filtered_sales = all_sales
        
        if len(filtered_sales) < 2:
            st.error("Not enough sales after filtering.")
        else:
            cutoff_120 = datetime.now() - timedelta(days=120)
            recent_sales = [s for s in filtered_sales if s['date'] >= cutoff_120]
            
            n = len(recent_sales)
            if n < 2:
                st.warning("Not enough sales in last 120 days.")
            else:
                prices = [s['price'] for s in recent_sales]
                avg_price = mean(prices)
                med_price = median(prices)
                min_p = min(prices)
                max_p = max(prices)
                
                # Simple trend: first half vs second half
                sorted_recent = sorted(recent_sales, key=lambda x: x['date'])
                mid = n // 2
                first_half_avg = mean([s['price'] for s in sorted_recent[:mid]]) if mid > 0 else avg_price
                second_half_avg = mean([s['price'] for s in sorted_recent[mid:]]) if mid < n else avg_price
                trend = "↑ rising" if second_half_avg > first_half_avg + 2 else \
                        "↓ falling" if second_half_avg < first_half_avg - 2 else "→ stable"
                
                avg_net = mean(calculate_net(p) for p in prices)
                
                last_10_sales = sorted(recent_sales, key=lambda x: x['date'], reverse=True)[:10]
                avg_net_last10 = mean(calculate_net(s['price']) for s in last_10_sales) if len(last_10_sales) > 0 else None
                
                avg_days_all = calculate_avg_days(recent_sales)
                
                avg_days_10 = calculate_avg_days(last_10_sales) if show_last_10 and len(last_10_sales) >= 2 else None
                
                target_roi = get_target_roi(avg_days_all) if avg_days_all is not None else 0.45
                
                # CHANGED: use avg_net (120-day average) instead of last-10
                max_pay = round(avg_net / (1 + target_roi), 2) if avg_net is not None else "N/A"
                
                # Warnings
                if n < 10:
                    st.warning(f"Only {n} sales in last 120 days — results may be less reliable")
                if len(recent_sales) < 5:
                    st.warning("Very low volume in 120 days — consider checking a longer period")
                
                st.success("Analysis Complete")
                
                st.markdown(f"""
**120-Day Summary**  
**Valid Sales**: {n}  
**Avg Sold Price**: £{avg_price:.2f}  
**Median Sold Price**: £{med_price:.2f}  
**Price Range**: £{min_p:.0f} – £{max_p:.0f}  
**Trend**: {trend}  
**Avg Net Payout**: £{avg_net:.2f}  
**Avg Net (Last 10)**: £{avg_net_last10:.2f if avg_net_last10 is not None else 'N/A'}  
**Average Days Between Sales**:  
- All in last 120 days → **{avg_days_all if avg_days_all is not None else 'N/A'} days** (used for ROI)
                """)
                
                if show_last_10 and avg_days_10 is not None:
                    st.markdown(f"- Last 10 sales → **{avg_days_10} days**")
                
                st.markdown(f"""
**Target ROI**: {target_roi:.0%}  
**Recommended Max Buy Price**: £{max_pay}  
*(calculated from 120-day Avg Net Payout)*
                """)
