"""Settings page - Configure policy and app settings."""

import os
from pathlib import Path

import streamlit as st
import yaml

from radar.utils import load_policy, save_policy

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

st.title("⚙️ Settings")
st.markdown("Configure scoring policy and operational parameters")

st.markdown("---")

# Load current policy
try:
    policy = load_policy()
    policy_dict = policy.model_dump()
except Exception as e:
    st.error(f"Failed to load policy: {e}")
    st.stop()

# Tabs for different settings sections
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Scoring Weights", "🧠 Heuristics", "📊 Feed Config", "🌐 Network"])

# Tab 1: Scoring Weights
with tab1:
    st.markdown("### 🎯 Scoring Weights")
    st.info("Adjust the importance of each heuristic. Weights must sum to 1.0.")

    weights = policy_dict["weights"].copy()

    col1, col2 = st.columns(2)

    with col1:
        weights["name_suspicion"] = st.slider(
            "Name Suspicion",
            0.0,
            1.0,
            weights["name_suspicion"],
            0.05,
            help="Weight for suspicious naming patterns",
        )

        weights["newness"] = st.slider(
            "Newness",
            0.0,
            1.0,
            weights["newness"],
            0.05,
            help="Weight for package age",
        )

        weights["repo_missing"] = st.slider(
            "Repo Missing",
            0.0,
            1.0,
            weights["repo_missing"],
            0.05,
            help="Weight for missing repository/homepage",
        )

    with col2:
        weights["maintainer_reputation"] = st.slider(
            "Maintainer Reputation",
            0.0,
            1.0,
            weights["maintainer_reputation"],
            0.05,
            help="Weight for maintainer count",
        )

        weights["script_risk"] = st.slider(
            "Script Risk",
            0.0,
            1.0,
            weights["script_risk"],
            0.05,
            help="Weight for install scripts (npm)",
        )

    # Check if weights sum to 1.0
    weights_sum = sum(weights.values())
    if abs(weights_sum - 1.0) > 0.001:
        st.warning(f"⚠️ Weights sum to {weights_sum:.3f} (should be 1.0)")
    else:
        st.success(f"✅ Weights sum to {weights_sum:.3f}")

    policy_dict["weights"] = weights

# Tab 2: Heuristics
with tab2:
    st.markdown("### 🧠 Heuristic Parameters")

    heuristics = policy_dict["heuristics"].copy()

    # New package days
    heuristics["new_package_days"] = st.number_input(
        "New Package Threshold (days)",
        min_value=1,
        max_value=365,
        value=heuristics["new_package_days"],
        help="Packages younger than this are considered 'new'",
    )

    # Fuzzy threshold
    heuristics["fuzzy_threshold"] = st.number_input(
        "Fuzzy Match Threshold",
        min_value=1,
        max_value=50,
        value=heuristics["fuzzy_threshold"],
        help="Distance threshold for similarity matching (lower = more strict)",
    )

    st.markdown("---")

    # Suspicious prefixes
    st.markdown("**Suspicious Prefixes** (brand/API names)")
    prefixes_text = st.text_area(
        "One per line",
        value="\n".join(heuristics["suspicious_prefixes"]),
        height=150,
        help="Package names starting with these trigger suspicion",
    )
    heuristics["suspicious_prefixes"] = [
        p.strip() for p in prefixes_text.split("\n") if p.strip()
    ]

    # Suspicious suffixes
    st.markdown("**Suspicious Suffixes** (common tropes)")
    suffixes_text = st.text_area(
        "One per line",
        value="\n".join(heuristics["suspicious_suffixes"]),
        height=150,
        help="Package names ending with these trigger suspicion",
    )
    heuristics["suspicious_suffixes"] = [
        s.strip() for s in suffixes_text.split("\n") if s.strip()
    ]

    policy_dict["heuristics"] = heuristics

# Tab 3: Feed Config
with tab3:
    st.markdown("### 📊 Feed Generation")

    feed = policy_dict["feed"].copy()

    col1, col2 = st.columns(2)

    with col1:
        feed["top_n"] = st.number_input(
            "Top N Candidates",
            min_value=1,
            max_value=200,
            value=feed["top_n"],
            help="Number of candidates to include in daily feed",
        )

    with col2:
        feed["min_score"] = st.slider(
            "Minimum Score",
            0.0,
            1.0,
            feed["min_score"],
            0.05,
            help="Only include candidates with score >= this",
        )

    policy_dict["feed"] = feed

# Tab 4: Network
with tab4:
    st.markdown("### 🌐 Network Configuration")

    network = policy_dict["network"].copy()

    network["user_agent"] = st.text_input(
        "User-Agent",
        value=network["user_agent"],
        help="User-Agent header for API requests",
    )

    network["pool_size"] = st.number_input(
        "Connection Pool Size",
        min_value=1,
        max_value=50,
        value=network["pool_size"],
        help="Number of concurrent connections",
    )

    policy_dict["network"] = network

    st.markdown("---")

    # Offline mode indicator
    offline_mode = os.environ.get("RADAR_OFFLINE", "0") == "1"

    if offline_mode:
        st.warning("⚠️ Offline mode is ENABLED (RADAR_OFFLINE=1)")
        st.info("The radar will use seed data instead of live API calls.")
    else:
        st.success("✅ Online mode - Live API calls enabled")

st.markdown("---")

# Save/Reset buttons
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("💾 Save Changes", type="primary"):
        try:
            # Reconstruct policy object
            from radar.types import PolicyConfig

            new_policy = PolicyConfig(**policy_dict)
            save_policy(new_policy)

            st.success("✅ Policy saved successfully!")
            st.balloons()

            # Clear cache to reload policy
            st.cache_data.clear()

        except Exception as e:
            st.error(f"Failed to save policy: {e}")

with col2:
    if st.button("🔄 Reset to Default"):
        st.warning("Reset functionality would restore default config/policy.yml")
        st.info("To reset, replace config/policy.yml with the default version from the repository.")

st.markdown("---")

# Policy preview
with st.expander("📄 View Full Policy YAML"):
    policy_yaml = yaml.dump(policy_dict, default_flow_style=False, sort_keys=False)
    st.code(policy_yaml, language="yaml")

st.markdown("---")

# Info
st.info(
    """
    **Note**: Changes to scoring weights and heuristics will affect future radar runs.
    Existing scored candidates and feeds are not automatically recalculated.

    To apply new settings:
    1. Save changes here
    2. Run `radar run-all` to regenerate feeds
    3. Refresh the app to see updated results
    """
)
