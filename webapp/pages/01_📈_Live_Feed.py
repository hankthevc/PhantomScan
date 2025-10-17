"""Live Feed page - Browse daily suspicious packages."""

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from radar.utils import load_json
from webapp.utils import get_risk_badge, get_ecosystem_badge, get_risk_level, format_score_display

st.set_page_config(page_title="Live Feed", page_icon="📈", layout="wide")

# Add custom CSS (same as main app)
st.markdown(
    """
    <style>
    .risk-badge-low {
        background-color: #28a745;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .risk-badge-medium {
        background-color: #ffc107;
        color: #000;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .risk-badge-high {
        background-color: #dc3545;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .risk-badge-critical {
        background-color: #6f1313;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .ecosystem-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: 500;
        font-size: 0.85rem;
    }
    .ecosystem-pypi {
        background-color: #3776ab;
        color: white;
    }
    .ecosystem-npm {
        background-color: #cb3837;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📈 Live Feed")
st.markdown("Browse suspicious packages detected by PhantomScan")

st.markdown("---")


@st.cache_data
def load_feed_for_date(date_str: str) -> list[dict] | None:
    """Load feed JSON for a specific date."""
    feed_path = Path("data/feeds") / date_str / "topN.json"
    if not feed_path.exists():
        return None
    return load_json(feed_path)


@st.cache_data
def get_available_dates() -> list[str]:
    """Get list of dates with available feeds."""
    feeds_dir = Path("data/feeds")
    if not feeds_dir.exists():
        return []

    dates = []
    for date_dir in feeds_dir.iterdir():
        if date_dir.is_dir() and (date_dir / "topN.json").exists():
            dates.append(date_dir.name)

    return sorted(dates, reverse=True)


# Check for today's feed
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
offline_mode = os.getenv("RADAR_OFFLINE", "0") == "1"

# Data source banner
if offline_mode:
    st.info("🔌 **OFFLINE MODE** - Using sample seed data for demo purposes")
else:
    st.success("🌐 **ONLINE MODE** - Fetching live package data")

# Date selector
col1, col2 = st.columns([1, 3])

with col1:
    available_dates = get_available_dates()

    if not available_dates:
        st.error("⚠️ No feed data available")
        
        if st.button("🚀 Generate Feed Now"):
            with st.spinner("Generating feed (offline mode)..."):
                try:
                    # Run radar in offline mode
                    result = subprocess.run(
                        ["radar", "run-all", "--limit", "100"],
                        env={**os.environ, "RADAR_OFFLINE": "1"},
                        capture_output=True,
                        text=True,
                    )
                    
                    if result.returncode == 0:
                        st.success("✅ Feed generated successfully! Refresh the page.")
                        st.rerun()
                    else:
                        st.error(f"❌ Feed generation failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        st.markdown("Or run from terminal:")
        st.code("RADAR_OFFLINE=1 radar run-all", language="bash")
        st.stop()

    selected_date = st.selectbox(
        "Select Date",
        options=available_dates,
        index=0,
    )

with col2:
    feed_info = f"📅 Showing feed for **{selected_date}** ({len(available_dates)} dates available)"
    
    # Check if today's feed exists
    if today not in available_dates:
        feed_info += f"\n\n⚠️ Today's feed ({today}) not yet generated"
    
    st.info(feed_info)

# Load feed
feed_data = load_feed_for_date(selected_date)

if not feed_data:
    st.error(f"Failed to load feed for {selected_date}")
    st.stop()

st.markdown("---")

# Feed metadata banner
col_banner1, col_banner2, col_banner3 = st.columns([2, 2, 1])

with col_banner1:
    st.markdown(f"**📅 Data Date:** {selected_date}")

with col_banner2:
    mode_str = "Offline (Seed Data)" if offline_mode else "Online (Live)"
    st.markdown(f"**🔌 Mode:** {mode_str}")

with col_banner3:
    st.markdown(f"**📦 Candidates:** {len(feed_data)}")

st.markdown("---")

# Summary metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Candidates", len(feed_data))

with col2:
    pypi_count = sum(1 for p in feed_data if p["ecosystem"] == "pypi")
    st.metric("PyPI Packages", pypi_count)

with col3:
    npm_count = sum(1 for p in feed_data if p["ecosystem"] == "npm")
    st.metric("npm Packages", npm_count)

with col4:
    avg_score = sum(p["score"] for p in feed_data) / len(feed_data) if feed_data else 0
    st.metric("Average Score", f"{avg_score:.2f}")

st.markdown("---")

# Filters
col1, col2, col3 = st.columns(3)

with col1:
    ecosystem_filter = st.multiselect(
        "Filter by Ecosystem",
        options=["pypi", "npm"],
        default=["pypi", "npm"],
    )

with col2:
    min_score_filter = st.slider("Minimum Score", 0.0, 1.0, 0.3, 0.05)

with col3:
    search_term = st.text_input("Search by name", "")

# Apply filters
filtered_data = [
    p
    for p in feed_data
    if p["ecosystem"] in ecosystem_filter
    and p["score"] >= min_score_filter
    and (not search_term or search_term.lower() in p["name"].lower())
]

st.markdown(f"**Showing {len(filtered_data)} of {len(feed_data)} packages**")

st.markdown("---")

# Display packages
for idx, pkg in enumerate(filtered_data, 1):
    # Get risk level info
    level, emoji, css_class = get_risk_level(pkg['score'])
    
    # Create expander with color-coded header
    with st.expander(
        f"#{idx} {pkg['name']} - {emoji} {level} ({pkg['score']:.2f})",
        expanded=idx <= 3,
    ):
        # Header with badges
        col_header1, col_header2, col_header3 = st.columns([2, 1, 1])
        
        with col_header1:
            st.markdown(f"### `{pkg['name']}`")
        
        with col_header2:
            st.markdown(get_ecosystem_badge(pkg['ecosystem']), unsafe_allow_html=True)
        
        with col_header3:
            st.markdown(get_risk_badge(pkg['score']), unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**Version**: {pkg['version']}")
            st.markdown(f"**Published**: {pkg['created_at'][:10]}")
            st.markdown(f"**Risk Score**: {format_score_display(pkg['score'])}")

            # Risk factors
            st.markdown("**⚠️ Risk Factors**:")
            for reason in pkg["reasons"]:
                st.markdown(f"- {reason}")

        with col2:
            # Metadata
            st.markdown("**Metadata**:")
            if pkg["homepage"]:
                st.markdown(f"🏠 [Homepage]({pkg['homepage']})")
            else:
                st.markdown("🏠 Homepage: ❌")

            if pkg["repository"]:
                st.markdown(f"📦 [Repository]({pkg['repository']})")
            else:
                st.markdown("📦 Repository: ❌")

            st.markdown(f"👥 Maintainers: {pkg['maintainers_count']}")

            if pkg["has_install_scripts"]:
                st.markdown("⚠️ Has install scripts")

        # Score breakdown chart
        st.markdown("**Score Breakdown**:")
        breakdown_df = pd.DataFrame(
            {
                "Heuristic": [
                    "Name Suspicion",
                    "Newness",
                    "Repo Missing",
                    "Maintainer Rep",
                    "Script Risk",
                ],
                "Score": [
                    pkg["breakdown"]["name_suspicion"],
                    pkg["breakdown"]["newness"],
                    pkg["breakdown"]["repo_missing"],
                    pkg["breakdown"]["maintainer_reputation"],
                    pkg["breakdown"]["script_risk"],
                ],
            }
        )
        st.bar_chart(breakdown_df.set_index("Heuristic"))

        # Actions
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            if st.button(f"📋 Copy Name", key=f"copy_{idx}"):
                st.code(pkg["name"], language=None)

        with col_b:
            casefile_path = Path("data/feeds") / selected_date / f"case_{pkg['ecosystem']}_{pkg['name']}.md"
            if casefile_path.exists():
                st.markdown(f"[📄 View Casefile]({casefile_path})")

        with col_c:
            with st.popover("🔍 Raw JSON"):
                st.json(pkg)

st.markdown("---")

# Export options
st.markdown("### 📥 Export Options")

col1, col2 = st.columns(2)

with col1:
    if st.button("Download as CSV"):
        df = pd.DataFrame(filtered_data)
        csv = df.to_csv(index=False)
        st.download_button(
            "⬇️ Download CSV",
            csv,
            file_name=f"phantom_feed_{selected_date}.csv",
            mime="text/csv",
        )

with col2:
    if st.button("Download Markdown Report"):
        md_path = Path("data/feeds") / selected_date / "feed.md"
        if md_path.exists():
            with open(md_path) as f:
                st.download_button(
                    "⬇️ Download Markdown",
                    f.read(),
                    file_name=f"phantom_feed_{selected_date}.md",
                    mime="text/markdown",
                )
