import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title="Concordia Academic Analytics")

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
                st.session_state.user_role = result[0]         
                st.session_state.assigned_subject = result[1]    
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

def run_query(query, params=None):
    if params is None:
        params = {}
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)

def execute_db_command(command, params=None):
    if params is None:
        params = {}
    with engine.begin() as conn:
        conn.execute(text(command), params)

# --- NAVIGATION SIDEBAR ---
st.sidebar.title("🏫 Menu Navigation")
menu_choice = st.sidebar.radio(
    "Go To Module:", 
    ["📊 Home Dashboard", "➕ Add Students", "📝 Enter Marks & Attendance", "📋 Section Summary Report", "📈 Multi-Test Progress Report", "🪪 Student Result Cards"]
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
    st.title("Concordia Colleges, Kasur")
    try:
        s_count = run_query("SELECT COUNT(*) FROM students").iloc[0, 0]
        m_count = run_query("SELECT COUNT(*) FROM marks").iloc[0, 0]
    except Exception:
        s_count, m_count = 0, 0
    c1, c2 = st.columns(2)
    c1.metric("Total Registered Students", s_count)
    c2.metric("Total Grade Records Captured", m_count)

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
            with c1: sel_discipline = st.selectbox("Select Discipline:", AVAILABLE_DISCIPLINE)
            with c2: 
                if st.session_state.user_role == 'teacher' and st.session_state.assigned_subject:
                    teacher_subj = st.session_state.assigned_subject.upper().strip()
                    sel_subject = st.selectbox("Select Subject:", [teacher_subj])
                else:
                    sel_subject = st.selectbox("Select Subject:", DISCIPLINE_SUBJECTS_MAP[sel_discipline])
            with c3: sel_section = st.selectbox("Select Section:", DISCIPLINE_SECTIONS_MAP[sel_discipline])
            
            row2_1, row2_2 = st.columns(2)
            with row2_1: sel_exam = st.selectbox("Test Type:", AVAILABLE_EXAMS)
            with row2_2: total_marks = st.number_input("Total Marks Assigned:", value=100)
            
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
                            st.success("🎉 Section marks matrix saved completely!")
                            st.rerun()
            except Exception as e:
                st.error(f"Database sync issue: {e}")

        elif entry_mode == "👤 By Single Student Roll Number":
            target_id = st.text_input("🔍 Enter Student Roll Number / ID:")
            if target_id and target_id.isdigit():
                student_info = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(target_id)})
                if student_info.empty:
                    st.error("❌ This roll number does not exist.")
                else:
                    s_name = student_info['name'].iloc[0].upper()
                    s_section = student_info['section'].iloc[0].upper().strip()
                    s_class = student_info['class'].iloc[0]
                    st.info(f"👤 Found: {s_name} | Class: {s_class} | Section: {s_section}")
                    
                    matched_disp = "MEDICAL"
                    for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                        if s_section in [x.upper().strip() for x in secs]:
                            matched_disp = disp
                            break
                    
                    c_sub, c_ex, c_m = st.columns(3)
                    with c_sub: single_subj = st.selectbox("Choose Subject:", DISCIPLINE_SUBJECTS_MAP[matched_disp], key="single_sub")
                    with c_ex: single_exam = st.selectbox("Choose Test Term Type:", AVAILABLE_EXAMS, key="single_exam")
                    with c_m: single_total = st.number_input("Total Marks Assigned:", value=100, key="single_max")
                    
                    existing_record = run_query("SELECT marks_obtained FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(target_id), "sub": single_subj, "exam": single_exam})
                    current_val = str(existing_record['marks_obtained'].iloc[0]) if not existing_record.empty else ""
                    single_score = st.text_input("✏️ Enter Marks Obtained:", value=current_val)
                    
                    if st.button("💾 Save Student Record", type="primary"):
                        execute_db_command("DELETE FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(target_id), "sub": single_subj, "exam": single_exam})
                        if single_score.strip() != "":
                            execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:id, :sub, :exam, :score, :total)", {"id": int(target_id), "sub": single_subj.strip().upper(), "exam": single_exam.strip(), "score": single_score.strip(), "total": single_total})
                        st.success("🎉 Marks updated successfully!")
                        st.rerun()

    elif sub_tab_selection == "📅 Monthly Attendance Entry":
        st.subheader("📅 Monthly Attendance Workspace")
        att_flow_mode = st.radio("Select Entry Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number"], horizontal=True, key="att_flow")
        
        if att_flow_mode == "📋 By Complete Section":
            col_as1, col_as2, col_as3 = st.columns(3)
            with col_as1: att_discipline = st.selectbox("Select Discipline Context:", AVAILABLE_DISCIPLINE, key="att_disc")
            with col_as2: att_section = st.selectbox("Select Target Section:", DISCIPLINE_SECTIONS_MAP[att_discipline], key="att_sec")
            with col_as3: att_month = st.selectbox("Select Attendance Month:", AVAILABLE_MONTHS, key="att_month")
                
            default_days = st.number_input("Set Total Working Days:", min_value=1, max_value=31, value=24, key="sec_global_days")
            
            students_att_list = run_query("""
                SELECT s.id AS "ID", s.name AS "Student Name", a.present_days
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id AND UPPER(TRIM(a.month_name)) = UPPER(TRIM(:month))
                WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section))
                ORDER BY s.id ASC
            """, {"month": att_month, "section": att_section})
            
            if not students_att_list.empty:
                with st.form("bulk_attendance_form"):
                    saved_att_presents = {}
                    for idx, row in students_att_list.iterrows():
                        c_b1, c_b2 = st.columns([3, 1])
                        c_b1.write(f"👤 **{row['ID']}** — {row['Student Name']}")
                        init_pres = int(row['present_days']) if pd.notna(row['present_days']) else default_days
                        saved_att_presents[row['ID']] = c_b2.number_input("Days Present", min_value=0, max_value=int(default_days), value=min(int(init_pres), int(default_days)), key=f"pres_{row['ID']}")
                    
                    if st.form_submit_button("💾 Save Attendance Ledger", type="primary"):
                        for s_id, p_d in saved_att_presents.items():
                            execute_db_command("""
                                INSERT INTO attendance (student_id, month_name, total_days, present_days)
                                VALUES (:s_id, :month, :td, :pd)
                                ON CONFLICT (student_id, month_name) DO UPDATE SET total_days = EXCLUDED.total_days, present_days = EXCLUDED.present_days
                            """, {"s_id": int(s_id), "month": att_month.strip(), "td": default_days, "pd": int(p_d)})
                        st.success("🎉 Section Attendance saved successfully!")
                        st.rerun()

# ----------------- 📋 SECTION SUMMARY REPORT -----------------
elif menu_choice == "📋 Section Summary Report":
    col_a, col_b, col_c = st.columns(3)
    with col_a: sel_disc = st.selectbox("Select Discipline:", AVAILABLE_DISCIPLINE, key="summary_disc")
    with col_b: sel_sec = st.selectbox("Select Section:", DISCIPLINE_SECTIONS_MAP[sel_disc], key="summary_sec")
    with col_c: sel_exam = st.selectbox("Select Exam Cycle:", AVAILABLE_EXAMS, key="summary_exam")
    
    students_df = run_query("SELECT id AS \"ID\", name AS \"Student Name\", section AS \"Section\", class AS \"Class\" FROM students WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) ORDER BY id ASC", {"section": sel_sec})
    
    if not students_df.empty:
        subjects = DISCIPLINE_SUBJECTS_MAP[sel_disc]
        marks_df = run_query("""
            SELECT m.student_id, UPPER(TRIM(m.subject)) as subject, m.marks_obtained, m.total_marks
            FROM marks m JOIN students s ON m.student_id = s.id
            WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section)) AND TRIM(m.exam_type) = TRIM(:exam)
        """, {"section": sel_sec, "exam": sel_exam})
        
        summary_rows = []
        for _, s_row in students_df.iterrows():
            s_id = s_row["ID"]
            entry = {"ID": s_id, "Student Name": s_row["Student Name"], "Section": s_row["Section"], "Class": s_row["Class"]}
            obtained_total, max_total, has_scores = 0.0, 0.0, False
            
            for sub in subjects:
                sub_match = marks_df[(marks_df["student_id"] == s_id) & (marks_df["subject"] == sub.upper().strip())]
                if not sub_match.empty:
                    val = str(sub_match["marks_obtained"].iloc[0]).strip().upper()
                    entry[f"{sub} (Obt)"] = val
                    if val.replace('.', '', 1).isdigit():
                        tot = float(sub_match["total_marks"].iloc[0])
                        obtained_total += float(val)
                        max_total += tot
                        has_scores = True
            entry["Total (Obt)"] = int(obtained_total) if has_scores else "-"
            summary_rows.append(entry)
            
        final_report_df = pd.DataFrame(summary_rows)
        st.dataframe(final_report_df.set_index("ID"), use_container_width=True)
import base64
import os

# ----------------- 📈 MULTI-TEST PROGRESS REPORT -----------------
if menu_choice == "📈 Multi-Test Progress Report":
    st.title("📈 Multi-Test Progress Analytics")
    st.markdown("Select your reporting scope below to generate high-fidelity, print-ready student progress cards.")

    # CSS Injection (Kept for print control classes remaining in parent app context)
    st.markdown("""
        <style>
        @media print {
            .no-print { display: none !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # --- LOGO BASE64 ENCODER ENGINE ---
    logo_base64 = ""
    logo_filename = "logo.png" 
    
    if os.path.exists(logo_filename):
        with open(logo_filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            ext = os.path.splitext(logo_filename)[1].replace(".", "").lower()
            if ext == "jpg": ext = "jpeg"
            logo_base64 = f"data:image/{ext};base64,{encoded_string}"
    else:
        st.warning(f"⚠️ Logo file '{logo_filename}' not found on disk. Falling back to text logo header.")

    # --- EXPLICIT TEST FRAMEWORK GLOBAL LIST ---
    all_frameworks = [
        "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "SEND_UP", "MT_5",
        "T_1", "T_2", "T_3", "T_4", "T_5", "T_6", "T_7", "T_8", "T_9", "T_10",
        "HALF_BOOK01", "HALF_BOOK02", "PRE_BOARD"
    ]

    # --- DYNAMIC CONTROLS INTERFACE PANEL ---
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    
    scope_choice = st.radio(
        "𖨾 Select Scope:",
        options=["👤 Single Student Card", "👥 Complete Section Cards"],
        index=0,
        horizontal=True,
        key="mt_reporting_scope"
    )

    months_list = ["May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.", "Jan.", "Feb.", "March", "April"]
    students_to_process = []
    selected_exams_list = []
    
    rendered_discipline = "N/A"
    rendered_section = "N/A"

    if scope_choice == "👤 Single Student Card":
        with st.form("single_student_secure_form"):
            st.markdown("##### 👤 Single Profile Verification Panel")
            col_s1, col_s2 = st.columns([2, 3])
            with col_s1:
                search_id = st.text_input("🔍 Enter Student Roll Number / ID:", value="", key="form_search_id_single")
            with col_s2:
                selected_exams_list = st.multiselect("🎯 Select Tests:", options=all_frameworks, default=["MT_1", "MT_2", "MT_3"], key="form_exams_single")
            
            submit_single = st.form_submit_button("🚀 Fetch & Compile Student Details", use_container_width=True)
            
        if submit_single:
            clean_id = search_id.strip()
            if not clean_id:
                st.error("⚠️ Please input a valid Student Roll Number / ID.")
            else:
                try:
                    query_id = int(clean_id) if clean_id.isdigit() else clean_id
                    
                    student_df = run_query("""
                        SELECT id, name, section, class 
                        FROM students 
                        WHERE id = :sid
                    """, {"sid": query_id})
                    
                    if not student_df.empty:
                        students_to_process = student_df.to_dict('records')
                        rendered_section = student_df.iloc[0]["section"]
                        rendered_discipline = "N/A"
                    else:
                        st.error(f"❌ Student ID #{clean_id} was not found in the database.")
                except Exception as e:
                    st.error(f"⚠️ Student verification query failed: {str(e)}.")

    else:
        with st.form("complete_section_secure_form"):
            st.markdown("##### 👥 Complete Section Processing Panel")
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                sel_disc = st.selectbox("Select Discipline Context:", AVAILABLE_DISCIPLINE, key="form_sel_disc_bulk")
            with col_c2:
                sel_sec = st.selectbox("Select Target Class Section:", DISCIPLINE_SECTIONS_MAP[sel_disc], key="form_sel_sec_bulk")
            with col_c3:
                selected_exams_list = st.multiselect("🎯 Select Tests:", options=all_frameworks, default=["MT_1", "MT_2", "MT_3"], key="form_exams_bulk")
                
            submit_bulk = st.form_submit_button("🚀 Compile All Section Cards", use_container_width=True)
            
        if submit_bulk:
            rendered_discipline = sel_disc
            rendered_section = sel_sec
            
            section_students_df = run_query("""
                SELECT id, name, section, class 
                FROM students 
                WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) 
                ORDER BY id ASC
            """, {"section": sel_sec})
            
            if not section_students_df.empty:
                students_to_process = section_students_df.to_dict('records')
            else:
                st.info(f"💡 No registered student profiles mapped to section '{sel_sec}'.")

    st.markdown('</div>', unsafe_allow_html=True)

    # --- DATA PROCESSING AND RENDERING PIPELINE ENGINE ---
    if students_to_process and not selected_exams_list:
        st.warning("⚠️ Select at least one test metric from the multi-select parameter tool to compile report views.")
        
    elif students_to_process:
        params_dict = {}
        placeholder_list = []
        
        for idx, s in enumerate(students_to_process):
            s_id = s['id']
            clean_s_id = int(s_id) if str(s_id).isdigit() else str(s_id).strip()
            
            key = f"sid_{idx}"
            placeholder_list.append(f":{key}")
            params_dict[key] = clean_s_id
            
        placeholders_str = ", ".join(placeholder_list)
        
        marks_df = pd.DataFrame()
        attendance_df = pd.DataFrame()

        try:
            sample_marks = run_query("SELECT * FROM marks LIMIT 1", {})
            cols_marks = [c.lower() for c in sample_marks.columns]
            
            sub_col = "subject_name" if "subject_name" in cols_marks else ("subject" if "subject" in cols_marks else cols_marks[min(1, len(cols_marks)-1)])
            exam_col = "exam_type" if "exam_type" in cols_marks else ("exam" if "exam" in cols_marks else "exam_type")
            obt_col = "marks_obtained" if "marks_obtained" in cols_marks else ("obtained_marks" if "obtained_marks" in cols_marks else "marks_obtained")
            tot_col = "total_marks" if "total_marks" in cols_marks else "total_marks"

            marks_df = run_query(f"""
                SELECT student_id, {sub_col} as subject_name, TRIM({exam_col}) as exam_type, {obt_col} as marks_obtained, {tot_col} as total_marks
                FROM marks
                WHERE student_id IN ({placeholders_str})
            """, params_dict)
        except Exception as e:
            st.error(f"⚠️ Failed fetching performance records. Details: {str(e)}")

        try:
            sample_att = run_query("SELECT * FROM attendance LIMIT 1", {})
            cols_att = [c.lower() for c in sample_att.columns]
            
            month_col = "month_name" if "month_name" in cols_att else ("month" if "month" in cols_att else "month_name")
            tot_days_col = "total_days" if "total_days" in cols_att else "total_days"
            
            att_days_col = "attended_days"
            for variant in ["attended_days", "present_days", "present", "attended"]:
                if variant in cols_att:
                    att_days_col = variant
                    break

            attendance_df = run_query(f"""
                SELECT student_id, {month_col} as month_name, {tot_days_col} as total_days, {att_days_col} as attended_days 
                FROM attendance
                WHERE student_id IN ({placeholders_str})
            """, params_dict)
        except Exception as e:
            st.error(f"⚠️ Failed fetching attendance logs: {str(e)}")

        st.write("---")

        composite_html_payload = f"""
        <html>
        <head>
        <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
        <style>
        body {{ background-color: #ffffff; margin: 0; padding: 10px; }}
        
        .action-dashboard-panel {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            max-width: 850px;
            margin: 10px auto 25px auto;
            font-family: 'Arial', sans-serif;
        }}
        .action-control-btn {{
            color: white;
            border: none;
            padding: 12px 18px;
            font-size: 14px;
            font-weight: bold;
            border-radius: 6px;
            cursor: pointer;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: background 0.2s, transform 0.1s, opacity 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .action-control-btn:active {{
            transform: scale(0.97);
        }}
        .btn-print-single {{ background-color: #2e7d32; }}
        .btn-print-single:hover {{ background-color: #1b5e20; }}
        .btn-print-bulk {{ background-color: #1565c0; }}
        .btn-print-bulk:hover {{ background-color: #0d47a1; }}
        .btn-img-single {{ background-color: #e65100; }}
        .btn-img-single:hover {{ background-color: #b33900; }}
        .btn-img-bulk {{ background-color: #6a1b9a; }}
        .btn-img-bulk:hover {{ background-color: #4a148c; }}

        .cck-container {{
            background-color: #ffffff;
            border: 1px solid #000000;
            padding: 30px;
            margin: 0 auto 30px auto;
            max-width: 850px;
            color: #000000;
            font-family: 'Arial', sans-serif;
            page-break-after: always;
            box-sizing: border-box;
        }}
        .cck-header-wrapper {{
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 5px;
            position: relative;
        }}
        
        .cck-logo-image-container {{
            width: 75px;
            height: 75px;
            position: absolute;
            left: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .cck-logo-image {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}
        
        .cck-logo-fallback-text {{
            background-color: #e67e22;
            color: #ffffff;
            font-weight: bold;
            font-size: 22px;
            width: 75px;
            height: 75px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
        }}
        
        .cck-title-block {{
            text-align: center;
        }}
        .cck-main-title {{
            font-size: 24px;
            font-weight: bold;
            margin: 15;
            letter-spacing: 0.5px;
        }}
        .cck-sub-title {{
            font-size: 13px;
            color: #444444;
            margin: 2px 0 0 0;
        }}
        .cck-badge-wrapper {{
            text-align: center;
            margin: 15px 0;
        }}
        .cck-doc-badge {{
            display: inline-block;
            background-color: #d1d5db;
            color: #000000;
            font-weight: bold;
            font-size: 16px;
            padding: 4px 20px;
            border-radius: 2px;
        }}
        .cck-meta-row {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .cck-meta-field {{
            margin-right: 15px;
            margin-bottom: 8px;
        }}
        .cck-line-fill {{
            border-bottom: 1px solid #000000;
            display: inline-block;
            min-width: 120px;
            padding-left: 5px;
            font-weight: bold;
        }}
        .cck-report-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
            font-size: 13px;
        }}
        .cck-report-table th, .cck-report-table td {{
            border: 1px solid #000000;
            padding: 6px 4px;
            text-align: center;
        }}
        .cck-report-table th {{
            background-color: #ffffff;
            font-weight: normal;
        }}
        .cck-report-table td:first-child {{
            text-align: left;
            padding-left: 8px;
        }}
        .cck-remarks-area {{
            margin-top: 100px;
            font-size: 14px;
            display: flex;
            align-items: flex-end;
        }}
        .cck-remarks-line {{
            flex-grow: 1;
            border-bottom: 1px solid #000000;
            margin-left: 8px;
            padding-left: 5px;
            font-style: italic;
        }}
        .cck-footer-sign {{
            margin-top: 25px;
            text-align: right;
            font-size: 14px;
            padding-right: 20px;
        }}
        
        @media print {{
            .action-dashboard-panel {{ display: none !important; }}
            .cck-single-print-isolation {{ display: block !important; }}
            .cck-single-print-hide {{ display: none !important; }}
            .cck-container {{
                border: none !important;
                padding: 0 !important;
                margin-bottom: 0 !important;
            }}
        }}
        </style>
        </head>
        <body>
            <div class="action-dashboard-panel">
                <button class="action-control-btn btn-print-single" onclick="executeTargetPrint(true)">👤 Print Single Student</button>
                <button class="action-control-btn btn-print-bulk" onclick="executeTargetPrint(false)">👥 Print Complete Section</button>
                <button class="action-control-btn btn-img-single" onclick="exportDossierToImage(true)">📸 Save Single as Picture</button>
                <button class="action-control-btn btn-img-bulk" onclick="exportDossierToImage(false)">🖼️ Save Section as Pictures</button>
            </div>
            
            <div id="dossiers-master-wrapper">
        """
        
        for index, s_meta in enumerate(students_to_process):
            s_id = str(s_meta["id"]).strip()
            
            raw_name = str(s_meta["name"])
            s_name = " ".join(raw_name.replace("\n", " ").split())
            
            raw_section = str(s_meta["section"]) if s_meta.get("section") else rendered_section
            s_section = " ".join(raw_section.replace("\n", " ").split())
            
            raw_class = str(s_meta["class"]) if s_meta.get("class") else "11th"
            s_class = " ".join(raw_class.replace("\n", " ").split())
            
            match_id = int(s_id) if s_id.isdigit() else s_id
            
            # --- MARKS CARD MATRIX PROCESSING ---
            if not marks_df.empty:
                s_marks = marks_df[marks_df["student_id"].astype(str) == str(match_id)]
            else:
                s_marks = pd.DataFrame()
                
            unique_subjects = sorted(list(s_marks["subject_name"].unique())) if not s_marks.empty else ["English", "Urdu", "Mathematics", "Physics", "Chemistry"]
            
            table_rows_html = ""
            exam_totals_obtained = {exam: 0.0 for exam in selected_exams_list}
            exam_totals_max = {exam: 0.0 for exam in selected_exams_list}
            exam_has_any_data = {exam: False for exam in selected_exams_list}

            for sub in unique_subjects:
                sub_marks = s_marks[s_marks["subject_name"] == sub] if not s_marks.empty else pd.DataFrame()
                row_html = f"<tr><td>{sub}</td>"
                sub_percentages = []

                for exam in selected_exams_list:
                    exam_subset = sub_marks[sub_marks["exam_type"].str.upper() == exam.upper()] if not sub_marks.empty else pd.DataFrame()
                    
                    if not exam_subset.empty:
                        m_obt = exam_subset.iloc[0]["marks_obtained"]
                        m_tot = exam_subset.iloc[0]["total_marks"]
                        
                        try:
                            val_obt = float(m_obt)
                            val_tot = float(m_tot) if float(m_tot) > 0 else 100.0
                            pct = (val_obt / val_tot) * 100
                            row_html += f"<td>{int(pct)}%</td>"
                            sub_percentages.append(pct)
                            
                            exam_totals_obtained[exam] += val_obt
                            exam_totals_max[exam] += val_tot
                            exam_has_any_data[exam] = True
                        except:
                            if str(m_obt).strip().upper() in ["A", "ABSENT"]:
                                row_html += "<td>A</td>"
                                exam_totals_max[exam] += float(m_tot) if m_tot else 100.0
                                exam_has_any_data[exam] = True
                                sub_percentages.append(0.0)
                            else:
                                row_html += "<td></td>"
                    else:
                        row_html += "<td></td>"
                
                if sub_percentages:
                    avg_pct = int(sum(sub_percentages) / len(sub_percentages))
                    row_html += f"<td><strong>{avg_pct}%</strong></td></tr>"
                else:
                    row_html += "<td></td></tr>"
                    
                table_rows_html += row_html

            total_row_html = "<tr><td><strong>Total</strong></td>"
            grand_total_percentages = []
            for exam in selected_exams_list:
                if exam_has_any_data[exam] and exam_totals_max[exam] > 0:
                    tot_pct = int((exam_totals_obtained[exam] / exam_totals_max[exam]) * 100)
                    total_row_html += f"<td><strong>{tot_pct}%</strong></td>"
                    grand_total_percentages.append(tot_pct)
                else:
                    total_row_html += "<td></td>"
            
            if grand_total_percentages:
                overall_avg = int(sum(grand_total_percentages) / len(grand_total_percentages))
                total_row_html += f"<td><strong>{overall_avg}%</strong></td></tr>"
            else:
                total_row_html += "<td></td></tr>"

            # --- ATTENDANCE TRACKER PROCESSING ---
            if not attendance_df.empty:
                s_att = attendance_df[attendance_df["student_id"].astype(str) == str(match_id)]
            else:
                s_att = pd.DataFrame()
            
            tot_days_row = ""
            att_days_row = ""
            pct_days_row = ""
            
            overall_tot_days = 0
            overall_att_days = 0

            for m in months_list:
                m_subset = s_att[s_att["month_name"].str.startswith(m[:3], na=False)] if not s_att.empty else pd.DataFrame()
                
                if not s_att.empty and not m_subset.empty:
                    t_d = int(m_subset.iloc[0]["total_days"])
                    a_d = int(m_subset.iloc[0]["attended_days"])
                    p_d = int((a_d / t_d) * 100) if t_d > 0 else 0
                    
                    overall_tot_days += t_d
                    overall_att_days += a_d
                    
                    tot_days_row += f"<td>{t_d}</td>"
                    att_days_row += f"<td>{a_d}</td>"
                    pct_days_row += f"<td>{p_d}%</td>"
                else:
                    tot_days_row += "<td></td>"
                    att_days_row += "<td></td>"
                    pct_days_row += "<td></td>"
            
            if overall_tot_days > 0:
                overall_att_pct = f"{int((overall_att_days / overall_tot_days) * 100)}%"
                tot_days_row += f"<td>{overall_tot_days}</td>"
                att_days_row += f"<td>{overall_att_days}</td>"
                pct_days_row += f"<td><strong>{overall_att_pct}</strong></td>"
            else:
                tot_days_row += "<td></td>"
                att_days_row += "<td></td>"
                pct_days_row += "<td></td>"

            # --- ANALYTIC AUTO REMARKS TEXT ---
            if grand_total_percentages:
                final_perf = grand_total_percentages[-1]
                if final_perf >= 85: remarks_text = "Excellent effort! An outstanding performer with exceptional academic discipline."
                elif final_perf >= 70: remarks_text = "Highly satisfactory progress across consecutive monthly milestones."
                elif final_perf >= 50: remarks_text = "Good core standing. Targeted revision in weaker subjects will boost performance."
                else: remarks_text = "Requires closer attention and regular conceptual reinforcement."
            else:
                remarks_text = "Assessment parameters incomplete or awaiting evaluation confirmation."

            thead_exams_th = "".join([f"<th style='font-weight: bold;'>{exam}</th>" for exam in selected_exams_list])
            thead_sub_tds = "".join(["<td>Obt. Age%</td>" for _ in selected_exams_list])

            if logo_base64:
                logo_element_markup = f'<img class="cck-logo-image" src="{logo_base64}" alt="College Logo" />'
            else:
                logo_element_markup = '<div class="cck-logo-fallback-text">CC</div>'

            composite_html_payload += f"""
            <div class="cck-container student-card-record" data-index="{index}" data-name="{s_name.replace(' ', '_')}" data-id="{s_id}">
                <div class="cck-header-wrapper">
                    <div class="cck-logo-image-container">
                        {logo_element_markup}
                    </div>
                    <div class="cck-title-block">
                        <div class="cck-main-title">CONCORDIA COLLEGE KASUR</div>
                    </div>
                </div>
                
                <div class="cck-badge-wrapper">
                    <div class="cck-doc-badge">Result Card</div>
                </div>
                
                <div class="cck-meta-row">
                    <div class="cck-meta-field">Name: <span class="cck-line-fill">{s_name}</span></div>
                    <div class="cck-meta-field">ID: <span class="cck-line-fill">{s_id}</span></div>
                    <div class="cck-meta-field">Section: <span class="cck-line-fill">{s_section}</span></div>
                    <div class="cck-meta-field">Class: <span class="cck-line-fill">{s_class}</span></div>
                </div>
                
                <table class="cck-report-table">
                    <thead>
                        <tr>
                            <th style="width: 25%;"></th>
                            {thead_exams_th}
                            <th></th>
                        </tr>
                        <tr>
                            <th style="text-align: left; padding-left: 8px; font-weight: bold;">Subjects</th>
                            {thead_sub_tds}
                            <td style="font-weight: bold;">Avg.%</td>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                        {total_row_html}
                    </tbody>
                </table>
                
                <div class="cck-badge-wrapper" style="margin-top: 10px; margin-bottom: 5px;">
                    <div class="cck-doc-badge" style="background-color: transparent; font-size: 15px; text-decoration: underline;">Attendance Report</div>
                </div>
                
                <table class="cck-report-table" style="font-size: 11px; margin-top: 5px;">
                    <thead>
                        <tr>
                            <th style="width: 14%;"></th>
                            <th>May</th><th>June</th><th>July</th><th>Aug.</th><th>Sept.</th><th>Oct.</th>
                            <th>Nov.</th><th>Dec.</th><th>Jan.</th><th>Feb.</th><th>March</th><th>April</th>
                            <th style="font-weight: bold;">Over All Att.</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td><strong>Total Days</strong></td>{tot_days_row}</tr>
                        <tr><td><strong>Att. Days</strong></td>{att_days_row}</tr>
                        <tr><td><strong>Age%</strong></td>{pct_days_row}</tr>
                    </tbody>
                </table>
                
                <div class="cck-remarks-area">
                    <strong>Remarks:</strong>
                    <div class="cck-remarks-line">{remarks_text}</div>
                </div>
                
                <div class="cck-footer-sign">
                    <strong>Principal Sign</strong>
                </div>
            </div>
            """
        
        composite_html_payload += """
            </div> 
            
            <script>
            function executeTargetPrint(isSingleTarget) {
                var cards = document.querySelectorAll('.student-card-record');
                if (cards.length === 0) return;
                
                if (isSingleTarget) {
                    cards.forEach(function(card, idx) {
                        if (idx === 0) {
                            card.classList.add('cck-single-print-isolation');
                            card.classList.remove('cck-single-print-hide');
                        } else {
                            card.classList.add('cck-single-print-hide');
                            card.classList.remove('cck-single-print-isolation');
                        }
                    });
                } else {
                    cards.forEach(function(card) {
                        card.classList.remove('cck-single-print-hide');
                        card.classList.remove('cck-single-print-isolation');
                    });
                }
                
                setTimeout(function() { window.print(); }, 200);
            }

            function triggerImageCaptureSequence(targetList, currentIndex) {
                if (currentIndex >= targetList.length) return;
                
                var currentElement = targetList[currentIndex];
                var studentName = currentElement.getAttribute('data-name') || 'Student';
                var studentID = currentElement.getAttribute('data-id') || 'Unknown';
                
                html2canvas(currentElement, {
                    scale: 2, 
                    useCORS: true,
                    backgroundColor: '#ffffff'
                }).then(function(canvas) {
                    var dataUrl = canvas.toDataURL('image/png');
                    var downloadAnchor = document.createElement('a');
                    
                    downloadAnchor.download = 'Result_Card_' + studentName + '_' + studentID + '.png';
                    downloadAnchor.href = dataUrl;
                    document.body.appendChild(downloadAnchor);
                    downloadAnchor.click();
                    document.body.removeChild(downloadAnchor);
                    
                    triggerImageCaptureSequence(targetList, currentIndex + 1);
                }).catch(function(err) {
                    console.error("Canvas image export failure configuration:", err);
                    triggerImageCaptureSequence(targetList, currentIndex + 1);
                });
            }

            function exportDossierToImage(isSingleTarget) {
                var cards = document.querySelectorAll('.student-card-record');
                if (cards.length === 0) {
                    alert("No valid student cards rendered to capture.");
                    return;
                }

                if (isSingleTarget) {
                    triggerImageCaptureSequence([cards[0]], 0);
                } else {
                    if (confirm("Generate and download separate PNG snapshots for all (" + cards.length + ") compiled records?")) {
                        triggerImageCaptureSequence(Array.from(cards), 0);
                    }
                }
            }
            </script>
        </body>
        </html>
        """
        
        dynamic_height = 1250 if len(students_to_process) == 1 else min(1150 * len(students_to_process), 9500)
        components.html(composite_html_payload, height=dynamic_height, scrolling=True)
To add the picture export functionality to your **Student Result Cards** engine, we will integrate `html2canvas` directly into your HTML/CSS layout structure and inject the required action buttons.

The image capture loops through each card element using its `data-id` and `data-name` parameters to dynamically save files precisely named after each student.

Here is your updated, fully integrated code segment:

```python
# ----------------- 🪪 STUDENT RESULT CARDS -----------------
elif menu_choice == "🪪 Student Result Cards":
    st.title("🪪 Student Result Cards — Print Engine")
    
    print_scope = st.radio("𖨾 Select Scope:", ["👤 Single Student Card", "👥 Complete Section Cards"], horizontal=True)
    col_c1, col_c2 = st.columns(2)
    with col_c1: search_id = st.text_input("🔍 Enter Student Roll Number / ID:")
    with col_c2: selected_test = st.selectbox("🎯 Select Test Term:", options=AVAILABLE_EXAMS)

    if search_id and search_id.isdigit() and selected_test:
        base_student = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(search_id)})
        if not base_student.empty:
            target_section = base_student['section'].iloc[0].upper().strip()
            
            if print_scope == "👥 Complete Section Cards":
                students_to_print = run_query("SELECT id, name, section, class FROM students WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) ORDER BY id ASC", {"section": target_section})
            else:
                students_to_print = pd.DataFrame([{"id": int(search_id), "name": base_student['name'].iloc[0], "section": target_section, "class": base_student['class'].iloc[0]}])

            # HTML PAYLOAD WITH INTEGRATED INLINE STYLES AND IMAGE EXPORT CAPABILITIES
            compiled_html = """
            <!DOCTYPE html>
            <html>
            <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
            <style>
                body { font-family: "Times New Roman", Times, serif; color: #000; background-color: #fff; margin: 0; padding: 10px; }
                .official-card-container { max-width: 850px; margin: 10px auto; padding: 25px; border: 1px solid #000; background: #fff; position: relative; }
                
                /* VERTICAL BLOCK HEADER LAYOUT */
                .header-block { text-align: left; margin-bottom: 20px; width: 100%; }
                .logo-row { display: block; width: 100%; margin-bottom: 12px; }
                .logo-img { max-height: 48px; width: auto; display: block; margin-left: 0; }
                
                .inst-main-header { font-weight: bold; font-size: 28px; letter-spacing: 0.5px; margin: 0; line-height: 1.1; text-align: center; width: 100%; }
                .inst-sub-header { font-size: 13px; font-weight: normal; margin: 4px 0 0 0; text-align: center; color: #444; width: 100%; }
                .doc-type-banner { text-align: center; font-weight: bold; font-size: 16px; text-transform: uppercase; margin: 25px 0 20px 0; letter-spacing: 1px; }
                
                /* THE HORIZONTAL STRUCTURAL GRID */
                .meta-layout-table { width: 100%; border-collapse: collapse; border: none; margin-bottom: 20px; font-size: 14px; }
                .meta-layout-table td { border: none; padding: 3px; vertical-align: bottom; white-space: nowrap; }
                .underlined-value-span { border-bottom: 1px solid #000; font-weight: bold; padding: 0 4px; display: inline-block; text-transform: uppercase; }
                
                .doc-data-table { width: 100%; border-collapse: collapse; margin-top: 5px; margin-bottom: 15px; font-size: 14px; }
                .doc-data-table th, .doc-data-table td { border: 1px solid #000; padding: 6px 4px; text-align: center; }
                .doc-data-table th { font-weight: bold; background-color: #fff; }
                
                .section-header-title { font-size: 15px; font-weight: bold; margin: 25px 0 8px 0; text-align: left; text-transform: uppercase; border-bottom: 1px dashed #000; padding-bottom: 3px; }
                
                /* HORIZONTAL ATTENDANCE LAYOUT */
                .attendance-matrix-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }
                .attendance-matrix-table th, .attendance-matrix-table td { border: 1px solid #000; padding: 5px 3px; text-align: center; }
                .attendance-matrix-table th { font-weight: bold; background-color: #fff; }
                .attendance-matrix-table td.row-title-cell { font-weight: bold; background-color: #fff; text-align: left; padding-left: 5px; font-size: 13px; }
                
                .footer-signatures-table { width: 100%; margin-top: 45px; font-size: 14px; border: none; }
                .footer-signatures-table td { border: none; }
                .sig-marker-line { border-top: 1px solid #000; width: 150px; text-align: center; padding-top: 4px; display: inline-block; font-weight: bold; }
                
                /* ACTION BUTTONS */
                .print-btn, .export-btn { 
                    background: #222; color: #fff; padding: 10px 20px; font-weight: bold; 
                    border-radius: 4px; border: none; cursor: pointer; margin-bottom: 20px; 
                    font-size: 14px; margin-right: 10px; transition: background 0.2s;
                }
                .export-btn { background: #007bff; }
                .export-btn:hover { background: #0056b3; }
                .print-btn:hover { background: #444; }

                @media print {
                    .print-btn, .export-btn { display: none !important; }
                    .official-card-container { border: none !important; margin: 0 auto 15mm auto !important; page-break-inside: avoid !important; break-inside: avoid !important; }
                    .print-page-break-divider { page-break-after: always !important; break-after: page !important; }
                }
            </style>
            <script>
                // JavaScript routine to target a specific card canvas and capture it as an image download
                function downloadCardImage(cardId, rollNum) {
                    var targetElement = document.getElementById(cardId);
                    if (targetElement) {
                        html2canvas(targetElement, {
                            useCORS: true,
                            scale: 2, // Enhances output image resolution clarity
                            logging: false
                        }).then(function(canvas) {
                            var downloadLink = document.createElement('a');
                            downloadLink.download = 'Result_Card_' + rollNum + '.png';
                            downloadLink.href = canvas.toDataURL('image/png');
                            downloadLink.click();
                        });
                    }
                }
            </script>
            </head>
            <body>
                <button class="print-btn" onclick="window.print();">🖨️ Trigger Document Print (Ctrl+P)</button>
            """

            for idx, student_row in students_to_print.iterrows():
                current_id = int(student_row['id'])
                name = str(student_row['name']).upper()
                section = str(student_row['section']).upper().strip()
                grade_class = str(student_row['class']).upper()
                test_name = selected_test.upper()
                
                matched_disp = "MEDICAL"
                for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                    if section in [x.upper().strip() for x in secs]: 
                        matched_disp = disp
                        break
                
                subjects_list = DISCIPLINE_SUBJECTS_MAP[matched_disp]
                raw_marks = run_query("SELECT UPPER(TRIM(subject)) as subject, TRIM(exam_type) as exam_type, marks_obtained, total_marks FROM marks WHERE student_id = :id", {"id": current_id})
                
                # Fetch full complete sequence ledger dataset for horizontal formatting table matrix reconstruction
                db_att = run_query("""
                    SELECT UPPER(TRIM(month_name)) as m_name, total_days, present_days 
                    FROM attendance WHERE student_id = :id
                """, {"id": current_id})
                
                att_cells = {}
                tot_sum, pres_sum = 0, 0
                for m in AVAILABLE_MONTHS:
                    m_upper = m.upper().strip()
                    match_att = db_att[db_att['m_name'] == m_upper]
                    if not match_att.empty:
                        td = int(match_att['total_days'].iloc[0])
                        pd_val = int(match_att['present_days'].iloc[0])
                        tot_sum += td
                        pres_sum += pd_val
                        pct = f"{int((pd_val / td) * 100)}%" if td > 0 else "0%"
                        att_cells[m] = {"td": str(td), "pd": str(pd_val), "pct": pct}
                    else:
                        att_cells[m] = {"td": "", "pd": "", "pct": ""}
                
                # Determine overall attendance percentage figure
                attendance_percentage = 0.0
                if tot_sum > 0:
                    attendance_percentage = (pres_sum / tot_sum) * 100
                        
                overall_pct_str = f"{int(attendance_percentage)}%" if tot_sum > 0 else ""
                att_cells["Over All Att."] = {"td": str(tot_sum) if tot_sum > 0 else "", "pd": str(pres_sum) if tot_sum > 0 else "", "pct": overall_pct_str}

                logo_base64 = "https://raw.githubusercontent.com/mirfanshakirpgc-art/Academics-Reports/main/logo.png"
                
                # Reset grand totals for this student card
                grand_total_marks = 0.0
                grand_obtained_marks = 0.0
                
                # Assign unique ID strings to dynamically handle specific cards during loop rendering iterations
                unique_card_id = f"student-card-{current_id}"

                compiled_html += f"""
                <button class="export-btn" onclick="downloadCardImage('{unique_card_id}', '{current_id}')">🖼️ Export Card ({current_id}) as PNG</button>
                
                <div class="official-card-container" id="{unique_card_id}">
                    <div class="header-block">
                        <div class="logo-row">
                            <img class="logo-img" src="{logo_base64}" alt="Concordia Logo">
                        </div>
                        <div class="inst-main-header">CONCORDIA COLLEGE KASUR</div>
                    </div>
                    
                    <div class="doc-type-banner"> Result Card</div>
                    
                    <table class="meta-layout-table">
                        <tr>
                            <td style="width: 40%;"> Name: <span class="underlined-value-span" style="width: 82%;">{name}</span></td>
                            <td style="width: 14%;"> ID: <span class="underlined-value-span" style="width: 68%;">{current_id}</span></td>
                            <td style="width: 16%;"> Section: <span class="underlined-value-span" style="width: 55%;">{section}</span></td>
                            <td style="width: 14%;"> Class: <span class="underlined-value-span" style="width: 55%;">{grade_class}</span></td>
                            <td style="width: 16%;"> Test: <span class="underlined-value-span" style="width: 65%;">{test_name}</span></td>
                        </tr>
                    </table>
                    
                    <table class="doc-data-table">
                        <thead>
                            <tr>
                                <th style="text-align: left; width: 35%; padding-left: 10px;">Subjects</th>
                                <th style="width: 13%;">Obt. Marks</th>
                                <th style="width: 13%;">Total Marks</th>
                                <th style="width: 13%;">Pass Marks</th>
                                <th style="width: 13%;">Age%</th>
                                <th style="width: 13%;">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                student_failed_any_subject = False
                has_valid_marks_data = False

                for sub in subjects_list:
                    match = raw_marks[(raw_marks['subject'] == sub) & (raw_marks['exam_type'] == selected_test)]
                    obt_disp, tot_marks_num, pass_marks_num, per_disp, status_disp = "", "", "", "", ""
                    if not match.empty:
                        try:
                            obt_val = str(match['marks_obtained'].iloc[0]).strip().upper()
                            tot_val = match['total_marks'].iloc[0]
                            tot_marks_num = int(tot_val) if tot_val else 100
                            pass_marks_num = int(tot_marks_num * 0.4)
                            
                            if obt_val in ["A", "ABSENT"]:
                                obt_disp, per_disp, status_disp = "A", "0%", "Fail"
                                grand_total_marks += tot_marks_num
                                student_failed_any_subject = True
                                has_valid_marks_data = True
                            elif obt_val.replace('.', '', 1).isdigit():
                                num_obt = float(obt_val)
                                obt_disp = str(int(num_obt)) if num_obt.is_integer() else str(num_obt)
                                per_disp = f"{int((num_obt / tot_marks_num) * 100)}%"
                                
                                grand_obtained_marks += num_obt
                                grand_total_marks += tot_marks_num
                                has_valid_marks_data = True
                                
                                if num_obt >= pass_marks_num:
                                    status_disp = "Pass"
                                else:
                                    status_disp = "Fail"
                                    student_failed_any_subject = True
                        except Exception: 
                            pass
                        
                    compiled_html += f"""
                            <tr>
                                <td style="text-align: left; font-weight: bold; padding-left: 10px;">{sub}</td>
                                <td>{obt_disp}</td>
                                <td>{tot_marks_num if tot_marks_num else "-"}</td>
                                <td>{pass_marks_num if pass_marks_num else "-"}</td>
                                <td>{per_disp}</td>
                                <td style="font-weight: bold;">{status_disp}</td>
                            </tr>
                    """
                
                # Grand Total calculation row
                grand_per_disp = ""
                grand_status_disp = ""
                if has_valid_marks_data and grand_total_marks > 0:
                    grand_per_disp = f"{int((grand_obtained_marks / grand_total_marks) * 100)}%"
                    grand_status_disp = "Fail" if student_failed_any_subject else "Pass"

                # --- ALGORITHMIC AUTOMATED REMARKS ENGINE ---
                remarks_text = "No records found."
                if has_valid_marks_data:
                    if student_failed_any_subject:
                        if tot_sum > 0 and attendance_percentage < 85.0:
                            remarks_text = "Unsatisfactory academic status with critical attendance below acceptable 85% benchmark. Immediate improvement required."
                        else:
                            remarks_text = "Academic failure detected in one or more subjects. Needs focused remedial attention and harder work."
                    else:
                        grand_percentage = (grand_obtained_marks / grand_total_marks) * 100
                        
                        if tot_sum > 0 and attendance_percentage < 85.0:
                            remarks_text = f"Good academic performance ({grand_percentage:.0f}%), but attendance is short ({attendance_percentage:.0f}%). Needs to maintain minimum 85% attendance."
                        else:
                            if grand_percentage >= 80:
                                remarks_text = "Excellent work! Exceptional academic progress and highly commendable attendance performance."
                            elif grand_percentage >= 60:
                                remarks_text = "Good overall performance. Capable of achieving higher results with consistent effort."
                            else:
                                remarks_text = "Fair performance. Has passed all subjects but possesses significant potential to increase scores."

                compiled_html += f"""
                            <tr style="background-color: #fff; font-weight: bold;">
                                <td style="text-align: left; padding-left: 10px;">GRAND TOTAL</td>
                                <td>{int(grand_obtained_marks) if grand_obtained_marks.is_integer() else grand_obtained_marks}</td>
                                <td>{int(grand_total_marks)}</td>
                                <td>-</td>
                                <td>{grand_per_disp}</td>
                                <td>{grand_status_disp}</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <div class="section-header-title">Attendance Report</div>
                    
                    <table class="attendance-matrix-table">
                        <thead>
                            <tr>
                                <th style="width: 12%;">Metric</th>
                                {''.join([f'<th style="width: 6.7%;">{m}</th>' for m in AVAILABLE_MONTHS])}
                                <th style="width: 11%;">Over All Att.</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="row-title-cell">Total Days</td>
                                {''.join([f'<td>{att_cells[m]["td"]}</td>' for m in AVAILABLE_MONTHS])}
                                <td style="font-weight: bold;">{att_cells["Over All Att."]["td"]}</td>
                            </tr>
                            <tr>
                                <td class="row-title-cell">Att. Days</td>
                                {''.join([f'<td>{att_cells[m]["pd"]}</td>' for m in AVAILABLE_MONTHS])}
                                <td style="font-weight: bold;">{att_cells["Over All Att."]["pd"]}</td>
                            </tr>
                            <tr>
                                <td class="row-title-cell">Age%</td>
                                {''.join([f'<td>{att_cells[m]["pct"]}</td>' for m in AVAILABLE_MONTHS])}
                                <td style="font-weight: bold;">{att_cells["Over All Att."]["pct"]}</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <div style="font-size:14px; margin-top:25px; margin-bottom:15px; font-weight: normal;">
                        Remarks: <span style="font-weight: bold; border-bottom: 1px solid #000; padding-bottom: 2px; display: inline-block; width: 88%; font-style: italic;">{remarks_text}</span>
                    </div>
                    
                    <table class="footer-signatures-table">
                        <tr>
                            <td style="text-align: left; width: 50%; visibility: hidden;"><span class="sig-marker-line">Class Incharge</span></td>
                            <td style="text-align: right; width: 50%;"><span class="sig-marker-line">Principal Sign</span></td>
                        </tr>
                    </table>
                </div>
                <div class="print-page-break-divider"></div>
                """
                
            compiled_html += """
            </body>
            </html>
            """
            
            # Render layout view frame container component
            components.html(compiled_html, height=800, scrolling=True)
