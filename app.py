import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from yahooquery import search
from newsapi import NewsApiClient
from groq import Groq
import unicodedata
import re
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

# ---------------- API KEYS ----------------

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
NEWS_API_KEY = st.secrets["NEWS_API_KEY"]

client = Groq(api_key=GROQ_API_KEY)
newsapi = NewsApiClient(api_key=NEWS_API_KEY)

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="AI Financial Intelligence Platform",
    layout="wide"
)

# ---------------- UI STYLE ----------------

st.markdown("""
<style>
body{
background-color:#0e1117;
color:white;
}

div[data-testid="stMetricValue"]{
font-size:26px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------

st.title("📈 AI Financial Intelligence Platform")
st.caption("Market Intelligence • AI Analytics • Portfolio Tools")

# ---------------- LIVE TICKER ----------------

ticker_list = {
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^NSEI": "NIFTY 50",
    "BTC-USD": "Bitcoin",
    "GC=F": "Gold"
}

ticker_text = ""

for symbol, name in ticker_list.items():

    try:
        data = yf.download(symbol, period="1d", interval="1m", progress=False)

        if not data.empty:
            price = float(data["Close"].iloc[-1])
            price = round(price, 2)

            ticker_text += f"{name}: {price} | "

    except:
        continue

st.markdown(f"""
<marquee style='
color:#00ffcc;
font-size:18px;
font-weight:600;
background:#111;
padding:8px;
border-radius:6px;
'>
{ticker_text}
</marquee>
""", unsafe_allow_html=True)

# ---------------- TEXT CLEANER ----------------

def clean_text(text):

    if not isinstance(text,str):
        return text

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii","ignore").decode("ascii")
    text = re.sub(r"[^\x00-\x7F]+","",text)

    return text.strip()

# ---------------- AI CALL ----------------

def ai_call(prompt):

    prompt = clean_text(prompt)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role":"system","content":"You are an expert financial analyst and educator."},
                {"role":"user","content":prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI Service Error: {str(e)}"

# ---------------- DATA FUNCTIONS ----------------

def safe_history(symbol, period="5d", interval="5m"):

    try:

        data = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False
        )

        if data.empty and not symbol.endswith(".NS"):

            data = yf.download(
                symbol+".NS",
                period=period,
                interval=interval,
                progress=False
            )

        if isinstance(data.columns,pd.MultiIndex):
            data.columns=data.columns.get_level_values(0)

        return data

    except:
        return pd.DataFrame()

def find_ticker(name):

    try:
        result = search(name)
        quotes = result.get("quotes",[])

        if quotes:
            return quotes[0]["symbol"]

    except:
        pass

    return name.upper()

# ---------------- SIDEBAR ----------------

section = st.sidebar.selectbox(
    "Platform Section",
    [
        "Dashboard",
        "Market Tools",
        "AI Tools",
        "Research",
        "Financial Education Academy"
    ]
)

# ---------------- PAGE NAVIGATION ----------------

if section=="Dashboard":
    page = st.sidebar.radio("",["Market Dashboard"])

elif section=="Market Tools":
    page = st.sidebar.radio("",[
        "Stock Analysis",
        "Stock Comparison",
        "Portfolio Manager",
        "NSE Heatmap"
    ])

elif section=="AI Tools":
    page = st.sidebar.radio("",[
        "AI Screener",
        "AI Signals",
        "AI Stock Score",
        "AI Assistant"
    ])

elif section=="Financial Education Academy":
    page = st.sidebar.radio("",[
        "Learning Paths",
        "AI Quiz Generator",
        "Jargon Buster"
    ])

else:
    page = st.sidebar.radio("",[
        "Financial Statements",
        "Market Leaders",
        "Finance News"
    ])

# ---------------- MARKET DASHBOARD ----------------

def market_dashboard():

    markets = {
        "S&P 500":"^GSPC",
        "NASDAQ":"^IXIC",
        "NIFTY 50":"^NSEI",
        "Gold":"GC=F",
        "Bitcoin":"BTC-USD"
    }

    cols = st.columns(len(markets))

    for i,(name,ticker) in enumerate(markets.items()):

        data = safe_history(ticker)

        if len(data)<2:
            cols[i].metric(name,"N/A")
            continue

        price = data["Close"].iloc[-1]
        prev = data["Close"].iloc[-2]

        change=((price-prev)/prev)*100

        cols[i].metric(name,round(price,2),f"{round(change,2)}%")

    st.divider()

    choice = st.selectbox("Market Chart", list(markets.keys()))

    data = safe_history(markets[choice])

    fig = px.line(data,x=data.index,y="Close")
    st.plotly_chart(fig,use_container_width=True)

    st.subheader("Economic Calendar")

    calendar = pd.DataFrame({
        "Event":[
            "US Federal Reserve Meeting",
            "US Inflation CPI",
            "US GDP Release",
            "ECB Rate Decision",
            "RBI Policy Meeting"
        ],
        "Impact":[
            "High","High","Medium","High","High"
        ]
    })

    st.dataframe(calendar)

# ---------------- STOCK ANALYSIS ----------------

def stock_analysis():

    company = clean_text(st.text_input("Company"))

    if not company:
        return

    ticker = find_ticker(company)
    data = safe_history(ticker)

    if data.empty:
        st.warning("Market data unavailable")
        return

    st.metric("Live Price", round(data["Close"].iloc[-1],2))

    fig = px.line(
        data,
        x=data.index,
        y="Close",
        title=f"{ticker} Recent Price Movement"
    )

    st.plotly_chart(fig,use_container_width=True)

# ---------------- STOCK COMPARISON ----------------

def stock_comparison():

    col1,col2 = st.columns(2)

    s1 = col1.text_input("Company 1","Apple")
    s2 = col2.text_input("Company 2","Microsoft")

    d1 = safe_history(find_ticker(s1))
    d2 = safe_history(find_ticker(s2))

    if d1.empty or d2.empty:
        st.warning("Data unavailable")
        return

    df = pd.concat([d1["Close"],d2["Close"]],axis=1)
    df.columns=[s1,s2]

    fig = px.line(df)

    st.plotly_chart(fig,use_container_width=True)

# ---------------- PORTFOLIO ----------------

def portfolio_manager():

    text = st.text_input("Enter companies separated by comma")

    if not text:
        return

    names=[x.strip() for x in text.split(",")]
    tickers=[find_ticker(x) for x in names]

    data=yf.download(
        tickers,
        period="5d",
        interval="5m",
        progress=False
    )

    prices=data["Close"]

    st.line_chart(prices)

# ---------------- NSE HEATMAP ----------------

def nse_heatmap():

    stocks=["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS"]
    rows=[]

    for s in stocks:

        data=safe_history(s)

        if len(data)<2:
            continue

        change=((data["Close"].iloc[-1]-data["Close"].iloc[-2])/data["Close"].iloc[-2])*100

        rows.append({"Stock":s,"Change":change})

    df=pd.DataFrame(rows)

    fig=px.treemap(df,path=["Stock"],values="Change",color="Change")

    st.plotly_chart(fig,use_container_width=True)

# ---------------- MARKET LEADERS ----------------

def market_leaders():

    tickers=["AAPL","MSFT","NVDA","TSLA","RELIANCE.NS","TCS.NS"]
    rows=[]

    for t in tickers:

        data=safe_history(t)

        if len(data)<2:
            continue

        change=((data["Close"].iloc[-1]-data["Close"].iloc[-2])/data["Close"].iloc[-2])*100

        rows.append({"Stock":t,"Change %":round(change,2)})

    df=pd.DataFrame(rows).sort_values("Change %",ascending=False)

    st.dataframe(df)

# ---------------- AI TOOLS ----------------

def ai_screener():

    q = clean_text(st.text_input("Describe stocks"))

    if q:

        with st.spinner("Screening stocks..."):

            response = ai_call(f"Suggest 5 stocks for: {q}")

            if response:
                st.write(response)

def ai_signals():

    stock = clean_text(st.text_input("Stock"))

    if stock:

        with st.spinner(f"Analyzing {stock}..."):

            response = ai_call(f"Buy Hold Sell analysis for {stock}")

            if response:
                st.write(response)

def ai_stock_score():

    stock = clean_text(st.text_input("Stock"))

    if stock:

        with st.spinner("Calculating score..."):

            response = ai_call(f"Score this stock out of 100: {stock}")

            if response:
                st.write(response)

def ai_assistant():

    q = clean_text(st.text_input("Ask finance question"))

    if q:

        with st.spinner("Analyzing..."):

            response = ai_call(q)

            if response:
                st.write(response)

# ---------------- EDUCATION ----------------

def learning_paths():

    topic = st.text_input("Learning Topic")

    if topic:

        with st.spinner("Generating path..."):

            response = ai_call(f"Create a learning path for {topic}")

            if response:
                st.write(response)

def quiz_generator():

    topic = st.text_input("Quiz Topic")

    if topic:

        with st.spinner("Creating quiz..."):

            response = ai_call(f"Create 5 quiz questions for {topic}")

            if response:
                st.write(response)

def jargon_buster():

    term = st.text_input("Financial Term")

    if term:

        with st.spinner("Simplifying..."):

            response = ai_call(f"Explain the financial term {term} in simple words")

            if response:
                st.write(response)

# ---------------- NEWS ----------------

def finance_news():

    try:

        news=newsapi.get_top_headlines(category="business",language="en")

        for a in news.get("articles", [])[:5]:

            st.markdown(f"### {a['title']}")
            st.write(a["description"])
            st.markdown(a["url"])
            st.divider()

    except Exception as e:

        st.error(f"News API Error: {str(e)}")

# ---------------- ROUTER ----------------

if page=="Market Dashboard":
    market_dashboard()

elif page=="Stock Analysis":
    stock_analysis()

elif page=="Stock Comparison":
    stock_comparison()

elif page=="Portfolio Manager":
    portfolio_manager()

elif page=="NSE Heatmap":
    nse_heatmap()

elif page=="Market Leaders":
    market_leaders()

elif page=="AI Screener":
    ai_screener()

elif page=="AI Signals":
    ai_signals()

elif page=="AI Stock Score":
    ai_stock_score()

elif page=="AI Assistant":
    ai_assistant()

elif page=="Learning Paths":
    learning_paths()

elif page=="AI Quiz Generator":
    quiz_generator()

elif page=="Jargon Buster":
    jargon_buster()

elif page=="Financial Statements":

    company = st.text_input("Company")

    if company:

        ticker=find_ticker(company)

        stock=yf.Ticker(ticker)

        st.dataframe(stock.financials)

elif page=="Finance News":
    finance_news()

st.markdown("---")
st.caption("Data sourced from public financial APIs. Educational purposes only.")