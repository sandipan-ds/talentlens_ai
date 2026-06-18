"""
Streamlit UI for recruiter weight configuration across all job roles.

This app allows recruiters to:
1. Select a job role from a dropdown
2. Assign importance weights (0-10) to each evaluation item
3. Save the configuration with normalization
4. Track completion status with visual indicators
"""

from pathlib import Path
import json
import streamlit as st
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "Job descriptions"

# Page config
st.set_page_config(
    page_title="HireIntel AI - Weight Configuration",
    page_icon="⚙️",
    layout="wide"
)

st.title("🎯 HireIntel AI - Recruiter Weight Configuration")
st.markdown(
    "Configure importance weights for job roles. Select a role, assign weightages, and save your configuration."
)

# Discover available roles
def get_available_roles() -> List[str]:
    """Find all role folders with weight templates."""
    roles = []
    for role_dir in sorted(DATA_DIR.iterdir()):
        if role_dir.is_dir():
            template_path = role_dir / f"{role_dir.name}_WeightTemplate.json"
            if template_path.exists():
                roles.append(role_dir.name)
    return roles


def load_template(role: str) -> Dict[str, Any]:
    """Load a weight template for a role."""
    template_path = DATA_DIR / role / f"{role}_WeightTemplate.json"
    with template_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_output_path(role: str) -> Path:
    """Get the output path for a filled weight config."""
    return DATA_DIR / role / f"{role}_WeightConfig_filled.json"


def normalize_weights(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize employer weight ratings to a 100-point scale."""
    all_items = []
    for category in config.get("categories", []):
        for item in category.get("items", []):
            importance = item.get("importance")
            if importance is not None:
                all_items.append(importance)

    total_max = 10 * len(all_items) if all_items else 0
    
    if total_max > 0:
        scale = 100.0 / total_max
    else:
        scale = 0.0

    for category in config.get("categories", []):
        for item in category.get("items", []):
            importance = item.get("importance")
            if importance is not None:
                item["normalized_importance"] = round(importance * scale, 2)

    config["max_score"] = total_max
    config["scale_factor"] = round(scale, 4)
    return config


def save_config(config: Dict[str, Any], role: str) -> None:
    """Save the filled weight config."""
    output_path = get_output_path(role)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def is_role_completed(role: str) -> bool:
    """Check if a role has a completed weight config."""
    output_path = get_output_path(role)
    return output_path.exists()


# Left sidebar for role selection and status
with st.sidebar:
    st.markdown("## 📋 Job Roles")
    roles = get_available_roles()
    
    # Display role completion status
    st.markdown("### Status")
    for role in roles:
        completed = is_role_completed(role)
        status_icon = "✅" if completed else "⭕"
        st.markdown(f"{status_icon} {role}")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### Select Job Role")
    roles = get_available_roles()
    
    if not roles:
        st.error("❌ No job roles found in data/Job descriptions/")
    else:
        selected_role = st.selectbox(
            "Choose a role to configure weights:",
            roles,
            key="role_selector"
        )
        
        if selected_role:
            template = load_template(selected_role)
            config = {
                "role": template.get("role"),
                "instructions": template.get("instructions"),
                "category_scale": template.get("category_scale"),
                "categories": []
            }
            
            st.markdown(f"### ⚙️ Configure weights for: **{selected_role}**")
            st.info(
                "Rate each item from 0 to 10. Higher ratings indicate higher importance for this role."
            )
            
            # Build form with categories and sliders
            for category in template.get("categories", []):
                with st.expander(f"📌 {category['name']}", expanded=True):
                    updated_items = []
                    for item in category.get("items", []):
                        col_name, col_slider = st.columns([2, 1])
                        
                        with col_name:
                            st.markdown(f"**{item['name']}**")
                            st.caption(item['description'])
                        
                        with col_slider:
                            importance = st.slider(
                                label=f"{item['name']} importance",
                                min_value=0,
                                max_value=10,
                                value=item.get("importance", 5),
                                step=1,
                                label_visibility="collapsed",
                                key=f"{selected_role}_{item['name']}"
                            )
                        
                        updated_item = item.copy()
                        updated_item["importance"] = importance
                        updated_items.append(updated_item)
                    
                    config["categories"].append({
                        "name": category["name"],
                        "items": updated_items
                    })
            
            # Save button
            st.markdown("---")
            col_save, col_preview = st.columns([1, 1])
            
            with col_save:
                if st.button(f"💾 Save {selected_role} Configuration", key=f"save_{selected_role}"):
                    saved_config = normalize_weights(config)
                    save_config(saved_config, selected_role)
                    st.success(f"✅ {selected_role} configuration saved successfully!")
                    st.balloons()
            
            with col_preview:
                if st.button("👁️ Preview Normalized Weights", key=f"preview_{selected_role}"):
                    preview_config = normalize_weights(config)
                    st.json({
                        "role": preview_config.get("role"),
                        "max_score": preview_config.get("max_score"),
                        "scale_factor": preview_config.get("scale_factor")
                    })

with col2:
    st.markdown("### 📊 Summary")
    if roles:
        total_roles = len(roles)
        completed_roles = sum(1 for role in roles if is_role_completed(role))
        completion_pct = (completed_roles / total_roles * 100) if total_roles > 0 else 0
        
        st.metric(label="Total Roles", value=total_roles)
        st.metric(label="Completed", value=completed_roles)
        st.metric(label="Completion %", value=f"{completion_pct:.0f}%")
        
        st.markdown("---")
        st.markdown("### Next Steps")
        st.markdown(
            """
            1. Configure all job roles with importance weights
            2. Review the normalization scale for each role
            3. Resume parsing and evaluation will use these weights
            """
        )


st.markdown("---")
st.caption("HireIntel AI © 2026 - Transparent Candidate Intelligence Platform")
