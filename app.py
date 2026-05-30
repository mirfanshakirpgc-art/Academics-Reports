import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

st.set_page_config(layout="wide", page_title="Concordia Academic Analytics")

# --- LINK TO SEPARATE STYLE FILE ---
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- DATABASE CONNECTION CONFIGURATION ---
DATABASE_URL = "postgresql+psycopg2://postgres.qykueriwcvgxsbxbbtso:Concordiakasur2023@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

@st.cache_resource
def get_db_engine():
    return create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

engine = get_db_engine()

# --- SETUP USER LOGIN SESSION MEMORY TRACKING ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "assigned_subject" not in st.session_state:
    st.session_state.assigned_subject = None

# --- SECURE GATEKEEPER LOGIN CHECK ---
if not st.session_state.logged_in:
    st.title("🏫 Concordia Colleges, Kasur")
    
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    
    if st.button("Log In"):
        with engine.connect() as conn:
            query = text("SELECT role, assigned_subject FROM app_users WHERE username = :u AND password = :p")
            result = conn.execute(query, {"u": username_input, "p": password_input}).fetchone()
            
            if result:
                st.session_state.logged_in = True
                st.session_state.user_role = result[0]         # 'controller' or 'teacher'
                st.session_state.assigned_subject = result[1]    # e.g., 'COMPUTER' or None
                st.success("Access Granted! Loading system...")
                st.rerun()
            else:
                st.error("Incorrect username or password. Please try again.")
    st.stop() 

# --- AUTOMATIC TABLE SETUP ---
def initialize_database():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS students (
                id INT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                section VARCHAR(100),
                class VARCHAR(100)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS marks (
                id SERIAL PRIMARY KEY,
                student_id INT REFERENCES students(id) ON DELETE CASCADE,
                subject VARCHAR(100) NOT NULL,
                exam_type VARCHAR(100) NOT NULL,
                marks_obtained VARCHAR(50),
                total_marks INT,
                UNIQUE(student_id, subject, exam_type)
            );
        """))

try:
    initialize_database()
except Exception as e:
    st.error(f"Failed to initialize database tables: {e}")

def run_query(query, params=()):
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)

def execute_db_command(command, params=()):
    with engine.begin() as conn:
        conn.execute(text(command), params)

# --- NAVIGATION SIDEBAR ---
st.sidebar.title("🏫 Menu Navigation")
menu_choice = st.sidebar.radio(
    "Go To Module:", 
    ["📊 Home Dashboard", "➕ Add Students", "📝 Enter Marks", "📋 Section Summary Report", "🪪 Student Result Cards", "📈 Master Performance Ledger"]
)

# --- MAP CONFIGURATIONS ---
DISCIPLINE_SUBJECTS_MAP = {
    "MEDICAL": ["CHEMISTRY", "BIOLOGY", "PHYSICS", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
    "ENGINEERING": ["CHEMISTRY", "MATHEMATICS", "PHYSICS", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
    "ICS_PHYSICS": ["COMPUTER", "MATHEMATICS", "PHYSICS", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
    "ICS_STATS": ["MATHEMATICS", "STATISTICS", "COMPUTER", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
    "COMMERCE": ["POA", "POC", "B_MATH", "POE", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
    "HUMANITIES": ["EDUCATION", "ISL_ELC", "COMPUTER", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"],
    "INFORMATION_TECHNOLOGY": ["COMPUTER_1", "COMPUTER_2", "COMPUTER_3", "COMPUTER_4", "COMPUTER_5"]
}

DISCIPLINE_SECTIONS_MAP = {
    "MEDICAL": ["MG_BLUE", "MG_WHITE", "MB_BLUE"],
    "ENGINEERING": ["EG_BLUE", "EB_BLUE"],
    "ICS_PHYSICS": ["CG_WHITE", "CG_GREEN", "CB_WHITE", "CB_GREEN"],
    "ICS_STATS": ["CG_STATS", "CB_STATS"],
    "COMMERCE": ["IG", "IB"],
    "HUMANITIES": ["FB", "FG"],
    "INFORMATION_TECHNOLOGY": ["DITB", "DITG"]
}

AVAILABLE_DISCIPLINE = list(DISCIPLINE_SUBJECTS_MAP.keys())
AVAILABLE_EXAMS = [
    "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "SEND_UP", "MT_5",
    "T_1", "T_2", "T_3", "T_4", "T_5", "T_6", "T_7", "T_8", "T_9", "T_10",
    "HALF_BOOK01", "HALF_BOOK02", "PRE_BOARD"
]

# ----------------- 📊 HOME DASHBOARD -----------------
if menu_choice == "📊 Home Dashboard":
    col1, col2 = st.columns([1, 8])
    with col1:
        st.image("logo.jpg", width=90)
    with col2:
        st.title("Concordia Colleges, Kasur")
        
    try:
        s_count = run_query("SELECT COUNT(*) FROM students").iloc[0, 0]
        m_count = run_query("SELECT COUNT(*) FROM marks").iloc[0, 0]
    except Exception:
        s_count, m_count = 0, 0
        
    c1, col2_metrics = st.columns(2)
    c1.metric("Total Registered Students", s_count)
    col2_metrics.metric("Total Grade Records Captured", m_count)

# ----------------- ➕ ADD STUDENTS -----------------
elif menu_choice == "➕ Add Students":
    st.title("➕ Student Profile Registration Portal")
    import_template = pd.DataFrame([{"ID": "", "Full Name": "", "Section": "", "Class": "11th"} for _ in range(35)])
    pasted_data = st.data_editor(import_template, use_container_width=True, num_rows="dynamic", key="bulk_paste_grid")
    
    if st.button("🚀 Process and Save Bulk Profiles", type="primary"):
        added_counter = 0
        for _, row in pasted_data.iterrows():
            r_id = str(row['ID']).strip()
            r_name = str(row['Full Name']).strip()
            r_sec = str(row['Section']).strip().upper()
            r_class = str(row['Class']).strip()
            if r_id.isdigit() and r_name != "":
                execute_db_command(
                    "INSERT INTO students (id, name, section, class) VALUES (:id, :name, :sec, :class) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, section = EXCLUDED.section, class = EXCLUDED.class",
                    {"id": int(r_id), "name": r_name, "sec": r_sec, "class": r_class}
                )
                added_counter += 1
        st.success(f"🎉 Successfully imported {added_counter} student profiles!")

# ----------------- 📝 ENTER MARKS -----------------
elif menu_choice == "📝 Enter Marks":
    st.title("📝 Interactive Marks Entry Portal")
    entry_mode = st.radio("🎯 Select Entry Workflow Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number"], horizontal=True)
    st.markdown("---")

    if entry_mode == "📋 By Complete Section":
        c1, c2, c3 = st.columns(3)
        with c1: 
            sel_discipline = st.selectbox("Select Discipline:", AVAILABLE_DISCIPLINE)
        with c2: 
            if st.session_state.user_role == 'teacher' and st.session_state.assigned_subject:
                teacher_subj = st.session_state.assigned_subject.upper().strip()
                if teacher_subj in DISCIPLINE_SUBJECTS_MAP[sel_discipline]:
                    sel_subject = st.selectbox("Select Subject:", [teacher_subj])
                else:
                    st.error(f"Your assigned subject '{teacher_subj}' doesn't exist in {sel_discipline}.")
                    st.stop()
            else:
                sel_subject = st.selectbox("Select Subject:", DISCIPLINE_SUBJECTS_MAP[sel_discipline])
        with c3: 
            sel_section = st.selectbox("Select Section:", DISCIPLINE_SECTIONS_MAP[sel_discipline])
        
        row2_1, row2_2 = st.columns(2)
        with row2_1: sel_exam = st.selectbox("Test Type:", AVAILABLE_EXAMS)
        with row2_2: total_marks = st.number_input("Total Marks Assigned:", value=100)
        
        st.markdown(f"### 📑 Active Marksheet View — Section: `{sel_section}`")
        try:
            roster_df = run_query("""
                SELECT s.id AS "ID", s.name AS "Student Name", m.marks_obtained AS "Marks"
                FROM students s
                LEFT JOIN marks m ON s.id = m.student_id AND UPPER(TRIM(m.subject)) = UPPER(TRIM(:subject)) AND TRIM(m.exam_type) = TRIM(:exam)
                WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section))
                ORDER BY s.id ASC
            """, {"subject": sel_subject, "exam": sel_exam, "section": sel_section})
            
            if roster_df.empty:
                st.info(f"💡 No students found registered in section '{sel_section}' yet.")
            else:
                roster_df['Marks'] = roster_df['Marks'].fillna("")
                with st.form("bulk_marks_form"):
                    updated_scores = {}
                    for idx, row in roster_df.iterrows():
                        col_s1, col_s2 = st.columns([3, 1])
                        col_s1.write(f"🏷️ **{row['ID']}** — {row['Student Name']}")
                        updated_scores[row['ID']] = col_s2.text_input("Score", value=str(row['Marks']), key=f"sec_{row['ID']}", label_visibility="collapsed")
                    
                    if st.form_submit_button("💾 Save Section Marks", type="primary"):
                        for s_id, score in updated_scores.items():
                            execute_db_command("DELETE FROM marks WHERE student_id = :s_id AND UPPER(TRIM(subject)) = UPPER(TRIM(:subject)) AND TRIM(exam_type) = TRIM(:exam)", {"s_id": int(s_id), "subject": sel_subject, "exam": sel_exam})
                            if score.strip() != "":
                                execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:s_id, :subject, :exam, :score, :total)", {"s_id": int(s_id), "subject": sel_subject.strip().upper(), "exam": sel_exam.strip(), "score": score.strip(), "total": total_marks})
                        st.success("🎉 Section marks matrix saved and updated completely!")
                        st.rerun()
        except Exception as e:
            st.error(f"Database sync issue. Error: {e}")

    elif entry_mode == "👤 By Single Student Roll Number":
        target_id = st.text_input("🔍 Enter Student Roll Number / ID:")
        if target_id and target_id.isdigit():
            student_info = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(target_id)})
            if student_info.empty:
                st.error("❌ This roll number does not exist in your registered profiles list.")
            else:
                s_name = student_info['name'].iloc[0].upper()
                s_section = student_info['section'].iloc[0].upper().strip()
                s_class = student_info['class'].iloc[0]
                st.info(f"👤 **Student Found:** {s_name} | **Class:** {s_class} | **Section Reference:** {s_section}")
                
                matched_disp = "MEDICAL"
                for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                    if s_section in [x.upper().strip() for x in secs]:
                        matched_disp = disp
                        break
                
                st.markdown("#### Assign Grades")
                c_sub, c_ex, c_m = st.columns(3)
                with c_sub: 
                    if st.session_state.user_role == 'teacher' and st.session_state.assigned_subject:
                        single_subj = st.selectbox("Choose Subject:", [st.session_state.assigned_subject.upper().strip()], key="single_sub")
                    else:
                        single_subj = st.selectbox("Choose Subject:", DISCIPLINE_SUBJECTS_MAP[matched_disp], key="single_sub")
                with c_ex: single_exam = st.selectbox("Choose Test Term Type:", AVAILABLE_EXAMS, key="single_exam")
                with c_m: single_total = st.number_input("Total Marks Assigned:", value=100, key="single_max")
                
                existing_record = run_query("SELECT marks_obtained FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(target_id), "sub": single_subj, "exam": single_exam})
                current_val = str(existing_record['marks_obtained'].iloc[0]) if not existing_record.empty else ""
                single_score = st.text_input("✏️ Enter Marks Obtained (Use numbers or 'A' for Absent):", value=current_val)
                
                if st.button("💾 Save Student Record Updates", type="primary"):
                    execute_db_command("DELETE FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(target_id), "sub": single_subj, "exam": single_exam})
                    if single_score.strip() != "":
                        execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:id, :sub, :exam, :score, :total)", {"id": int(target_id), "sub": single_subj.strip().upper(), "exam": single_exam.strip(), "score": single_score.strip(), "total": single_total})
                    st.success(f"🎉 Marks successfully updated for {s_name}!")
                    st.rerun()

# ----------------- 📋 SECTION SUMMARY REPORT -----------------
elif menu_choice == "📋 Section Summary Report":
    col_a, col_b, col_c = st.columns(3)
    with col_a: sel_disc = st.selectbox("Select Discipline:", AVAILABLE_DISCIPLINE, key="summary_disc")
    with col_b: sel_sec = st.selectbox("Select Section:", DISCIPLINE_SECTIONS_MAP[sel_disc], key="summary_sec")
    with col_c: sel_exam = st.selectbox("Select Exam Cycle:", AVAILABLE_EXAMS, key="summary_exam")
    st.markdown("---")
    
    students_df = run_query("SELECT id AS \"ID\", name AS \"Student Name\", section AS \"Section\", class AS \"Class\" FROM students WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) ORDER BY id ASC", {"section": sel_sec})
    
    if students_df.empty:
        st.warning(f"No students found registered under section '{sel_sec}'.")
    else:
        subjects = DISCIPLINE_SUBJECTS_MAP[sel_disc]
        marks_df = run_query("""
            SELECT m.student_id, UPPER(TRIM(m.subject)) as subject, m.marks_obtained, m.total_marks
            FROM marks m
            JOIN students s ON m.student_id = s.id
            WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section)) AND TRIM(m.exam_type) = TRIM(:exam)
        """, {"section": sel_sec, "exam": sel_exam})
        
        summary_rows = []
        for _, s_row in students_df.iterrows():
            s_id = s_row["ID"]
            entry = {"ID": s_id, "Student Name": s_row["Student Name"], "Section": s_row["Section"], "Class": s_row["Class"]}
            obtained_total = 0.0
            max_total = 0.0
            has_scores = False
            
            for sub in subjects:
                sub_match = marks_df[(marks_df["student_id"] == s_id) & (marks_df["subject"] == sub.upper().strip())]
                if not sub_match.empty:
                    val = str(sub_match["marks_obtained"].iloc[0]).strip().upper()
                    entry[f"{sub} (Obt)"] = val
                    if val.replace('.', '', 1).isdigit():
                        tot = float(sub_match["total_marks"].iloc[0])
                        entry[f"{sub} (%)"] = f"{int((float(val) / tot) * 100)}%"
                        obtained_total += float(val)
                        max_total += tot
                        has_scores = True
                    elif val == "A":
                        entry[f"{sub} (%)"] = "A"
                    else:
                        entry[f"{sub} (%)"] = "-"
                else:
                    entry[f"{sub} (Obt)"] = "-"
                    entry[f"{sub} (%)"] = "-"
            
            if has_scores and max_total > 0:
                entry["Total (Obt)"] = int(obtained_total)
                entry["Total (%)"] = f"{int((obtained_total / max_total) * 100)}%"
            else:
                entry["Total (Obt)"] = "-"
                entry["Total (%)"] = "-"
            summary_rows.append(entry)
            
        final_report_df = pd.DataFrame(summary_rows)
        st.subheader(f"📊 Section Sheet Ledger View — {sel_sec} ({sel_exam})")
        st.dataframe(final_report_df.set_index("ID"), use_container_width=True)
        
        csv_data = final_report_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Ledger Grid to Excel/CSV Spreadsheet", data=csv_data, file_name=f"Summary_{sel_sec}_{sel_exam}.csv", mime="text/csv", type="primary")

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
            
            st.write("") 
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

    # 3. CORE DATA LOADING & TABLE RENDERING LOGIC
    if search_id and search_id.isdigit():
        base_student = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(search_id)})
        if base_student.empty:
            st.error("❌ No student record discovered with that Roll Number.")
        elif not selected_tests:
            st.warning("Please pick at least one test type option.")
        else:
            target_section = base_student['section'].iloc[0].upper().strip()
            
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
                name = str(student_row['name']).upper()
                section = str(student_row['section']).upper().strip()
                grade_class = str(student_row['class'])
                
                st.markdown(f"""
                <div style="background-color:#f8a100; padding:15px; border-radius:5px; color:white; font-weight:bold; margin-top:20px; margin-bottom:10px; font-family:sans-serif;">
                    <h2 style='margin:0; color:white;'>ACADEMICS PERFORMANCE REPORT</h2>
                    <p style='margin:5px 0 0 0; font-size:16px; color:white;'>
                        <b>NAME:</b> {name} &nbsp;&nbsp;|&nbsp;&nbsp; 
                        <b>ID:</b> {current_id} &nbsp;&nbsp;|&nbsp;&nbsp; 
                        <b>SECTION:</b> {section} &nbsp;&nbsp;|&nbsp;&nbsp; 
                        <b>CLASS:</b> {grade_class}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                raw_marks = run_query("""
                    SELECT UPPER(TRIM(subject)) as subject, TRIM(exam_type) as exam_type, marks_obtained, total_marks 
                    FROM marks 
                    WHERE student_id = :id AND exam_type IN :exams
                """, {"id": current_id, "exams": tuple(selected_tests)})
                
                assigned_discipline = "MEDICAL"
                for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                    if section in [x.upper().strip() for x in secs]:
                        assigned_discipline = disp
                        break
                
                ordered_subjects = DISCIPLINE_SUBJECTS_MAP[assigned_discipline]
                matrix_data = []
                for subj in ordered_subjects:
                    row_entry = {"SUBJECTS": subj}
                    sub_total_obtained = 0
                    sub_total_max = 0
                    for exam in selected_tests:
                        match = raw_marks[(raw_marks['subject'] == subj.upper().strip()) & (raw_marks['exam_type'] == exam.strip())]
                        if not match.empty:
                            obt = str(match['marks_obtained'].iloc[0]).strip().upper()
                            tot = match['total_marks'].iloc[0]
                            row_entry[f"{exam} (OBT)"] = obt
                            if str(obt).replace('.','',1).isdigit():
                                row_entry[f"{exam} (%)"] = f"{int(float(obt)/tot * 100)}%"
                                sub_total_obtained += float(obt)
                                sub_total_max += tot
                            elif obt == "A":
                                row_entry[f"{exam} (%)"] = "A"
                            else:
                                row_entry[f"{exam} (%)"] = "-"
                        else:
                            row_entry[f"{exam} (OBT)"] = "-"
                            row_entry[f"{exam} (%)"] = "-"
                    if sub_total_max > 0:
                        row_entry["SUMMARY (OBT)"] = f"{int(sub_total_obtained)}"
                        row_entry["SUMMARY (%)"] = f"{int((sub_total_obtained / sub_total_max) * 100)}%"
                    else:
                        row_entry["SUMMARY (OBT)"] = "-"
                        row_entry["SUMMARY (%)"] = "-"
                    matrix_data.append(row_entry)
                
                report_df = pd.DataFrame(matrix_data)
                total_row = {"SUBJECTS": "⚡ TOTAL"}
                for exam in selected_tests:
                    exam_matches = raw_marks[raw_marks['exam_type'] == exam.strip()]
                    valid_exam_matches = exam_matches[exam_matches['marks_obtained'].apply(lambda x: str(x).replace('.','',1).isdigit())]
                    if not valid_exam_matches.empty:
                        t_obt = valid_exam_matches['marks_obtained'].astype(float).sum()
                        t_max = exam_matches['total_marks'].iloc[0] * len(ordered_subjects)
                        total_row[f"{exam} (OBT)"] = f"{int(t_obt)}"
                        total_row[f"{exam} (%)"] = f"{int((t_obt/t_max)*100)}%"
                    else:
                        total_row[f"{exam} (OBT)"] = "-"
                        total_row[f"{exam} (%)"] = "-"
                
                valid_all = raw_marks[raw_marks['marks_obtained'].apply(lambda x: str(x).replace('.','',1).isdigit())]
                if not valid_all.empty:
                    m_obt = valid_all['marks_obtained'].astype(float).sum()
                    m_max = sum([raw_marks[raw_marks['subject']==s.upper().strip()]['total_marks'].iloc[0] for s in ordered_subjects if not raw_marks[raw_marks['subject']==s.upper().strip()].empty])
                    total_row["SUMMARY (OBT)"] = f"{int(m_obt)}"
                    total_row["SUMMARY (%)"] = f"{int((m_obt/m_max)*100)}%" if m_max > 0 else "-"
                else:
                    total_row["SUMMARY (OBT)"] = "-"
                    total_row["SUMMARY (%)"] = "-"
                
                report_df = pd.concat([report_df, pd.DataFrame([total_row])], ignore_index=True)
                st.dataframe(report_df.set_index("SUBJECTS"), use_container_width=True, key=f"tbl_{current_id}")
                st.markdown('<div class="print-card-break"></div>', unsafe_allow_html=True)

# ----------------- 📈 PERFORMANCE LEDGER -----------------
elif menu_choice == "📈 Master Performance Ledger":
    st.title("📈 Subject-wise Consolidated Performance Ledger")
    c1, c2, c3 = st.columns(3)
    with c1: l_disc = st.selectbox("Select Discipline:", AVAILABLE_DISCIPLINE, key="l_disc")
    with c2: l_subj = st.selectbox("Select Subject:", DISCIPLINE_SUBJECTS_MAP[l_disc], key="l_subj")
    with c3: l_sec = st.selectbox("Select Section:", DISCIPLINE_SECTIONS_MAP[l_disc], key="l_sec")
    st.markdown("---")
    
    raw_ledger = run_query("""
        SELECT s.id AS "ID", s.name AS "Student Name", m.exam_type, m.marks_obtained
        FROM students s
        LEFT JOIN marks m ON s.id = m.student_id AND UPPER(TRIM(m.subject)) = UPPER(TRIM(:subject))
        WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section))
        ORDER BY s.id ASC
    """, {"subject": l_subj, "section": l_sec})
    
    if raw_ledger.empty:
        st.info("No student information found for this configuration.")
    else:
        pivot_df = raw_ledger.pivot_table(index=["ID", "Student Name"], columns="exam_type", values="marks_obtained", aggfunc="first").reset_index()
        for exam in AVAILABLE_EXAMS:
            if exam not in pivot_df.columns: pivot_df[exam] = "-"
        ordered_cols = ["ID", "Student Name"] + [e for e in AVAILABLE_EXAMS if e in pivot_df.columns]
        pivot_df = pivot_df[ordered_cols].fillna("-")
        st.dataframe(pivot_df, use_container_width=True)
        csv = pivot_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Report Ledger to CSV / Excel", data=csv, file_name=f"Ledger_{l_sec}_{l_subj}.csv", mime="text/csv")
