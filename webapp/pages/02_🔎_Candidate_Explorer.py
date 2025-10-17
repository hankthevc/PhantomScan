"""Candidate Explorer page - Search and investigate packages."""

from pathlib import Path

import pandas as pd
import streamlit as st

from radar.reports.casefile import generate_casefile
from radar.utils import load_json
from webapp.utils import get_risk_badge, get_ecosystem_badge, get_risk_level, format_score_display

st.set_page_config(page_title="Candidate Explorer", page_icon="🔎", layout="wide")

# Add custom CSS
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

st.title("🔎 Candidate Explorer")
st.markdown("Search and investigate individual package candidates")

st.markdown("---")


@st.cache_data
def load_all_candidates() -> list[dict]:
    """Load all candidates from available feeds."""
    feeds_dir = Path("data/feeds")
    if not feeds_dir.exists():
        return []

    all_candidates = []
    for date_dir in feeds_dir.iterdir():
        if date_dir.is_dir():
            feed_path = date_dir / "topN.json"
            if feed_path.exists():
                feed_data = load_json(feed_path)
                if feed_data:
                    for pkg in feed_data:
                        pkg["feed_date"] = date_dir.name
                    all_candidates.extend(feed_data)

    return all_candidates


# Load all candidates
candidates = load_all_candidates()

if not candidates:
    st.error("No candidate data available. Run `radar run-all` to generate feeds.")
    st.stop()

st.success(f"📦 Loaded {len(candidates)} candidates from all feeds")

# Search interface
st.markdown("### 🔍 Search")

col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input(
        "Search by package name",
        placeholder="Enter package name (e.g., 'openai-cli', 'requests2')",
    )

with col2:
    ecosystem_search = st.selectbox("Ecosystem", ["All", "pypi", "npm"])

# Filter candidates
filtered = candidates

if search_query:
    filtered = [c for c in filtered if search_query.lower() in c["name"].lower()]

if ecosystem_search != "All":
    filtered = [c for c in filtered if c["ecosystem"] == ecosystem_search]

# Sort options
sort_by = st.radio("Sort by", ["Score (High to Low)", "Date (Newest First)", "Name (A-Z)"], horizontal=True)

if sort_by == "Score (High to Low)":
    filtered = sorted(filtered, key=lambda x: x["score"], reverse=True)
elif sort_by == "Date (Newest First)":
    filtered = sorted(filtered, key=lambda x: x["feed_date"], reverse=True)
else:
    filtered = sorted(filtered, key=lambda x: x["name"])

st.markdown(f"**Found {len(filtered)} matching packages**")

st.markdown("---")

# Display results
if filtered:
    # Create a dataframe for the table view
    table_data = []
    for pkg in filtered:
        level, emoji, _ = get_risk_level(pkg['score'])
        table_data.append(
            {
                "Name": pkg["name"],
                "Ecosystem": pkg["ecosystem"].upper(),
                "Risk": f"{emoji} {level}",
                "Score": f"{pkg['score']:.2f}",
                "Published": pkg["created_at"][:10],
                "Feed Date": pkg["feed_date"],
                "Maintainers": pkg["maintainers_count"],
                "Has Scripts": "⚠️" if pkg["has_install_scripts"] else "✓",
            }
        )

    df = pd.DataFrame(table_data)

    # Interactive table
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Detailed view
    st.markdown("### 📋 Detailed View")

    selected_name = st.selectbox(
        "Select a package to investigate",
        options=[pkg["name"] for pkg in filtered],
        format_func=lambda x: f"{x} ({next(p['ecosystem'] for p in filtered if p['name'] == x)}) - Score: {next(p['score'] for p in filtered if p['name'] == x):.2f}",
    )

    if selected_name:
        # Find the selected package
        pkg = next((p for p in filtered if p["name"] == selected_name), None)

        if pkg:
            # Header with badges
            col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
            
            with col_h1:
                st.markdown(f"## `{pkg['name']}`")
            
            with col_h2:
                st.markdown(get_ecosystem_badge(pkg['ecosystem']), unsafe_allow_html=True)
            
            with col_h3:
                st.markdown(get_risk_badge(pkg['score']), unsafe_allow_html=True)
            
            st.markdown("---")
            
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Version**: {pkg['version']}")
                st.markdown(f"**Published**: {pkg['created_at'][:10]}")
                st.markdown(f"**Detected**: {pkg['feed_date']}")
                st.markdown(f"**Risk Score**: {format_score_display(pkg['score'])}")
                
                # Risk assessment
                level, emoji, _ = get_risk_level(pkg["score"])
                if level == "CRITICAL":
                    st.error(f"{emoji} {level} RISK")
                elif level == "HIGH":
                    st.error(f"{emoji} {level} RISK")
                elif level == "MEDIUM":
                    st.warning(f"{emoji} {level} RISK")
                else:
                    st.success(f"{emoji} {level} RISK")

                # Risk factors
                st.markdown("**⚠️ Risk Factors**:")
                for reason in pkg["reasons"]:
                    st.markdown(f"- {reason}")

            with col2:
                st.markdown("**Metadata**")

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
                    st.warning("⚠️ Has install scripts")

            # Score breakdown
            st.markdown("---")
            st.markdown("### 📊 Score Breakdown")

            breakdown_data = {
                "Name Suspicion": pkg["breakdown"]["name_suspicion"],
                "Newness": pkg["breakdown"]["newness"],
                "Repo Missing": pkg["breakdown"]["repo_missing"],
                "Maintainer Reputation": pkg["breakdown"]["maintainer_reputation"],
                "Script Risk": pkg["breakdown"]["script_risk"],
            }

            col1, col2 = st.columns([2, 1])

            with col1:
                breakdown_df = pd.DataFrame(
                    {
                        "Heuristic": list(breakdown_data.keys()),
                        "Score": list(breakdown_data.values()),
                    }
                )
                st.bar_chart(breakdown_df.set_index("Heuristic"))

            with col2:
                for key, value in breakdown_data.items():
                    st.metric(key, f"{value:.2f}")

            # Actions
            st.markdown("---")
            st.markdown("### 🔧 Actions")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📄 Generate Casefile"):
                    with st.spinner("Generating casefile..."):
                        output_path = generate_casefile(pkg, pkg["feed_date"])
                        st.success(f"✅ Casefile generated: {output_path}")

                        # Display preview
                        with open(output_path) as f:
                            st.markdown("**Preview**:")
                            st.markdown(f.read()[:1000] + "...")

            with col2:
                if st.button("📋 Copy Install Command"):
                    if pkg["ecosystem"] == "pypi":
                        cmd = f"pip install {pkg['name']}=={pkg['version']}"
                    else:
                        cmd = f"npm install {pkg['name']}@{pkg['version']}"

                    st.code(cmd)

            with col3:
                with st.popover("🔍 Raw JSON"):
                    st.json(pkg)

else:
    st.info("No packages match your search criteria.")
