"""PhantomScan Streamlit App - Main Entry Point."""

import httpx
import streamlit as st

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

# Quick Score Panel
st.markdown("## ⚡ Quick Score")
st.markdown("Score any package in real-time using the PhantomScan API")

with st.expander("🔍 Score a Package", expanded=False):
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        quick_ecosystem = st.selectbox(
            "Ecosystem",
            options=["PyPI", "npm"],
            key="quick_ecosystem",
        )

    with col2:
        quick_name = st.text_input(
            "Package Name",
            placeholder="e.g., requests, express",
            key="quick_name",
        )

    with col3:
        quick_strict = st.toggle(
            "Strict Mode", value=True, help="Reject packages not found in registry"
        )

    col3, col4 = st.columns([1, 1])

    with col3:
        quick_version = st.text_input(
            "Version (optional)",
            placeholder="e.g., 1.0.0",
            value="0.0.0",
            key="quick_version",
        )

    with col4:
        quick_maintainers = st.number_input(
            "Maintainers Count",
            min_value=1,
            max_value=100,
            value=1,
            key="quick_maintainers",
        )

    if st.button("🚀 Score Package", type="primary"):
        if not quick_name:
            st.error("Please enter a package name")
        else:
            with st.spinner("Scoring package..."):
                try:
                    # Call the FastAPI endpoint
                    api_url = "http://localhost:8000/score"
                    payload = {
                        "ecosystem": quick_ecosystem.lower(),
                        "name": quick_name,
                        "version": quick_version or "0.0.0",
                        "maintainers_count": quick_maintainers,
                        "strict_exists": quick_strict,
                    }

                    response = httpx.post(api_url, json=payload, timeout=10.0)

                    if response.status_code == 200:
                        data = response.json()

                        # Display score badge
                        score = data["score"]
                        score_color = "🔴" if score > 0.7 else "🟡" if score > 0.4 else "🟢"
                        st.markdown(f"### {score_color} Risk Score: {score:.2f} / 1.0")

                        # Display breakdown table
                        st.markdown("#### Score Breakdown")
                        breakdown = data["breakdown"]

                        # Show existence status if present
                        if "exists_in_registry" in breakdown:
                            if breakdown["exists_in_registry"]:
                                st.success("✅ Package verified in registry")
                            else:
                                reason = breakdown.get("not_found_reason", "unknown")
                                st.warning(f"⚠️ Package not found in registry (reason: {reason})")

                        breakdown_data = []
                        for key, value in breakdown.items():
                            if key not in ["exists_in_registry", "not_found_reason"]:
                                if isinstance(value, (int, float)):
                                    breakdown_data.append(
                                        {
                                            "Component": key.replace("_", " ").title(),
                                            "Score": f"{value:.2f}",
                                        }
                                    )

                        st.table(breakdown_data)

                        # Display reasons
                        st.markdown("#### Risk Indicators")
                        reasons = data.get("reasons", [])
                        if reasons:
                            for reason in reasons:
                                st.markdown(f"- {reason}")
                        else:
                            st.info("No significant risk indicators detected")

                    elif response.status_code == 404:
                        st.error(
                            f"❌ Package '{quick_name}' not found in registry (strict mode enabled)"
                        )
                        st.info("💡 Disable strict mode to score packages that may not exist yet")
                    elif response.status_code == 503:
                        st.error(
                            "⏱️ Scoring timeout - enrichment services may be temporarily unavailable"
                        )
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")

                except httpx.ConnectError:
                    st.error(
                        "❌ Cannot connect to API. Make sure the FastAPI server is running on port 8000."
                    )
                except httpx.TimeoutException:
                    st.error("⏱️ Request timeout - the API took too long to respond")
                except Exception as e:
                    st.error(f"Error scoring package: {e!s}")

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
