# ==============================================================================
# 1. ABSOLUTE TOP OF APP.PY: GLOBAL INITIALIZATIONS (Fixes Line 532 NameError)
# ==============================================================================
import streamlit as st
import pandas as pd
import sqlite3
import os
import base64

logo_filename = "logo.png"
logo_base64 = ""

# Pre-load and encode logo globally so any module can read it instantly
if os.path.exists(logo_filename):
    try:
        with open(logo_filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            ext = os.path.splitext(logo_filename)[1].replace(".", "").lower()
            if ext == "jpg": ext = "jpeg"
            logo_base64 = f"data:image/{ext};base64,{encoded_string}"
    except Exception:
        pass

# ==============================================================================
# 2. YOUR REST OF THE CODE CONTINUES BELOW HERE...
# ==============================================================================
import os
import base64

# --- GLOBAL SETTINGS (Prevents NameErrors anywhere in the app) ---
logo_filename = "logo.png" 
logo_base64 = ""

if os.path.exists(logo_filename):
    try:
        with open(logo_filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            ext = os.path.splitext(logo_filename)[1].replace(".", "").lower()
            if ext == "jpg": ext = "jpeg"
            logo_base64 = f"data:image/{ext};base64,{encoded_string}"
    except Exception:
        pass
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
    # Display the official logo centered or cleanly sized on the login page
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

def run_update(query, params=None):
    if params is None:
        params = {}
    # This uses your existing 'engine' and automatically handles COMMITs!
    with engine.begin() as conn:
        conn.execute(text(query), params)

def execute_db_command(command, params=None):
    if params is None:
        params = {}
    with engine.begin() as conn:
        conn.execute(text(command), params)

# --- NAVIGATION SIDEBAR ---
st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.markdown("<h3 style='text-align: center; margin-top: -5px;'>Menu Navigation</h3>", unsafe_allow_html=True)
menu_choice = st.sidebar.radio(
    "Go To Module:", 
    ["📊 Home Dashboard", "⚙️ Master Module", "📝 Enter Marks & Attendance", "📋 Section Summary Report", "📈 Multi-Test Progress Report", "🪪 Student Result Cards", "Student Management", "👨‍🏫 Teacher Management", "🎓 Promote Students"]
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

# ---------------------------------------------------------
# ⚙️ MASTER MODULE (STICKY DROPDOWN CATEGORY VERSION)
# ---------------------------------------------------------
elif menu_choice == "⚙️ Master Module":
    st.title("⚙️ Global Academic Configuration Master Module")
    st.info("Configure your system settings here. This data dynamically populates dropdowns across all reporting sheets.")

    # Initialize a session state variable for the dropdown category if it doesn't exist
    if "current_category" not in st.session_state:
        st.session_state.current_category = "DISCIPLINE"

    # Automatically ensure the master registry table structure is initialized in PostgreSQL
    execute_db_command("""
        CREATE TABLE IF NOT EXISTS master_registry (
            id SERIAL PRIMARY KEY,
            item_type VARCHAR(50) NOT NULL,
            item_key VARCHAR(100) NOT NULL,
            item_value VARCHAR(255) NOT NULL,
            parent_key VARCHAR(100),
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE(item_type, item_key)
        );
    """)

    # Setup specialized workspaces via Tabs
    tab_add, tab_view = st.tabs(["➕ Add New Configuration Entry", "📋 View & Manage Active Registry"])

    with tab_add:
        st.subheader("Define Global System Dropdown Data")
        
        # We handle state by calculating the default index for the selectbox dynamically
        categories = ["DISCIPLINE", "CLASS", "SECTION", "SUBJECT", "TEST_TYPE", "SESSION", "CAMPUS"]
        try:
            default_index = categories.index(st.session_state.current_category)
        except ValueError:
            default_index = 0

        with st.form("master_registry_input_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                item_type = st.selectbox(
                    "Dropdown Type Category:", 
                    options=categories,
                    index=default_index
                )
                item_value = st.text_input("Display Name Value (e.g., Medical, 11th Class, MG_BLUE):").strip()
                
            with col2:
                # Dynamic context assignment: dynamically pulls items to serve as parents if required
                parent_query = "SELECT item_key, item_value FROM master_registry WHERE is_active = TRUE ORDER BY item_value ASC"
                try:
                    p_df = run_query(parent_query)
                    p_options = {"No Parent Relationship Link": ""}
                    if not p_df.empty:
                        for _, r in p_df.iterrows():
                            p_options[f"[{r['item_key']}] {r['item_value']}"] = r['item_key']
                except Exception:
                    p_options = {"No Parent Relationship Link": ""}
                    
                parent_selection = st.selectbox("Assign Parent Connection Link (Optional):", options=list(p_options.keys()))
                final_parent_key = p_options[parent_selection]

            if st.form_submit_button("🚀 Deploy Component Entry into Database", type="primary"):
                if not item_value:
                    st.error("The Display Name Value entry is strictly required!")
                else:
                    # Save the user's selected category to session state BEFORE reloading
                    st.session_state.current_category = item_type
                    
                    # Automatically generate a clean, safe database Key from the Display Name
                    generated_key = item_value.upper().replace(" ", "_").replace("-", "_").replace(".", "")
                    
                    insert_cmd = """
                        INSERT INTO master_registry (item_type, item_key, item_value, parent_key, is_active)
                        VALUES (:type, :key, :value, :parent, TRUE)
                        ON CONFLICT (item_type, item_key) 
                        DO UPDATE SET item_value = EXCLUDED.item_value, parent_key = EXCLUDED.parent_key, is_active = TRUE;
                    """
                    try:
                        run_update(insert_cmd, {
                            "type": item_type,
                            "key": generated_key,
                            "value": item_value,
                            "parent": final_parent_key if final_parent_key != "" else None
                        })
                        st.success(f"🎉 Core Registry successfully updated: '{item_value}' added under '{item_type}'!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to submit to database: {e}")

    with tab_view:
        st.subheader("Current Active Framework Architecture Registry")
        filter_scope = st.radio(
            "Filter Registry View Schema Scope:", 
            ["ALL VIEW"] + categories, 
            horizontal=True
        )
        
        view_query = "SELECT id, item_type, item_key, item_value, parent_key, is_active FROM master_registry"
        params = {}
        if filter_scope != "ALL VIEW":
            view_query += " WHERE item_type = :type"
            params["type"] = filter_scope
        view_query += " ORDER BY item_type, item_value ASC"
        
        try:
            df_grid = run_query(view_query, params)
            if not df_grid.empty:
                st.dataframe(df_grid, use_container_width=True)
                
                # Quick-delete action for data administration maintenance
                st.markdown("---")
                delete_target = st.text_input("🎯 Enter Unique Code Key to Remove from System Matrix (See table above):")
                if st.button("🗑️ Deactivate Target Reference Entry", type="secondary"):
                    if delete_target:
                        execute_db_command("UPDATE master_registry SET is_active = FALSE WHERE item_key = :key", {"key": delete_target.upper().strip()})
                        st.success("Target element marked inactive.")
                        st.rerun()
            else:
                st.info("No active registry tracks discovered matching selection variables framework options.")
        except Exception as e:
            st.error(f"Error drawing database system tables records summaries grids: {e}")
# ---------------------------------------------------------
# 📝 ENTER MARKS & ATTENDANCE MODULE (COMPLETE UPGRADED ENGINE)
# ---------------------------------------------------------
elif menu_choice == "📝 Enter Marks & Attendance":
    st.title("📝 Data Intake Management Dashboard")
    sub_tab_selection = st.radio("🎯 Select Workspace Sub-Module Target:", ["📝 Academic Exam Marks Entry", "📅 Monthly Attendance Entry"], horizontal=True)
    st.markdown("---")

    # Get active session identity data safely
    current_user_id = st.session_state.get('user_id', None)
    current_role = st.session_state.get('role', st.session_state.get('user_role', 'teacher'))

    # =========================================================
    # 1. ACADEMIC EXAM MARKS ENTRY SUB-MODULE
    # =========================================================
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
                    with c2: sel_subject = st.selectbox("Select Subject:", allowed_subs)
                    with c3: sel_section = st.selectbox("Select Section:", allowed_secs)
                else:
                    st.warning("🚨 You do not have any active subjects or sections assigned yet.")
                    sel_subject, sel_section = None, None
            else:
                with c1: sel_discipline = st.selectbox("Select Discipline:", AVAILABLE_DISCIPLINE)
                with c2: sel_subject = st.selectbox("Select Subject:", DISCIPLINE_SUBJECTS_MAP[sel_discipline])
                with c3: sel_section = st.selectbox("Select Section:", DISCIPLINE_SECTIONS_MAP[sel_discipline])
            
            if sel_subject and sel_section:
                row2_1, row2_2 = st.columns(2)
                with row2_1: sel_exam = st.selectbox("Test Type:", AVAILABLE_EXAMS)
                with row2_2: total_marks = st.number_input("Total Marks Assigned:", value=100)
                
                try:
                    roster_df = run_query("""
    SELECT s.id AS "ID", s.name AS "Student Name", m.marks_obtained AS "Marks"
    FROM students s
    LEFT JOIN marks m ON s.id = m.student_id AND UPPER(TRIM(m.subject)) = UPPER(TRIM(:subject)) AND TRIM(m.exam_type) = TRIM(:exam)
    WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section))
      AND (s.status IS NULL OR UPPER(TRIM(s.status)) != 'LEFT')
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
            target_id = st.text_input("🔍 Enter Student Roll Number / ID:", key="single_marks_id")
            if target_id and target_id.isdigit():
                student_info = run_query("""
    SELECT name, section, class, status 
    FROM students 
    WHERE id = :id 
      AND (status IS NULL OR UPPER(TRIM(status)) != 'LEFT')
""", {"id": int(target_id)})
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
                    current_val = str(existing_record['marks_obtained'].iloc[0]) if not existing_record.empty else """
                    single_score = st.text_input("✏️ Enter Marks Obtained:", value=current_val)
                    
                    if st.button("💾 Save Student Record", type="primary"):
                        execute_db_command("DELETE FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(target_id), "sub": single_subj, "exam": single_exam})
                        if single_score.strip() != "":
                            execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:id, :sub, :exam, :score, :total)", {"id": int(target_id), "sub": single_subj.strip().upper(), "exam": single_exam.strip(), "score": single_score.strip(), "total": single_total})
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
                        if st.button("🚀 Process and Save Bulk Marks", type="primary"):
                            success_count = 0
                            for _, row in df.iterrows():
                                s_id = str(row['student_id']).split('.')[0].strip()
                                score = str(row['marks_obtained']).strip()
                                if s_id.isdigit():
                                    execute_db_command("DELETE FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND TRIM(exam_type) = TRIM(:exam)", {"id": int(s_id), "sub": xl_subject, "exam": xl_exam})
                                    if score != "" and score.lower() != 'nan':
                                        execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:id, :sub, :exam, :score, :total)", {"id": int(s_id), "sub": xl_subject.strip().upper(), "exam": xl_exam.strip(), "score": score, "total": xl_total})
                                        success_count += 1
                            st.success(f"🎉 Successfully updated {success_count} student grade rows!")
                            st.rerun()
                    else:
                        st.error("❌ Heading processing mistake! Confirm column tags match 'student_id' and 'marks_obtained' names exactly.")
                except Exception as e:
                    st.error(f"Error handling system processing upload: {e}")

    # =========================================================
    # 2. MONTHLY ATTENDANCE ENTRY SUB-MODULE
    # =========================================================
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
                with col_as2: att_section = st.selectbox("Select Target Section:", allowed_secs, key="att_sec")
                with col_as3: att_month = st.selectbox("Select Attendance Month:", AVAILABLE_MONTHS, key="att_month")
            else:
                with col_as1: att_discipline = st.selectbox("Select Discipline Context:", AVAILABLE_DISCIPLINE, key="att_disc")
                with col_as2: att_section = st.selectbox("Select Target Section:", DISCIPLINE_SECTIONS_MAP[att_discipline], key="att_sec")
                with col_as3: att_month = st.selectbox("Select Attendance Month:", AVAILABLE_MONTHS, key="att_month")
            
            if att_section:
                default_days = st.number_input("Set Total Working Days:", min_value=1, max_value=31, value=24, key="sec_global_days")
               # Single-line string concatenation to guarantee no quote mismatches
        query_text = (
            "SELECT s.id AS \"ID\", s.name AS \"Student Name\", a.present_days \n"
            "FROM students s \n"
            "LEFT JOIN attendance a ON s.id = a.student_id AND UPPER(TRIM(a.month_name)) = UPPER(TRIM(:month)) \n"
            "WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section)) \n"
            "ORDER BY s.id ASC"
        )
        
        students_att_list = run_query(query_text, {"month": att_month, "section": att_section})
        """
        
        students_att_list = run_query(query_text, {"month": att_month, "section": att_section})
                
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
                    
                    if st.button("💾 Save Individual Attendance Record", type="primary"):
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
                        if st.button("🚀 Process and Save Bulk Attendance", type="primary"):
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
# ----------------- 📋 SECTION SUMMARY REPORT (OPTIMIZED) -----------------
elif menu_choice == "📋 Section Summary Report":
    st.title("📋 Section Performance Analytics Report")
    col_a, col_b, col_c = st.columns(3)
    with col_a: sel_disc = st.selectbox("Select Discipline:", AVAILABLE_DISCIPLINE, key="summary_disc")
    with col_b: sel_sec = st.selectbox("Select Section:", DISCIPLINE_SECTIONS_MAP[sel_disc], key="summary_sec")
    with col_c: sel_exam = st.selectbox("Select Exam Cycle:", AVAILABLE_EXAMS, key="summary_exam")
    
    # Simple dictionary mapping for short-form subject names
    SHORT_SUBJECTS_MAP = {
        "MATHEMATICS": "MATH",
        "COMPUTER SCIENCE": "COMP",
        "COMPUTER": "COMP",
        "PHYSICS": "PHY",
        "CHEMISTRY": "CHEM",
        "BIOLOGY": "BIO",
        "ENGLISH": "ENG",
        "URDU": "URDU",
        "ISLAMIAT": "ISL",
        "PAKISTAN STUDIES": "PAK.ST"
    }
    
    # 1. Fetch Students
    students_df = run_query("""
        SELECT id AS "ID", name AS "Student Name", section AS "Section", class AS "Class" 
        FROM students 
        WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) 
        ORDER BY id ASC
    """, {"section": sel_sec})
    
    if not students_df.empty:
        subjects = DISCIPLINE_SUBJECTS_MAP[sel_disc]
        
     # 2. Fetch Marks Entries (Synchronized to exclude LEFT statuses)
        marks_df = run_query("""
            SELECT m.student_id, UPPER(TRIM(m.subject)) as subject, m.marks_obtained, m.total_marks
            FROM marks m 
            JOIN students s ON m.student_id = s.id
            WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section)) 
              AND TRIM(m.exam_type) = TRIM(:exam)
              AND (s.status IS NULL OR UPPER(TRIM(s.status)) != 'LEFT')
        """, {"section": sel_sec, "exam": sel_exam})
        
        if marks_df.empty:
            st.warning(f"⚠️ No marks data found in the database for Section **{sel_sec}** under Exam Cycle **{sel_exam}**. Please make sure marks have been saved in the 'Enter Marks & Attendance' module.")
            
        summary_rows = []
        for _, s_row in students_df.iterrows():
            s_id = s_row["ID"]
            
            # Fetch status safely from row data (defaulting to 'Active')
            s_status = s_row["Status"] if "Status" in s_row and pd.notna(s_row["Status"]) else "Active"
            
            entry = {
                "ID": s_id, 
                "Student Name": s_row["Student Name"], 
                "Section": s_row["Section"], 
                "Class": s_row["Class"],
                "Status": s_status
            }
            
            obtained_total = 0.0
            max_total = 0.0
            has_valid_scores = False  
            has_explicit_nc = False
            
            for sub in subjects:
                sub_upper = sub.upper().strip()
                short_sub = SHORT_SUBJECTS_MAP.get(sub_upper, sub)
                
                sub_match = marks_df[(marks_df["student_id"] == s_id) & (marks_df["subject"] == sub_upper)]
                
                if not sub_match.empty:
                    val = str(sub_match["marks_obtained"].iloc[0]).strip().upper()
                    tot = float(sub_match["total_marks"].iloc[0]) if pd.notna(sub_match["total_marks"].iloc[0]) else 100.0
                    
                    if val == "NC":
                        entry[short_sub] = "NC"
                        has_explicit_nc = True
                    elif val == "A":
                        entry[short_sub] = "A"
                        max_total += tot       
                        has_valid_scores = True
                    elif val.replace('.', '', 1).isdigit() or val.isdigit():
                        entry[short_sub] = float(val)
                        obtained_total += float(val)
                        max_total += tot       
                        has_valid_scores = True
                    else:
                        entry[short_sub] = val
                else:
                    entry[short_sub] = "-"

            # Dynamic total calculation rules
            if has_valid_scores:
                entry["Total (Obt)"] = int(obtained_total)
                entry["Total Max"] = int(max_total)
            elif has_explicit_nc:
                entry["Total (Obt)"] = "NC"
                entry["Total Max"] = "NC"
            else:
                entry["Total (Obt)"] = "-"
                entry["Total Max"] = "-"
                
            summary_rows.append(entry)
            
        final_report_df = pd.DataFrame(summary_rows)
        
      # ----------------- RE-ENGINEERED HTML PRINT EMBED -----------------
        # Generate clean short form subject labels without "(Obt)"
        short_subject_labels = [SHORT_SUBJECTS_MAP.get(sub.upper().strip(), sub) for sub in subjects]
        thead_subjects_html = "".join([f'<th>{lbl}</th>' for lbl in short_subject_labels])
        
        # Dynamic Rows Compilation
        tbody_rows_html = ""
        for _, row in final_report_df.iterrows():
            s_id = row["ID"]
            current_status = row["Status"]
            
            # Dynamic visual status badge for Re-Active student profiles
            status_badge = ""
            if current_status == "Re-Active":
                status_badge = " <span style='background: #e1f5fe; color: #0288d1; font-size: 10px; padding: 2px 5px; border-radius: 3px; font-weight: bold;'>RE-JOIN</span>"
            
            # Find old/hidden subject marks that aren't part of this student's current layout mapping
            old_marks_badges = []
            hidden_marks_df = marks_df[marks_df["student_id"] == s_id]
            for _, h_row in hidden_marks_df.iterrows():
                h_sub = h_row["subject"]
                if h_sub not in [sub.upper().strip() for sub in subjects]:
                    short_h_sub = SHORT_SUBJECTS_MAP.get(h_sub, h_sub)
                    old_marks_badges.append(f"{short_h_sub}: {h_row['marks_obtained']}")
            
            history_str = ""
            if old_marks_badges:
                history_str = f"<br><span style='color: #d35400; font-size: 11px; font-style: italic;'>Dropped ({', '.join(old_marks_badges)})</span>"
            
            row_subjects_cells = ""
            for lbl in short_subject_labels:
                cell_val = str(row[lbl])
                cell_style = "color: #e74c3c; font-weight: bold;" if cell_val in ["A", "FAIL"] else ("color: #7f8c8d; font-weight: bold;" if cell_val == "NC" else "")
                row_subjects_cells += f'<td style="{cell_style}">{cell_val}</td>'
            
            tbody_rows_html += f"""
            <tr>
                <td>{row['ID']}</td>
                <td style="text-align: left; font-weight: bold; padding-left: 12px;">
                    {row['Student Name']} {status_badge} {history_str}
                </td>
                <td>{row['Section']}</td>
                <td>{row['Class']}</td>
                {row_subjects_cells}
                <td style="font-weight: bold; background-color: #fcfcfc;">{row['Total (Obt)']}</td>
                <td style="font-weight: bold; color: #555; background-color: #fcfcfc;">{row['Total Max']}</td>
            </tr>
            """
            
        logo_url = "https://raw.githubusercontent.com/mirfanshakirpgc-art/Academics-Reports/main/logo.png"
        
        # HTML Rendering Payload Configuration
        analytics_html_payload = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: "Segoe UI", Arial, sans-serif; color: #333; background-color: #fff; margin: 0; padding: 10px; }}
            .report-wrapper-container {{ max-width: 100%; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 6px; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            
            /* TOP ACTION UTILITIES PANEL */
            .action-panel-bar {{ display: flex; gap: 12px; margin-bottom: 22px; }}
            .btn-action {{ padding: 10px 22px; font-weight: bold; font-size: 14px; border: none; border-radius: 4px; cursor: pointer; transition: background 0.2s; }}
            .btn-print {{ background: #222; color: #fff; }}
            .btn-image {{ background: #0066cc; color: #fff; }}
            .btn-action:hover {{ opacity: 0.9; }}
            
            /* OFFICIAL BRAND BANNER HEADER */
            .header-banner {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #222; padding-bottom: 15px; margin-bottom: 20px; }}
            .header-branding {{ text-align: left; }}
            .inst-title {{ font-size: 24px; font-weight: 800; color: #111; letter-spacing: 0.5px; margin: 0; }}
            .doc-subtitle {{ font-size: 15px; color: #555; margin: 4px 0 0 0; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
            .meta-details {{ text-align: right; font-size: 13px; color: #444; line-height: 1.5; }}
            .brand-logo-img {{ max-height: 55px; width: auto; object-fit: contain; }}
            
            /* DATA LEDGER TABLE GRID STRUCTURE */
            .analytics-grid-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }}
            .analytics-grid-table th, .analytics-grid-table td {{ border: 1px solid #dcdcdc; padding: 10px 8px; text-align: center; }}
            .analytics-grid-table th {{ background-color: #f8f9fa; font-weight: 700; color: #2c3e50; white-space: nowrap; }}
            .analytics-grid-table tr:nth-child(even) {{ background-color: #fbfbfb; }}
            .analytics-grid-table tr:hover {{ background-color: #f5f7fa; }}
            
            @media print {{
                .action-panel-bar {{ display: none !important; }}
                body {{ padding: 0; margin: 0; }}
                .report-wrapper-container {{ border: none !important; box-shadow: none !important; padding: 0 !important; }}
            }}
        </style>
        </head>
        <body>
            <div class="action-panel-bar">
                <button class="btn-action btn-print" onclick="window.print();">🖨️ Print Summary Ledger</button>
                <button class="btn-action btn-image" id="capture-summary-trigger">📸 Save Layout As Image</button>
            </div>
            
            <div class="report-wrapper-container" id="printable-summary-target">
                <div class="header-banner">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <img class="brand-logo-img" src="{logo_url}" alt="Logo">
                        <div class="header-branding">
                            <h1 class="inst-title">CONCORDIA COLLEGE KASUR</h1>
                            <div class="doc-subtitle">Section Performance Summary Report</div>
                        </div>
                    </div>
                    <div class="meta-details">
                        <b>Discipline:</b> {sel_disc}<br>
                        <b>Section Block:</b> {sel_sec}<br>
                        <b>Exam Phase:</b> {sel_exam}
                    </div>
                </div>
                
                <table class="analytics-grid-table">
                    <thead>
                        <tr>
                            <th style="width: 7%;">ID</th>
                            <th style="text-align: left; padding-left: 12px;">Student Name</th>
                            <th style="width: 9%;">Section</th>
                            <th style="width: 7%;">Class</th>
                            {thead_subjects_html}
                            <th style="background-color: #f1f3f5; width: 10%;">Total (Obt)</th>
                            <th style="background-color: #f1f3f5; width: 9%;">Total Max</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tbody_rows_html}
                    </tbody>
                </table>
            </div>

            <script>
                document.getElementById('capture-summary-trigger').addEventListener('click', function() {{
                    const targetEl = document.getElementById('printable-summary-target');
                    const filenameStr = "Summary_Report_{sel_sec}_{sel_exam}.png";
                    
                    html2canvas(targetEl, {{ scale: 2, useCORS: true }}).then(canvas => {{
                        const linkHook = document.createElement('a');
                        linkHook.download = filenameStr;
                        linkHook.href = canvas.toDataURL('image/png');
                        linkHook.click();
                    }});
                }});
            </script>
        </body>
        </html>
        """
        
        # Render components safely
        components.html(analytics_html_payload, height=750, scrolling=True)
        
    else:
        st.info("💡 No active student profiles loaded under this section yet.")

# ----------------- 📈 MULTI-TEST PROGRESS REPORT -----------------
if menu_choice == "📈 Multi-Test Progress Report":
    st.title("📈 Multi-Test Progress Analytics")
    st.markdown("Select your reporting scope below to generate high-fidelity, print-ready student progress cards.")

    # CSS Injection 
    st.markdown("""
        <style>
        @media print {
            .no-print { display: none !important; }
        }
        </style>
    """, unsafe_allow_html=True)

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
                filtered_sections = DISCIPLINE_SECTIONS_MAP.get(sel_disc, [])
                sel_sec = st.selectbox("Select Target Class Section:", filtered_sections, key="form_sel_sec_bulk")
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
                s_marks = marks_df[marks_df["student_id"].astype(str) == str(match_id)].copy()
            else:
                s_marks = pd.DataFrame()
                
            if not s_marks.empty:
                s_marks["subject_clean"] = s_marks["subject_name"].astype(str).str.strip().str.title()
                
                detected_sec = "UNKNOWN"
                if "section" in s_marks.columns and not s_marks["section"].dropna().empty:
                    detected_sec = str(s_marks["section"].dropna().iloc[-1]).upper().strip()
                else:
                    detected_sec = s_section.upper().strip()
                
                # Verify structural track selection safely
                target_section_context = s_section.upper().strip() if s_section else detected_sec
                
                medical_secs = ["MG_BLUE", "MG_WHITE", "MB_BLUE"]
                engineering_secs = ["EG_BLUE", "EB_BLUE"]
                ics_physics_secs = ["CG_WHITE", "CG_GREEN", "CB_WHITE", "CB_GREEN"]
                ics_stats_secs = ["CG_STATS", "CB_STATS"]
                commerce_secs = ["IG", "IB"]
                humanities_secs = ["FB", "FG"]
                it_secs = ["DITB", "DITG"]
                
                compulsory_subs = ["English", "Urdu", "Isl_Eth", "T_Quran"]
                
                if any(x in target_section_context for x in medical_secs) or target_section_context.startswith("M"):
                    active_electives = ["Chemistry", "Biology", "Physics"]
                elif any(x in target_section_context for x in engineering_secs) or target_section_context.startswith("E"):
                    active_electives = ["Chemistry", "Mathematics", "Physics"]
                elif any(x in target_section_context for x in ics_physics_secs):
                    active_electives = ["Computer", "Mathematics", "Physics"]
                elif any(x in target_section_context for x in ics_stats_secs) or "STATS" in target_section_context:
                    active_electives = ["Computer", "Mathematics", "Statistics"]
                elif any(x in target_section_context for x in commerce_secs) or target_section_context.startswith("I"):
                    # 4 elective track unique to Commerce
                    active_electives = ["Accounting", "Economics", "Commerce", "B_Math"]
                elif any(x in target_section_context for x in humanities_secs) or target_section_context.startswith("F"):
                    # 3 standard electives for Humanities
                    active_electives = ["Education", "Isl_Elc", "Computer"]
                elif any(x in target_section_context for x in it_secs) or target_section_context.startswith("DIT"):
                    active_electives = ["Information Technology", "Computer Science", "Networks"]
                else:
                    active_electives = ["Computer", "Mathematics", "Statistics", "Physics", "Chemistry", "Biology"]
                
                raw_subjects = list(set(compulsory_subs + active_electives))
                unique_subjects = sorted(raw_subjects, key=lambda x: (x == "B_Math", x.upper()))
                
                # Preserved historical matrix maps for all tracks including FB / FG
                history_bridge_map = {
                    "Chemistry": ["Computer"],
                    "Biology": ["Statistics"],
                    "Physics": ["Mathematics"],
                    "Education": ["Mathematics", "Physics", "Chemistry"],
                    "Isl_Elc": ["Statistics", "Biology", "Economics", "Accounting"],
                    "Accounting": ["Mathematics"],       
                    "Economics": ["Chemistry", "Computer"], 
                    "Commerce": ["Physics", "Biology"]
                }
            else:
                target_section_context = s_section.upper().strip() if s_section else "UNKNOWN"
                if any(x in target_section_context for x in ["IB", "IG"]):
                    raw_subjects = ["English", "Urdu", "Accounting", "Economics", "Commerce", "Isl_Eth", "T_Quran", "B_Math"]
                    unique_subjects = sorted(raw_subjects, key=lambda x: (x == "B_Math", x.upper()))
                elif any(x in target_section_context for x in ["FB", "FG"]):
                    unique_subjects = ["English", "Urdu", "Education", "Isl_Elc", "Computer", "Isl_Eth", "T_Quran"]
                else:
                    unique_subjects = ["English", "Urdu", "Mathematics", "Computer", "Statistics", "Isl_Eth", "T_Quran"]
                history_bridge_map = {}
            
            table_rows_html = ""
            exam_totals_obtained = {exam: 0.0 for exam in selected_exams_list}
            exam_totals_max = {exam: 0.0 for exam in selected_exams_list}
            exam_has_any_data = {exam: False for exam in selected_exams_list}

            for sub in unique_subjects:
                row_html = f"<tr><td>{sub.upper()}</td>"
                sub_percentages = []

                for exam in selected_exams_list:
                    exam_subset = s_marks[(s_marks["subject_clean"] == sub) & (s_marks["exam_type"].str.upper() == exam.upper())] if not s_marks.empty else pd.DataFrame()
                    
                    if exam_subset.empty and sub in history_bridge_map and not s_marks.empty:
                        possible_old_subs = history_bridge_map[sub]
                        old_match = s_marks[(s_marks["subject_clean"].isin(possible_old_subs)) & (s_marks["exam_type"].str.upper() == exam.upper())]
                        
                        if not old_match.empty:
                            old_sub_clean = old_match.iloc[0]["subject_clean"]
                            shorthand_tag = old_sub_clean[:4] if len(old_sub_clean) > 4 else old_sub_clean
                            
                            m_obt = old_match.iloc[0]["marks_obtained"]
                            m_tot = old_match.iloc[0]["total_marks"]
                            try:
                                val_obt = float(m_obt)
                                val_tot = float(m_tot) if float(m_tot) > 0 else 100.0
                                pct = (val_obt / val_tot) * 100
                                row_html += f"<td><span style='font-size:11px; color:#7f8c8d;'>{shorthand_tag}({int(pct)}%)</span></td>"
                                sub_percentages.append(pct)
                                exam_totals_obtained[exam] += val_obt
                                exam_totals_max[exam] += val_tot
                                exam_has_any_data[exam] = True
                                continue 
                            except:
                                pass

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
                            clean_obt = str(m_obt).strip().upper()
                            if clean_obt in ["A", "ABSENT", "ABS"]:
                                row_html += "<td>A</td>"
                                exam_totals_max[exam] += float(m_tot) if pd.notna(m_tot) and float(m_tot) > 0 else 100.0
                                exam_has_any_data[exam] = True
                                sub_percentages.append(0.0)
                            elif clean_obt in ["NC", "N.C"]:
                                row_html += "<td style='color: #7f8c8d; font-weight: bold;'>NC</td>"
                            else:
                                row_html += "<td>-</td>"
                    else:
                        row_html += "<td>-</td>"
                
                if sub_percentages:
                    avg_pct = int(sum(sub_percentages) / len(sub_percentages))
                    row_html += f"<td><strong>{avg_pct}%</strong></td></tr>"
                else:
                    row_html += "<td><strong>-</strong></td></tr>"
                table_rows_html += row_html

            # --- GRAND TOTALS ROW ---
            total_row_html = "<tr><td><strong>Total</strong></td>"
            grand_total_percentages = []
            for exam in selected_exams_list:
                if exam_has_any_data[exam] and exam_totals_max[exam] > 0:
                    tot_pct = int((exam_totals_obtained[exam] / exam_totals_max[exam]) * 100)
                    total_row_html += f"<td><strong>{tot_pct}%</strong></td>"
                    grand_total_percentages.append(tot_pct)
                else:
                    total_row_html += "<td><strong>-</strong></td>"
            
            if grand_total_percentages:
                overall_avg = int(sum(grand_total_percentages) / len(grand_total_percentages))
                total_row_html += f"<td><strong>{overall_avg}%</strong></td></tr>"
            else:
                total_row_html += "<td><strong>-</strong></td></tr>"
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

            # HTML PAYLOAD WITH INTEGRATED INLINE STYLES AND LAYOUT
            compiled_html = """
            <!DOCTYPE html>
            <html>
            <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
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
                
                /* CONTROL ACTIONS BUTTONS BAR styling wrapper element */
                .action-controls-bar { max-width: 850px; margin: 0 auto 20px auto; display: flex; gap: 10px; flex-wrap: wrap; }
                .print-btn { background: #222; color: #fff; padding: 10px 20px; font-weight: bold; border-radius: 4px; border: none; cursor: pointer; font-size: 14px; }
                .image-single-btn { background: #0066cc; color: #fff; padding: 10px 20px; font-weight: bold; border-radius: 4px; border: none; cursor: pointer; font-size: 14px; }
                .image-section-btn { background: #198754; color: #fff; padding: 10px 20px; font-weight: bold; border-radius: 4px; border: none; cursor: pointer; font-size: 14px; }
                
                button:disabled { background: #6c757d !important; cursor: not-allowed; opacity: 0.8; }
                
                @media print {
                    .action-controls-bar { display: none !important; }
                    .official-card-container { border: none !important; margin: 0 auto 15mm auto !important; page-break-inside: avoid !important; break-inside: avoid !important; }
                    .print-page-break-divider { page-break-after: always !important; break-after: page !important; }
                }
            </style>
            </head>
            <body>
                <div class="action-controls-bar">
                    <button class="print-btn" onclick="window.print();">🖨️ Print Document (Ctrl+P)</button>
                    <button class="image-single-btn" id="save-single-card-trigger">📸 Save Current Card as Picture</button>
                    <button class="image-section-btn" id="save-section-cards-trigger">🗂️ Save Complete Section Cards (ZIP)</button>
                </div>
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
                
                # Assigned explicit distinct container target ID hook tag for DOM processing pipeline execution
                compiled_html += f"""
                <div class="official-card-container" id="card-{current_id}" data-student-name="{name.replace(' ', '_')}">
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
                            
                            if obt_val == "NC":
                                obt_disp, per_disp, status_disp = "NC", "NC", "NC"
                            elif obt_val in ["A", "ABSENT"]:
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
                        
                    style_override = "color: #7f8c8d; font-weight: bold;" if obt_disp == "NC" else ""
                    
                    compiled_html += f"""
                    <tr>
                        <td style="text-align: left; font-weight: bold; padding-left: 10px;">{sub}</td>
                        <td style="{style_override}">{obt_disp}</td>
                        <td style="{style_override}">{tot_marks_num if obt_disp != "NC" else "NC"}</td>
                        <td style="{style_override}">{pass_marks_num if obt_disp != "NC" else "NC"}</td>
                        <td style="{style_override}">{per_disp}</td>
                        <td style="font-weight: bold; {style_override}">{status_disp}</td>
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
                
            # INJECT JAVASCRIPT ASYNC IMAGE CAPTURE INTERFACE LOGIC
            compiled_html += """
            <script>
                // 1. Save Current / First visible student card layout asset configuration
                document.getElementById('save-single-card-trigger').addEventListener('click', function() {
                    const targetCard = document.querySelector('.official-card-container');
                    if (!targetCard) return alert("No active result card engine target detected.");
                    
                    const sName = targetCard.getAttribute('data-student-name') || "student";
                    const sId = targetCard.id || "result";
                    
                    html2canvas(targetCard, { scale: 2, useCORS: true }).then(canvas => {
                        const dlLink = document.createElement('a');
                        dlLink.download = `${sId}_${sName}.png`;
                        dlLink.href = canvas.toDataURL('image/png');
                        dlLink.click();
                    });
                });

                // 2. Iterative loop rendering pipeline logic to build and downloard a compressed ZIP package file mapping
                document.getElementById('save-section-cards-trigger').addEventListener('click', async function() {
                    const allCards = document.querySelectorAll('.official-card-container');
                    if (allCards.length === 0) return alert("Empty stack context scope configuration payload mapping.");
                    
                    const actionBtn = this;
                    const primaryLabel = actionBtn.innerText;
                    actionBtn.innerText = "⏳ Generating Archive Images...";
                    actionBtn.disabled = true;
                    
                    const archiveBundle = new JSZip();
                    
                    try {
                        for(let index = 0; index < allCards.length; index++) {
                            const currentCard = allCards[index];
                            const cardIdStr = currentCard.id || `card_${index}`;
                            const studentNameStr = currentCard.getAttribute('data-student-name') || "record";
                            
                            // High DPI scale conversion setup to ensure text rendering elements stay perfectly crisp
                            const renderingCanvas = await html2canvas(currentCard, { scale: 2, useCORS: true });
                            const sanitizedBase64Payload = renderingCanvas.toDataURL('image/png').split(',')[1];
                            
                            archiveBundle.file(`${cardIdStr}_${studentNameStr}.png`, sanitizedBase64Payload, { base64: true });
                        }
                        
                        const compiledZipBlob = await archiveBundle.generateAsync({ type: 'blob' });
                        const dlLink = document.createElement('a');
                        dlLink.download = "Section_Result_Cards_Archive.zip";
                        dlLink.href = URL.createObjectURL(compiledZipBlob);
                        dlLink.click();
                        
                    } catch (error) {
                        console.error(error);
                        alert("An engine configuration runtime execution interruption occurred.");
                    } finally {
                        actionBtn.innerText = primaryLabel;
                        actionBtn.disabled = false;
                    }
                });
            </script>
            </body>
            </html>
            """
            
            # Render layout view frame container component
            components.html(compiled_html, height=800, scrolling=True)
    elif menu_choice == "Student Management":
    st.title("👥 Student Profile Management & Registration")
    st.info("Register and manage student profiles. Dropdown values are pulled directly from your Configuration Master Module.")
    
    # 1. Initialize students database schema safely
    execute_db_command("""
        CREATE TABLE IF NOT EXISTS students (
...

    # 1. Initialize students database schema safely
    execute_db_command("""
        CREATE TABLE IF NOT EXISTS students (
            student_id SERIAL PRIMARY KEY,
            admission_no VARCHAR(50) UNIQUE NOT NULL,
            student_name VARCHAR(150) NOT NULL,
            father_name VARCHAR(150),
            discipline_key VARCHAR(100) NOT NULL,
            class_key VARCHAR(100) NOT NULL,
            section_key VARCHAR(100) NOT NULL,
            session_key VARCHAR(100) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        );
    """)

    # Setup Workspaces: Add Tab and View Tab
    tab_register, tab_directory = st.tabs(["➕ Register New Student", "📋 Student Directory View"])

    with tab_register:
        # 2. Leverage your standalone get_registry_options tool to extract configurations
        try:
            df_disc = get_registry_options("DISCIPLINE")
            df_class = get_registry_options("CLASS")
            df_sec = get_registry_options("SECTION")
            df_sess = get_registry_options("SESSION")
        except Exception as e:
            st.error(f"Failed to access Master Module system registries: {e}")
            st.stop()

        # Create mapping dictionaries: Display Name -> Under-the-hood System Key
        disc_map = {r['item_value']: r['item_key'] for _, r in df_disc.iterrows()} if not df_disc.empty else {}
        class_map = {r['item_value']: r['item_key'] for _, r in df_class.iterrows()} if not df_class.empty else {}
        sec_map = {r['item_value']: r['item_key'] for _, r in df_sec.iterrows()} if not df_sec.empty else {}
        sess_map = {r['item_value']: r['item_key'] for _, r in df_sess.iterrows()} if not df_sess.empty else {}

        if not (disc_map and class_map and sec_map and sess_map):
            st.warning("⚠️ Stop: Please configure your active Disciplines, Classes, Sections, and Sessions in the Master Module before registering profiles.")
        else:
            with st.form("student_profile_entry_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    admission_no = st.text_input("Admission Number (Unique ID Reference):").strip().upper()
                    student_name = st.text_input("Student Full Name:").strip()
                    father_name = st.text_input("Father's Name:").strip()
                    
                with col2:
                    selected_disc = st.selectbox("Select Discipline Faculty:", options=list(disc_map.keys()))
                    selected_class = st.selectbox("Select Academic Placement Year:", options=list(class_map.keys()))
                    selected_sec = st.selectbox("Select Section Cohort Allocation:", options=list(sec_map.keys()))
                    selected_sess = st.selectbox("Select Active Operational Session:", options=list(sess_map.keys()))

                if st.form_submit_button("🚀 Finalize & Register Student Profile", type="primary"):
                    if not admission_no or not student_name:
                        st.error("Admission Number and Student Full Name fields cannot be empty!")
                    else:
                        insert_query = """
                            INSERT INTO students (admission_no, student_name, father_name, discipline_key, class_key, section_key, session_key, is_active)
                            VALUES (:adm, :name, :father, :disc, :class, :sec, :sess, TRUE)
                            ON CONFLICT (admission_no) DO UPDATE SET
                                student_name = EXCLUDED.student_name,
                                father_name = EXCLUDED.father_name,
                                discipline_key = EXCLUDED.discipline_key,
                                class_key = EXCLUDED.class_key,
                                section_key = EXCLUDED.section_key,
                                session_key = EXCLUDED.session_key,
                                is_active = TRUE;
                        """
                        try:
                            run_update(insert_query, {
                                "adm": admission_no,
                                "name": student_name,
                                "father": father_name,
                                "disc": disc_map[selected_disc],
                                "class": class_map[selected_class],
                                "sec": sec_map[selected_sec],
                                "sess": sess_map[selected_sess]
                            })
                            st.success(f"🎉 Success: Student record '{student_name}' has been created under ID {admission_no}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database sync operation failed: {e}")

    with tab_directory:
        st.subheader("🔍 Filter Active Student Roster")
        
        # Simple Search Bar
        search_term = st.text_input("Search student by name or admission number:").strip().upper()
        
        # Fetch data while joining against the master registry to display human-readable names instead of raw code keys
        view_query = """
            SELECT 
                s.admission_no AS "Admission No",
                s.student_name AS "Student Name",
                s.father_name AS "Father Name",
                m_disc.item_value AS "Discipline",
                m_class.item_value AS "Class",
                m_sec.item_value AS "Section",
                m_sess.item_value AS "Session"
            FROM students s
            LEFT JOIN master_registry m_disc ON s.discipline_key = m_disc.item_key AND m_disc.item_type = 'DISCIPLINE'
            LEFT JOIN master_registry m_class ON s.class_key = m_class.item_key AND m_class.item_type = 'CLASS'
            LEFT JOIN master_registry m_sec ON s.section_key = m_sec.item_key AND m_sec.item_type = 'SECTION'
            LEFT JOIN master_registry m_sess ON s.session_key = m_sess.item_key AND m_sess.item_type = 'SESSION'
            WHERE s.is_active = TRUE
        """
        
        params = {}
        if search_term:
            view_query += " AND (UPPER(s.student_name) LIKE :term OR UPPER(s.admission_no) LIKE :term)"
            params["term"] = f"%{search_term}%"
            
        view_query += " ORDER BY s.admission_no DESC"
        
        try:
            students_df = run_query(view_query, params)
            if not students_df.empty:
                st.dataframe(students_df, use_container_width=True)
                
                # Management Option: Deactivate a profile entry
                st.markdown("---")
                st.subheader("🗑️ Administrative Maintenance")
                remove_id = st.text_input("Enter Admission Number to remove from active roster:").strip().upper()
                if st.button("Deactivate Student Profile", type="secondary"):
                    if remove_id:
                        execute_db_command("UPDATE students SET is_active = FALSE WHERE admission_no = :adm", {"adm": remove_id})
                        st.success(f"Student profile {remove_id} marked inactive.")
                        st.rerun()
            else:
                st.info("No matching student profile records found in the database.")
        except Exception as e:
            st.error(f"Error displaying student summary ledger: {e}")
# ---------------------------------------------------------
# ROUTER INTEGRATION: 👨‍🏫 TEACHER MANAGEMENT MODULE
# ---------------------------------------------------------
elif menu_choice == "👨‍🏫 Teacher Management":
    st.title("👨‍🏫 Teacher Allocation & Performance Engine")
    
    # Safely acquire access credentials
    current_user = st.session_state.get('username', 'admin')
    current_role = st.session_state.get('role', 'controller') 
    
    if current_role == 'controller':
        menu_options = ["Subject Allocations", "Teacher Marks Portal", "Teacher Analysis", "Discipline Analysis"]
    else:
        menu_options = ["Teacher Marks Portal", "Teacher Analysis"]
        
    sub_menu = st.sidebar.radio("Navigate Module:", menu_options, key="teacher_sub_menu")

    # Ensure assignments storage index mapping table runs cleanly
    execute_db_command("""
        CREATE TABLE IF NOT EXISTS allocations (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            subject VARCHAR(100) NOT NULL,
            section VARCHAR(100) NOT NULL
        );
    """)

    # ---------------------------------------------------------
    # SUB-MODULE A: SUBJECT ALLOCATIONS
    # ---------------------------------------------------------
    if sub_menu == "Subject Allocations":
        st.subheader("🔗 Allocate Subjects & Sections to Registered Faculty")
        
        teachers_df = run_query("SELECT id, username FROM app_users WHERE role = 'teacher' ORDER BY username ASC")
        
        if not teachers_df.empty:
            t_options = {row['username']: row['id'] for _, row in teachers_df.iterrows()}
            
            # DYNAMIC MASTER UPGRADE: Pull directly from database registries instead of hardcoded maps
            try:
                df_subs = get_registry_options("SUBJECT")
                df_secs = get_registry_options("SECTION")
            except Exception as e:
                st.error(f"Failed to load systemic parameters configuration: {e}")
                st.stop()

            all_subs = sorted(list(df_subs['item_value'].unique())) if not df_subs.empty else ["Math", "English", "Science"]
            all_secs = sorted(list(df_secs['item_value'].unique())) if not df_secs.empty else ["A", "B", "C"]
            
            # Map values back to their original master keys for standard database writes
            sub_key_map = {r['item_value']: r['item_key'] for _, r in df_subs.iterrows()} if not df_subs.empty else {}
            sec_key_map = {r['item_value']: r['item_key'] for _, r in df_secs.iterrows()} if not df_secs.empty else {}

            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1: selected_t = st.selectbox("Select Teacher Account:", options=list(t_options.keys()))
            with col_a2: selected_sub = st.selectbox("Select Subject:", options=all_subs)
            with col_a3: selected_sec = st.selectbox("Assign Section:", options=all_secs)
                
            if st.button("🔒 Authorize Data Entry Rights"):
                target_user_id = int(t_options[selected_t])
                target_sub_key = sub_key_map.get(selected_sub, selected_sub)
                target_sec_key = sec_key_map.get(selected_sec, selected_sec)
                
                check_dup = run_query("""
                    SELECT id FROM allocations 
                    WHERE user_id = :uid AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND UPPER(TRIM(section)) = UPPER(TRIM(:sec))
                """, {"uid": target_user_id, "sub": target_sub_key, "sec": target_sec_key})
                
                if check_dup.empty:
                    execute_db_command("""
                        INSERT INTO allocations (user_id, subject, section) 
                        VALUES (:uid, :sub, :sec)
                    """, {"uid": target_user_id, "sub": target_sub_key, "sec": target_sec_key})
                    st.success(f"Access granted! {selected_t} can now manage {selected_sub} in Section {selected_sec}.")
                    st.rerun()
                else:
                    st.warning("This allocation already exists.")
                    
            st.markdown("---")
            st.write("#### Active Institutional Rights Log")
            alloc_log = run_query("""
                SELECT a.id, u.username as teacher, m_sub.item_value as subject, m_sec.item_value as section 
                FROM allocations a
                JOIN app_users u ON a.user_id = u.id
                LEFT JOIN master_registry m_sub ON a.subject = m_sub.item_key AND m_sub.item_type = 'SUBJECT'
                LEFT JOIN master_registry m_sec ON a.section = m_sec.item_key AND m_sec.item_type = 'SECTION'
                ORDER BY u.username ASC
            """)
            if not alloc_log.empty:
                st.dataframe(alloc_log, use_container_width=True)
        else:
            st.info("No users with the role 'teacher' found in app_users.")

    # ---------------------------------------------------------
    # SUB-MODULE B: SECURED MARKS PORTAL
    # ---------------------------------------------------------
    elif sub_menu == "Teacher Marks Portal":
        st.subheader("🔑 Secure Faculty Data Input Gateway")
        
        teachers_df = run_query("SELECT id, username FROM app_users WHERE role = 'teacher' ORDER BY username ASC")
        if not teachers_df.empty:
            t_options = {row['username']: row['id'] for _, row in teachers_df.iterrows()}
            active_teacher = st.selectbox("View Portal As Teacher:", options=list(t_options.keys()))
            uid = int(t_options[active_teacher])
        else:
            st.info("No teachers available.")
            uid = None
            
        if uid is not None:
            my_rights = run_query("""
                SELECT a.subject as sub_key, m_sub.item_value as sub_val, a.section as sec_key, m_sec.item_value as sec_val
                FROM allocations a
                LEFT JOIN master_registry m_sub ON a.subject = m_sub.item_key AND m_sub.item_type = 'SUBJECT'
                LEFT JOIN master_registry m_sec ON a.section = m_sec.item_key AND m_sec.item_type = 'SECTION'
                WHERE a.user_id = :uid
            """, {"uid": uid})
            
            if not my_rights.empty:
                col_m1, col_m2 = st.columns(2)
                
                sub_opts = {row['sub_val']: row['sub_key'] for _, row in my_rights.iterrows() if row['sub_val']}
                sec_opts = {row['sec_val']: row['sec_key'] for _, row in my_rights.iterrows() if row['sec_val']}
                
                with col_m1: sel_sub_val = st.selectbox("Assigned Subjects:", options=list(sub_opts.keys()))
                with col_m2: sel_sec_val = st.selectbox("Assigned Sections:", options=list(sec_opts.keys()))
                
                sel_sub_key = sub_opts[sel_sub_val]
                sel_sec_key = sec_opts[sel_sec_val]
                
                try:
                    df_exams = get_registry_options("TEST_TYPE")
                    exams_list = list(df_exams['item_value'].unique()) if not df_exams.empty else ["Mid Term", "Final Exam"]
                except Exception:
                    exams_list = ["Mid Term", "Final Exam"]
                    
                sel_exam = st.selectbox("Target Assessment Term Type:", options=exams_list)
                
                students = run_query("""
                    SELECT student_id, admission_no, student_name FROM students 
                    WHERE section_key = :sec AND is_active = TRUE 
                    ORDER BY student_name ASC
                """, {"sec": sel_sec_key})
                
                if not students.empty:
                    st.info(f"Displaying Roster Table for {sel_sub_val} — Section: {sel_sec_val}")
                    
                    marks_data = []
                    for _, s_row in students.iterrows():
                        sid = s_row['student_id']
                        sname = s_row['student_name']
                        sadm = s_row['admission_no']
                        
                        existing = run_query("""
                            SELECT marks_obtained, total_marks FROM marks 
                            WHERE student_id = :sid AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND exam_type = :exam
                        """, {"sid": sid, "sub": sel_sub_key, "exam": sel_exam})
                        
                        val_fill = "0"
                        tot_fill = 100
                        if not existing.empty:
                            val_fill = str(existing['marks_obtained'].iloc[0])
                            tot_fill = int(existing['total_marks'].iloc[0])
                            
                        c_left, c_right = st.columns([3, 1])
                        with c_left: m_val = st.text_input(f"[{sadm}] {sname}:", value=val_fill, key=f"m_{sid}_{sel_sub_key}")
                        with c_right: t_val = st.number_input("Total Max:", min_value=10, max_value=200, value=tot_fill, key=f"t_{sid}_{sel_sub_key}")
                        
                        marks_data.append({"sid": sid, "obtained": m_val, "total": t_val})
                        
                    if st.button("🎯 Finalize & Commit Marks Values"):
                        for record in marks_data:
                            execute_db_command("""
                                DELETE FROM marks WHERE student_id = :sid 
                                AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND exam_type = :exam
                            """, {"sid": record['sid'], "sub": sel_sub_key, "exam": sel_exam})
                            
                            execute_db_command("""
                                INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks)
                                VALUES (:sid, :sub, :exam, :obt, :tot)
                            """, {"sid": record['sid'], "sub": sel_sub_key, "exam": sel_exam, "obt": record['obtained'].strip().upper(), "tot": record['total']})
                        st.success("Assessment marks record updated securely!")
                else:
                    st.error("No students found in this section.")
            else:
                st.warning("🚨 No subject assignments have been allocated to this account yet.")

    # ---------------------------------------------------------
    # SUB-MODULE C: TEACHER ANALYSIS
    # ---------------------------------------------------------
    elif sub_menu == "Teacher Analysis":
        st.subheader("📊 Performance Evaluation by Instructor")
        
        teachers_df = run_query("SELECT id, username FROM app_users WHERE role = 'teacher' ORDER BY username ASC")
        if not teachers_df.empty:
            t_options = {row['username']: row['id'] for _, row in teachers_df.iterrows()}
            selected_t = st.selectbox("Select Teacher Account to Analyze:", options=list(t_options.keys()))
            uid = int(t_options[selected_t])
            
            allocations = run_query("""
                SELECT a.subject as sub_key, m_sub.item_value as sub_val, a.section as sec_key, m_sec.item_value as sec_val
                FROM allocations a
                LEFT JOIN master_registry m_sub ON a.subject = m_sub.item_key AND m_sub.item_type = 'SUBJECT'
                LEFT JOIN master_registry m_sec ON a.section = m_sec.item_key AND m_sec.item_type = 'SECTION'
                WHERE a.user_id = :uid
            """, {"uid": uid})
            
            if not allocations.empty:
                summary_metrics = []
                for _, a_row in allocations.iterrows():
                    sub_key = a_row['sub_key']
                    sub_val = a_row['sub_val']
                    sec_key = a_row['sec_key']
                    sec_val = a_row['sec_val']
                    
                    performance_data = run_query("""
                        SELECT m.marks_obtained, m.total_marks FROM marks m
                        JOIN students s ON m.student_id = s.student_id
                        WHERE s.section_key = :sec AND UPPER(TRIM(m.subject)) = UPPER(TRIM(:sub))
                    """, {"sec": sec_key, "sub": sub_key})
                    
                    if not performance_data.empty:
                        performance_data['num_obt'] = pd.to_numeric(performance_data['marks_obtained'], errors='coerce')
                        valid_scores = performance_data.dropna(subset=['num_obt'])
                        
                        if not valid_scores.empty:
                            avg_pct = (valid_scores['num_obt'].sum() / valid_scores['total_marks'].sum()) * 100
                            pass_count = sum(valid_scores['num_obt'] >= (valid_scores['total_marks'] * 0.40))
                            pass_ratio = (pass_count / len(valid_scores)) * 100
                            
                            summary_metrics.append({
                                "Subject Class": sub_val,
                                "Section Group": sec_val,
                                "Evaluated Count": len(valid_scores),
                                "Average Score": f"{avg_pct:.1f}%",
                                "Passing KPI Rate": f"{pass_ratio:.1f}%"
                            })
                            
                if summary_metrics:
                    st.write(f"#### Class Metrics Managed by {selected_t}")
                    st.table(pd.DataFrame(summary_metrics))
                else:
                    st.info("No marks records found for this instructor's classes.")
            else:
                st.warning("This profile holds no active class assignments.")

    # ---------------------------------------------------------
    # SUB-MODULE D: DISCIPLINE ANALYSIS
    # ---------------------------------------------------------
    elif sub_menu == "Discipline Analysis":
        st.subheader("🏢 High-Level Discipline Stream Overview")
        
        try:
            df_exams = get_registry_options("TEST_TYPE")
            exams_list = list(df_exams['item_value'].unique()) if not df_exams.empty else ["Mid Term", "Final Exam"]
            df_disc = get_registry_options("DISCIPLINE")
        except Exception:
            exams_list = ["Mid Term", "Final Exam"]
            df_disc = pd.DataFrame()
            
        exam_term = st.selectbox("Select Academic Term Focus:", options=exams_list, key="disc_exam_focus")
        
        if not df_disc.empty:
            discipline_summary = []
            for _, d_row in df_disc.iterrows():
                disc_key = d_row['item_key']
                disc_name = d_row['item_value']
                
                query_str = """
                    SELECT m.marks_obtained, m.total_marks FROM marks m
                    JOIN students s ON m.student_id = s.student_id
                    WHERE s.discipline_key = :disc_key AND m.exam_type = :exam
                """
                
                disc_data = run_query(query_str, {"disc_key": disc_key, "exam": exam_term})
                
                if not disc_data.empty:
                    disc_data['num_obt'] = pd.to_numeric(disc_data['marks_obtained'], errors='coerce')
                    valid_disc_scores = disc_data.dropna(subset=['num_obt'])
                    
                    if not valid_disc_scores.empty:
                        avg_disc_pct = (valid_disc_scores['num_obt'].sum() / valid_disc_scores['total_marks'].sum()) * 100
                        disc_pass = sum(valid_disc_scores['num_obt'] >= (valid_disc_scores['total_marks'] * 0.40))
                        disc_pass_ratio = (disc_pass / len(valid_disc_scores)) * 100
                        
                        discipline_summary.append({
                            "Academic Stream": disc_name,
                            "Total Checked Scripts": len(valid_disc_scores),
                            "Mean Score": f"{avg_disc_pct:.1f}%",
                            "Overall Pass Percentage": f"{disc_pass_ratio:.1f}%"
                        })
                        
            if discipline_summary:
                st.write(f"### Comparative Stream Standings — {exam_term}")
                st.dataframe(pd.DataFrame(discipline_summary), use_container_width=True)
            else:
                st.info("No checked metrics recorded for this term focus criteria.")
        else:
            st.warning("No disciplines configured in the Master Module database framework.")
# ---------------------------------------------------------
# 👥 STUDENT MANAGEMENT MODULE
# ---------------------------------------------------------
elif menu_choice == "Student Management":
    st.title("👥 Student Profile Management & Registration")
    st.info("Register and manage student profiles. Dropdown values are pulled directly from your Configuration Master Module.")

    # 1. Initialize students database schema safely
    execute_db_command("""
        CREATE TABLE IF NOT EXISTS students (
            student_id SERIAL PRIMARY KEY,
            admission_no VARCHAR(50) UNIQUE NOT NULL,
            student_name VARCHAR(150) NOT NULL,
            father_name VARCHAR(150),
            discipline_key VARCHAR(100) NOT NULL,
            class_key VARCHAR(100) NOT NULL,
            section_key VARCHAR(100) NOT NULL,
            session_key VARCHAR(100) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        );
    """)

    # Setup Workspaces: Add Tab and View Tab
    tab_register, tab_directory = st.tabs(["➕ Register New Student", "📋 Student Directory View"])

    with tab_register:
        # 2. Leverage your standalone get_registry_options tool to extract configurations
        try:
            df_disc = get_registry_options("DISCIPLINE")
            df_class = get_registry_options("CLASS")
            df_sec = get_registry_options("SECTION")
            df_sess = get_registry_options("SESSION")
        except Exception as e:
            st.error(f"Failed to access Master Module system registries: {e}")
            st.stop()

        # Create mapping dictionaries: Display Name -> Under-the-hood System Key
        disc_map = {r['item_value']: r['item_key'] for _, r in df_disc.iterrows()} if not df_disc.empty else {}
        class_map = {r['item_value']: r['item_key'] for _, r in df_class.iterrows()} if not df_class.empty else {}
        sec_map = {r['item_value']: r['item_key'] for _, r in df_sec.iterrows()} if not df_sec.empty else {}
        sess_map = {r['item_value']: r['item_key'] for _, r in df_sess.iterrows()} if not df_sess.empty else {}

        if not (disc_map and class_map and sec_map and sess_map):
            st.warning("⚠️ Stop: Please configure your active Disciplines, Classes, Sections, and Sessions in the Master Module before registering profiles.")
        else:
            with st.form("student_profile_entry_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    admission_no = st.text_input("Admission Number (Unique ID Reference):").strip().upper()
                    student_name = st.text_input("Student Full Name:").strip()
                    father_name = st.text_input("Father's Name:").strip()
                    
                with col2:
                    selected_disc = st.selectbox("Select Discipline Faculty:", options=list(disc_map.keys()))
                    selected_class = st.selectbox("Select Academic Placement Year:", options=list(class_map.keys()))
                    selected_sec = st.selectbox("Select Section Cohort Allocation:", options=list(sec_map.keys()))
                    selected_sess = st.selectbox("Select Active Operational Session:", options=list(sess_map.keys()))

                if st.form_submit_button("🚀 Finalize & Register Student Profile", type="primary"):
                    if not admission_no or not student_name:
                        st.error("Admission Number and Student Full Name fields cannot be empty!")
                    else:
                        insert_query = """
                            INSERT INTO students (admission_no, student_name, father_name, discipline_key, class_key, section_key, session_key, is_active)
                            VALUES (:adm, :name, :father, :disc, :class, :sec, :sess, TRUE)
                            ON CONFLICT (admission_no) DO UPDATE SET
                                student_name = EXCLUDED.student_name,
                                father_name = EXCLUDED.father_name,
                                discipline_key = EXCLUDED.discipline_key,
                                class_key = EXCLUDED.class_key,
                                section_key = EXCLUDED.section_key,
                                session_key = EXCLUDED.session_key,
                                is_active = TRUE;
                        """
                        try:
                            run_update(insert_query, {
                                "adm": admission_no,
                                "name": student_name,
                                "father": father_name,
                                "disc": disc_map[selected_disc],
                                "class": class_map[selected_class],
                                "sec": sec_map[selected_sec],
                                "sess": sess_map[selected_sess]
                            })
                            st.success(f"🎉 Success: Student record '{student_name}' has been created under ID {admission_no}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database sync operation failed: {e}")

    with tab_directory:
        st.subheader("🔍 Filter Active Student Roster")
        
        # Simple Search Bar
        search_term = st.text_input("Search student by name or admission number:").strip().upper()
        
        # Isolated SQL query string to eliminate nested formatting issues
        view_query = """
            SELECT 
                s.admission_no AS "Admission No",
                s.student_name AS "Student Name",
                s.father_name AS "Father Name",
                m_disc.item_value AS "Discipline",
                m_class.item_value AS "Class",
                m_sec.item_value AS "Section",
                m_sess.item_value AS "Session"
            FROM students s
            LEFT JOIN master_registry m_disc ON s.discipline_key = m_disc.item_key AND m_disc.item_type = 'DISCIPLINE'
            LEFT JOIN master_registry m_class ON s.class_key = m_class.item_key AND m_class.item_type = 'CLASS'
            LEFT JOIN master_registry m_sec ON s.section_key = m_sec.item_key AND m_sec.item_type = 'SECTION'
            LEFT JOIN master_registry m_sess ON s.session_key = m_sess.item_key AND m_sess.item_type = 'SESSION'
            WHERE s.is_active = TRUE
       # Ensure the multi-line query string is completely closed here
        view_query = """
            SELECT 
                s.admission_no, 
                s.student_name, 
                s.father_name
            FROM students s
            LEFT JOIN master_registry m_sess 
                ON s.session_key = m_sess.item_key 
                AND m_sess.item_type = 'SESSION'
            WHERE s.is_active = TRUE
        """ # <--- This closes the SQL query cleanly so your Python code can run safely below it
        
        params = {}
        if search_term:
            view_query += " AND (UPPER(s.student_name) LIKE :term OR UPPER(s.admission_no) LIKE :term)"
            params["term"] = f"%{search_term}%"
            
        view_query += " ORDER BY s.admission_no DESC"
        
        try:
            students_df = run_query(view_query, params)
            if not students_df.empty:
                st.dataframe(students_df, use_container_width=True)
                
                # Management Option: Deactivate a profile entry
                st.markdown("---")
                st.subheader("🗑️ Administrative Maintenance")
                remove_id = st.text_input("Enter Admission Number to remove from active roster:").strip().upper()
                if st.button("Deactivate Student Profile", type="secondary"):
                    if remove_id:
                        execute_db_command("UPDATE students SET is_active = FALSE WHERE admission_no = :adm", {"adm": remove_id})
                        st.success(f"Student profile {remove_id} marked inactive.")
                        st.rerun()
            else:
                st.info("No matching student profile records found in the database.")
        except Exception as e:
            st.error(f"Error displaying student summary ledger: {e}")
