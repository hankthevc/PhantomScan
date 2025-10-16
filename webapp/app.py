"""PhantomScan Streamlit App - Main Entry Point."""

import os
import streamlit as st
from datetime import datetime
from pathlib import Path
from radar.utils import load_json

# Page configuration
st.set_page_config(
    page_title="PhantomScan",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better UI
st.markdown(
    """
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Main page content
st.markdown('<div class="main-header">🔭 PhantomScan</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Phantom Dependency Radar - Slopsquatting Detection</div>',
    unsafe_allow_html=True,
)

st.markdown("---")

# Data banner with guardrails
today_str = datetime.utcnow().strftime("%Y-%m-%d")
feed_path = Path("data/feeds") / today_str / "topN.json"
offline_mode = os.environ.get("RADAR_OFFLINE", "0") == "1"

col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 2])
with col_a:
    st.metric("Data Date", today_str)
with col_b:
    st.metric("Mode", "OFFLINE" if offline_mode else "ONLINE")
with col_c:
    count = 0
    if feed_path.exists():
        data = load_json(feed_path)
        count = len(data) if data else 0
    st.metric("Candidates", count)
with col_d:
    if not feed_path.exists():
        st.warning("Today's feed is missing")

# Welcome section
st.markdown(
    """
    ## Welcome to PhantomScan

    PhantomScan is a real-time threat intelligence platform for detecting suspicious package publications
    that may be supply-chain attacks (slopsquatting, typosquatting, brandjacking).

    ### 📊 What We Monitor

    - **PyPI** - Python Package Index
    - **npm** - Node Package Manager

    ### 🎯 How It Works

    1. **Fetch**: Collect recent package publications from registries
    2. **Score**: Apply multi-factor heuristics (name patterns, age, metadata)
    3. **Feed**: Generate top-N daily threat intelligence feeds
    4. **Investigate**: Provide investigation tools and casefiles

    ### 🚀 Get Started

    Use the sidebar to navigate:
    - **📈 Live Feed** - Browse today's suspicious packages
    - **🔎 Candidate Explorer** - Search and investigate packages
    - **📄 Casefile Generator** - Create investigation reports
    - **⚙️ Settings** - Configure scoring policy
    """
)

st.markdown("---")

# Quick stats
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🎯 Detection Method", "Multi-Heuristic")

with col2:
    st.metric("🌐 Ecosystems", "PyPI + npm")

with col3:
    st.metric("🔄 Update Frequency", "Daily")

st.markdown("---")

# Info boxes
st.info(
    """
    **Offline Mode**: If `RADAR_OFFLINE=1` is set, the app uses sample seed data instead of live feeds.
    This is useful for demos or network-constrained environments.
    """
)

st.warning(
    """
    **Disclaimer**: Automated scoring may produce false positives. Always manually verify findings
    before taking action against packages or maintainers.
    """
)

st.markdown("---")

# Footer
st.markdown(
    """
    <div style="text-align: center; color: #888; margin-top: 3rem;">
        PhantomScan v0.1.0 | Built with ❤️ for defensive security research
    </div>
    """,
    unsafe_allow_html=True,
)
