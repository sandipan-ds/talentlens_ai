from pathlib import Path
import json
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "data" / "Job descriptions" / "BusinessAnalyst" / "BusinessAnalyst_WeightTemplate.json"
OUTPUT_PATH = ROOT / "data" / "Job descriptions" / "BusinessAnalyst" / "BusinessAnalyst_WeightConfig_filled.json"


def load_template(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_weights(config: dict) -> dict:
    all_items = []
    for category in config["categories"]:
        for item in category["items"]:
            importance = item.get("importance")
            if importance is not None:
                all_items.append(importance)

    total_score = sum(all_items)
    max_score = 10 * len(all_items) if all_items else 0
    normalized_items = []

    if max_score > 0:
        scale = 100.0 / max_score
    else:
        scale = 0.0

    for category in config["categories"]:
        for item in category["items"]:
            importance = item.get("importance")
            if importance is not None:
                item["normalized_importance"] = round(importance * scale, 2)
                normalized_items.append(item)

    config["max_score"] = max_score
    config["scale_factor"] = round(scale, 4)
    return config


def save_config(config: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def main() -> None:
    st.set_page_config(page_title="Business Analyst Weight Configuration")
    st.title("Business Analyst Lead Employer Weighting")
    st.write(
        "Use this form to rate each Business Analyst requirement on a scale of 0 to 10. "
        "The values will be saved and normalized to a 100-point scale."
    )

    template = load_template(TEMPLATE_PATH)
    config = template.copy()
    config["categories"] = []

    for category in template["categories"]:
        with st.expander(category["name"], expanded=True):
            updated_items = []
            for item in category["items"]:
                importance = st.slider(
                    label=f"{item['name']}: {item['description']}",
                    min_value=0,
                    max_value=10,
                    value=item.get("importance", 5),
                    step=1,
                )
                updated_item = item.copy()
                updated_item["importance"] = importance
                updated_items.append(updated_item)

            config["categories"].append({"name": category["name"], "items": updated_items})

    if st.button("Save Employer Weight Configuration"):
        saved_config = normalize_weights(config)
        save_config(saved_config, OUTPUT_PATH)
        st.success(f"Saved filled config to {OUTPUT_PATH}")
        st.json({
            "max_score": saved_config["max_score"],
            "scale_factor": saved_config["scale_factor"],
        })

    st.markdown("---")
    st.subheader("Normalization example")
    st.write(
        "If the employer ratings sum to a total raw score, the app will normalize the weights so "
        "the maximum possible score equals 100. This keeps scoring comparable across role definitions."
    )

    if st.button("Preview Normalized Weights"):
        preview_config = normalize_weights(config)
        for category in preview_config["categories"]:
            st.markdown(f"**{category['name']}**")
            for item in category["items"]:
                st.write(
                    f"{item['name']}: importance={item['importance']} -> normalized={item.get('normalized_importance', 0)}"
                )


if __name__ == "__main__":
    main()
