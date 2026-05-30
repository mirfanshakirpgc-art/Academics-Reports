# ... (Your existing layout configurations variables are right above here) ...
    max_w_val = "800px" if border_style != "None" else "100%"

    # Send choices directly to our CSS engine variables
    st.markdown(f"""
        <style>
        :root {{
            --paper-orient: {paper_orient};
            --paper-size: {paper_size};
            --paper-margin: {margin_val};
            --font-size-choice: {font_val};
            --border-choice: {border_val};
            --break-choice: {break_val};
            --max-width-choice: {max_w_val};
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # --- ADD THIS PRINT PREVIEW BUTTON BLOCK HERE ---
    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        # This button triggers the browser's window.print() layout script natively
        if st.button("🖨️ Open Print Preview", type="primary", use_container_width=True):
            st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
            
    st.markdown("---") # Visual separator line before your search bar
    # ------------------------------------------------
    
    search_id = st.text_input("🔍 Search Student Roll Number / ID:")
    # ... (The rest of your student card search logic continues here) ...
