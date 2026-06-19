"""Streamlit entry point for the recruiter UI."""

import streamlit as st

from hireintel_ai.core.config import get_settings


def main() -> None:
    """Render the initial Streamlit application shell.

    Side Effects:
        Writes Streamlit UI elements to the active page.
    """
    settings = get_settings()
    st.set_page_config(page_title=settings.app_name)
    st.title(settings.app_name)
    st.write("Recruiter-controlled candidate intelligence workspace.")


if __name__ == "__main__":
    main()

