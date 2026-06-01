import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import base64
import os

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
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.markdown("<h3 style='text-align: center; margin-top: -5px;'>Menu Navigation</h3>", unsafe_allow_html=True)
menu_choice = st.sidebar.radio(
    "Go To Module:", 
    ["📊 Home Dashboard", "➕ Add Students", "📝 Enter Marks & Attendance", "📋 Section Summary Report", "📈 Multi-Test Progress Report", "🪪 Student Result Cards", "👨‍🏫 Teacher Management"],
    key="primary_sidebar_navigation"
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

# ---------------------------------------------------------
# 📝 ENTER MARKS & ATTENDANCE MODULE
# ---------------------------------------------------------
elif menu_choice == "📝 Enter Marks & Attendance":
    st.title("📝 Data Intake Management Dashboard")
    sub_tab_selection = st.radio("🎯 Select Workspace Sub-Module Target:", ["📝 Academic Exam Marks Entry", "📅 Monthly Attendance Entry"], horizontal=True, key="intake_sub_navigation")
    st.markdown("---")

    current_user_id = st.session_state.get('user_id', None)
    current_role = st.session_state.get('role', st.session_state.get('user_role', 'teacher'))

    # 1. ACADEMIC EXAM MARKS ENTRY SUB-MODULE
    if sub_tab_selection == "📝 Academic Exam Marks Entry":
        entry_mode = st.radio("🎯 Select Entry Workflow Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number", "📤 Bulk Excel/CSV Import"], horizontal=True, key="marks_workflow_mode")
        st.markdown("---")

        if entry_mode == "📋 By Complete Section":
            c1, c2, c3 = st.columns(3)
            if current_role == 'teacher' and current_user_id is not None:
                teacher_rights = run_query("SELECT subject, section FROM allocations WHERE user_id = :uid", {"uid": int(current_user_id)})
                if not teacher_rights.empty:
                    allowed_subs = sorted(list(teacher_rights['subject'].unique()))
                    allowed_secs = sorted(list(teacher_rights['section'].unique()))
                    with c1: st.info("🔒 Bound to Assigned Allocation Profile")
                    with c2: sel_subject = st.selectbox("Select Subject:", allowed_subs, key="m_teacher_sub")
                    with c3: sel_section = st.selectbox("Select Section:", allowed_secs, key="m_teacher_sec")
                else:
                    st.warning("🚨 You do not have any active subjects or sections assigned yet.")
                    sel_subject, sel_section = None, None
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
                                updated_scores[row['ID']] = col_s2.text_input("Score", value=str(row['Marks']), key=f"sec_input_{row['ID']}", label_visibility="collapsed")
                            
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
                    with c_sub: single_subj = st.selectbox("Choose Subject:", DISCIPLINE_SUBJECTS_MAP[matched_disp], key="single_sub")
                    with c_ex: single_exam = st.selectbox("Choose Test Term Type:", AVAILABLE_EXAMS, key="single_exam")
                    with c_m: single_total = st.number_input("Total Marks Assigned:", value=100, key="single_max")
                    
                    existing_record = run_query("SELECT marks_obtained FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(target_id), "sub": single_subj, "exam": single_exam})
                    current_val = str(existing_record['marks_obtained'].iloc[0]) if not existing_record.empty else ""
                    single_score = st.text_input("✏️ Enter Marks Obtained:", value=current_val, key="single_score_field")
                    
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
            
            with c_xl1: xl_subject = st.selectbox("Target Entry Subject:", all_subjects_flat, key="xl_m_sub")
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

    # 2. MONTHLY ATTENDANCE ENTRY SUB-MODULE
    elif sub_tab_selection == "📅 Monthly Attendance Entry":
        st.subheader("📅 Monthly Attendance Workspace")
        att_flow_mode = st.radio("Select Entry Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number", "📤 Bulk Excel/CSV Import"], horizontal=True, key="attendance_workflow_mode")
        st.markdown("---")
        
        if att_flow_mode == "📋 By Complete Section":
            col_as1, col_as2, col_as3 = st.columns(3)
            if current_role == 'teacher' and current_user_id is not None:
                teacher_rights = run_query("SELECT section FROM allocations WHERE user_id = :uid", {"uid": int(current_user_id)})
                allowed_secs = sorted(list(teacher_rights['section'].unique())) if not teacher_rights.empty else []
                with col_as1: st.info("🔒 Logged Teacher Roster View")
                with col_as2: att_section = st.selectbox("Select Target Section:", allowed_secs, key="att_sec_teacher")
                with col_as3: att_month = st.selectbox("Select Attendance Month:", AVAILABLE_MONTHS, key="att_month_teacher")
            else:
                with col_as1: att_discipline = st.selectbox("Select Discipline Context:", AVAILABLE_DISCIPLINE, key="att_disc_admin")
                with col_as2: att_section = st.selectbox("Select Target Section:", DISCIPLINE_SECTIONS_MAP[att_discipline], key="att_sec_admin")
                with col_as3: att_month = st.selectbox("Select Attendance Month:", AVAILABLE_MONTHS, key="att_month_admin")
            
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

# ----------------- 📈 MULTI-TEST PROGRESS REPORT -----------------
elif menu_choice == "📈 Multi-Test Progress Report":
    st.title("📈 Multi-Test Progress Analytics")
    st.markdown("Select your reporting scope below to generate high-fidelity, print-ready student progress cards.")

    st.markdown("""
        <style>
        @media print {
            .no-print { display: none !important; }
        }
        </style>
    """, unsafe_allow_html=True)

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

    all_frameworks = [
        "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "SEND_UP", "MT_5",
        "T_1", "T_2", "T_3", "T_4", "T_5", "T_6", "T_7", "T_8", "T_9", "T_10",
        "HALF_BOOK01", "HALF_BOOK02", "PRE_BOARD"
    ]

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
                    students_to_process = [query_id]
                    st.info(f"Loaded student ID: {query_id}")
                except Exception as e:
                    st.error(f"Error compiling single user: {e}")
