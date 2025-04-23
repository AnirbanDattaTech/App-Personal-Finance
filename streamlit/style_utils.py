# streamlit/style_utils.py
import streamlit as st
import logging
from pathlib import Path # Use pathlib for robust path handling

# --- Assume styles.css is in the same directory as this script ---
CSS_FILE = Path(__file__).parent / "styles.css"

def load_css():
    """Loads CSS from the styles.css file located in the same directory."""
    if CSS_FILE.is_file():
        try:
            with open(CSS_FILE, "r") as f:
                css = f.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
            # logging.info(f"Successfully loaded CSS from {CSS_FILE}") # Optional: for debugging
        except Exception as e:
            logging.error(f"Error reading CSS file {CSS_FILE}: {e}")
            st.error("Failed to load page styles.")
    else:
        logging.warning(f"CSS file not found at expected location: {CSS_FILE}")
        # st.warning("Page styling may be incomplete (CSS not found).")