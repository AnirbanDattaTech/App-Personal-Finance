# style_utils.py
import streamlit as st
import logging # For logging errors
import os # For checking file existence

def load_css(file_path: str = "styles.css"):
    """
    Loads CSS from a file and injects it into the Streamlit app.

    Args:
        file_path (str): The path to the CSS file. Defaults to "styles.css".
    """
    if not os.path.exists(file_path):
        logging.warning(f"CSS file not found at {file_path}. Skipping CSS load.")
        return # Exit gracefully if file doesn't exist

    try:
        with open(file_path, "r", encoding='utf-8') as f: # Specify encoding
            css = f.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
            logging.debug(f"Successfully loaded CSS from {file_path}")
    except OSError as e:
        logging.error(f"Error reading CSS file {file_path}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading CSS: {e}")