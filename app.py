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
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                student_id INT REFERENCES students(id) ON DELETE CASCADE,
                month_name VARCHAR(50) NOT NULL,
                total_days INT DEFAULT 0,
                present_days INT DEFAULT 0,
                UNIQUE(student_id, month_name)
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
    ["📊 Home Dashboard", "➕ Add Students", "📝 Enter Marks & Attendance", "📋 Section Summary Report", "🪪 Student Result Cards", "📈 Master Performance Ledger"]
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
AVAILABLE_MONTHS = ["May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.", "Jan.", "Feb.", "March", "April"]

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

# ----------------- 📝 ENTER MARKS & ATTENDANCE -----------------
elif menu_choice == "📝 Enter Marks & Attendance":
    st.title("📝 Data Intake Management Dashboard")
    sub_tab_selection = st.radio("🎯 Select Workspace Sub-Module Target:", ["📝 Academic Exam Marks Entry", "📅 Monthly Attendance Entry"], horizontal=True)
    st.markdown("---")

    if sub_tab_selection == "📝 Academic Exam Marks Entry":
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

    elif sub_tab_selection == "📅 Monthly Attendance Entry":
        st.subheader("📅 Monthly Attendance Management Workspace")
        att_flow_mode = st.radio("🎯 Select Attendance Entry Workflow Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number"], horizontal=True, key="att_flow")
        st.markdown("---")
        
        if att_flow_mode == "📋 By Complete Section":
            col_as1, col_as2, col_as3 = st.columns(3)
            with col_as1:
                att_discipline = st.selectbox("Select Discipline Context:", AVAILABLE_DISCIPLINE, key="att_disc")
            with col_as2:
                att_section = st.selectbox("Select Target Section:", DISCIPLINE_SECTIONS_MAP[att_discipline], key="att_sec")
            with col_as3:
                att_month = st.selectbox("Select Reporting Attendance Month:", AVAILABLE_MONTHS, key="att_month")
                
            # Single entry for total working days assigned across the selected section layout row
            default_days = st.number_input("📌 Set Total Working Days for this entire Section:", min_value=1, max_value=31, value=24, key="sec_global_days")
            
            st.markdown(f"### 📋 Roster Grid: Attendance Log for `{att_section}` ({att_month})")
            
            students_att_list = run_query("""
                SELECT s.id AS "ID", s.name AS "Student Name", a.present_days
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id AND a.month_name = :month
                WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section))
                ORDER BY s.id ASC
            """, {"month": att_month, "section": att_section})
            
            if students_att_list.empty:
                st.info("💡 No student records registered in this section yet.")
            else:
                with st.form("bulk_attendance_form"):
                    saved_att_presents = {}
                    
                    for idx, row in students_att_list.iterrows():
                        c_b1, c_b2 = st.columns([3, 1])
                        c_b1.write(f"👤 **{row['ID']}** — {row['Student Name']}")
                        
                        init_pres = int(row['present_days']) if pd.notna(row['present_days']) else default_days
                        saved_att_presents[row['ID']] = c_b2.number_input("Days Present", min_value=0, max_value=int(default_days), value=min(int(init_pres), int(default_days)), key=f"pres_{row['ID']}")
                    
                    if st.form_submit_button("💾 Save Section Attendance Ledger", type="primary"):
                        for s_id in saved_att_presents.keys():
                            p_d = int(saved_att_presents[s_id])
                                
                            execute_db_command("""
                                INSERT INTO attendance (student_id, month_name, total_days, present_days)
                                VALUES (:s_id, :month, :td, :pd)
                                ON CONFLICT (student_id, month_name) 
                                DO UPDATE SET total_days = EXCLUDED.total_days, present_days = EXCLUDED.present_days
                            """, {"s_id": int(s_id), "month": att_month, "td": default_days, "pd": p_d})
                            
                        st.success(f"🎉 Monthly Section Attendance ledger saved completely with total days set to {default_days}!")
                        st.rerun()

        elif att_flow_mode == "👤 By Single Student Roll Number":
            att_target_id = st.text_input("🔍 Enter Student Roll Number for Attendance Lookup:")
            if att_target_id and att_target_id.isdigit():
                student_info = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(att_target_id)})
                if student_info.empty:
                    st.error("❌ This roll number does not exist in your registered profiles list.")
                else:
                    s_name = student_info['name'].iloc[0].upper()
                    s_section = student_info['section'].iloc[0].upper().strip()
                    s_class = student_info['class'].iloc[0]
                    st.info(f"👤 **Student Found:** {s_name} | **Class:** {s_class} | **Section:** {s_section}")
                    
                    c_m1, c_m2, c_m3 = st.columns(3)
                    with c_m1:
                        single_att_month = st.selectbox("Select Month:", AVAILABLE_MONTHS, key="single_att_m")
                    
                    existing_att = run_query("SELECT total_days, present_days FROM attendance WHERE student_id = :id AND month_name = :month", {"id": int(att_target_id), "month": single_att_month})
                    
                    curr_tot = int(existing_att['total_days'].iloc[0]) if not existing_att.empty else 24
                    curr_pres = int(existing_att['present_days'].iloc[0]) if not existing_att.empty else 24
                    
                    with c_m2:
                        single_total_days = st.number_input("Total Days:", min_value=1, max_value=31, value=curr_tot)
                    with c_m3:
                        single_present_days = st.number_input("Present Days:", min_value=0, max_value=31, value=min(curr_pres, single_total_days))
                    
                    if single_present_days > single_total_days:
                        st.error("❌ Present days cannot be greater than Total days.")
                    elif st.button("💾 Save Individual Attendance Record", type="primary"):
                        execute_db_command("""
                            INSERT INTO attendance (student_id, month_name, total_days, present_days)
                            VALUES (:id, :month, :td, :pd)
                            ON CONFLICT (student_id, month_name)
                            DO UPDATE SET total_days = EXCLUDED.total_days, present_days = EXCLUDED.present_days
                        """, {"id": int(att_target_id), "month": single_att_month, "td": single_total_days, "pd": single_present_days})
                        st.success(f"🎉 Attendance updated successfully for {s_name} in {single_att_month}!")
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
            font_size = st.selectbox("Text Font Size:", ["11pt (Compact)", "13pt (Normal)", "15pt (Large)"], index=1)
        with col_p2:
            st.markdown("**Page Margin Settings (mm):**")
            margin_top = st.slider("Top Margin", min_value=0, max_value=50, value=15, step=1)
            margin_bottom = st.slider("Bottom Margin", min_value=0, max_value=50, value=15, step=1)
        with col_p3:
            st.markdown("**Page Margin Settings (mm):**")
            margin_left = st.slider("Left Margin", min_value=0, max_value=50, value=15, step=1)
            margin_right = st.slider("Right Margin", min_value=0, max_value=50, value=15, step=1)
            
            border_style = st.selectbox("Card Border Style:", ["4px double #f8a100 (Official)", "2px solid #000000 (Minimal)", "None"])
            page_break = st.toggle("Force 1 Card per Page", value=True)

    font_val = "11pt" if "Compact" in font_size else ("15pt" if "Large" in font_size else "13pt")
    border_val = "none" if border_style == "None" else border_style.split(" (")[0]
    break_val = "always" if page_break else "auto"
    max_w_val = "100%" if paper_orient == "landscape" else "800px"

    # --- ENHANCED PRINT ENGINE INJECTIONS ---
    st.markdown(f"""
        <style>
        /* Modern CSS Variables for System State Mapping */
        :root {{
            --paper-orient: {paper_orient};
            --paper-size: {paper_size};
            --font-size-choice: {font_val};
            --border-choice: {border_val};
            --break-choice: {break_val};
            --max-width-choice: {max_w_val};
        }}
        
        /* 🖨️ ADVANCED MECHANICAL PRINT-TARGET TUNING */
        @media print {{
            @page {{
                size: {paper_size} {paper_orient};
                margin: {margin_top}mm {margin_right}mm {margin_bottom}mm {margin_left}mm !important;
            }}
            
            /* 1. AGGRESSIVE LAYOUT COLLAPSE: Lift app out of hidden parent container spacing blocks */
            div[data-testid="stAppViewMainContainer"],
            .stAppViewMainContainer,
            .stAppViewBlockContainer,
            .stMainBlockContainer,
            .stMain,
            .main,
            .block-container {{
                padding-top: 0px !important;
                padding-bottom: 0px !important;
                margin-top: 0px !important;
                margin-bottom: 0px !important;
                top: 0px !important;
                position: absolute !important;
                width: 100% !important;
            }}
            
            /* 2. Absolute eradication of all interactive Web UI application frames */
            [data-testid="stSidebar"], 
            header, 
            footer, 
            [data-testid="stHeader"],
            h1, 
            .stExpander, 
            [data-testid="stRadio"], 
            [data-testid="stTextInput"], 
            [data-testid="stMultiSelect"], 
            hr,
            iframe,
            .stButton,
            div[style*="height"] {{
                display: none !important;
                height: 0px !important;
                margin: 0px !important;
                padding: 0px !important;
                visibility: hidden !important;
            }}
            
            /* 3. Force card structure to snap directly flush to top edge settings */
            .result-card-container {{
                border: {border_val} !important;
                box-shadow: none !important;
                background: transparent !important;
                margin-top: 0px !important; 
                margin-bottom: 0px !important;
                padding: 5px !important;
                width: 100% !important;
                max-width: 100% !important;
            }}
            
            .print-card-break {{
                page-break-after: {break_val} !important;
                break-after: page !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}
            
            .attendance-print-table th {{
                background-color: #8b0000 !important;
                color: #ffffff !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
        }}
        
        /* 🖥️ PREVIEW SCREEN INTERFACE STYLING (Live App Rendering Mode) */
        .result-card-container {{
            max-width: {max_w_val};
            border: {border_val};
            padding: 25px;
            margin: 0px auto 35px auto;
            background-color: #ffffff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border-radius: 8px;
            font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
            font-size: {font_val};
            color: #222222;
        }}
        
        .card-header-banner {{
            background: linear-gradient(135deg, #e68a00 0%, #f8a100 100%);
            padding: 20px;
            border-radius: 6px;
            color: white;
            margin-bottom: 20px;
        }}
        
        .attendance-print-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            margin-bottom: 20px;
            background-color: #ffffff;
        }}
        
        .attendance-print-table th, .attendance-print-table td {{
            border: 1px solid #111111;
            padding: 10px 8px;
            text-align: center;
            vertical-align: middle;
        }}
        
        .attendance-print-table th {{
            background-color: #8b0000;
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.95em;
            letter-spacing: 0.5px;
        }}
        
        .attendance-print-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        .attendance-print-table td small {{
            color: #555555;
            font-weight: bold;
        }}
        </style>
    """, unsafe_allow_html=True)
    
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
            padding: 12px 24px; 
            border-radius: 4px; 
            cursor: pointer;
            font-family: sans-serif;
            font-size: 16px;
            width: 220px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: all 0.2s ease;
        ">🖨️ Open Print Preview</button>
    """, height=60)
            
    st.markdown("---")

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
                
                matched_disp = "MEDICAL"
                for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                    if section in [x.upper().strip() for x in secs]:
                        matched_disp = disp
                        break
                
                subjects_list = DISCIPLINE_SUBJECTS_MAP[matched_disp]
                
                raw_marks = run_query("""
                    SELECT UPPER(TRIM(subject)) as subject, TRIM(exam_type) as exam_type, marks_obtained, total_marks 
                    FROM marks 
                    WHERE student_id = :id
                """, {"id": current_id})
                
                raw_attendance = run_query("""
                    SELECT month_name, total_days, present_days 
                    FROM attendance 
                    WHERE student_id = :id
                """, {"id": current_id})
                
                # Header Structural Component Build Block
                st.markdown(f"""
                <div class="result-card-container print-card-break">
                    <div class="card-header-banner">
                        <h2 style='margin:0; color:white; letter-spacing:1px;'>CONCORDIA COLLEGES, KASUR</h2>
                        <p style='margin:8px 0 0 0; font-size:15px; color:white; opacity:0.95;'>
                            <b>STUDENT NAME:</b> {name} &nbsp;&nbsp;•&nbsp;&nbsp; 
                            <b>ROLL NO / ID:</b> {current_id} &nbsp;&nbsp;•&nbsp;&nbsp; 
                            <b>SECTION:</b> {section} &nbsp;&nbsp;•&nbsp;&nbsp; 
                            <b>CLASS:</b> {grade_class}
                        </p>
                    </div>
                    <h4 style='margin: 15px 0 5px 0; color:#8b0000; text-transform:uppercase; letter-spacing:0.5px;'>📊 Academic Performance Matrix</h4>
                """, unsafe_allow_html=True)
                
                # Rendering Marks Performance Table Data Grid
                html_table = """
                <table class="attendance-print-table">
                    <thead>
                        <tr>
                            <th style="text-align: left; width: 35%;">Subject Title</th>
                """
                for t_type in selected_tests:
                    html_table += f"<th>{t_type}</th>"
                html_table += "</tr></thead><tbody>"
                
                for sub in subjects_list:
                    html_table += f"<tr><td style='text-align:left; font-weight:bold; background-color:#fafafa;'>{sub}</td>"
                    for t_type in selected_tests:
                        match = raw_marks[(raw_marks['subject'] == sub) & (raw_marks['exam_type'] == t_type)]
                        if not match.empty:
                            obt = match['marks_obtained'].iloc[0]
                            tot = match['total_marks'].iloc[0]
                            html_table += f"<td><b>{obt}</b> <span style='color:#777; font-size:0.85em;'>/ {tot}</span></td>"
                        else:
                            html_table += "<td style='color:#ccc;'>-</td>"
                    html_table += "</tr>"
                html_table += "</tbody></table>"
                st.markdown(html_table, unsafe_allow_html=True)
                
                # Attendance Log Grid Footer Card Render Core Block
                html_att = """
                <h4 style='margin: 25px 0 5px 0; color:#8b0000; text-transform:uppercase; letter-spacing:0.5px;'>📅 Session Attendance Breakdown Summary</h4>
                <table class="attendance-print-table" style="font-size: 0.9em;">
                    <thead><tr>
                """
                for m in AVAILABLE_MONTHS:
                    html_att += f"<th style='padding: 6px 4px;'>{m}</th>"
                html_att += "</tr></thead><tbody><tr>"
                
                for m in AVAILABLE_MONTHS:
                    att_match = raw_attendance[raw_attendance['month_name'] == m]
                    if not att_match.empty:
                        p_d = att_match['present_days'].iloc[0]
                        t_d = att_match['total_days'].iloc[0]
                        percentage = int((p_d / t_d) * 100) if t_d > 0 else 0
                        html_att += f"<td><b>{p_d}/{t_d}</b><br><small>({percentage}%)</small></td>"
                    else:
                        html_att += "<td style='color:#999;'>-</td>"
                        
                html_att += "</tr></tbody></table></div>"
                st.markdown(html_att, unsafe_allow_html=True)

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
