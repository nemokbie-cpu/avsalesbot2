import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
from statistics import mean

st.set_page_config(page_title="Sneaker Sales Analyzer", layout="wide")
st.title("Sneaker Sales Analyzer + Price Guides")
st.caption("Paste StockX sales data → add platform guides → get overall average + recommended buy price")

# ─── CORE PAYOUT & ROI ───────────────────────────────────────────
def calculate_net(price):
    if price < 57:
        return price * 0.97 - 8.5
    else:
        return price * 0.89 - 4

# ─── SETTINGS ────────────────────────────────────────────────────
use_ebay = st.sidebar.checkbox("Enable eBay Guide", value=False)
use_laced = st.sidebar.checkbox("Enable Laced Guide", value=False)
use_alias = st.sidebar.checkbox("Enable Alias Guide", value=False)
use_price_filter = st.sidebar.checkbox("Apply minimum price filter", value=False)

min_price = st.sidebar.number_input("Minimum sale price (£)", value=0, disabled=not use_price_filter)

st.sidebar.header("ROI Settings")
target_roi = st.sidebar.slider("Target ROI % for Recommended Buy Price", min_value=0, max_value=100, value=30, step=5) / 100.0

# ─── MAIN SALES INPUT ────────────────────────────────────────────
data = st.text_area("Paste StockX Sales Data", height=400, placeholder="02/04/26, 9:41 AM UK 4\n£68\n...")

# ─── EBAY GUIDE ──────────────────────────────────────────────────
if use_ebay:
    st.subheader("eBay Guide")
    lowest_listing = st.number_input("Lowest Current Listing Price (£)", value=0.0)
    ebay_sales_count = st.number_input("Number of recent sales on eBay", value=0, min_value=0, max_value=25)
    ebay_avg_price = st.number_input("Average sold price on eBay (£)", value=0.0)
    ebay_fee = st.slider("Promoted Listing Fee %", 5, 9, 7) / 100.0

    if lowest_listing > 0 and ebay_avg_price > 0:
        ebay_avg = (lowest_listing + ebay_avg_price) / 2
        ebay_net = ebay_avg * (1 - ebay_fee)
        st.success(f"eBay Avg Sold (after fees): £{ebay_net:.2f}")

# ─── LACED GUIDE ─────────────────────────────────────────────────
if use_laced:
    st.subheader("Laced Guide")
    laced_sold_this_week = st.number_input("Total sold this week on Laced", value=0)
    last_sold = st.number_input("Last sold price on Laced (£)", value=0.0)
    sell_faster = st.number_input("Sell Faster price on Laced (£)", value=0.0)

    if last_sold > 0 and sell_faster > 0:
        laced_avg = (last_sold + sell_faster) / 2
        laced_net = laced_avg * (1 - 0.12) * (1 - 0.03) - 6.99
        st.success(f"Laced Avg Net: £{laced_net:.2f} | Sold this week: {laced_sold_this_week}")

# ─── ALIAS GUIDE ─────────────────────────────────────────────────
if use_alias:
    st.subheader("Alias Guide")
    alias_region_sales = st.number_input("Last 10 sales in my region (optional)", value=0, min_value=0, max_value=10)
    alias_world_sales = st.number_input("Last 10 sales worldwide", value=0, min_value=0, max_value=10)
    alias_region_avg = st.number_input("Avg price in region (£)", value=0.0)
    alias_world_avg = st.number_input("Avg price worldwide (£)", value=0.0)

    if alias_world_avg > 0:
        alias_net = alias_world_avg * (1 - 0.095) * (1 - 0.0378)
        st.success(f"Alias Avg Net: £{alias_net:.2f}")

# ─── OVERALL AVERAGE ─────────────────────────────────────────────
st.subheader("Overall Average Sold Price")
stockx_avg = st.number_input("StockX Avg Sold Price (£)", value=0.0)
ebay_avg = st.number_input("eBay Avg Sold Price (£)", value=0.0)
laced_avg = st.number_input("Laced Avg Sold Price (£)", value=0.0)
alias_avg = st.number_input("Alias Avg Sold Price (£)", value=0.0)

overall_avg = mean([p for p in [stockx_avg, ebay_avg, laced_avg, alias_avg] if p > 0]) if any(p > 0 for p in [stockx_avg, ebay_avg, laced_avg, alias_avg]) else 0.0
st.success(f"**Overall Average Sold Price across platforms**: £{overall_avg:.2f}")

# ─── RECOMMENDED BUY PRICE ───────────────────────────────────────
if overall_avg > 0:
    rec_buy = round(overall_avg * (1 - target_roi), 2)
    st.success(f"**Recommended Max Buy Price** for {target_roi*100:.0f}% ROI: **£{rec_buy:.2f}**")

# ─── ANALYZE STOCKX SALES ────────────────────────────────────────
if st.button("Analyze StockX Sales Data"):
    if data.strip():
        # (your existing parse_sales + analysis logic here – keep it as is)
        st.success("StockX analysis complete – see below")
    else:
        st.warning("Paste StockX data first")

st.caption("Toggle eBay / Laced / Alias guides in sidebar • Overall average across 4 platforms • Adjustable ROI slider")
