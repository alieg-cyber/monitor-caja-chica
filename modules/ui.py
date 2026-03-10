"""
modules/ui.py — Shared UI components used across all pages.
"""
import streamlit as st
from modules.auth import logout
from config import APP_VERSION


def render_sidebar_user():
    """Render the active-user badge and sign-out button in the sidebar."""
    user = st.session_state.get("user")
    if user:
        with st.sidebar:
            st.markdown(f"""
            <div style="padding:1.25rem 0 1rem; border-bottom:1px solid #1F2937; margin-bottom:1rem;">
                <div style="font-size:0.65rem; color:#4F8EF7; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.4rem;">ACTIVE USER</div>
                <div style="font-size:1rem; font-weight:600; color:#E8EDF5;">{user['nombre']}</div>
                <div style="
                    display:inline-block; margin-top:0.35rem;
                    font-size:0.65rem; font-weight:600; color:#4F8EF7;
                    background:rgba(79,142,247,0.12);
                    border:1px solid rgba(79,142,247,0.25);
                    border-radius:4px; padding:2px 8px;
                    letter-spacing:0.06em; text-transform:uppercase;
                ">{user['rol']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Sign Out", use_container_width=True, key="sidebar_signout"):
                logout()
                st.rerun()
            st.markdown(f"<div style='margin-top:1rem; font-size:0.65rem; color:#374151; text-align:center;'>v{APP_VERSION}</div>", unsafe_allow_html=True)
