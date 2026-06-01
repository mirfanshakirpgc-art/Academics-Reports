import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import base64
import os

# --- CONFIGURE INITIAL PERSISTENT LAYOUT DISPLAY STATE ---
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
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120) 
    st.title("Concordia College Kasur")
    
    username_input = st.text_input("Username", key="login_username_input")
    password_input = st.text_input("Password", type="password", key="login_password_input")
    
    if st.button("Log In", key="login_submit_btn"):
        with engine.connect() as conn:
            # Enforce infrastructure baseline tables if absent
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS app_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'teacher',
                    assigned_subject VARCHAR(100)
                );
            """))
            # Inject primary recovery administrator profiles safely
            conn.execute(text("""
                INSERT INTO app_users (username, password, role) 
                VALUES ('admin', 'concordia123', 'admin') 
                ON CONFLICT (username) DO NOTHING;
            """))
            
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

# --- AUTOMATIC DATA TABLES INITIALIZER MATRIX ---
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

# --- GLOBAL UTILITY ABSTRACT DATA LAYERS ---
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
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.markdown("<h3 style='text-align: center; margin-top: -5px;'>Menu Navigation</h3>", unsafe_allow_html=True)
menu_choice = st.sidebar.radio(
    "Go To Module:", 
    ["📊 Home Dashboard", "➕ Add Students", "📝 Enter Marks & Attendance", "📋 Section Summary Report", "📈 Multi-Test Progress Report", "🪪 Student Result Cards", "👨‍🏫 Teacher Management"],
    key="primary_sidebar_navigation"
)

if st.sidebar.button("🚪 Log Out", key="sidebar_logout_btn"):
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.assigned_subject = None
    st.rerun()

# --- MAP GLOBAL STRUCTURAL TARGET CONFIGURATIONS ---
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
    st.title("Concordia College Kasur")
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
    
    if st.button("🚀 Process and Save Bulk Profiles", type="primary", key="save_bulk_profiles_btn"):
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
    sub_tab_selection = st.radio("🎯 Select Workspace Sub-Module Target:", ["📝 Academic Exam Marks Entry", "📅 Monthly Attendance Entry"], horizontal=True, key="intake_sub_navigation")
    st.markdown("---")

    current_role = st.session_state.get('user_role', 'teacher')
    assigned_subject = st.session_state.get('assigned_subject', None)

    if sub_tab_selection == "📝 Academic Exam Marks Entry":
        entry_mode = st.radio("🎯 Select Entry Workflow Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number", "📤 Bulk Excel/CSV Import"], horizontal=True, key="marks_workflow_mode")
        st.markdown("---")

        if entry_mode == "📋 By Complete Section":
            c1, c2, c3 = st.columns(3)
            if current_role == 'teacher' and assigned_subject:
                with c1: st.info(f"🔒 Bound to Your Assigned Subject: {assigned_subject}")
                sel_subject = assigned_subject
                with c2: 
                    all_secs_flat = sum(DISCIPLINE_SECTIONS_MAP.values(), [])
                    sel_section = st.selectbox("Select Section:", sorted(list(set(all_secs_flat))), key="m_teacher_sec")
            else:
                with c1: sel_discipline = st.selectbox("Select Discipline:", AVAILABLE_DISCIPLINE, key="m_admin_disc")
                with c2: sel_subject = st.selectbox("Select Subject:", DISCIPLINE_SUBJECTS_MAP[sel_discipline], key="m_admin_sub")
                with c3: sel_section = st.selectbox("Select Section:", DISCIPLINE_SECTIONS_MAP[sel_discipline], key="m_admin_sec")
            
            if sel_subject and sel_section:
                row2_1, row2_2 = st.columns(2)
                with row2_1: sel_exam = st.selectbox("Test Type:", AVAILABLE_EXAMS, key="m_exam_type_sec")
                with row2_2: total_marks = st.number_input("Total Marks Assigned:", value=100, key="m_total_assigned_sec")
                
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
                                updated_scores[row['ID']] = col_s2.text_input("Score (Numeric, A or NC)", value=str(row['Marks']), key=f"sec_input_{row['ID']}", label_visibility="collapsed")
                            
                            if st.form_submit_button("💾 Save Section Marks", type="primary"):
                                for s_id, score in updated_scores.items():
                                    execute_db_command("DELETE FROM marks WHERE student_id = :s_id AND UPPER(TRIM(subject)) = UPPER(TRIM(:subject)) AND TRIM(exam_type) = TRIM(:exam)", {"s_id": int(s_id), "subject": sel_subject, "exam": sel_exam})
                                    
                                    cleaned_score = score.strip().upper()
                                    if cleaned_score != "":
                                        execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:s_id, :subject, :exam, :score, :total)", {"s_id": int(s_id), "subject": sel_subject.strip().upper(), "exam": sel_exam.strip(), "score": cleaned_score, "total": total_marks})
                                st.success("🎉 Section marks matrix saved completely!")
                                st.rerun()
                except Exception as e:
                    st.error(f"Database sync issue: {e}")

        elif entry_mode == "👤 By Single Student Roll Number":
            target_id = st.text_input("🔍 Enter Student Roll Number / ID:", key="single_marks_id")
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
                    with c_sub: 
                        if current_role == 'teacher' and assigned_subject:
                            single_subj = st.selectbox("Choose Subject:", [assigned_subject], key="single_sub")
                        else:
                            single_subj = st.selectbox("Choose Subject:", DISCIPLINE_SUBJECTS_MAP[matched_disp], key="single_sub")
                    with c_ex: single_exam = st.selectbox("Choose Test Term Type:", AVAILABLE_EXAMS, key="single_exam")
                    with c_m: single_total = st.number_input("Total Marks Assigned:", value=100, key="single_max")
                    
                    existing_record = run_query("SELECT marks_obtained FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(target_id), "sub": single_subj, "exam": single_exam})
                    current_val = str(existing_record['marks_obtained'].iloc[0]) if not existing_record.empty else ""
                    single_score = st.text_input("✏️ Enter Marks Obtained (Numeric, A or NC):", value=current_val, key="single_score_field")
                    
                    if st.button("💾 Save Student Record", type="primary", key="save_single_student_mark_btn"):
                        execute_db_command("DELETE FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(target_id), "sub": single_subj, "exam": single_exam})
                        
                        cleaned_single_score = single_score.strip().upper()
                        if cleaned_single_score != "":
                            execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:id, :sub, :exam, :score, :total)", {"id": int(target_id), "sub": single_subj.strip().upper(), "exam": single_exam.strip(), "score": cleaned_single_score, "total": single_total})
                        st.success("🎉 Marks updated successfully!")
                        st.rerun()

        elif entry_mode == "📤 Bulk Excel/CSV Import":
            st.subheader("📤 Bulk Marks CSV Document Importer")
            st.info("📊 Spreadsheet layout must use these lowercase headers: **student_id** and **marks_obtained**")
            
            c_xl1, c_xl2, c_xl3 = st.columns(3)
            all_subjects_flat = sorted(list(set(sum(DISCIPLINE_SUBJECTS_MAP.values(), []))))
            
            with c_xl1: 
                if current_role == 'teacher' and assigned_subject:
                    xl_subject = st.selectbox("Target Entry Subject:", [assigned_subject], key="xl_m_sub")
                else:
                    xl_subject = st.selectbox("Target Entry Subject:", all_subjects_flat, key="xl_m_sub")
            with c_xl2: xl_exam = st.selectbox("Target Entry Test Context:", AVAILABLE_EXAMS, key="xl_m_exam")
            with c_xl3: xl_total = st.number_input("Set Assignment Total Marks Capacity:", value=100, key="xl_m_total")
            
            uploaded_file = st.file_uploader("Choose CSV Sheet file to import:", type=['csv'], key="marks_uploader_widget")
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    df.columns = [str(c).lower().strip() for c in df.columns]
                    
                    if 'student_id' in df.columns and 'marks_obtained' in df.columns:
                        st.dataframe(df, use_container_width=True)
                        if st.button("🚀 Process and Save Bulk Marks", type="primary", key="bulk_marks_save_btn"):
                            success_count = 0
                            for _, row in df.iterrows():
                                s_id = str(row['student_id']).split('.')[0].strip()
                                score = str(row['marks_obtained']).strip().upper()
                                if s_id.isdigit():
                                    execute_db_command("DELETE FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(s_id), "sub": xl_subject, "exam": xl_exam})
                                    if score != "" and score != 'NAN':
                                        execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:id, :sub, :exam, :score, :total)", {"id": int(s_id), "sub": xl_subject.strip().upper(), "exam": xl_exam.strip(), "score": score, "total": xl_total})
                                        success_count += 1
                            st.success(f"🎉 Successfully updated {success_count} student grade rows!")
                            st.rerun()
                    else:
                        st.error("❌ Heading processing mistake! Confirm column tags match 'student_id' and 'marks_obtained' names exactly.")
                except Exception as e:
                    st.error(f"Error handling system processing upload: {e}")

    elif sub_tab_selection == "📅 Monthly Attendance Entry":
        st.subheader("📅 Monthly Attendance Workspace")
        att_flow_mode = st.radio("Select Entry Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number", "📤 Bulk Excel/CSV Import"], horizontal=True, key="attendance_workflow_mode")
        st.markdown("---")
        
        if att_flow_mode == "📋 By Complete Section":
            col_as1, col_as2, col_as3 = st.columns(3)
            all_secs_flat = sorted(list(set(sum(DISCIPLINE_SECTIONS_MAP.values(), []))))
            
            with col_as1: 
                if current_role == 'teacher':
                    st.info("🔒 Logged Teacher Roster View")
                else:
                    st.info("⚙️ Administrative Master View")
            with col_as2: att_section = st.selectbox("Select Target Section:", all_secs_flat, key="att_sec_unrestricted")
            with col_as3: att_month = st.selectbox("Select Attendance Month:", AVAILABLE_MONTHS, key="att_month_global")
            
            if att_section:
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

        elif att_flow_mode == "👤 By Single Student Roll Number":
            st.subheader("👤 Single Student Attendance Record Manager")
            single_att_id = st.text_input("🔍 Enter Student Roll Number / ID:", key="single_att_id_input")
            
            if single_att_id and single_att_id.isdigit():
                student_info = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(single_att_id)})
                if student_info.empty:
                    st.error("❌ This roll number does not exist.")
                else:
                    s_name = student_info['name'].iloc[0].upper()
                    s_section = student_info['section'].iloc[0].upper().strip()
                    st.info(f"👤 Found Student: {s_name} | Current Section: {s_section}")
                    
                    c_at1, c_at2, c_at3 = st.columns(3)
                    with c_at1: single_att_month = st.selectbox("Select Target Month:", AVAILABLE_MONTHS, key="s_att_m")
                    with c_at2: single_att_total = st.number_input("Total Tracked Days:", min_value=1, max_value=31, value=24, key="s_att_tot")
                    
                    existing_att = run_query("SELECT present_days FROM attendance WHERE student_id = :id AND UPPER(TRIM(month_name)) = UPPER(TRIM(:month))", {"id": int(single_att_id), "month": single_att_month})
                    init_present_val = int(existing_att['present_days'].iloc[0]) if not existing_att.empty else int(single_att_total)
                    
                    with c_at3: single_att_present = st.number_input("Days Attended:", min_value=0, max_value=int(single_att_total), value=min(int(init_present_val), int(single_att_total)), key="s_att_pres")
                    
                    if st.button("💾 Save Individual Attendance Record", type="primary", key="save_single_att_btn"):
                        execute_db_command("""
                            INSERT INTO attendance (student_id, month_name, total_days, present_days)
                            VALUES (:s_id, :month, :td, :pd)
                            ON CONFLICT (student_id, month_name) DO UPDATE SET total_days = EXCLUDED.total_days, present_days = EXCLUDED.present_days
                        """, {"s_id": int(single_att_id), "month": single_att_month.strip(), "td": single_att_total, "pd": single_att_present})
                        st.success(f"🎉 Attendance updated successfully for {s_name}!")
                        st.rerun()

        elif att_flow_mode == "📤 Bulk Excel/CSV Import":
            st.subheader("📤 Bulk Attendance CSV Document Importer")
            st.info("📊 Spreadsheet layout must use these lowercase headers: **student_id** and **present_days**")
            
            c_ax1, c_ax2 = st.columns(2)
            with c_ax1: xl_month = st.selectbox("Target Log Target Month:", AVAILABLE_MONTHS, key="xl_a_month")
            with c_ax2: xl_total_days = st.number_input("Total Monthly Accountable Days:", min_value=1, max_value=31, value=24, key="xl_a_td")
            
            uploaded_att_file = st.file_uploader("Choose CSV Sheet file to import:", type=['csv'], key="att_uploader_widget")
            if uploaded_att_file is not None:
                try:
                    df = pd.read_csv(uploaded_att_file)
                    df.columns = [str(c).lower().strip() for c in df.columns]
                    
                    if 'student_id' in df.columns and 'present_days' in df.columns:
                        st.dataframe(df, use_container_width=True)
                        if st.button("🚀 Process and Save Bulk Attendance", type="primary", key="save_bulk_att_imported_btn"):
                            success_count = 0
                            for _, row in df.iterrows():
                                s_id = str(row['student_id']).split('.')[0].strip()
                                p_days = str(row['present_days']).split('.')[0].strip()
                                if s_id.isdigit() and p_days.isdigit():
                                    execute_db_command("""
                                        INSERT INTO attendance (student_id, month_name, total_days, present_days)
                                        VALUES (:s_id, :month, :td, :pd)
                                        ON CONFLICT (student_id, month_name) DO UPDATE SET total_days = EXCLUDED.total_days, present_days = EXCLUDED.present_days
                                    """, {"s_id": int(s_id), "month": xl_month.strip(), "td": xl_total_days, "pd": int(p_days)})
                                    success_count += 1
                            st.success(f"🎉 Successfully imported attendance logs for {success_count} students!")
                            st.rerun()
                    else:
                        st.error("❌ Heading processing mistake! Confirm column tags match 'student_id' and 'present_days' names exactly.")
                except Exception as e:
                    st.error(f"Error handling system processing upload: {e}")

# ----------------- 📋 SECTION SUMMARY REPORT -----------------
elif menu_choice == "📋 Section Summary Report":
    st.title("📋 Section Performance Analytics Report")
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
                    tot = float(sub_match["total_marks"].iloc[0]) if pd.notna(sub_match["total_marks"].iloc[0]) else 0.0
                    
                    if val == "NC":
                        entry[f"{sub} (Obt)"] = "NC"
                    elif val == "A":
                        entry[f"{sub} (Obt)"] = "A"
                        max_total += tot
                        has_scores = True
                    elif val.replace('.', '', 1).isdigit():
                        entry[f"{sub} (Obt)"] = val
                        obtained_total += float(val)
                        max_total += tot
                        has_scores = True
                    else:
                        entry[f"{sub} (Obt)"] = val
                else:
                    entry[f"{sub} (Obt)"] = "-"

            if has_scores:
                entry["Total (Obt)"] = f"{int(obtained_total)} / {int(max_total)}"
            else:
                entry["Total (Obt)"] = "NC"
                
            summary_rows.append(entry)
            
        final_report_df = pd.DataFrame(summary_rows)
        st.dataframe(final_report_df.set_index("ID"), use_container_width=True)
    else:
        st.info("No active profiles loaded under this section yet.")

# ----------------- 📈 MULTI-TEST PROGRESS REPORT (PRINT ENGINE) -----------------
elif menu_choice == "📈 Multi-Test Progress Report":
    st.title("📈 Multi-Test Progress Analytics")
    st.markdown("Select your reporting scope below to generate high-fidelity, print-ready student progress cards.")

    # CSS Injection for Clean Media Controls
    st.markdown("""
        <style>
        @media print {
            .no-print { display: none !important; }
            .print-card { 
                page-break-after: always; 
                border: 2px solid #333 !important;
                padding: 25px !important;
                margin-bottom: 0px !important;
            }
        }
        .print-card {
            background-color: white;
            color: black;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 25px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .print-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 3px solid #1e3d59;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .print-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .print-table th {
            background-color: #1e3d59;
            color: white;
            text-align: left;
            padding: 8px;
            font-size: 14px;
        }
        .print-table td {
            border-bottom: 1px solid #ddd;
            padding: 8px;
            font-size: 13px;
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

    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    scope_choice = st.radio(
        "𖨾 Select Scope:",
        options=["👤 Single Student Card", "👥 Complete Section Cards"],
        index=0, horizontal=True, key="mt_reporting_scope"
    )

    students_to_process = []
    selected_exams_list = []
    rendered_discipline = "N/A"
    rendered_section = "N/A"

    if scope_choice == "👤 Single Student Card":
        with st.form("single_student_secure_form"):
            st.markdown("##### 👤 Single Profile Verification Panel")
            col_s1, col_s2 = st.columns([2, 3])
            with col_s1: search_id = st.text_input("🔍 Enter Student Roll Number / ID:", value="", key="form_search_id_single")
            with col_s2: selected_exams_list = st.multiselect("🎯 Select Tests:", options=AVAILABLE_EXAMS, default=["MT_1", "MT_2", "MT_3"], key="form_exams_single")
            submit_single = st.form_submit_button("🚀 Fetch & Compile Student Details", use_container_width=True)
            
        if submit_single and search_id.strip():
            clean_id = search_id.strip()
            student_profile = run_query("SELECT id, name, section, class FROM students WHERE id = :id", {"id": int(clean_id) if clean_id.isdigit() else 0})
            if not student_profile.empty:
                students_to_process = student_profile.to_dict(orient="records")
                rendered_section = student_profile['section'].iloc[0].upper().strip()
                for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                    if rendered_section in [x.upper().strip() for x in secs]:
                        rendered_discipline = disp
                        break
            else:
                st.error("❌ Roll number verification lookup failed inside registry storage.")

    elif scope_choice == "👥 Complete Section Cards":
        with st.form("section_bulk_secure_form"):
            st.markdown("##### 👥 Class Section Batch Compilation Panel")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1: sel_disc = st.selectbox("Choose Target Discipline:", AVAILABLE_DISCIPLINE, key="bulk_disc")
            with col_b2: sel_sec = st.selectbox("Choose Target Section:", DISCIPLINE_SECTIONS_MAP[sel_disc], key="bulk_sec")
            with col_b3: selected_exams_list = st.multiselect("Choose Scope Matrix Target Terms:", AVAILABLE_EXAMS, default=["MT_1", "MT_2", "MT_3"], key="bulk_exams")
            submit_bulk = st.form_submit_button("🚀 Compile Batch Section Roster", use_container_width=True)
            
        if submit_bulk:
            rendered_discipline = sel_disc
            rendered_section = sel_sec
            section_roster = run_query("SELECT id, name, section, class FROM students WHERE UPPER(TRIM(section)) = UPPER(TRIM(:sec)) ORDER BY id ASC", {"sec": sel_sec})
            if not section_roster.empty:
                students_to_process = section_roster.to_dict(orient="records")
            else:
                st.warning("No active student profiles loaded inside chosen target parameters.")

    st.markdown('</div>', unsafe_allow_html=True)

    if students_to_process and selected_exams_list:
        st.markdown('<div class="no-print" style="margin-bottom:20px;">', unsafe_allow_html=True)
        if st.button("🖨️ Direct Print Result Cards", type="primary", key="trigger_system_print_call_btn"):
            st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        subjects = DISCIPLINE_SUBJECTS_MAP.get(rendered_discipline, ["CHEMISTRY", "BIOLOGY", "PHYSICS", "URDU", "ENGLISH", "ISL_ETH", "T_QURAN"])
        
        all_ids = [int(s['id']) for s in students_to_process]
        marks_raw = run_query("""
            SELECT student_id, UPPER(TRIM(subject)) as subject, exam_type, marks_obtained, total_marks 
            FROM marks WHERE student_id IN :ids AND exam_type IN :exams
        """, {"ids": tuple(all_ids), "exams": tuple(selected_exams_list)})
        
        attendance_raw = run_query("""
            SELECT student_id, month_name, total_days, present_days 
            FROM attendance WHERE student_id IN :ids
        """, {"ids": tuple(all_ids)})

        html_buffer = ""
        for student in students_to_process:
            s_id = student['id']
            s_name = str(student['name']).upper()
            header_img_html = f'<img src="{logo_base64}" style="max-height: 75px;">' if logo_base64 else '<div style="font-size:22px; font-weight:bold; color:#1e3d59;">CONCORDIA COLLEGE</div>'
            
            html_buffer += f"""
            <div class="print-card">
                <div class="print-header">
                    <div style="text-align: left;">
                        <h2 style="margin: 0; color: #1e3d59; font-size:24px;">CONCORDIA COLLEGE KASUR</h2>
                        <p style="margin: 4px 0 0 0; color: #555; font-size:14px;">Academic Performance Tracking Report Card</p>
                    </div>
                    <div>{header_img_html}</div>
                </div>
                
                <table style="width:100%; margin-bottom:15px; font-size:14px; background:#f9f9f9; padding:10px; border-radius:4px;">
                    <tr>
                        <td style="border:none; padding:4px;"><b>Student Name:</b> {s_name}</td>
                        <td style="border:none; padding:4px;"><b>Roll Number / ID:</b> {s_id}</td>
                    </tr>
                    <tr>
                        <td style="border:none; padding:4px;"><b>Class Scope:</b> {student['class']} ({rendered_discipline})</td>
                        <td style="border:none; padding:4px;"><b>Section Assignment:</b> {rendered_section}</td>
                    </tr>
                </table>
                
                <table class="print-table">
                    <thead>
                        <tr>
                            <th>Subject Program Focus Track</th>
            """
            for exam in selected_exams_list:
                html_buffer += f"<th>{exam}</th>"
            html_buffer += "</tr></thead><tbody>"

            for sub in subjects:
                html_buffer += f"<tr><td><b>{sub}</b></td>"
                for exam in selected_exams_list:
                    match = marks_raw[(marks_raw['student_id'] == s_id) & (marks_raw['subject'] == sub.upper().strip()) & (marks_raw['exam_type'] == exam)]
                    if not match.empty:
                        val = str(match['marks_obtained'].iloc[0]).strip().upper()
                        tot = str(int(float(match['total_marks'].iloc[0]))) if pd.notna(match['total_marks'].iloc[0]) else "100"
                        score_display = f"{val} / {tot}" if (val != "A" and val != "NC") else val
                        html_buffer += f"<td>{score_display}</td>"
                    else:
                        html_buffer += "<td>-</td>"
                html_buffer += "</tr>"

            html_buffer += "</tbody></table>"
            
            s_att = attendance_raw[attendance_raw['student_id'] == s_id]
            att_str = ", ".join([f"{r['month_name']}: {r['present_days']}/{r['total_days']}" for _, r in s_att.iterrows()]) if not s_att.empty else "No logs recorded"
            
            html_buffer += f"""
                <div style="margin-top:20px; font-size:12px; color:#666; display:flex; justify-content:space-between; border-top:1px solid #eee; padding-top:10px;">
                    <div><b>Attendance Registry History Tracker:</b> {att_str}</div>
                    <div>Report Generated Authenticated Secure Online Stack</div>
                </div>
            </div>
            """
        st.markdown(html_buffer, unsafe_allow_html=True)

# ----------------- 🪪 STUDENT RESULT CARDS -----------------
elif menu_choice == "🪪 Student Result Cards":
    st.title("🪪 Individual Grade Report Cards")
    
    col_rc1, col_rc2 = st.columns(2)
    with col_rc1: target_id_card = st.text_input("🔍 Search Student Roll Number:", key="rc_roll_search")
    with col_rc2: target_exam_card = st.selectbox("Select Report Target Exam:", AVAILABLE_EXAMS, key="rc_exam_select")
    
    if target_id_card and target_id_card.isdigit():
        student_info = run_query("SELECT id, name, section, class FROM students WHERE id = :id", {"id": int(target_id_card)})
        if student_info.empty:
            st.error("Roll number verification lookup failed inside registry storage.")
        else:
            s_name = student_info['name'].iloc[0].upper()
            s_sec = student_info['section'].iloc[0].upper().strip()
            s_class = student_info['class'].iloc[0]
            
            st.markdown(f"### 🪪 Performance Overview: {s_name} ({target_id_card})")
            st.write(f"**Class:** {s_class} | **Section Assigned:** {s_sec}")
            
            matched_disp = "MEDICAL"
            for disp, secs in DISCIPLINE_SECTIONS_MAP.items():
                if s_sec in [x.upper().strip() for x in secs]:
                    matched_disp = disp
                    break
            
            subjects = DISCIPLINE_SUBJECTS_MAP[matched_disp]
            marks_df = run_query("""
                SELECT UPPER(TRIM(subject)) as subject, marks_obtained, total_marks 
                FROM marks WHERE student_id = :id AND TRIM(exam_type) = TRIM(:exam)
            """, {"id": int(target_id_card), "exam": target_exam_card})
            
            display_rows = []
            grand_obt, grand_tot, counted = 0.0, 0.0, False
            
            for sub in subjects:
                sub_match = marks_df[marks_df["subject"] == sub.upper().strip()]
                if not sub_match.empty:
                    val = str(sub_match["marks_obtained"].iloc[0]).strip().upper()
                    tot_val = float(sub_match["total_marks"].iloc[0]) if pd.notna(sub_match["total_marks"].iloc[0]) else 0.0
                    
                    if val == "NC":
                        display_rows.append({"Subject": sub, "Marks Obtained": "NC", "Total Marks": "NC"})
                    elif val == "A":
                        display_rows.append({"Subject": sub, "Marks Obtained": "A", "Total Marks": int(tot_val)})
                        grand_tot += tot_val
                        counted = True
                    elif val.replace('.', '', 1).isdigit():
                        display_rows.append({"Subject": sub, "Marks Obtained": val, "Total Marks": int(tot_val)})
                        grand_obt += float(val)
                        grand_tot += tot_val
                        counted = True
                    else:
                        display_rows.append({"Subject": sub, "Marks Obtained": val, "Total Marks": int(tot_val)})
                else:
                    display_rows.append({"Subject": sub, "Marks Obtained": "-", "Total Marks": "-"})
            
            st.table(pd.DataFrame(display_rows))
            if counted:
                st.metric("Cumulative Term Score", f"{int(grand_obt)} / {int(grand_tot)}")
            else:
                st.metric("Cumulative Term Score", "NC")

# ----------------- 👨‍🏫 TEACHER MANAGEMENT -----------------
elif menu_choice == "👨‍🏫 Teacher Management":
    st.title("👨‍🏫 System Account & Allocation Setup Workspace")
    
    if st.session_state.get('user_role', 'teacher') != 'admin':
        st.warning("🔒 Administrative clearance credentials required to access system allocation options.")
    else:
        st.subheader("👥 Current User Registry Overview")
        users_df = run_query("SELECT id, username, role, assigned_subject FROM app_users ORDER BY id ASC")
        st.dataframe(users_df, use_container_width=True)
        
        with st.form("create_new_user_profile_form"):
            st.markdown("##### ➕ Provision New User Credentials")
            u_name = st.text_input("Account Username Key:")
            u_pass = st.text_input("Account Password String:", type="password")
            u_role = st.selectbox("Role Permission Group Allocation:", ["teacher", "admin"])
            u_sub = st.text_input("Default Assigned Subject Focus Block (e.g., CHEMISTRY, PHYSICS):")
            
            if st.form_submit_button("Add User Profile"):
                if u_name and u_pass:
                    try:
                        execute_db_command(
                            "INSERT INTO app_users (username, password, role, assigned_subject) VALUES (:u, :p, :r, :s)",
                            {"u": u_name.strip(), "p": u_pass.strip(), "r": u_role, "s": u_sub.strip().upper() if u_sub.strip() else None}
                        )
                        st.success("New active account provisioned inside database registry records.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to create user account (Username may already exist): {ex}")
