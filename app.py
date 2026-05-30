# ----------------- 🪪 STUDENT RESULT CARDS -----------------
elif menu_choice == "🪪 Student Result Cards":
    st.title("🍁 Concordia Colleges, Kasur — Academic Report Card")
    
    # --- DYNAMIC PRINT LAYOUT CONFIGURATION OPTIONS PANEL ---
    with st.expander("🛠️ Customize Print Layout Options (Click to Change)"):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            paper_orient = st.selectbox("Paper Orientation:", ["portrait", "landscape"])
            paper_size = st.selectbox("Paper Size:", ["A4", "letter", "legal"])
            font_size = st.selectbox("Text Font Size:", ["13pt (Normal)", "11pt (Compact)", "15pt (Large)"])
        with col_p2:
            st.markdown("**Page Margin Settings (mm):**")
            margin_top = st.slider("Top Margin", min_value=0, max_value=50, value=15, step=1)
            margin_bottom = st.slider("Bottom Margin", min_value=0, max_value=50, value=15, step=1)
        with col_p3:
            st.markdown("**Page Margin Settings (mm):**")
            margin_left = st.slider("Left Margin", min_value=0, max_value=50, value=15, step=1)
            margin_right = st.slider("Right Margin", min_value=0, max_value=50, value=15, step=1)
            
            st.write("") # Spacer
            border_style = st.selectbox("Card Border Style:", ["None", "4px double #f8a100 (Official)", "2px solid #000000 (Minimal)"])
            page_break = st.toggle("Force 1 Card per Page", value=True)

    # Convert settings names into system-usable variables
    font_val = "11pt" if "Compact" in font_size else ("15pt" if "Large" in font_size else "13pt")
    border_val = "none" if border_style == "None" else border_style
    break_val = "always" if page_break else "auto"
    max_w_val = "800px" if border_style != "None" else "100%"

    # Send choices directly to our CSS engine variables
    st.markdown(f"""
        <style>
        :root {{
            --paper-orient: {paper_orient};
            --paper-size: {paper_size};
            --font-size-choice: {font_val};
            --border-choice: {border_val};
            --break-choice: {break_val};
            --max-width-choice: {max_w_val};
        }}
        
        /* 🖨️ CRITICAL PRINT INSTRUCTION: This applies your custom four-way margins and hides setup controls */
        @media print {{
            @page {{
                size: {paper_size} {paper_orient};
                margin-top: {margin_top}mm !important;
                margin-bottom: {margin_bottom}mm !important;
                margin-left: {margin_left}mm !important;
                margin-right: {margin_right}mm !important;
            }}
            
            [data-testid="stSidebar"], 
            header, 
            footer, 
            [data-testid="stHeader"] {{
                display: none !important;
            }}
            
            h1, 
            .stExpander, 
            [data-testid="stRadio"], 
            [data-testid="stTextInput"], 
            [data-testid="stMultiSelect"], 
            hr,
            iframe {{
                display: none !important;
            }}
            
            .print-card-break {{
                page-break-after: always !important;
                break-after: page !important;
            }}
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # --- PRINT MODE CONTROLLER ---
    print_scope = st.radio("🖨️ Select Print Output Scope:", ["👤 Print Single Student Card", "👥 Print Complete Section Cards"], horizontal=True)
    
    search_id = st.text_input("🔍 Search Student Roll Number / ID:", key="print_card_search")
    selected_tests = st.multiselect("🎯 Select Specific Test Terms to Compare:", options=AVAILABLE_EXAMS, default=["MT_1"])
    
    import streamlit.components.v1 as components
    components.html("""
        <button onclick="window.parent.parent.focus(); window.parent.parent.print();" style="
            background-color: #f8a100; 
            color: white; 
            border: none;
            font-weight: bold; 
            padding: 10px 24px; 
            border-radius: 4px; 
            cursor: pointer;
            font-family: sans-serif;
            font-size: 16px;
            width: 220px;
        ">🖨️ Open Print Preview</button>
    """, height=60)
            
    st.markdown("---")
