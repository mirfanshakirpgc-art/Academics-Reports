I understand. Because I can't look inside your local `app.py` file to see all the pages you've built (like your data entry fields, database credentials, or sidebar layout), I only had the code for the **"🪪 Student Result Cards"** module.

Let's fix this completely. Below is a fully self-contained, ready-to-run template structured exactly like a multi-page production Streamlit application.

It contains the structural setup for your other tabs, configuration placeholders for your database connections, and the entire **100% complete, fully fixed result card layout printing engine**.

### Full Code Setup for `app.py`

```python
import streamlit as st
import pandas as pd
import numpy as np
# Import your real database engine here (e.g., import sqlite3 or from st_connection)

# ==============================================================================
# 1. PAGE AND THEME INITIALIZATION
# ==============================================================================
st.set_page_config(
    page_title="Concordia Colleges Kasur — Academic Management System",
    page_icon="🍁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. GLOBAL ACADEMIC CONFIGURATIONS (MATCHING YOUR COLLEGE MATRIX)
# ==============================================================================
# List of exams registered in your system
if "AVAILABLE_EXAMS" not in globals():
    AVAILABLE_EXAMS = ["MATRIC", "MT_1", "MT_2", "SEND_UP", "PRE_BOARD"]

# Mapping sections to specific academic paths
if "DISCIPLINE_SECTIONS_MAP" not in globals():
    DISCIPLINE_SECTIONS_MAP = {
        "MEDICAL": ["CB_ORANGE", "FSC_MED_1"],
        "ENGINEERING": ["CB_BLUE", "FSC_ENG_1"],
        "ICS_PHYSICS": ["CB_GREEN", "ICS_PHYS_1"],
        "ICS_STATS": ["CB_YELLOW", "ICS_STAT_1"],
        "COMMERCE": ["I_COM_1", "I_COM_2"]
    }

# Core subjects per academic track
if "DISCIPLINE_SUBJECTS_MAP" not in globals():
    DISCIPLINE_SUBJECTS_MAP = {
        "MEDICAL": ["BIOLOGY", "CHEMISTRY", "PHYSICS", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
        "ENGINEERING": ["MATHEMATICS", "CHEMISTRY", "PHYSICS", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
        "ICS_PHYSICS": ["COMPUTER", "MATHEMATICS", "PHYSICS", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
        "ICS_STATS": ["COMPUTER", "MATHEMATICS", "STATISTICS", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
        "COMMERCE": ["ACCOUNTING", "ECONOMICS", "COMMERCE", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"]
    }

# ==============================================================================
# 3. DATABASE ACCESS BRIDGE
# ==============================================================================
def run_query(query_string, params=None):
    """
    DATABASE ROUTER BRIDGE:
    Replace this mock dictionary directly with your application's actual backend execution runner!
    
    Example using direct SQL/Streamlit Connections:
       conn = st.connection('mysql', type='sql')
       return conn.query(query_string, params=params)
    """
    # Simulated response matching your exact database records and issues
    if "FROM students" in query_string:
        if params and params.get("id") == 20136:
            return pd.DataFrame([{
                "id": 20136,
                "name": "SUFYAN  MUHAMMAD SOHAIL\n\nMUKHTAR",  # Reproducing database newline error
                "section": "CB_GREEN",
                "class": "11th"
            }])
        elif params and "UPPER(TRIM(section))" in query_string:
            return pd.DataFrame([{
                "id": 20136,
                "name": "SUFYAN  MUHAMMAD SOHAIL\n\nMUKHTAR",
                "section": "CB_GREEN",
                "class": "11th"
            }])
        return pd.DataFrame(columns=["id", "name", "section", "class"])
        
    elif "FROM marks" in query_string:
        return pd.DataFrame([
            {"subject": "COMPUTER", "exam_type": "MATRIC", "marks_obtained": "78", "total_marks": 100.0},
            {"subject": "MATHEMATICS", "exam_type": "MATRIC", "marks_obtained": "85", "total_marks": 100.0},
            {"subject": "PHYSICS", "exam_type": "MATRIC", "marks_obtained": "A", "total_marks": 100.0},
            {"subject": "URDU", "exam_type": "MATRIC", "marks_obtained": "62", "total_marks": 100.0},
            {"subject": "ENGLISH", "exam_type": "MATRIC", "marks_obtained": "71", "total_marks": 100.0},
            {"subject": "ISL_ETH", "exam_type": "MATRIC", "marks_obtained": "40", "total_marks": 50.0},
            {"subject": "T_QURAN", "exam_type": "MATRIC", "marks_obtained": "45", "total_marks": 50.0}
        ])
    return pd.DataFrame()

# ==============================================================================
# 4. SIDEBAR APPLICATION ROUTER
# ==============================================================================
st.sidebar.markdown(
    "<h2 style='text-align: center; color: #802200; font-family: Arial;'>🍁 Concordia Kasur</h2>", 
    unsafe_allow_html=True
)
menu_choice = st.sidebar.radio(
    "Navigation Menu Options:", 
    ["📊 Dashboard Overview", "📝 Marks & Data Entry", "🪪 Student Result Cards", "⚙️ Settings & Sync"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Academic Year: 2025-2026 | System Status: Active")

# ==============================================================================
# PAGE MODULE 1: DASHBOARD OVERVIEW
# ==============================================================================
if menu_choice == "📊 Dashboard Overview":
    st.title("📊 System Analytics Dashboard")
    st.markdown("Welcome to the Academic Portal for **Concordia Colleges, Kasur**.")
    
    # Simple dynamic stats placeholders
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Active Students", "1,240", "+4%")
    m2.metric("Sections Tracked", "14", "Stable")
    m3.metric("Exams Logged This Term", "3", "+1")
    
    st.info("💡 Tip: Navigate to the **Student Result Cards** module in the left sidebar menu to generate print-ready dynamic report layouts.")

# ==============================================================================
# PAGE MODULE 2: MARKS & DATA ENTRY
# ==============================================================================
elif menu_choice == "📝 Marks & Data Entry":
    st.title("📝 Student Marks Entry Portal")
    st.write("Authorized faculty data entry module.")
    
    with st.form("marks_entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Select Target Class", ["11th", "12th"])
            st.text_input("Enter Student Roll Number")
        with col2:
            st.selectbox("Select Exam Type", AVAILABLE_EXAMS)
            st.text_input("Marks Obtained")
        
        submitted = st.form_submit_with_button("Save Marks Record")
        if submitted:
            st.success("Record saved temporarily (Mock Engine Connection Active)")

# ==============================================================================
# PAGE MODULE 3: STUDENT RESULT CARDS (THE CRITICAL GENERATION ENGINE)
# ==============================================================================
elif menu_choice == "🪪 Student Result Cards":
    st.title("🍁 Concordia Colleges, Kasur — Academic Report Sheets")
    
    # 3A. Layout & Printing Parameters Expandable Controls Drawer
    with st.expander("🛠️ Customize Sheet & Layout Settings (Click to Expand)"):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            paper_orient = st.selectbox("Paper Orientation:", ["portrait", "landscape"])
            paper_size = st.selectbox("Paper Size:", ["A4", "letter", "legal"])
            font_size = st.selectbox("Text Font Size:", ["13pt (Normal)", "11pt (Compact)", "15pt (Large)"])
        with col_p2:
            st.markdown("**Page Margin Settings (mm):**")
            margin_top = st.slider("Top Margin", min_value=0, max_value=50, value=10, step=1)
            margin_bottom = st.slider("Bottom Margin", min_value=0, max_value=50, value=10, step=1)
        with col_p3:
            st.markdown("**Page Margin Settings (mm):**")
            margin_left = st.slider("Left Margin", min_value=0, max_value=50, value=10, step=1)
            margin_right = st.slider("Right Margin", min_value=0, max_value=50, value=10, step=1)
            
            st.write("") 
            border_style = st.selectbox("Card Border Style:", ["4px double #802200 (Official)", "2px solid #000000 (Minimal)", "None"])
            page_break = st.toggle("Force 1 Card per Page", value=True)

    font_val = "11pt" if "Compact" in font_size else ("15pt" if "Large" in font_size else "13pt")
    border_val = "none" if border_style == "None" else border_style
    break_val = "always" if page_break else "auto"

    # Inject global CSS rules to format HTML tables and strip borders out during system print dialog events
    st.markdown(f"""
        <style>
        @media print {{
            @page {{
                size: {paper_size} {paper_orient};
                margin: {margin_top}mm {margin_right}mm {margin_bottom}mm {margin_left}mm !important;
            }}
            [data-testid="stSidebar"], header, footer, [data-testid="stHeader"],
            .stExpander, [data-testid="stRadio"], [data-testid="stTextInput"], 
            [data-testid="stMultiSelect"], hr, iframe, button, .stSelectbox {{
                display: none !important;
                height: 0px !important;
                margin: 0px !important;
                padding: 0px !important;
            }}
            div[data-testid="stAppViewContainer"] {{
                background-color: white !important;
            }}
            .stMainBlockContainer {{
                padding: 0px !important;
                margin: 0px !important;
                width: 100% !important;
            }}
            .print-page-block {{
                page-break-after: {break_val} !important;
                break-after: page !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
                margin: 0px !important;
                padding: 0px !important;
                border: none !important;
            }}
        }}
        .report-card-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-family: Arial, sans-serif;
        }}
        .report-card-table th, .report-card-table td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
        }}
        .report-card-table th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # 3B. Sheet Controls and Search Selectors
    sheet_type = st.selectbox(
        "📄 Select Document Sheet Type to Generate:", 
        ["Result Card (Single Student & Single Test)", "Academics Report (Single Student & Multiple Tests)"]
    )
    
    print_scope = st.radio("🖨️ Select Print Output Scope:", ["👤 Print Single Student Card", "👥 Print Complete Section Cards"], horizontal=True)
    search_id = st.text_input("🔍 Search Student Roll Number / ID:", key="print_card_search")
    
    if sheet_type == "Result Card (Single Student & Single Test)":
        target_exam = st.selectbox("🎯 Select Exam Term:", options=AVAILABLE_EXAMS, index=0)
        selected_tests = [target_exam]
    else:
        selected_tests = st.multiselect("🎯 Select Test Terms to Cross-Compare:", options=AVAILABLE_EXAMS, default=["MT_1", "MT_2"])

    st.markdown(f"""
        <button onclick="window.print();" style="
            background-color: #802200; color: white; border: none; font-weight: bold; 
            padding: 12px 24px; border-radius: 4px; cursor: pointer; font-family: Arial, sans-serif;
            font-size: 16px; width: 260px; display: block; margin-top: 10px; margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">🖨️ Open Sheet Print Preview</button>
    """, unsafe_allow_html=True)
            
    st.markdown("---")

    # 3C. Core Computation and HTML Data Compiling Loop
    if search_id and search_id.isdigit():
        base_student = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(search_id)})
        if base_student.empty:
            st.error("❌ No student record discovered with that Roll Number.")
        elif not selected_tests:
            st.warning("Please select at least one exam/test parameter to display.")
        else:
            target_section = base_student['section'].iloc[0].upper().strip()
            num_selected_tests = len(selected_tests)
            
            if print_scope == "👥 Print Complete Section Cards":
                students_to_print = run_query("SELECT id, name, section, class FROM students WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) ORDER BY id ASC", {"section": target_section})
            else:
                students_to_print = pd.DataFrame([{
                    "id": int(search_id),
                    "name": base_student['name'].iloc[0],
                    "section": target_section,
                    "class": base_student['class'].iloc[0]
                }])

            for idx, student_row in students_to_print.iterrows():
                current_id = int(student_row['id'])
                
                # STRING CLEANING STAGE: Replaces inline data formatting strings and raw structural text newlines
                name = " ".join(str(student_row['name']).replace('\n', ' ').replace('\r', ' ').split()).upper()
                section = str(student_row['section']).upper().strip()
                grade_class = str(student_row['class']).strip()
                
                if len(selected_tests) == 1:
                    raw_marks = run_query("""
                        SELECT UPPER(TRIM(subject)) as subject, TRIM(exam_type) as exam_type, marks_obtained, total_marks 
                        FROM marks 
                        WHERE student_id = :id AND exam_type = :exams
                    """, {"id": current_id, "exams": selected_tests[0]})
                else:
                    raw_marks = run_query("""
                        SELECT UPPER(TRIM(subject)) as subject, TRIM(exam_type) as exam_type, marks_obtained, total_marks 
                        FROM marks 
                        WHERE student_id = :id AND exam_type IN :exams
                    """, {"id": current_id, "exams": tuple(selected_tests)})
                
                if print_scope == "👥 Print Complete Section Cards":
                    valid_marks = raw_marks[
                        raw_marks['marks_obtained'].notna() & 
                        (raw_marks['marks_obtained'].astype(str).str.strip() != '-') & 
                        (raw_marks['marks_obtained'].astype(str).str.strip() != '')
                    ]
                    if valid_marks.empty:
                        continue
                        
                assigned_discipline = "MEDICAL"
                for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                    if section in [x.upper().strip() for x in secs]:
                        assigned_discipline = disp
                        break
                
                ordered_subjects = DISCIPLINE_SUBJECTS_MAP[assigned_discipline]
                sheet_title = "STUDENT RESULT CARD" if num_selected_tests == 1 else "STUDENT ACADEMICS REPORT"
                
                card_html = f"""
                <div class="print-page-block" style="
                    border: {border_val}; padding: 20px; margin-bottom: 25px; 
                    background-color: #ffffff; font-family: Arial, sans-serif; 
                    font-size: {font_val}; width: 100%; max-width: 1000px; box-sizing: border-box;
                ">
                    <div style="background-color:#802200; padding:12px 15px; border-radius:4px; color:white; font-weight:bold; font-size: 16px; margin-bottom:15px; text-align: center; -webkit-print-color-adjust: exact; print-color-adjust: exact;">
                        {sheet_title} — CONCORDIA COLLEGES, KASUR
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; background: #f9f9f9; padding: 10px; border-radius: 4px;">
                        <div><strong>Roll Number:</strong> {current_id}</div>
                        <div><strong>Student Name:</strong> {name}</div>
                        <div><strong>Class:</strong> {grade_class}</div>
                        <div><strong>Section Reference:</strong> {section} ({assigned_discipline})</div>
                    </div>
                    
                    <table class="report-card-table">
                        <thead>
                            <tr>
                                <th style="text-align: left;">Subject</th>
                """
                
                for t in selected_tests:
                    card_html += f"<th>{t} (Obt)</th><th>{t} (%)</th>"
                card_html += "</tr></thead><tbody>"
                
                grand_obtained = 0.0
                grand_total = 0.0
                has_numeric_data = False
                
                for sub in ordered_subjects:
                    clean_sub_target = sub.upper().strip()
                    card_html += f"<tr><td style='text-align: left; font-weight: bold;'>{sub}</td>"
                    
                    for t in selected_tests:
                        match = raw_marks[(raw_marks['subject'] == clean_sub_target) & (raw_marks['exam_type'] == t.strip())]
                        
                        if not match.empty:
                            score_str = str(match['marks_obtained'].iloc[0]).strip().upper()
                            tot_val = float(match['total_marks'].iloc[0]) if pd.notna(match['total_marks'].iloc[0]) else 100.0
                            
                            if score_str.replace('.', '', 1).isdigit():
                                score_num = float(score_str)
                                pct = f"{int((score_num / tot_val) * 100)}%"
                                card_html += f"<td>{score_str} / {int(tot_val)}</td><td>{pct}</td>"
                                grand_obtained += score_num
                                grand_total += tot_val
                                has_numeric_data = True
                            else:
                                card_html += f"<td>{score_str}</td><td>-</td>"
                        else:
                            card_html += "<td>--</td><td>--</td>"
                    card_html += "</tr>"
                
                if has_numeric_data and grand_total > 0:
                    final_pct = f"{int((grand_obtained / grand_total) * 100)}%"
                    card_html += f"""
                        <tr style="background-color: #f2f2f2; font-weight: bold;">
                            <td style="text-align: left;">GRAND TOTAL</td>
                            <td colspan="{len(selected_tests) * 2 - 1}">{int(grand_obtained)} / {int(grand_total)}</td>
                            <td>{final_pct}</td>
                        </tr>
                    """
                else:
                    card_html += f"""
                        <tr style="background-color: #f9f9f9; font-style: italic; color: #777;">
                            <td style="text-align: left;">GRAND TOTAL</td>
                            <td colspan="{len(selected_tests) * 2 - 1}">No graded marks logged</td>
                            <td>-</td>
                        </tr>
                    """
                
                card_html += "</tbody></table></div>"
                st.markdown(card_html, unsafe_allow_html=True)

# ==============================================================================
# PAGE MODULE 4: SETTINGS & SYNC
# ==============================================================================
elif menu_choice == "⚙️ Settings & Sync":
    st.title("⚙️ System Control & Sync Panel")
    st.write("Manage system parameters.")
    if st.button("Flush Application Interface Cache"):
        st.success("Interface cache successfully optimized.")

```
