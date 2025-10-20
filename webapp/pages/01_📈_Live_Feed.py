"""Live Feed page - Browse daily suspicious packages."""

from pathlib import Path

import pandas as pd
import streamlit as st

from radar.utils import load_json

st.set_page_config(page_title="Live Feed", page_icon="📈", layout="wide")

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
def load_watchlist_for_date(date_str: str) -> list[dict] | None:
    """Load watchlist JSON for a specific date."""
    watchlist_path = Path("data/feeds") / date_str / "watchlist.json"
    if not watchlist_path.exists():
        return []
    return load_json(watchlist_path) or []


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


# Date selector
col1, col2 = st.columns([1, 3])

with col1:
    available_dates = get_available_dates()

    if not available_dates:
        st.error("No feed data available. Run `radar run-all` to generate feeds.")
        st.stop()

    selected_date = st.selectbox(
        "Select Date",
        options=available_dates,
        index=0,
    )

with col2:
    st.info(f"📅 Showing feed for **{selected_date}** ({len(available_dates)} dates available)")

# Load feed and watchlist
feed_data = load_feed_for_date(selected_date)
watchlist_data = load_watchlist_for_date(selected_date)

if not feed_data:
    st.error(f"Failed to load feed for {selected_date}")
    st.stop()

st.markdown("---")

# Create tabs for Active Packages vs Watchlist
tab1, tab2 = st.tabs(["✅ Active Packages", "⚠️ Watchlist (Not Yet in Registry)"])

with tab1:
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
            key="active_ecosystem_filter",
        )

    with col2:
        min_score_filter = st.slider(
            "Minimum Score", 0.0, 1.0, 0.3, 0.05, key="active_score_filter"
        )

    with col3:
        search_term = st.text_input("Search by name", "", key="active_search")

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
        with st.expander(
            f"#{idx} {pkg['name']} ({pkg['ecosystem']}) - Score: {pkg['score']:.2f}",
            expanded=idx <= 3,
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Package**: `{pkg['name']}`")
                st.markdown(f"**Version**: {pkg['version']}")
                st.markdown(f"**Ecosystem**: {pkg['ecosystem'].upper()}")
                st.markdown(f"**Published**: {pkg['created_at'][:10]}")
                st.markdown(f"**Risk Score**: {pkg['score']:.2f} / 1.00")

                # Existence flag
                if "breakdown" in pkg and "exists_in_registry" in pkg["breakdown"]:
                    exists = pkg["breakdown"]["exists_in_registry"]
                    if exists:
                        st.success("✅ Verified in registry")
                    else:
                        reason = pkg["breakdown"].get("not_found_reason", "unknown")
                        st.warning(f"⚠️ Not found in registry (reason: {reason})")

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
                if st.button("📋 Copy Name", key=f"copy_{idx}"):
                    st.code(pkg["name"], language=None)

            with col_b:
                casefile_path = (
                    Path("data/feeds") / selected_date / f"case_{pkg['ecosystem']}_{pkg['name']}.md"
                )
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
        if st.button("Download as CSV", key="download_active_csv"):
            df = pd.DataFrame(filtered_data)
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                csv,
                file_name=f"phantom_feed_{selected_date}.csv",
                mime="text/csv",
                key="download_active_csv_btn",
            )

    with col2:
        if st.button("Download Markdown Report", key="download_active_md"):
            md_path = Path("data/feeds") / selected_date / "feed.md"
            if md_path.exists():
                with open(md_path) as f:
                    st.download_button(
                        "⬇️ Download Markdown",
                        f.read(),
                        file_name=f"phantom_feed_{selected_date}.md",
                        mime="text/markdown",
                        key="download_active_md_btn",
                    )

with tab2:
    # Watchlist tab
    if not watchlist_data:
        st.info("🎉 No packages in watchlist! All detected packages exist in their registries.")
    else:
        st.warning(
            f"⚠️ **{len(watchlist_data)} package(s)** detected but not found in registry. "
            "These may be false positives, removed packages, or packages that haven't propagated yet."
        )

        # Watchlist metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Watchlist Count", len(watchlist_data))

        with col2:
            pypi_wl = sum(1 for p in watchlist_data if p["ecosystem"] == "pypi")
            st.metric("PyPI", pypi_wl)

        with col3:
            npm_wl = sum(1 for p in watchlist_data if p["ecosystem"] == "npm")
            st.metric("npm", npm_wl)

        st.markdown("---")

        # Watchlist filters
        wl_ecosystem_filter = st.multiselect(
            "Filter by Ecosystem",
            options=["pypi", "npm"],
            default=["pypi", "npm"],
            key="watchlist_ecosystem_filter",
        )

        wl_search = st.text_input("Search watchlist", "", key="watchlist_search")

        filtered_watchlist = [
            p
            for p in watchlist_data
            if p["ecosystem"] in wl_ecosystem_filter
            and (not wl_search or wl_search.lower() in p["name"].lower())
        ]

        st.markdown(f"**Showing {len(filtered_watchlist)} of {len(watchlist_data)} packages**")

        st.markdown("---")

        # Display watchlist entries
        for idx, entry in enumerate(filtered_watchlist, 1):
            with st.expander(
                f"#{idx} {entry['name']} ({entry['ecosystem']}) - Not Found: {entry['not_found_reason']}",
                expanded=idx <= 5,
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**Package**: `{entry['name']}`")
                    st.markdown(f"**Ecosystem**: {entry['ecosystem'].upper()}")
                    st.markdown(f"**First Seen**: {entry['first_seen_at'][:19]}")
                    st.markdown(f"**Reason**: {entry['not_found_reason']}")

                    # Explain reasons
                    reason = entry["not_found_reason"]
                    if reason == "404":
                        st.info(
                            "📝 Package not found in registry. May be a false positive or removed package."
                        )
                    elif reason == "timeout":
                        st.warning("⏱️ Registry request timed out. May exist but was unreachable.")
                    elif reason == "offline":
                        st.info("🔌 Checked in offline mode. Actual status unknown.")
                    elif reason == "error":
                        st.error("❌ Error checking registry. Status unknown.")

                with col2:
                    st.markdown("**Actions**:")
                    ecosystem_val = entry["ecosystem"]
                    name_val = entry["name"]

                    if ecosystem_val == "pypi":
                        registry_url = f"https://pypi.org/project/{name_val}/"
                    else:  # npm
                        registry_url = f"https://www.npmjs.com/package/{name_val}"

                    st.markdown(f"🔗 [Check Registry]({registry_url})")

                    if st.button("📋 Copy Name", key=f"wl_copy_{idx}"):
                        st.code(name_val, language=None)

                with st.popover("🔍 Raw JSON", key=f"wl_json_{idx}"):
                    st.json(entry)

        st.markdown("---")

        # Watchlist export
        st.markdown("### 📥 Export Watchlist")

        if st.button("Download Watchlist as CSV", key="download_wl_csv"):
            df = pd.DataFrame(filtered_watchlist)
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                csv,
                file_name=f"watchlist_{selected_date}.csv",
                mime="text/csv",
                key="download_wl_csv_btn",
            )
