"""Casefile Generator page - Bulk generate investigation reports."""

from pathlib import Path

import streamlit as st

from radar.reports.casefile import generate_casefile
from radar.utils import load_json
from webapp.utils import get_risk_level

st.set_page_config(page_title="Casefile Generator", page_icon="📄", layout="wide")

st.title("📄 Casefile Generator")
st.markdown("Generate investigation reports for suspicious packages")

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


# Date selector
available_dates = get_available_dates()

if not available_dates:
    st.error("No feed data available. Run `radar run-all` to generate feeds.")
    st.stop()

selected_date = st.selectbox("Select Feed Date", options=available_dates, index=0)

feed_data = load_feed_for_date(selected_date)

if not feed_data:
    st.error(f"Failed to load feed for {selected_date}")
    st.stop()

st.success(f"📦 Loaded {len(feed_data)} candidates from {selected_date}")

st.markdown("---")

# Selection mode
st.markdown("### 📝 Select Packages")

mode = st.radio(
    "Selection Mode",
    ["Select Individual Packages", "Bulk Generate (Top N)", "Generate All"],
    horizontal=True,
)

selected_packages = []

if mode == "Select Individual Packages":
    # Multi-select interface
    selected_names = st.multiselect(
        "Choose packages to generate casefiles for",
        options=[f"{pkg['name']} ({pkg['ecosystem']}) - Score: {pkg['score']:.2f}" for pkg in feed_data],
        default=[],
    )

    # Parse selected names
    for display_name in selected_names:
        name = display_name.split(" (")[0]
        pkg = next((p for p in feed_data if p["name"] == name), None)
        if pkg:
            selected_packages.append(pkg)

elif mode == "Bulk Generate (Top N)":
    top_n = st.slider("Number of top packages", 1, len(feed_data), min(10, len(feed_data)))
    selected_packages = feed_data[:top_n]

    st.info(f"Selected top {top_n} packages by score")

else:  # Generate All
    selected_packages = feed_data
    st.info(f"Selected all {len(feed_data)} packages")

st.markdown(f"**{len(selected_packages)} packages selected**")

st.markdown("---")

# Preview selected
if selected_packages:
    st.markdown("### 👀 Preview Selected Packages")

    preview_data = []
    for pkg in selected_packages[:10]:  # Show max 10 in preview
        level, emoji, _ = get_risk_level(pkg['score'])
        preview_data.append(
            {
                "Name": pkg["name"],
                "Ecosystem": pkg["ecosystem"].upper(),
                "Risk": f"{emoji} {level}",
                "Score": f"{pkg['score']:.2f}",
                "Published": pkg["created_at"][:10],
            }
        )

    import pandas as pd

    st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)

    if len(selected_packages) > 10:
        st.info(f"... and {len(selected_packages) - 10} more")

st.markdown("---")

# Generation options
st.markdown("### ⚙️ Generation Options")

col1, col2 = st.columns(2)

with col1:
    output_dir = st.text_input(
        "Output Directory",
        value=f"data/feeds/{selected_date}",
        help="Where to save generated casefiles",
    )

with col2:
    preview_enabled = st.checkbox("Show preview after generation", value=True)

st.markdown("---")

# Generate button
if st.button("🚀 Generate Casefiles", type="primary", disabled=len(selected_packages) == 0):
    progress_bar = st.progress(0)
    status_text = st.empty()

    generated_files = []

    for idx, pkg in enumerate(selected_packages):
        status_text.text(f"Generating casefile for {pkg['name']}... ({idx + 1}/{len(selected_packages)})")

        try:
            output_path = generate_casefile(pkg, selected_date, Path(output_dir))
            generated_files.append(output_path)
        except Exception as e:
            st.error(f"Failed to generate casefile for {pkg['name']}: {e}")

        progress_bar.progress((idx + 1) / len(selected_packages))

    status_text.text("")
    progress_bar.empty()

    st.success(f"✅ Generated {len(generated_files)} casefiles!")

    # Show generated files
    st.markdown("### 📁 Generated Files")

    for file_path in generated_files[:5]:  # Show first 5
        st.markdown(f"- `{file_path}`")

    if len(generated_files) > 5:
        st.info(f"... and {len(generated_files) - 5} more files")

    # Preview first casefile
    if preview_enabled and generated_files:
        st.markdown("---")
        st.markdown("### 📄 Preview (First Casefile)")

        with open(generated_files[0]) as f:
            content = f.read()

        with st.expander(f"View {generated_files[0].name}", expanded=True):
            st.markdown(content)

    # Download option
    st.markdown("---")

    if st.button("📦 Create ZIP Archive"):
        import zipfile
        from io import BytesIO

        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in generated_files:
                zip_file.write(file_path, file_path.name)

        st.download_button(
            "⬇️ Download ZIP",
            zip_buffer.getvalue(),
            file_name=f"phantom_casefiles_{selected_date}.zip",
            mime="application/zip",
        )

st.markdown("---")

# Info box
st.info(
    """
    **Casefile Format**: Casefiles are Markdown documents containing:
    - Executive summary with risk assessment
    - Detailed metadata and score breakdown
    - Investigation checklist
    - Recommended actions
    - SIEM detection guidance

    Use these reports to document your investigation process and share findings with your team.
    """
)
