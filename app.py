# --- LINE 1: ALL IMPORTS MUST BE HERE ---
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os
import base64
import datetime
from sqlalchemy import create_engine, text
import streamlit.components.v1 as components

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Concordia Academic Analytics")

# --- INITIALIZE GLOBAL IMAGES AND LOGOS ---
logo_filename = "logo.png"

# 1. Always initialize the variable to prevent NameError/UnboundLocalError
logo_base64 = ""

# 2. Check existence and handle loading
if os.path.exists(logo_filename):
    try:
        with open(logo_filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            # Handle extensions correctly
            ext = os.path.splitext(logo_filename)[1].replace(".", "").lower()
            if ext in ["jpg", "jpeg"]: 
                mime_type = "jpeg"
            elif ext == "png": 
                mime_type = "png"
            else: 
                mime_type = "png" # Default fallback
            
            logo_base64 = f"data:image/{mime_type};base64,{encoded_string}"
    except Exception as e:
        # Log the error to your console so you know why the image failed
        print(f"Error loading logo file: {e}")
        logo_base64 = ""
else:
    print(f"Warning: Logo file '{logo_filename}' not found.")

# --- CORE HELPER FUNCTIONS ---
def apply_filters(df, tab_key):
    st.markdown("### ⚙️ Filter Configuration")
    s_options = sorted(df['session'].unique())
    d_options = sorted(df['discipline'].unique())
    sec_options = sorted(df['section'].unique())
    
    col1, col2 = st.columns(2)
    with col1:
        s = st.multiselect("Session:", s_options, default=s_options, key=f"s_{tab_key}")
        d = st.multiselect("Discipline:", d_options, default=d_options, key=f"d_{tab_key}")
    with col2:
        sec = st.multiselect("Section:", sec_options, default=sec_options, key=f"sec_{tab_key}")
    
    f_df = df.copy()
    f_df = f_df[f_df['session'].isin(s if s else s_options)]
    f_df = f_df[f_df['discipline'].isin(d if d else d_options)]
    f_df = f_df[f_df['section'].isin(sec if sec else sec_options)]
    return f_df

@st.cache_data(ttl=600)
def fetch_analytics_data():
    query = """
        SELECT s.id, s.name, s.section, s.class, s.session, 
               m.subject, m.marks_obtained, m.total_marks, m.exam_type
        FROM students s
        LEFT JOIN marks m ON s.id = m.student_id
    """
    return run_query(query, {})

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

# 🚀 --- SYSTEM SETTINGS: GLOBAL ACADEMIC SESSION TRACKING ---
if "current_session" not in st.session_state:
    st.session_state["current_session"] = "2026-28"  # Default system active session

if "available_sessions" not in st.session_state:
    st.session_state["available_sessions"] = ["2024-26", "2025-27", "2026-28", "2027-29"]


# --- SECURE GATEKEEPER LOGIN CHECK ---
if not st.session_state.logged_in:
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

# ==============================================================================
# --- AUTOMATIC TABLE SETUP ---
# ==============================================================================
def initialize_database():
    with engine.begin() as conn:
        # 1. Create students table with system_type and discipline tracking columns
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                section VARCHAR(100),
                class VARCHAR(100),
                session VARCHAR(50),
                discipline VARCHAR(100),
                status VARCHAR(50) DEFAULT 'ACTIVE',
                system_type VARCHAR(50) DEFAULT 'Annual System'
            );
        """))
        
        # 2. Safe Patch: Force-inject system_type and discipline columns into existing Supabase tables
        try:
            conn.execute(text("""
                ALTER TABLE students 
                ADD COLUMN IF NOT EXISTS system_type VARCHAR(50) DEFAULT 'Annual System';
            """))
        except Exception:
            pass # Skips quietly if the column already exists

        try:
            conn.execute(text("""
                ALTER TABLE students 
                ADD COLUMN IF NOT EXISTS discipline VARCHAR(100);
            """))
        except Exception:
            pass # Skips quietly if the column already exists
        
        # 3. Create teachers table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_teachers (
                teacher_id SERIAL PRIMARY KEY,
                teacher_name VARCHAR(255) NOT NULL UNIQUE,
                phone_number VARCHAR(50),
                email_address VARCHAR(255),
                status VARCHAR(50) DEFAULT 'ACTIVE'
            );
        """))

        # 4. Create allocations table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS academic_allocations (
                allocation_id SERIAL PRIMARY KEY,
                session_term VARCHAR(50) NOT NULL,
                class_level VARCHAR(100) NOT NULL,
                section_name VARCHAR(100) NOT NULL,
                subject_title VARCHAR(100) NOT NULL,
                assigned_teacher_name VARCHAR(255) REFERENCES system_teachers(teacher_name) ON DELETE CASCADE,
                is_class_incharge VARCHAR(10) DEFAULT 'No',
                UNIQUE(session_term, class_level, section_name, subject_title)
            );
        """))
        
        # 5. Create marks table
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
        
        # 6. Create attendance table
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

# ==============================================================================
# --- DATABASE COMMAND UTILITIES ---
# ==============================================================================
def run_query(query, params=None):
    """
    Safely executes a read query. 
    Handles cases where query might be passed as a tuple due to calling errors.
    """
    if params is None:
        params = {}

    # 1. Defensive check: If query is a tuple, extract the string
    if isinstance(query, tuple):
        # Assuming the first element is the string query and second is params
        # This handles cases where you accidentally passed (query, params)
        if len(query) >= 2 and isinstance(query[0], str):
            params = query[1]
            query = query[0]
        else:
            query = str(query[0])

    # 2. Proceed with string operations safely
    clean_query = query.replace("[Session Name]", '"Session Name"')
    
    try:
        with engine.connect() as conn:
            return pd.read_sql_query(text(clean_query), conn, params=params)
    except Exception as original_error:
        # Retry logic: Attempt to repair missing columns/tables
        try:
            with engine.begin() as txn_conn:
                # Ensure base tables exist
                txn_conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS academic_sessions (
                        id SERIAL PRIMARY KEY,
                        session_name VARCHAR(50) UNIQUE NOT NULL,
                        status VARCHAR(20) DEFAULT 'ACTIVE'
                    );
                """))
                
                # Patch columns if they are missing
                for table_name in ["academic_sessions", "system_sections", "exam_cycles"]:
                    try:
                        txn_conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ACTIVE';"))
                    except Exception:
                        pass 

            with engine.connect() as retry_conn:
                return pd.read_sql_query(text(clean_query), retry_conn, params=params)
        except Exception:
            raise original_error

def execute_db_command(query, params=None):
    """Safely executes write operations."""
    if params is None:
        params = {}
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params)
    except Exception as e:
        raise RuntimeError(f"Database write execution failed: {str(e)}")

# ==============================================================================
# SIDEBAR NAVIGATION MODULE 
# ==============================================================================
menu_choice = st.sidebar.radio(
    "Go To Module:",
    [
        "📊 Home Dashboard", 
        "➕ Add Students", 
        "📝 Academic Exam Marks Entry",      
        "📅 Attendance Entry Management",    
        "📋 Daily Attendance Report",
        "📋 Section Summary Report", 
        "📈 Multi-Test Progress Report", 
        "🪪 Student Result Cards", 
        "👨‍🏫 Teacher Management",  
        "📈 Academic Analysis Reports",
        "👥 Student Operations Management",
        "⚙️ Settings"
    ]
)

# ==============================================================================
# --- SYSTEM CONTROL: UNIFIED MULTI-LEVEL SUBJECT MASTER CONFIGURATIONS ---
# ==============================================================================
CLASS_SUBJECTS_MASTER_MAP = {
    "11th": {
        "MEDICAL": ["English", "Urdu", "Physics", "Chemistry", "Biology", "Islamic Studies", "T_Quran"],
        "ENGINEERING": ["English", "Urdu", "Physics", "Chemistry", "Mathematics", "Islamic Studies", "T_Quran"],
        "ICS_PHYSICS": ["English", "Urdu", "Physics", "Computer Science", "Mathematics", "Islamic Studies", "T_Quran"],
        "ICS_STATS": ["English", "Urdu", "Statistics", "Computer Science", "Mathematics", "Islamic Studies", "T_Quran"],
        "HUMANITIES": ["English", "Urdu", "Education", "Computer", "Isl_Elc", "Islamic Studies", "T_Quran"],
        "COMMERCE": ["English", "Urdu", "Islamic Studies", "Principles of Accounting", "Principles of Commerce", "Principles of Economics", "Business Mathematics", "T_Quran"]
    },
    "12th": {
        "MEDICAL": ["English", "Urdu", "Physics", "Chemistry", "Biology", "Pak_St", "T_Quran"],
        "ENGINEERING": ["English", "Urdu", "Physics", "Chemistry", "Mathematics", "Pak_St", "T_Quran"],
        "ICS_PHYSICS": ["English", "Urdu", "Physics", "Computer Science", "Mathematics", "Pak_St", "T_Quran"],
        "ICS_STATS": ["English", "Urdu", "Statistics", "Computer Science", "Mathematics", "Pak_St", "T_Quran"],
        "HUMANITIES": ["English", "Urdu", "Education", "Computer", "Isl_Elc", "Pak_St", "T_Quran"],
        "COMMERCE": ["English", "Urdu", "Pak_St", "Principles of Accounting", "Banking", "Commercial Geography", "Business Statistics", "T_Quran"]
    },
    "Semester 1": {
        "INFORMATION_TECHNOLOGY": ["Information Technology", "Office Automation", "Networking", "C-Programming", "Operating System", "Project"]
    },
    "Semester 2": {
        "INFORMATION_TECHNOLOGY": ["Data Base System", "Video Editing", "Web Development Essential", "Graphics Design", "Project"]
    },
    "Semester 3": {
        "INFORMATION_TECHNOLOGY": ["English", "Urdu", "Mathematics", "Statistics", "T_Quran", "Islamic_Studies"]
    },
    "Semester 4": {
        "INFORMATION_TECHNOLOGY": ["English", "Urdu", "Mathematics", "Statistics", "T_Quran", "Islamic_Studies"]
    }
}

DISCIPLINE_SECTIONS_MAP = {
    "MEDICAL": {
        "11th": ["MG_BLUE", "MG_WHITE", "MB_BLUE"],
        "12th": ["MQ1", "MQ2", "MK"]
    },
    "ENGINEERING": {
        "11th": ["EG_BLUE", "EB_BLUE"],
        "12th": ["EQ", "EK"]
    },
    "ICS (PHYSICS)": {
        "11th": ["CG_WHITE", "CG_GREEN", "CB_WHITE", "CB_GREEN"],
        "12th": ["CQ1", "CQ2", "CK1", "CK2"]
    },
    "ICS (STATS)": {
        "11th": ["CG_STATS", "CB_STATS"],
        "12th": ["CQ3", "CK3"]
    },
    "COMMERCE": {
        "11th": ["IG", "IB"],
        "12th": ["IK", "IQ"]
    },
    "HUMANITIES": {
        "11th": ["FB", "FG"],
        "12th": ["FK", "FQ"]
    },
    "INFORMATION_TECHNOLOGY": {
        "Semester 1": ["DIT_B", "DIT_G"],
        "Semester 2": ["DIT_B", "DIT_G"],
        "Semester 3": ["DIT_B", "DIT_G"],
        "Semester 4": ["DIT_B", "DIT_G"]
    }
}

AVAILABLE_DISCIPLINE = list(CLASS_SUBJECTS_MASTER_MAP["11th"].keys())
AVAILABLE_EXAMS = [
    "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "SEND_UP", "MT_5",
    "T_1", "T_2", "T_3", "T_4", "T_5", "T_6", "T_7", "T_8", "T_9", "T_10",
    "HALF_BOOK01", "HALF_BOOK02", "PRE_BOARD", "BISE-11th", "BISE-12th", "PBTE_1", "PBTE_2", "PBTE_3", "PBTE_4"
]
AVAILABLE_MONTHS = ["May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.", "Jan.", "Feb.", "March", "April"]
AVAILABLE_SESSIONS = ["2024-26", "2025-27", "2026-28", "2027-29"]

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
    
    session_options = st.session_state.get("available_sessions", ["2024-26", "2025-27", "2026-28", "2027-29"])
    active_session = st.session_state.get("current_session", "2026-28")
    
    default_index = session_options.index(active_session) if active_session in session_options else 0
        
    discipline_options = ["MEDICAL", "ENGINEERING", "ICS (PHYSICS)", "ICS (STATS)", "COMMERCE", "HUMANITIES"]

    c1, c2 = st.columns(2)
    with c1: 
        selected_session = st.selectbox("🎯 1. Select Session:", session_options, index=default_index, key="add_stu_sess")
    with c2: 
        academic_system = st.radio("🏫 Select Academic System Structure:", ["🗓️ Annual System", "🎓 Semester System"], horizontal=True, key="add_stu_system_type")

    st.markdown("---")

    if academic_system == "🗓️ Annual System":
        c3, c4, c5 = st.columns(3)
        with c3: 
            selected_class = st.selectbox("📚 2. Select Class Level:", ["11th", "12th"], key="add_stu_class")
        with c4: 
            selected_discipline = st.selectbox("🔬 3. Select Discipline:", discipline_options, key="add_stu_disc")
            
        with c5:
            normalized_discipline = (
                selected_discipline.upper()
                .replace(" ", "_")
                .replace("(", "")
                .replace(")", "")
            )
            
            if "PHYSIC" in normalized_discipline:
                normalized_discipline = "ICS_PHYSICS"
            elif "STAT" in normalized_discipline:
                normalized_discipline = "ICS_STATS"

            available_sections = DISCIPLINE_SECTIONS_MAP.get(normalized_discipline, {}).get(selected_class, [])
            cleaned_sections = [str(sec).strip().upper() for sec in available_sections]
            
            if cleaned_sections:
                selected_section = st.selectbox("📋 4. Select Target Section:", cleaned_sections, key="add_stu_sec_annual")
            else:
                selected_section = st.text_input("📋 4. Enter Target Section Manually:", value="CK2", key="add_stu_sec_annual_manual").strip().upper()
    
    else:
        c3, c4 = st.columns(2)
        with c3: 
            selected_class = st.selectbox("⏳ 2. Select Semester:", ["Semester 1", "Semester 2", "Semester 3", "Semester 4"], key="add_stu_semester")
        
        selected_discipline = "INFORMATION_TECHNOLOGY"
        available_sections = DISCIPLINE_SECTIONS_MAP.get(selected_discipline, {}).get(selected_class, ["DIT_B", "DIT_G"])
        cleaned_sections = [str(sec).strip().upper() for sec in available_sections]
        
        with c4:
            if cleaned_sections:
                selected_section = st.selectbox("📋 3. Select Target Section:", cleaned_sections, key="add_stu_sec_semester")
            else:
                selected_section = st.text_input("📋 3. Enter Target Section Manually:", value="DIT_B", key="add_stu_sec_semester_manual").strip().upper()

    st.markdown("---")
    
    workflow_mode = st.radio(
        "⚙️ Select Registration Workflow Mode:", 
        ["👤 Single Student Registration", "📤 Bulk Upload (Excel/CSV)", "🛠️ Manage Existing Students (Edit/Delete)"], 
        horizontal=True, 
        key="add_stu_workflow_choice"
    )
    st.markdown("---")

    # ====================================================================================
    # WORKFLOW A: SINGLE STUDENT REGISTRATION
    # ====================================================================================
    if workflow_mode == "👤 Single Student Registration":
        st.subheader(f"👤 Enter Student Profile Particulars — Section ({selected_section})")
        
        with st.form("interactive_student_addition_form", clear_on_submit=True):
            form_row1_left, form_row1_right = st.columns(2)
            with form_row1_left:
                input_roll_number = st.text_input("🆔 Class Roll Number / Student ID*")
            with form_row1_right:
                input_student_name = st.text_input("👤 Student Name Full Identity*")
                
            input_status = st.selectbox("📌 Enrollment Registration Status:", ["ACTIVE", "PENDING", "LEAVE"])
                
            st.markdown("##")
            submit_registration_btn = st.form_submit_button("💾 Commit Profile to Institutional Database Ledger", type="primary", use_container_width=True)
            
            if submit_registration_btn:
                if not input_roll_number.strip() or not input_student_name.strip():
                    st.error("❌ Processing Blocked: Roll Number and Student Name cannot be left blank.")
                elif not input_roll_number.strip().isdigit():
                    st.error("❌ Validation Failed: Roll Number / Student ID must be numerical digits only.")
                else:
                    try:
                        clean_id = int(input_roll_number.strip())
                        clean_name = input_student_name.strip().upper()
                        clean_system_type = academic_system.replace("🗓️ ", "").replace("🎓 ", "").strip()
                        
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO students (id, name, class, section, session, status, system_type)
                                VALUES (:id, :name, :class, :section, :session, :status, :system_type)
                            """), {
                                "id": clean_id,
                                "name": clean_name,
                                "class": selected_class,
                                "section": selected_section,
                                "session": selected_session,
                                "status": input_status,
                                "system_type": clean_system_type
                            })
                        
                        st.success(f"🎉 Success! Profile for {clean_name} has been formally registered under {clean_system_type}.")
                        st.balloons()
                    except Exception as db_err:
                        st.error(f"❌ Database Exception Triggered: Verify that Roll Number ID `{input_roll_number}` isn't already assigned. Details: {db_err}")

    # ====================================================================================
    # WORKFLOW B: BULK EXCEL/CSV IMPORT ENGINE
    # ====================================================================================
    elif workflow_mode == "📤 Bulk Upload (Excel/CSV)":
        st.subheader(f"📤 Bulk Import Rosters — Section ({selected_section})")
        st.info("💡 Important Sheet Guidelines: Your file columns must include exactly **'ID'** and **'Name'** headings.")
        
        uploaded_bulk_file = st.file_uploader("Upload roster matrix spreadsheet", type=["csv", "xlsx"], key="bulk_student_file_uploader")
        
        if uploaded_bulk_file is not None:
            try:
                if uploaded_bulk_file.name.endswith(".csv"):
                    bulk_df = pd.read_csv(uploaded_bulk_file)
                else:
                    bulk_df = pd.read_excel(uploaded_bulk_file)
                
                bulk_df.columns = [str(col).strip().upper() for col in bulk_df.columns]
                
                if 'ID' not in bulk_df.columns or 'NAME' not in bulk_df.columns:
                    st.error("❌ Template Validation Error! The upload requires a data structure mapped with clear 'ID' and 'Name' headings.")
                else:
                    st.markdown("##### 📊 Document Sample Row Preview")
                    st.dataframe(bulk_df.head(8), use_container_width=True)
                    
                    if st.button("🚀 Process & Batch Insert System Records", type="primary", use_container_width=True):
                        success_count = 0
                        error_count = 0
                        clean_system_type = academic_system.replace("🗓️ ", "").replace("🎓 ", "").strip()
                        
                        for index, row in bulk_df.iterrows():
                            raw_id = str(row['ID']).strip().split('.')[0]
                            raw_name = str(row['NAME']).strip().upper()
                            
                            if raw_id.isdigit() and raw_name != "":
                                try:
                                    with engine.begin() as conn:
                                        conn.execute(text("""
                                            INSERT INTO students (id, name, class, section, session, status, system_type)
                                            VALUES (:id, :name, :class, :section, :session, 'ACTIVE', :system_type)
                                        """), {
                                            "id": int(raw_id),
                                            "name": raw_name,
                                            "class": selected_class,
                                            "section": selected_section,
                                            "session": selected_session,
                                            "system_type": clean_system_type
                                        })
                                    success_count += 1
                                except Exception:
                                    error_count += 1
                            else:
                                error_count += 1
                                
                        st.success(f"🎉 Import complete! Successfully processed and committed {success_count} student records to database under {clean_system_type}.")
                        if error_count > 0:
                            st.warning(f"⚠️ Skipped {error_count} row records because of primary key ID duplication conflicts or empty cells.")
                        st.balloons()
                        
            except Exception as read_err:
                st.error(f"❌ Failed to parse data file payload accurately: {read_err}")

    # ====================================================================================
    # WORKFLOW C: UNIFIED MANAGE & PROMOTION HUB
    # ====================================================================================
    else:
        st.markdown("### 🛠️ Student Records Administrative Hub")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            global_session = st.selectbox("1️⃣ Select Operational Session:", ["2024-26", "2025-27", "2026-28", "2027-29"])
        with col_g2:
            global_system = st.selectbox("2️⃣ Select Academic System:", ["🗓️ Annual System", "🎓 Semester System"])
            clean_global_system = global_system.replace("🗓️ ", "").replace("🎓 ", "").strip()

        st.markdown("---")
        
        left_branch_col, right_branch_col = st.columns([1.1, 0.9])
        
        with left_branch_col:
            st.markdown("#### 👤 Single Student Operations")
            search_id = st.text_input("🔍 Search Student by Unique ID:", key="single_search_id_input").strip()
            
            if search_id:
                if not search_id.isdigit():
                    st.error("❌ Invalid Format: Student ID entries must be numbers only.")
                else:
                    try:
                        with engine.connect() as connection:
                            stu_query = text("""
                                SELECT id, name, class, section, session, status, system_type 
                                FROM students WHERE id = :id
                            """)
                            stu_df = pd.read_sql(stu_query, connection, params={"id": int(search_id)})
                        
                        if stu_df.empty:
                            st.warning(f"⚠️ No active profile record found matching Student ID: {search_id}")
                        else:
                            student = stu_df.iloc[0]
                            
                            st.markdown(f"""
                            > **Identity:** {str(student['name']).upper()}  
                            > 🏫 **Placement:** Class {student['class']} | Section {student['section']}  
                            > 📊 **Status:** `{student['status']}` | System: {student['system_type']}
                            """)
                            
                            st.markdown("##### ⚙️ Apply Target Field Mutations")
                            
                            all_sessions = ["2024-26", "2025-27", "2026-28", "2027-29"]
                            all_sections = ["MG_BLUE", "MG_WHITE", "MB_BLUE", "DIT_B", "DIT_G", "CQ1", "CK1"]
                            
                            col_m1, col_m2 = st.columns(2)
                            with col_m1:
                                mutation_session = st.selectbox("🎯 Target Session:", all_sessions, index=all_sessions.index(student['session']) if student['session'] in all_sessions else 0)
                            with col_m2:
                                mutation_section = st.selectbox("🎯 Target Section:", all_sections, index=all_sections.index(student['section']) if student['section'] in all_sections else 0)
                                
                            mutation_system = st.selectbox("🎯 Target Academic System:", ["Annual System", "Semester System"], 
                                                           index=0 if student['system_type'] == "Annual System" else 1)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            btn_col1, btn_col2, btn_col3 = st.columns(3)
                            
                            with btn_col1:
                                if st.button("🔄 Session Change", use_container_width=True):
                                    with engine.begin() as conn:
                                        conn.execute(text("UPDATE students SET session = :session WHERE id = :id"), {"session": mutation_session, "id": student['id']})
                                    st.success("Session Updated Successfully!")
                                    st.rerun()
                                    
                                if st.button("🚪 Left", use_container_width=True, type="secondary"):
                                    with engine.begin() as conn:
                                        conn.execute(text("UPDATE students SET status = 'LEFT' WHERE id = :id"), {"id": student['id']})
                                    st.warning("Profile flagged as 'LEFT'.")
                                    st.rerun()
                                    
                            with btn_col2:
                                if st.button("📐 Section Change", use_container_width=True):
                                    with engine.begin() as conn:
                                        conn.execute(text("UPDATE students SET section = :section WHERE id = :id"), {"section": mutation_section, "id": student['id']})
                                    st.success("Section Updated Successfully!")
                                    st.rerun()
                                    
                                if st.button("🟢 Re-Active", use_container_width=True):
                                    with engine.begin() as conn:
                                        conn.execute(text("UPDATE students SET status = 'ACTIVE' WHERE id = :id"), {"id": student['id']})
                                    st.success("Enrollment status set back to ACTIVE.")
                                    st.rerun()
                                    
                            with btn_col3:
                                if st.button("🎓 System Change", use_container_width=True):
                                    with engine.begin() as conn:
                                        conn.execute(text("UPDATE students SET system_type = :system_type WHERE id = :id"), {"system_type": mutation_system, "id": student['id']})
                                    st.success("Academic System Structure Updated!")
                                    st.rerun()
                    except Exception as e:
                        st.error(f"Error executing operation: {e}")

        with right_branch_col:
            st.markdown("#### 👥 Bulk Actions / Section Promotion")
            st.info("Your remaining functional block modules connect from here.")

        # ====================================================================================
        # RIGHT OPERATIONS BRANCH: SECTION SECTIONING & PROMOTION BATCH RUNNER
        # ====================================================================================
        with right_branch_col:
            st.markdown("#### 🏢 Section-Based Batch Promotion")
            
            # Query sections conditionally based on the global top-tier controls
            try:
                with engine.connect() as connection:
                    sec_query = text("""
                        SELECT DISTINCT section FROM students 
                        WHERE session = :sess AND system_type = :syst AND status = 'ACTIVE'
                    """)
                    available_sections = [r[0] for r in connection.execute(sec_query, {"sess": global_session, "syst": clean_global_system}).fetchall()]
            except Exception:
                available_sections = []
                
            if not available_sections:
                st.info(f"ℹ️ No batch segments found matching: {global_session} | Track: {clean_global_system}")
            else:
                source_section = st.selectbox("📁 Select Source Section to Process:", available_sections)
                
                try:
                    with engine.connect() as connection:
                        count_res = connection.execute(text("""
                            SELECT COUNT(*) FROM students 
                            WHERE session = :sess AND system_type = :syst AND section = :sec AND status = 'ACTIVE'
                        """), {"sess": global_session, "syst": clean_global_system, "sec": source_section}).fetchone()
                        batch_count = count_res[0] if count_res else 0
                except Exception:
                    batch_count = 0
                    
                st.metric(label="👥 Active Group Size Selected:", value=f"{batch_count} Students")
                
                if batch_count > 0:
                    st.markdown("##### 🚀 Promoted Destination Targets")
                    
                    target_classes_list = [str(i) for i in range(1, 13)] + ["Graduated"]
                    
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        promo_target_class = st.selectbox("🎓 Promoted To Class:", target_classes_list, index=11)  # Default index points directly to class 12th
                    with col_p2:
                        try:
                            with engine.connect() as conn:
                                target_sections_list = [r[0] for r in conn.execute(text("SELECT section_name FROM system_sections")).fetchall()]
                        except Exception:
                            target_sections_list = ["A", "B", "C"]
                        promo_target_section = st.selectbox("📐 Target Section Placement:", target_sections_list)
                        
                    if st.button("🚀 Process Batch Promotion Sequence", type="primary", use_container_width=True):
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE students 
                                    SET class = :target_class, section = :target_section
                                    WHERE session = :sess AND system_type = :syst AND section = :src_sec AND status = 'ACTIVE'
                                """), {
                                    "target_class": promo_target_class,
                                    "target_section": promo_target_section,
                                    "sess": global_session,
                                    "syst": clean_global_system,
                                    "src_sec": source_section
                                })
                            st.success(f"🎉 Success! Promoted {batch_count} students to Class {promo_target_class} - {promo_target_section}!")
                            st.balloons()
                            st.rerun()
                        except Exception as promo_err:
                            st.error(f"Batch execution exception: {promo_err}")

# ====================================================================================
# MODULE 1: ACADEMIC EXAM MARKS ENTRY
# ====================================================================================
elif menu_choice == "📝 Academic Exam Marks Entry":
    st.title("📝 Academic Exam Marks Entry Workspace")
    entry_mode = st.radio("🎯 Select Entry Workflow Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number", "📤 Bulk Excel/CSV Import"], horizontal=True, key="marks_workflow_mode")
    st.markdown("---")

    # --- DYNAMIC FRAMEWORK FETCH FROM DATABASE ---
    try:
        active_cycles_df = run_query("SELECT exam_code FROM exam_cycles WHERE status = 'ACTIVE'")
        all_frameworks = active_cycles_df["exam_code"].tolist() if not active_cycles_df.empty else []
    except Exception:
        all_frameworks = [
            "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "SEND_UP", 
            "HALF_BOOK01", "HALF_BOOK02", "PRE_BOARD", "BISE-11th", "BISE-12th"
        ]

    try:
        session_options = AVAILABLE_SESSIONS
        if "2024-26" in session_options:
            session_options = [s for s in session_options if s != "2024-26"]
        if "2027-29" not in session_options:
            session_options.append("2027-29")
    except NameError:
        session_options = ["2025-27", "2026-28", "2027-29"]

    DISCIPLINE_SUBJECTS_MAP = {
        "MEDICAL_11TH": ["English", "Urdu", "Physics", "Chemistry", "Biology", "Islamic Studies", "T_Quran"],
        "MEDICAL_12TH": ["English", "Urdu", "Physics", "Chemistry", "Biology", "Pak_St", "T_Quran"],
        "ENGINEERING_11TH": ["English", "Urdu", "Physics", "Chemistry", "Mathematics", "Islamic Studies", "T_Quran"],
        "ENGINEERING_12TH": ["English", "Urdu", "Physics", "Chemistry", "Mathematics", "Pak_St", "T_Quran"],
        "ICS_PHYSICS_11TH": ["English", "Urdu", "Physics", "Computer Science", "Mathematics", "Islamic Studies", "T_Quran"],
        "ICS_PHYSICS_12TH": ["English", "Urdu", "Physics", "Computer Science", "Mathematics", "Pak_St", "T_Quran"],
        "ICS_STATISTICS_11TH": ["English", "Urdu", "Statistics", "Computer Science", "Mathematics", "Islamic Studies", "T_Quran"],
        "ICS_STATISTICS_12TH": ["English", "Urdu", "Statistics", "Computer Science", "Mathematics", "Pak_St", "T_Quran"],
        "HUMANITIES_11TH": ["English", "Urdu", "Education", "Computer", "Isl_Elc", "Islamic Studies", "T_Quran"],
        "HUMANITIES_12TH": ["English", "Urdu", "Education", "Computer", "Isl_Elc", "Pak_St", "T_Quran"],
        "COMMERCE_11TH": ["English", "Urdu", "Islamic Studies", "Principles of Accounting", "Principles of Commerce", "Principles of Economics", "Business Mathematics", "T_Quran"],
        "COMMERCE_12TH": ["English", "Urdu", "Pak_St", "Principles of Accounting", "Banking", "Commercial Geography", "Business Statistics", "T_Quran"]
    }

    # Enhanced CSS to cancel out empty collapsed label blocks inside columns
    st.markdown("""
        <style>
            .vertical-align-center {
                display: flex;
                align-items: center;
                height: 40px; /* Matches standard Streamlit text input height exactly */
            }
            /* Strip the native top layout margins from naked collapsed checkboxes */
            div[data-testid="stCheckbox"] {
                margin-top: 8px !important;
                padding-top: 0px !important;
            }
            .main-module-card { 
                background-color: #ffffff; 
                border: 2px solid #cbd5e1; 
                border-radius: 12px; 
                padding: 24px; 
                margin-bottom: 25px; 
            }
        </style>
    """, unsafe_allow_html=True)

    # ====================================================================================
    # WORKFLOW MODE A: COMPLETE SECTION LEDGER ENTRY
    # ====================================================================================
    if entry_mode == "📋 By Complete Section":
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        
        current_role = st.session_state.get('user_role', st.session_state.get('role', 'admin'))
        current_user_id = st.session_state.get('user_id', None)
        
        sel_discipline = "MEDICAL" 
        sel_class = "ALL"
        
        if current_role == 'teacher' and current_user_id is not None:
            teacher_rights = run_query("SELECT subject, section FROM allocations WHERE user_id = :uid", {"uid": int(current_user_id)})
            if not teacher_rights.empty:
                allowed_subs = sorted(list(teacher_rights['subject'].unique()))
                allowed_secs = sorted(list(teacher_rights['section'].unique()))
                
                with c1: sel_session = st.selectbox("Select Session:", session_options, key="entry_sess_t")
                with c2: academic_system = st.selectbox("System Type:", ["Annual System", "Semester System"], key="marks_sys_type_t")
                with c3: sel_class = st.selectbox("Class Level:", ["11th", "12th", "ALL"], key="entry_class_teacher")
                with c4: 
                    st.text_input("Select Discipline:", value="ALLOCATED", disabled=True, key="teacher_disc_disabled")
                    sel_discipline = "TEACHER_MODE"
                with c5: sel_section = st.selectbox("Select Target Section:", allowed_secs, key="entry_sec_filter_teacher")
                with c6: sel_exam = st.selectbox("Exam Cycle:", all_frameworks, index=1, key="entry_exam_sel_t")
                
                if sel_exam == "MATRIC":
                    sel_subject = "OVERALL"
                else:
                    sel_subject = st.selectbox("Select Subject:", allowed_subs, key="entry_sub_filter_teacher")
            else:
                st.warning("🚨 You do not have any active subjects or sections assigned yet.")
                sel_subject, sel_section, sel_session, sel_class, sel_exam = None, None, None, None, None
        else:
            with c1: sel_session = st.selectbox("Select Session:", session_options, key="entry_sess_a")
            with c2: academic_system = st.selectbox("Select Academic System:", ["Annual System", "Semester System"], key="marks_sys_type_a")
            with c3:
                if academic_system == "Annual System":
                    sel_class = st.selectbox("Select Class Level:", ["11th", "12th", "ALL"], key="entry_class_filter_a")
                else:
                    sel_class = st.selectbox("Select Semester Context:", ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester", "ALL"], key="entry_sem_filter_a")

            with c4: 
                if academic_system == "Annual System":
                    discipline_ui_options = ["MEDICAL", "ENGINEERING", "ICS (PHYSICS)", "ICS (STATS)", "COMMERCE", "HUMANITIES"]
                    selected_ui_discipline = st.selectbox("Select Discipline:", discipline_ui_options, key="marks_disc_sel")
                    sel_discipline = selected_ui_discipline.upper().replace(" ", "_").replace("(", "").replace(")", "")
                    if "PHYSIC" in sel_discipline: sel_discipline = "ICS_PHYSICS"
                    elif "STAT" in sel_discipline: sel_discipline = "ICS_STATISTICS"
                else:
                    sel_discipline = "DIPLOMA_IN_IT_DIT"
                    st.text_input("Select Discipline:", value="DIT", disabled=True, key="marks_disc_sel_disabled")

            with c5: 
                valid_sections_list = []
                if academic_system == "Annual System":
                    lookup_key = "ICS (PHYSICS)" if sel_discipline == "ICS_PHYSICS" else ("ICS (STATS)" if sel_discipline == "ICS_STATISTICS" else sel_discipline)
                    try:
                        target_class_levels = ["11th", "12th"] if sel_class == "ALL" else [sel_class]
                        for c_lvl in target_class_levels:
                            sections_found = DISCIPLINE_SECTIONS_MAP.get(lookup_key, {}).get(c_lvl, [])
                            valid_sections_list.extend(sections_found)
                    except NameError:
                        pass
                else:
                    valid_sections_list = ["DIT_G", "DIT_B"]

                valid_sections_list = sorted(list(set(valid_sections_list)))
                if not valid_sections_list:
                    valid_sections_list = ["DIT_G", "DIT_B"] if academic_system == "Semester System" else ["MG_BLUE", "EG_BLUE", "CG_WHITE"]
                
                sel_section = st.selectbox("Select Target Section:", valid_sections_list, key="entry_sec_filter_a")

            with c6: sel_exam = st.selectbox("Exam Cycle:", all_frameworks, index=1, key="entry_exam_sel_a")

            if sel_exam == "MATRIC":
                sel_subject = "OVERALL"
                st.info("🎓 **MATRIC Macro Entry Mode Active**: Ledger updates mapped directly to record column 'OVERALL'.")
            else:
                if academic_system == "Annual System":
                    if sel_class == "ALL":
                        list_11th = DISCIPLINE_SUBJECTS_MAP.get(f"{sel_discipline}_11TH", [])
                        list_12th = DISCIPLINE_SUBJECTS_MAP.get(f"{sel_discipline}_12TH", [])
                        available_subjects = list(dict.fromkeys(list_11th + list_12th))
                    else:
                        suffix = "_12TH" if sel_class == "12th" else "_11TH"
                        available_subjects = DISCIPLINE_SUBJECTS_MAP.get(f"{sel_discipline}{suffix}", ["English", "Urdu", "Physics"])
                else:
                    if "1st Semester" in sel_class:
                        available_subjects = ["Information Technology", "Office Automation", "Networking", "C-Programming", "Operating System", "Project"]
                    elif "2nd Semester" in sel_class:
                        available_subjects = ["Data Base System", "Video Editing", "Web Development Essential", "Graphics Design", "Project"]
                    else: 
                        available_subjects = ["English", "Urdu", "Mathematics", "Statistics", "T_Quran", "Islamic_Studies"]
                
                sel_subject = st.selectbox("📚 Select Course/Subject to Grade:", available_subjects, key="entry_sub_filter_a")
        
        if sel_subject and sel_section and sel_session and sel_exam:
            default_total_marks = 1200 if sel_exam == "MATRIC" else 100
            max_total_limit = 2000 if sel_exam == "MATRIC" else 200
            
            st.markdown("##### ⚙️ Setup Score Schema Boundaries")
            total_marks = st.number_input("Set Total Marks Scale for this Entry Ledger:", min_value=1, max_value=max_total_limit, value=default_total_marks, key="sec_global_marks")
            
            target_sub_slug = str(sel_subject).strip().upper().replace(" ", "_")
            target_exam = str(sel_exam).strip().upper()

            try:
                roster_df = run_query("""
                    SELECT DISTINCT s.id AS "ID", s.name AS "Student Name", m.marks_obtained AS "Marks"
                    FROM students s
                    LEFT JOIN marks m ON s.id = m.student_id 
                        AND UPPER(TRIM(m.subject)) = :subject
                        AND UPPER(TRIM(m.exam_type)) = :exam
                    WHERE UPPER(TRIM(s.section)) = :section
                      AND UPPER(TRIM(CAST(s.session AS VARCHAR))) = :session
                      AND (s.status IS NULL OR UPPER(TRIM(s.status)) NOT IN ('LEFT', 'INACTIVE', 'DROPOUT'))
                    ORDER BY s.id ASC
                """, {"subject": target_sub_slug, "exam": target_exam, "section": str(sel_section).strip().upper(), "session": str(sel_session).strip()})
                
                if roster_df.empty:
                    st.info(f"💡 No active student records found in Section '{sel_section}' under Session {sel_session}.")
                else:
                    st.markdown(f"##### 📝 Enter Obtained Marks for {sel_section} — {sel_subject} ({sel_exam})")
                    
                    # --- FOCUS SHIFT JAVASCRIPT ENGINE ---
                    st.components.v1.html("""
                        <script>
                            const rootDoc = window.parent.document;
                            rootDoc.addEventListener('keydown', function(event) {
                                const el = rootDoc.activeElement;
                                if (el && el.tagName === 'INPUT' && el.getAttribute('aria-label') && el.getAttribute('aria-label').startsWith('sec_field_m_')) {
                                    if (event.key === 'Tab' || event.key === 'Enter') {
                                        event.preventDefault();
                                        const labelAttr = el.getAttribute('aria-label');
                                        const parts = labelAttr.split('_');
                                        const currentIdx = parseInt(parts[parts.length - 1], 10);
                                        const nextIdx = event.shiftKey ? currentIdx - 1 : currentIdx + 1;
                                        
                                        const targetInput = rootDoc.querySelector(`input[aria-label$='_${nextIdx}']`);
                                        if (targetInput) {
                                            targetInput.focus();
                                            targetInput.select();
                                        }
                                    }
                                }
                            }, true);
                        </script>
                    """, height=0)

                    col_b1, col_b2, col_b3 = st.columns([3, 1, 1])
                    with col_b2:
                        if st.button("🏁 Mark All Absent", use_container_width=True, key=f"bulk_absent_btn_{sel_exam}_{sel_subject}"):
                            for r_idx, r_row in roster_df.iterrows():
                                st.session_state[f"sec_abs_{r_row['ID']}_{target_sub_slug}_{target_exam}"] = True
                                st.session_state[f"sec_nc_{r_row['ID']}_{target_sub_slug}_{target_exam}"] = False
                            st.rerun()
                    with col_b3:
                        if st.button("🚫 Mark All NC", use_container_width=True, key=f"bulk_nc_btn_{sel_exam}_{sel_subject}"):
                            for r_idx, r_row in roster_df.iterrows():
                                st.session_state[f"sec_abs_{r_row['ID']}_{target_sub_slug}_{target_exam}"] = False
                                st.session_state[f"sec_nc_{r_row['ID']}_{target_sub_slug}_{target_exam}"] = True
                            st.rerun()
                    
                    with st.form(f"bulk_marks_form_{sel_exam}_{sel_subject}"):
                        updated_section_scores = {}
                        
                        # LEDGER HEADERS
                        h_cols = st.columns([1.5, 3.5, 3.0, 1.0, 1.0])
                        h_cols[0].caption("🆔 **Roll No**")
                        h_cols[1].caption("👤 **Student Name**")
                        h_cols[2].caption("🔢 **Obtained Marks Input**")
                        h_cols[3].caption("❌ **Absent**")
                        h_cols[4].caption("➖ **NC**")
                        st.markdown("<hr style='margin:2px 0px 10px 0px; padding:0px;'>", unsafe_allow_html=True)
                        
                        # DATA ROWS
                        for idx, row in roster_df.iterrows():
                            student_id = int(row['ID'])
                            student_name = str(row['Student Name']).upper()
                            db_val = str(row['Marks']).strip().upper() if pd.notna(row['Marks']) else ""
                            
                            state_abs_key = f"sec_abs_{student_id}_{target_sub_slug}_{target_exam}"
                            state_nc_key = f"sec_nc_{student_id}_{target_sub_slug}_{target_exam}"
                            state_marks_key = f"sec_mark_in_{student_id}_{target_sub_slug}_{target_exam}"
                            
                            if state_abs_key not in st.session_state: st.session_state[state_abs_key] = (db_val in ['A', 'ABSENT'])
                            if state_nc_key not in st.session_state: st.session_state[state_nc_key] = (db_val == 'NC')
                            
                            chk_absent = st.session_state[state_abs_key]
                            chk_nc = st.session_state[state_nc_key]
                            is_disabled = chk_absent or chk_nc
                            display_score = "A" if chk_absent else ("NC" if chk_nc else ("" if db_val in ['A', 'ABSENT', 'NC'] else db_val))
                            
                            with st.container():
                                r_cols = st.columns([1.5, 3.5, 3.0, 1.0, 1.0])
                                
                                r_cols[0].markdown(f"<div class='vertical-align-center' style='font-family: monospace; font-weight: bold;'>{student_id}</div>", unsafe_allow_html=True)
                                r_cols[1].markdown(f"<div class='vertical-align-center' style='font-size: 0.9rem; font-weight: 500;'>{student_name}</div>", unsafe_allow_html=True)
                                
                                with r_cols[2]:
                                    score_input = st.text_input(
                                        f"sec_field_m_{student_id}_{idx}", 
                                        value=display_score, 
                                        placeholder="Score", 
                                        key=state_marks_key, 
                                        label_visibility="collapsed", 
                                        disabled=is_disabled
                                    )
                                    
                                with r_cols[3]:
                                    st.checkbox("ABS", key=state_abs_key, label_visibility="collapsed")
                                    
                                with r_cols[4]:
                                    st.checkbox("NC", key=state_nc_key, label_visibility="collapsed")
                                    
                            updated_section_scores[student_id] = {"marks": score_input, "abs_key": state_abs_key, "nc_key": state_nc_key}
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.form_submit_button("💾 Save Examination Marks Ledger", type="primary", use_container_width=True):
                            import time
                            for s_id, record in updated_section_scores.items():
                                is_a = st.session_state.get(record["abs_key"], False)
                                is_nc = st.session_state.get(record["nc_key"], False)
                                score_clean = "A" if is_a else ("NC" if is_nc else str(record["marks"]).strip().upper())
                                
                                execute_db_command("DELETE FROM marks WHERE student_id = :s_id AND UPPER(TRIM(subject)) = UPPER(TRIM(:subject)) AND UPPER(TRIM(exam_type)) = UPPER(TRIM(:exam))", {"s_id": int(s_id), "subject": target_sub_slug, "exam": target_exam})
                                if score_clean != "":
                                    execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:s_id, :subject, :exam, :score, :total)", 
                                                      {"s_id": int(s_id), "subject": target_sub_slug, "exam": target_exam, "score": score_clean, "total": float(total_marks)})
                            
                            st.success(f"🎉 Marks ledger for Section {sel_section} recorded successfully!")
                            time.sleep(1.2)
                            st.rerun()
            except Exception as e:
                st.error(f"Database sync issue: {e}")

    # ====================================================================================
    # WORKFLOW MODE B: SINGLE STUDENT ROLL NUMBER ENTRY
    # ====================================================================================
    elif entry_mode == "👤 By Single Student Roll Number":
        st.markdown('<div class="main-module-card">', unsafe_allow_html=True)
        st.subheader("👤 Single Student Marks Record Manager")
        
        sc1, sc2, sc3 = st.columns(3)
        with sc1: s_system = st.selectbox("Academic System:", ["Annual System", "Semester System"], key="single_sys_type")
        with sc2: s_session_sel = st.selectbox("Session Context:", session_options, key="single_sess_type")
        with sc3:
            if s_system == "Annual System":
                s_class_sel = st.selectbox("Class Level:", ["11th", "12th", "ALL"], key="single_class_type")
            else:
                s_class_sel = st.selectbox("Semester Context:", ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester", "ALL"], key="single_class_type")

        single_id = st.text_input("🔍 Enter Student Roll Number / ID:", key="single_marks_id_input")
        
        if single_id and single_id.isdigit():
            query_conds = {"id": int(single_id), "sess": str(s_session_sel).strip()}
            base_sql = "SELECT name, section, session, class FROM students WHERE id = :id AND UPPER(TRIM(CAST(session AS VARCHAR))) = :sess"
            if s_class_sel != "ALL":
                base_sql += " AND UPPER(TRIM(class)) = :cls"
                query_conds["cls"] = str(s_class_sel).strip().upper()
                
            student_info = run_query(base_sql, query_conds)
            
            if student_info.empty:
                st.error(f"❌ Roll number '{single_id}' not found matching Session ({s_session_sel}) and Class ({s_class_sel}).")
            else:
                s_name = student_info['name'].iloc[0].upper()
                s_section = student_info['section'].iloc[0].upper().strip()
                s_session = student_info['session'].iloc[0]
                s_class = str(student_info['class'].iloc[0]).upper().strip()
                
                detected_discipline = "MEDICAL"  
                if s_system == "Annual System":
                    try:
                        for disc_key, class_map in DISCIPLINE_SECTIONS_MAP.items():
                            for cls_level, sections in class_map.items():
                                if s_section in [str(sec).upper().strip() for sec in sections]:
                                    detected_discipline = str(disc_key).upper().replace(" ", "_").replace("(", "").replace(")", "")
                                    if "PHYSIC" in detected_discipline: detected_discipline = "ICS_PHYSICS"
                                    elif "STAT" in detected_discipline: detected_discipline = "ICS_STATISTICS"
                                    break
                    except NameError:
                        if any(k in s_section for k in ["EG", "ENG", "ENGINEERING"]): detected_discipline = "ENGINEERING"
                        elif "ICS" in s_section: detected_discipline = "ICS_PHYSICS"
                        elif any(k in s_section for k in ["CG", "COM", "COMMERCE"]): detected_discipline = "COMMERCE"
                        elif any(k in s_section for k in ["HUM", "ARTS"]): detected_discipline = "HUMANITIES"
                
                st.info(f"👤 Student Found: **{s_name}** | Auto-detected Discipline: **{detected_discipline}** | Section: **{s_section}**")
                
                allocated_subjects_df = run_query("""
                    SELECT DISTINCT subject_title FROM academic_allocations 
                    WHERE UPPER(TRIM(class_level)) = :cls AND UPPER(TRIM(section_name)) = :sec ORDER BY subject_title ASC
                """, {"cls": s_class, "sec": s_section})

                if allocated_subjects_df.empty or len(allocated_subjects_df) < 3:
                    if s_system == "Annual System":
                        year_suffix = "12TH" if "12" in str(s_class) else "11TH"
                        subjects_list = DISCIPLINE_SUBJECTS_MAP.get(f"{detected_discipline.upper()}_{year_suffix}", ["English", "Urdu", "Physics"])
                    else:
                        if "1ST" in s_class: subjects_list = ["Information Technology", "Office Automation", "Networking"]
                        else: subjects_list = ["English", "Urdu", "Mathematics"]
                else:
                    subjects_list = allocated_subjects_df['subject_title'].tolist()

                single_exam = st.selectbox("Select Target Test/Exam:", all_frameworks, index=1, key="s_exam_val")
                total_marks_input = st.number_input("Total Marks (Shared Scale):", min_value=1, max_value=2000, value=100, step=1, key="s_total_val")
                
                target_exam_slug = str(single_exam).strip().upper()

                # --- SINGLE PROFILE FOCUS DIRECTION SHIFT JS ---
                st.components.v1.html("""
                    <script>
                        const parentDoc = window.parent.document;
                        parentDoc.addEventListener('keydown', function(e) {
                            const activeNode = parentDoc.activeElement;
                            if (activeNode && activeNode.tagName === 'INPUT' && activeNode.getAttribute('aria-label') && activeNode.getAttribute('aria-label').startsWith('single_field_m_')) {
                                if (e.key === 'Tab' || e.key === 'Enter') {
                                    e.preventDefault();
                                    const labelAttr = activeNode.getAttribute('aria-label');
                                    const segments = labelAttr.split('_');
                                    const currentPos = parseInt(segments[segments.length - 1], 10);
                                    const nextPos = e.shiftKey ? currentPos - 1 : currentPos + 1;
                                    
                                    const destinationNode = parentDoc.querySelector(`input[aria-label$='_${nextPos}']`);
                                    if (destinationNode) {
                                        destinationNode.focus();
                                        destinationNode.select();
                                    }
                                }
                            }
                        }, true);
                    </script>
                """, height=0)

                with st.form(key=f"roll_number_entry_form_{single_id}_{single_exam}"):
                    st.markdown("### 🔢 Marks Evaluation Ledger")
                    
                    updated_scores = {}
                    
                    s_h_cols = st.columns([4.0, 3.0, 1.0, 1.0])
                    s_h_cols[0].caption("📖 **Course Subject**")
                    s_h_cols[1].caption("🔢 **Obtained Marks**")
                    s_h_cols[2].caption("❌ **Absent**")
                    s_h_cols[3].caption("➖ **NC**")
                    st.markdown("<hr style='margin:2px 0px 10px 0px; padding:0px;'>", unsafe_allow_html=True)

                    for idx, subject_name in enumerate(subjects_list):
                        sub_slug = str(subject_name).strip().upper().replace(" ", "_")
                        
                        existing_df = run_query("""
                            SELECT marks_obtained FROM marks 
                            WHERE student_id = :s_id AND UPPER(TRIM(subject)) = :sub AND UPPER(TRIM(exam_type)) = :exam
                        """, {"s_id": int(single_id), "sub": sub_slug, "exam": target_exam_slug})
                        
                        db_score = str(existing_df.iloc[0]['marks_obtained']).strip().upper() if not existing_df.empty else ""
                        
                        s_abs_key = f"s_abs_{single_id}_{sub_slug}_{target_exam_slug}"
                        s_nc_key = f"s_nc_{single_id}_{sub_slug}_{target_exam_slug}"
                        s_mark_key = f"s_mark_in_{single_id}_{sub_slug}_{target_exam_slug}"
                        
                        if s_abs_key not in st.session_state: st.session_state[s_abs_key] = (db_score in ['A', 'ABSENT'])
                        if s_nc_key not in st.session_state: st.session_state[s_nc_key] = (db_score == 'NC')
                        
                        chk_abs = st.session_state[s_abs_key]
                        chk_nc = st.session_state[s_nc_key]
                        is_dis = chk_abs or chk_nc
                        display_val = "A" if chk_abs else ("NC" if chk_nc else ("" if db_score in ['A', 'ABSENT', 'NC'] else db_score))
                        
                        with st.container():
                            s_cols = st.columns([4.0, 3.0, 1.0, 1.0])
                            
                            s_cols[0].markdown(f"<div class='vertical-align-center'><b>📖 {subject_name}</b></div>", unsafe_allow_html=True)
                            
                            with s_cols[1]:
                                score_input = st.text_input(
                                    f"single_field_m_{single_id}_{idx}", 
                                    value=display_val, 
                                    placeholder="Score", 
                                    key=s_mark_key, 
                                    label_visibility="collapsed", 
                                    disabled=is_dis
                                )
                                
                            with s_cols[2]:
                                st.checkbox("S_ABS", key=s_abs_key, label_visibility="collapsed")
                                
                            with s_cols[3]:
                                st.checkbox("S_NC", key=s_nc_key, label_visibility="collapsed")
                                
                        updated_scores[sub_slug] = {"marks": score_input, "abs_key": s_abs_key, "nc_key": s_nc_key}

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.form_submit_button("💾 Batch Save Dynamic Student Record Sheet", type="primary", use_container_width=True):
                        import time
                        for sub_slug, record in updated_scores.items():
                            is_a = st.session_state.get(record["abs_key"], False)
                            is_nc = st.session_state.get(record["nc_key"], False)
                            final_score = "A" if is_a else ("NC" if is_nc else str(record["marks"]).strip().upper())
                            
                            execute_db_command("DELETE FROM marks WHERE student_id = :s_id AND UPPER(TRIM(subject)) = :sub AND UPPER(TRIM(exam_type)) = :exam", {"s_id": int(single_id), "sub": sub_slug, "exam": target_exam_slug})
                            if final_score != "":
                                execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:s_id, :sub, :exam, :score, :total)",
                                                  {"s_id": int(single_id), "sub": sub_slug, "exam": target_exam_slug, "score": final_score, "total": float(total_marks_input)})
                        
                        st.success(f"🎉 Performance matrix for Roll Number {single_id} saved successfully!")
                        time.sleep(1.2)
                        st.rerun()
        # This belongs inside the 'Single Entry' block (indented 8 spaces)
        st.markdown('</div>', unsafe_allow_html=True)

    elif entry_mode == "📊 Bulk Excel/CSV Import":
        st.subheader("📊 Bulk Marks Import Portal")
        # Your bulk import code continues here...
# ==============================================================================
# 🗓️ MODULE 2: ATTENDANCE ENTRY MANAGEMENT (Flush against the left wall)
# ==============================================================================
if "Attendance Entry Management" in menu_choice:
    import datetime  
    import pandas as pd
    from sqlalchemy import text
    
    st.title("🗓️ Attendance Entry Management Panel")
    
    att_sub_type = st.segmented_control(
        "Select Attendance Interval Mode:",
        ["📅 Daily Attendance Entry", "👤 By Single Student Roll Number"],
        default="📅 Daily Attendance Entry",
        key="attendance_interval_segmented_control"
    )
    st.markdown("###")

    # 🚀 CLEAN STATE INTEGRATION: Read strictly from settings to prevent duplicates
    session_options = st.session_state.get("available_sessions", ["2024-26", "2025-27", "2026-28", "2027-29"])
    active_session = st.session_state.get("current_session", "2026-28")
    
    # Force the selector index to point right to your active session choice
    default_index = session_options.index(active_session) if active_session in session_options else 0

    # --------------------------------------------------------------------------------
    # WORKFLOW 1: DAILY ATTENDANCE ROSTER SHEET
    # --------------------------------------------------------------------------------
    if att_sub_type == "📅 Daily Attendance Entry":
        st.subheader("📅 Daily Attendance Roster Sheet")
        st.markdown("---")
        
        d1, d2, d3, d4 = st.columns([1.2, 1.3, 1.5, 2.0])
        with d1:
            sel_session = st.selectbox("Select Session:", session_options, index=default_index, key="daily_att_sess")
            
        with d2:
            academic_system = st.selectbox("System Type:", ["Annual System", "Semester System"], key="att_sys_type")
            
        with d3:
            if academic_system == "Annual System":
                class_options = ["11th", "12th"]
                sel_class = st.selectbox("Select Class Level:", class_options, key="daily_att_class")
            else:
                class_options = ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester"]
                sel_class = st.selectbox("Select Semester Context:", class_options, key="daily_att_sem")
                
        with d4:
            section_options = []
            if academic_system == "Annual System":
                try:
                    for discipline, class_map in DISCIPLINE_SECTIONS_MAP.items():
                        sections_list = class_map.get(sel_class, [])
                        section_options.extend(sections_list)
                    section_options = sorted(list(set(section_options)))
                except NameError:
                    if sel_class == "11th":
                        section_options = ["MG_BLUE", "MG_WHITE", "MB_BLUE", "EG_BLUE", "EB_BLUE", "CG_WHITE", "CG_GREEN", "CB_WHITE", "CB_GREEN", "CG_STATS", "CB_STATS", "IG", "IB", "FB", "FG"]
                    else:
                        section_options = ["MQ1", "MQ2", "MK", "EQ", "EK", "CQ1", "CQ2", "CK1", "CK2", "CQ3", "CK3", "IK", "IQ", "FK", "FQ"]
            else:
                section_options = ["DIT_B", "DIT_G"]
                
            sel_section = st.selectbox("Select Target Section:", section_options, key="daily_att_sec")

        row_date_1, _ = st.columns([1.5, 2.5])
        with row_date_1:
            target_date = st.date_input("Attendance Date:", value=datetime.date.today(), key="daily_att_date")

        if sel_section and sel_session:
            roster_df = run_query("""
                SELECT s.id AS "ID", s.name AS "Student Name", d.status AS "SavedStatus"
                FROM students s
                LEFT JOIN daily_attendance d ON s.id = d.student_id AND d.attendance_date = :att_date
                WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:section))
                  AND UPPER(TRIM(CAST(s.session AS VARCHAR))) = UPPER(TRIM(:session))
                  AND (s.status IS NULL OR UPPER(TRIM(s.status)) NOT IN ('LEFT', 'INACTIVE', 'DROPOUT'))
                ORDER BY s.id ASC
            """, {
                "att_date": str(target_date), 
                "section": str(sel_section).strip().upper(), 
                "session": str(sel_session).strip()
            })

            if roster_df.empty:
                st.warning(f"⚠️ No active student profiles found under Section '{sel_section}' inside Session {sel_session}.")
            else:
                st.markdown(f"🔬 **Roster Grid Active:** {sel_class} Section {sel_section} — {target_date.strftime('%d-%b-%Y')} ({len(roster_df)} Students Loaded)")
                
                action_box_col, info_box_col = st.columns([2, 3])
                with action_box_col:
                    master_attendance_toggle = st.checkbox("🟢 Check All as Present (Default)", value=True, key="master_att_switch")
                with info_box_col:
                    st.caption("💡 Uncheck rows manually to mark students Absent (A).")

                with st.form("interactive_daily_attendance_form", clear_on_submit=False):
                    attendance_checkbox_map = {}
                    h_col1, h_col2, h_col3 = st.columns([1, 3, 1])
                    h_col1.markdown("**Roll No / ID**")
                    h_col2.markdown("**Student Name**")
                    h_col3.markdown("**Is Present?**")
                    st.markdown("<hr style='margin:0px; padding:0px; margin-bottom:10px;' />", unsafe_allow_html=True)

                    for idx, row in roster_df.iterrows():
                        col_s1, col_s2, col_s3 = st.columns([1, 3, 1])
                        col_s1.write(f"🆔 `{row['ID']}`")
                        col_s2.write(f"👤 **{row['Student Name']}**")
                        
                        saved_db_status = str(row['SavedStatus']).strip().upper() if row['SavedStatus'] is not None else None
                        if saved_db_status in ['P', 'PRESENT', '1']:
                            initial_checkbox_state = True
                        elif saved_db_status in ['A', 'ABSENT', '0']:
                            initial_checkbox_state = False
                        else:
                            initial_checkbox_state = master_attendance_toggle
                            
                        attendance_checkbox_map[row['ID']] = col_s3.checkbox(
                            "Present", 
                            value=initial_checkbox_state, 
                            key=f"chk_student_{row['ID']}", 
                            label_visibility="collapsed"
                        )

                    st.markdown("###")
                    submit_roster = st.form_submit_button("💾 Save & Lock Daily Attendance Sheet", type="primary", use_container_width=True)
                    
                    if submit_roster:
                        try:
                            with st.spinner("Writing records to database..."):
                                with engine.begin() as conn:
                                    for s_id, checked_present in attendance_checkbox_map.items():
                                        status_code = "P" if checked_present else "A"
                                        
                                        conn.execute(text("""
                                            INSERT INTO daily_attendance (student_id, attendance_date, status) 
                                            VALUES (:s_id, :att_date, :status)
                                            ON CONFLICT (student_id, attendance_date) 
                                            DO UPDATE SET status = EXCLUDED.status
                                        """), {
                                            "s_id": int(s_id), 
                                            "att_date": str(target_date), 
                                            "status": status_code
                                        })
                                    
                            st.success(f"🎉 Attendance roster saved successfully for Section {sel_section}!")
                            st.toast(f"Saved roster for {target_date.strftime('%d-%b-%Y')}", icon="💾")
                            import time
                            time.sleep(1.2)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error encountered during standard write cycle: {e}")

    # --------------------------------------------------------------------------------
    # WORKFLOW 2: SINGLE STUDENT ATTENDANCE MANAGER (DYNAMIC LIVE AGGREGATES)
    # --------------------------------------------------------------------------------
    elif att_sub_type == "👤 By Single Student Roll Number":
        st.subheader("👤 Single Student Attendance Record Manager")
        st.markdown("---")
        
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            s_session_sel = st.selectbox("Select Session Context:", session_options, index=default_index, key="single_att_sess_filter")
        with sc2:
            s_system = st.selectbox("Select Academic System:", ["Annual System", "Semester System"], key="single_att_sys_filter")
        with sc3:
            if s_system == "Annual System":
                s_class_sel = st.selectbox("Select Class Level:", ["11th", "12th", "ALL"], key="single_att_class_filter")
            else:
                s_class_sel = st.selectbox("Select Semester Context:", ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester", "ALL"], key="single_att_filter_sem")

        col_search, _ = st.columns([2, 2])
        with col_search:
            single_id = st.text_input("🔍 Search Student Roll Number / ID:", key="single_att_id_input")
            
        if single_id and single_id.isdigit():
            query_conds = {
                "id": int(single_id), 
                "sess": str(s_session_sel).strip()
            }
            
            base_sql = """
                SELECT name, section, session, class FROM students 
                WHERE id = :id AND UPPER(TRIM(CAST(session AS VARCHAR))) = UPPER(TRIM(:sess))
            """
            
            if s_class_sel != "ALL":
                base_sql += " AND UPPER(TRIM(class)) = :cls"
                query_conds["cls"] = str(s_class_sel).strip().upper()
                
            student_info = run_query(base_sql, query_conds)
            
            if student_info.empty:
                st.error(f"❌ Roll number '{single_id}' not found matching Session ({s_session_sel}) and Class Level ({s_class_sel}).")
            else:
                s_name = student_info['name'].iloc[0].upper()
                s_section = student_info['section'].iloc[0].upper().strip()
                s_session = student_info['session'].iloc[0]
                s_class = student_info['class'].iloc[0]
                
                st.info(f"👤 **Student Profile:** {s_name}  |  **Class/Sem:** {s_class}  |  **Section:** {s_section}  |  **Session:** {s_session}")
                
                st.markdown("##### 📅 Log Single Day Entry")
                ca1, ca2, ca3 = st.columns([2, 1.5, 1.5])
                with ca1:
                    att_date = st.date_input("Target Date:", value=datetime.date.today(), key="single_att_date_pick")
                with ca2:
                    existing_status = run_query("""
                        SELECT status FROM daily_attendance WHERE student_id = :id AND attendance_date = :dt
                    """, {"id": int(single_id), "dt": str(att_date)})
                    
                    default_idx = 0
                    if not existing_status.empty:
                        clean_status = str(existing_status['status'].iloc[0]).strip().upper()
                        default_idx = 0 if clean_status in ["P", "PRESENT"] else 1
                        
                    status_choice = st.selectbox("Status:", ["Present (P)", "Absent (A)"], index=default_idx, key="single_att_status_pick")
                
                with ca3:
                    st.markdown("##") 
                    if st.button("💾 Log Entry", type="primary", use_container_width=True, key="execute_single_att_save"):
                        final_status_code = "P" if "Present" in status_choice else "A"
                        
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO daily_attendance (student_id, attendance_date, status) 
                                    VALUES (:id, :dt, :st)
                                    ON CONFLICT (student_id, attendance_date) 
                                    DO UPDATE SET status = EXCLUDED.status
                                """), {"id": int(single_id), "dt": str(att_date), "st": final_status_code})
                                
                            st.success(f"🎉 Attendance log saved successfully for {s_name}!")
                            import time
                            time.sleep(1.2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error encountered updating record profile: {e}")
                        
                st.markdown("---")
                st.markdown("##### 📊 Dynamically Compiled Monthly Summary (From Daily Logs)")
                
                raw_logs = run_query("""
                    SELECT attendance_date, status FROM daily_attendance WHERE student_id = :id
                """, {"id": int(single_id)})
                
                if raw_logs.empty:
                    st.caption("ℹ️ No active daily logs found to compute monthly values yet.")
                else:
                    raw_logs['attendance_date'] = pd.to_datetime(raw_logs['attendance_date'], errors='coerce')
                    raw_logs = raw_logs.dropna(subset=['attendance_date'])
                    
                    raw_logs['Month'] = raw_logs['attendance_date'].dt.strftime('%B')
                    raw_logs['Month_Num'] = raw_logs['attendance_date'].dt.month
                    raw_logs['Is_Present'] = raw_logs['status'].astype(str).str.strip().str.upper().isin(['P', 'PRESENT', '1'])
                    
                    summary_df = raw_logs.groupby(['Month_Num', 'Month']).agg(
                        Present_Days=('Is_Present', 'sum'),
                        Total_Days=('status', 'count')
                    ).reset_index()
                    
                    summary_df = summary_df.sort_values(by='Month_Num', ascending=False)
                    
                    history_df = summary_df[['Month', 'Present_Days', 'Total_Days']].rename(columns={
                        "Present_Days": "Present Days",
                        "Total_Days": "Total Days"
                    })
                    
                    st.dataframe(history_df, use_container_width=True, hide_index=True)
# ====================================================================================
# MODULE: DAILY ATTENDANCE REPORT (FINAL COMPLETE ROSTER ENGINE)
# ====================================================================================
elif menu_choice == "📋 Daily Attendance Report":
    import datetime
    import pandas as pd
    import streamlit.components.v1 as components
    from io import BytesIO

    st.title("📋 Daily Attendance Report")

    # 1. SETUP (Dynamically linked to Settings)
    try:
        # Queries active sessions directly from your settings configuration table
        session_data = run_query("SELECT session_name FROM sessions WHERE status = 'ACTIVE' ORDER BY session_name DESC")
        session_choices = session_data["session_name"].tolist() if not session_data.empty else []
    except Exception:
        # Emergency fallback if database connection drops or table name varies
        try:
            session_choices = sorted(list(set(AVAILABLE_SESSIONS)))
        except NameError:
            session_choices = ["2025-27", "2026-28", "2027-29"]
            
    # Quick sanity filter: eliminate 2024-26 if it bypassed settings
    if "2024-26" in session_choices:
        session_choices.remove("2024-26")
        
    c1, c2 = st.columns(2)
    with c1:
        report_sessions = st.multiselect("🎯 Select Session Grouping(s):", session_choices, default=[session_choices[0]])
    with c2:
        report_date = st.date_input("🗓️ Target Date:", value=datetime.date.today())

    if not report_sessions:
        st.warning("Please select at least one session.")
        st.stop()

    # 2. DATA FETCHING (Robust)
    session_tuple = tuple(report_sessions) if len(report_sessions) > 1 else (report_sessions[0],)
    
    query = "SELECT id, class, section, status FROM students WHERE session IN :sessions"
    raw_students = run_query(query, {"sessions": session_tuple})
    raw_att = run_query("SELECT student_id, status FROM daily_attendance WHERE attendance_date = :dt", {"dt": report_date.isoformat()})
    raw_alloc = run_query("SELECT section_name, assigned_teacher_name FROM academic_allocations WHERE subject_title = '🌟 CLASS IN-CHARGE (ROLE ONLY)'", {})

    if raw_students.empty:
        st.info("ℹ️ No student records found for the selected sessions.")
    else:
        # DATA PROCESSING
        df = raw_students.merge(raw_att, left_on='id', right_on='student_id', how='left')
        teacher_map = dict(zip(raw_alloc['section_name'].astype(str).str.replace(" ", "").str.upper(), raw_alloc['assigned_teacher_name']))
        
        df['Class'] = df['class'].fillna('Unknown').astype(str).str.upper().str.strip()
        df['Section'] = df['section'].fillna('Unknown').astype(str).str.upper().str.strip()
        df['In_Charge'] = df['Section'].apply(lambda x: teacher_map.get(str(x).replace(" ", "").upper(), '---'))
        df['Attendance_Status'] = df['status_y'].fillna('').astype(str).str.upper().str.strip()

        def classify(row):
            cls, sec = str(row['Class']), str(row['Section'])
            if "11" in cls: 
                return "11th (Girls)" if any(x in sec for x in ["G", "WHITE", "GREEN"]) else "11th (Boys)"
            if "12" in cls: 
                return "12th (Girls)" if any(x in sec for x in ["Q", "G", "WHITE", "GREEN"]) else "12th (Boys)"
            return "Other Tiers (DIT)"
            
        df['Group_Category'] = df.apply(classify, axis=1)

        summary = df.groupby(['Group_Category', 'Section', 'In_Charge']).agg(
            Total=('id', 'count'), 
            Present=('Attendance_Status', lambda x: x.isin(['P', 'PRESENT', '1']).sum()),
            Absent=('Attendance_Status', lambda x: x.isin(['A', 'ABSENT', '0']).sum())
        ).reset_index()

        # 3. HTML PRINT ENGINE
        table_rows = ""
        grand_total = {"Total": 0, "Present": 0, "Absent": 0}
        
        for cat in ["11th (Girls)", "12th (Girls)", "11th (Boys)", "12th (Boys)", "Other Tiers (DIT)"]:
            cat_data = summary[summary['Group_Category'] == cat]
            if cat_data.empty: 
                continue
            
            sub_total = cat_data.agg({'Total': 'sum', 'Present': 'sum', 'Absent': 'sum'})
            grand_total['Total'] += sub_total['Total']
            grand_total['Present'] += sub_total['Present']
            grand_total['Absent'] += sub_total['Absent']
            
            row_span = len(cat_data)
            for i, (_, row) in enumerate(cat_data.iterrows()):
                pct = f"{int((row['Present']/row['Total'])*100)}%" if row['Total'] > 0 else "0%"
                table_rows += f"<tr>"
                if i == 0: 
                    table_rows += f'<td rowspan="{row_span}" style="border:1px solid #000; font-weight:bold; background:#fff;">{cat}</td>'
                table_rows += f'<td>{row["Section"]}</td><td>{row["In_Charge"]}</td><td>{row["Total"]}</td><td>{row["Present"]}</td><td>{row["Absent"]}</td><td>{pct}</td></tr>'
            
            sub_total_pct = f"{int((sub_total['Present']/sub_total['Total'])*100)}%" if sub_total['Total'] > 0 else "0%"
            table_rows += f'<tr style="background:#f9f9f9; font-weight:bold;">' \
                          f'<td colspan="3" style="text-align:left; padding-left:10px;">Sub-Total ({cat})</td>' \
                          f'<td>{sub_total["Total"]}</td><td>{sub_total["Present"]}</td><td>{sub_total["Absent"]}</td>' \
                          f'<td>{sub_total_pct}</td></tr>'

        grand_pct = f"{int((grand_total['Present']/grand_total['Total'])*100)}%" if grand_total['Total'] > 0 else "0%"
        table_rows += f'<tr style="background:#ddd; font-weight:bold; font-size:14px;">' \
                      f'<td colspan="3" style="text-align:left; padding-left:10px;">GRAND TOTAL</td>' \
                      f'<td>{grand_total["Total"]}</td><td>{grand_total["Present"]}</td><td>{grand_total["Absent"]}</td><td>{grand_pct}</td></tr>'

        # Render complete layout
        html_template = f"""
        <html>
        <head>
            <style>
                body {{ font-family: "Times New Roman", serif; padding: 10px; }}
                .header-container {{ display: flex; align-items: center; margin-bottom: 20px; }}
                .logo {{ width: 80px; }}
                .title-group {{ flex-grow: 1; text-align: center; }}
                
                table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
                th, td {{ border: 1px solid #000; padding: 4px; text-align: center; font-size: 11px; }}
                th {{ background: #eee; }}
                
                @media print {{ 
                    @page {{ size: A4 portrait; margin: 10mm; }}
                    .print-btn {{ display: none; }} 
                }}
            </style>
        </head>
        <body>
            <button class="print-btn" onclick="window.print()">🖨️ Print Report</button>
            
            <div class="header-container">
                <img src="https://raw.githubusercontent.com/mirfanshakirpgc-art/Academics-Reports/main/logo.png" class="logo">
                <div class="title-group">
                    <h1 style="font-size: 20px; margin: 0;">CONCORDIA COLLEGE KASUR</h1>
                    <h3 style="font-size: 16px; margin: 0;">Daily Attendance Report - {report_date}</h3>
                </div>
            </div>
            
            <table>
                <tr><th>Class</th><th>Section</th><th>In Charge</th><th>Total</th><th>Present</th><th>Absent</th><th>%age</th></tr>
                {table_rows}
            </table>
            <div style="margin-top: 40px; text-align: right; font-weight:bold;">Principal Signature: ___________</div>
        </body>
        </html>
        """
        components.html(html_template, height=800, scrolling=True)

        # 4. EXCEL EXPORT
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            summary.to_excel(writer, index=False, sheet_name='Attendance')
            ws = writer.sheets['Attendance']
            ws.set_column('A:A', 15)
            ws.set_column('B:B', 12)
            ws.set_column('C:C', 30)
            ws.set_column('D:G', 10)
            ws.set_default_row(25)
            
        st.download_button("📥 Download Excel", output.getvalue(), f"Attendance_{report_date}.xlsx", key="att_excel_dl")
                    
# ====================================================================================                   
# MODULE: 📋 SECTION SUMMARY REPORT (DYNAMIC DB DISCOVERY + ATTENDANCE INTEGRATION)
# ====================================================================================
elif menu_choice == "📋 Section Summary Report":
    import streamlit as st
    import pandas as pd
    import streamlit.components.v1 as components
    import io

    st.title("📋 Section Summary Report Ledger")

    # 🚀 CONNECT DROPDOWN ENGINE TO SYSTEM SESSION STATE Memory Tracking
    session_options = st.session_state.get("available_sessions", ["2024-26", "2025-27", "2026-28", "2027-29"])
    active_session = st.session_state.get("current_session", "2026-28")
    
    # Calculate matching index dynamically so it syncs with the Settings choice
    default_index = session_options.index(active_session) if active_session in session_options else 0

    # --- 1. PARAMETERS CONFIGURATION ---
    # (Update your session selectbox below this to use: options=session_options, index=default_index)
    try:
        session_options = list(AVAILABLE_SESSIONS)
        if "2024-26" in session_options:
            session_options = [s for s in session_options if s != "2024-26"]
    except NameError:
        session_options = ["2025-27", "2026-28", "2027-29"]

    # --- 2. LAYOUT GENERATION & DISCIPLINE ROUTING ---
    col_sess, col_sys, col_class, col_a, col_b, col_c = st.columns(6)
    
    with col_sess:
        selected_session = st.selectbox("Select Session:", session_options, key="summary_session")
        db_session_string = str(selected_session).strip() if selected_session else "2025-27"
        
    with col_sys:
        academic_system = st.selectbox("System Type:", ["Annual System", "Semester System"], key="summary_sys_type")
        
    with col_class:
        if academic_system == "Annual System":
            selected_class = st.selectbox("Select Class Level:", ["11th", "12th"], key="summary_class")
        else:
            selected_class = st.selectbox("Select Semester:", ["Semester 1", "Semester 2", "Semester 3", "Semester 4"], key="summary_class")
        
    with col_a: 
        if academic_system == "Annual System":
            disc_options = ["MEDICAL", "ENGINEERING", "ICS (PHYSICS)", "ICS (STATS)", "COMMERCE", "HUMANITIES"]
            raw_disc = st.selectbox("Select Discipline:", disc_options, key="summary_report_discipline_key")
            sel_disc = str(raw_disc).strip().upper()
        else:
            sel_disc = "INFORMATION_TECHNOLOGY"
            st.info("⚡ DIT System Active")
        
    with col_b: 
        # Pull static sections directly from your mapping dictionary using structural lookup keys
        map_sections = DISCIPLINE_SECTIONS_MAP.get(sel_disc, {}).get(selected_class, [])
        
        # Query active profile records existing in your DB environment
        try:
            sec_lookup_df = run_query("""
                SELECT DISTINCT TRIM(section) as section_name 
                FROM students 
                WHERE UPPER(TRIM(class)) = UPPER(TRIM(:class_val))
                  AND TRIM(session) = TRIM(:sess_val)
                ORDER BY section_name ASC
            """, {"class_val": selected_class, "sess_val": db_session_string})
            
            db_sections = sec_lookup_df["section_name"].dropna().tolist() if not sec_lookup_df.empty else []
        except Exception:
            db_sections = []

        # Intersection: Display sections that exist in the database AND belong to the configuration dictionary map
        if db_sections:
            sec_options = [s for s in db_sections if s in map_sections]
            if not sec_options:
                sec_options = map_sections
        else:
            sec_options = map_sections

        # Safe default fallback boundary checks
        if not sec_options:
            sec_options = ["FK"] if sel_disc == "HUMANITIES" else ["MG_BLUE"]

        # Track widget state seamlessly without unexpected duplication errors
        fixed_key = "summary_report_section_key"
        default_index = 0
        if fixed_key in st.session_state:
            current_value = st.session_state[fixed_key]
            if current_value in sec_options:
                default_index = sec_options.index(current_value)

        sel_sec = st.selectbox(
            "Select Section:", 
            sec_options, 
            index=default_index, 
            key=fixed_key
        )
        
    with col_c: 
        # --- DYNAMIC EVALUATION CYCLE TRACK FETCH ---
        try:
            exam_data = run_query("""
                SELECT exam_code 
                FROM exam_cycles 
                WHERE system_type = :sys_type AND status = 'ACTIVE'
                ORDER BY exam_display_name ASC
            """, {"sys_type": academic_system})
            
            exam_options = exam_data["exam_code"].tolist() if not exam_data.empty else []
        except Exception:
            exam_options = []

        if not exam_options:
            if academic_system == "Semester System":
                exam_options = ["MID_TERM", "FINAL_TERM", "ASSIGNMENT", "QUIZ", "PBTE_1", "PBTE_2", "PBTE_3", "PBTE_4"]
            else:
                exam_options = [
                    "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "MT_5", 
                    "T_1", "T_2", "T_3", "T_4", "T_5", "T_6", "T_7", "T_8", "T_9", "T_10",
                    "HALF_BOOK01", "HALF_BOOK02", "SEND_UP", "PRE_BOARD", "BISE-11th", "BISE-12th"
                ]

        if exam_options:
            sel_exam = st.selectbox("Select Exam Cycle:", exam_options, key="summary_exam")
        else:
            st.warning("⚠️ No active evaluation frameworks registered for this academic track.")
            sel_exam = None

    # --- 3. SUBJECT TRANSLATION GLOSSARY ---
    SHORT_SUBJECTS_MAP = {
        "MATHEMATICS": "MATH", "COMPUTER SCIENCE": "COMP", "COMPUTER": "COMP",
        "PHYSICS": "PHY", "CHEMISTRY": "CHEM", "BIOLOGY": "BIO", "STATISTICS": "STATS", "STATS": "STATS",
        "ENGLISH": "ENG", "URDU": "URDU", "ISLAMIAT": "ISL", "PAKISTAN STUDIES": "PAK.ST",
        "ISL_ETH": "ISL", "T_QURAN": "QURAN", "T_QUANT": "QURAN",
        "PRINCIPLES OF ACCOUNTING": "ACC", "ECONOMICS": "ECO", "COMMERCE": "COMM",
        "ICT": "ICT", "INTRODUCTION TO MS-OFFICE": "OFFICE", "COMPUTER NETWORKS": "NETWORKS",
        "OPERATING SYSTEM": "O.S", "INTRODUCTION TO PROGRAMMING": "PROG",
        "DATA BASE SYSTEM": "DBMS", "VIDEO EDITING": "VIDEO", "WEB DEVELOPMENT ESSENTIAL": "WEB",
        "GRAPHICS DESIGN": "DESIGN", "PROJECT": "PROJ"
    }
    
    # --- 4. DYNAMIC SUBJECT LIST ROUTING ---
    # FIXED: Realigned structural keys with upper dropdown formats to stop breaking test lists
    DISCIPLINE_MAP = {
        "MEDICAL": {
            "11th": ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "BIOLOGY", "ISL_ETH", "T_QURAN"],
            "12th": ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "BIOLOGY", "PAK_ST", "T_QURAN"]
        },
        "ENGINEERING": {
            "11th": ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "MATHEMATICS", "ISL_ETH", "T_QURAN"],
            "12th": ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "MATHEMATICS", "PAK_ST", "T_QURAN"]
        },
        "ICS (PHYSICS)": {
            "11th": ["ENGLISH", "URDU", "PHYSICS", "COMPUTER", "MATHEMATICS", "ISL_ETH", "T_QURAN"],
            "12th": ["ENGLISH", "URDU", "PHYSICS", "COMPUTER", "MATHEMATICS", "PAK_ST", "T_QURAN"]
        },
        "ICS (STATS)": {
            "11th": ["ENGLISH", "URDU", "STATISTICS", "COMPUTER", "MATHEMATICS", "ISL_ETH", "T_QURAN"],
            "12th": ["ENGLISH", "URDU", "STATISTICS", "COMPUTER", "MATHEMATICS", "PAK_ST", "T_QURAN"]
        },
        "COMMERCE": {
            "11th": ["ENGLISH", "URDU", "PRINCIPLES OF ACCOUNTING", "PRINCIPLES OF COMMERCE", "PRINCIPLES OF ECONOMICS", "BUSINESS MATHEMATICS", "ISL_ETH", "T_QURAN"],
            "12th": ["ENGLISH", "URDU", "PRINCIPLES OF ACCOUNTING", "BANKING", "COMMERCIAL GEOGRAPHY", "BUSINESS STATISTICS", "PAK_ST", "T_QURAN"]
        },
        "HUMANITIES": {
            "11th": ["ENGLISH", "URDU", "EDUCATION", "COMPUTER", "ISL_ELC", "ISL_ETH", "T_QURAN"],
            "12th": ["ENGLISH", "URDU", "EDUCATION", "COMPUTER", "ISL_ELC", "PAK_ST", "T_QURAN"]
        },
    }

    if academic_system == "Annual System":
        disc_key = sel_disc.upper().strip()
        subjects = DISCIPLINE_MAP.get(disc_key, {}).get(selected_class, ["ENGLISH", "URDU"])
    else:
        if "Semester 1" in selected_class:
            subjects = ["ICT", "OFFICE AUTOMATION", "NETWORKING", "C-PROGRAMMING", "OPERATING SYSTEM", "PROJECT"]
        else:
            subjects = ["ICT", "OFFICE AUTOMATION"]

    # --- 5. DATABASE INTEGRATION ENGINE ---
    students_df = run_query("""
        SELECT id AS "ID", name AS "Student Name", section AS "Section", class AS "Current Class", status AS "Status"
        FROM students 
        WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) 
          AND TRIM(session) = TRIM(:session_str)
          AND UPPER(TRIM(class)) = UPPER(TRIM(:class))
          AND (status IS NULL OR UPPER(TRIM(status)) != 'LEFT')
        ORDER BY id ASC
    """, {"section": sel_sec, "session_str": db_session_string, "class": selected_class})
    
    if students_df.empty:
        st.info(f"💡 No active profiles found under Section '{sel_sec}' ({selected_class}) for Session {selected_session}.")
    else:
        try:
            marks_df = run_query("""
                SELECT CAST(student_id AS TEXT) as student_key, UPPER(TRIM(subject)) as subject_name, marks_obtained, total_marks
                FROM marks 
                WHERE UPPER(TRIM(exam_type)) = UPPER(TRIM(:exam))
            """, {"exam": sel_exam})
            if not marks_df.empty:
                marks_df["student_key"] = marks_df["student_key"].astype(str).str.strip()
        except Exception:
            marks_df = pd.DataFrame()

        try:
            att_df = run_query("""
                SELECT CAST(student_id AS TEXT) as student_key, status
                FROM daily_attendance
            """, {})
            if not att_df.empty:
                att_df["student_key"] = att_df["student_key"].astype(str).str.strip()
        except Exception:
            att_df = pd.DataFrame()

        # --- 6. PERFORMANCE GRID COMPILER ---
        summary_rows = []
        for _, s_row in students_df.iterrows():
            s_id = str(s_row["ID"]).strip()
            s_status = s_row["Status"] if pd.notna(s_row["Status"]) else "ACTIVE"
            
            entry = {
                "ID": s_row["ID"], 
                "Student Name": s_row["Student Name"], 
                "Section": s_row["Section"], 
                "Class": s_row["Current Class"],
                "Status": s_status
            }
            
            obtained_total = 0.0
            max_total = 0.0
            has_valid_scores = False  
            
            for sub in subjects:
                sub_upper = sub.upper().strip()
                short_sub = SHORT_SUBJECTS_MAP.get(sub_upper, sub_upper[:4])
                
                alias_list = [sub_upper]
                if "STAT" in sub_upper: alias_list.extend(["STATISTICS", "STATS"])
                elif "PHYS" in sub_upper: alias_list.extend(["PHYSICS"])
                elif "COMP" in sub_upper: alias_list.extend(["COMPUTER SCIENCE", "COMPUTER", "INTRODUCTION TO MS-OFFICE"])
                elif "QURAN" in sub_upper or "QUANT" in sub_upper: alias_list.extend(["T_QURAN", "QURAN", "T_QUANT"])
                
                if not marks_df.empty:
                    sub_match = marks_df[
                        (marks_df["student_key"] == s_id) & 
                        (marks_df["subject_name"].isin(alias_list))
                    ]
                else:
                    sub_match = pd.DataFrame()
                
                if not sub_match.empty:
                    val = str(sub_match["marks_obtained"].iloc[0]).strip().upper()
                    tot = float(sub_match["total_marks"].iloc[0]) if pd.notna(sub_match["total_marks"].iloc[0]) else 100.0
                    
                    if val == "NC":
                        entry[short_sub] = "NC"
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

            if has_valid_scores:
                entry["Total (Obt)"] = int(obtained_total)
                entry["Total Max"] = int(max_total)
            else:
                entry["Total (Obt)"] = "-"
                entry["Total Max"] = "-"
                
            if not att_df.empty:
                st_att_logs = att_df[att_df["student_key"] == s_id]
                if not st_att_logs.empty:
                    total_days = len(st_att_logs)
                    present_days = len(st_att_logs[st_att_logs["status"].str.strip().str.upper().isin(["P", "PRESENT"])])
                    pct = (present_days / total_days) * 100 if total_days > 0 else 100.0
                    entry["Attendance"] = f"{int(pct)}%"
                else:
                    entry["Attendance"] = "100%"
            else:
                entry["Attendance"] = "100%"
                
            summary_rows.append(entry)
            
        final_report_df = pd.DataFrame(summary_rows)
        
        # --- Excel Payload Compiler Hub ---
        excel_export_df = final_report_df.copy()
        
        short_subject_labels = [SHORT_SUBJECTS_MAP.get(sub.upper().strip(), sub[:4]) for sub in subjects]
        for col_lbl in short_subject_labels:
            if col_lbl in excel_export_df.columns:
                excel_export_df[col_lbl] = excel_export_df[col_lbl].apply(
                    lambda cell: int(cell) if isinstance(cell, (int, float)) else cell
                )
        
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            excel_export_df.to_excel(writer, index=False, sheet_name='Performance_Summary')
        excel_data_payload = excel_buffer.getvalue()

        col_download_hook, _ = st.columns([2, 4])
        with col_download_hook:
            st.download_button(
                label="📥 Download Excel Spreadsheet Summary",
                data=excel_data_payload,
                file_name=f"Summary_Report_{sel_sec}_{selected_class}_{db_session_string}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="summary_excel_downloader_widget",
                use_container_width=True
            )
        
        # --- 7. HTML LIVE COMPONENT INTERFACE GENERATOR ---
        thead_subjects_html = "".join([f'<th>{lbl}</th>' for lbl in short_subject_labels])
        
        tbody_rows_html = ""
        for _, row in final_report_df.iterrows():
            st_id = str(row["ID"]).strip()
            current_status = row["Status"]
            
            status_badge = ""
            if current_status == "Re-Active":
                status_badge = " <span style='background: #e1f5fe; color: #0288d1; font-size: 10px; padding: 2px 5px; border-radius: 3px; font-weight: bold;'>RE-JOIN</span>"
            
            old_marks_badges = []
            hidden_marks_df = marks_df[marks_df["student_key"] == st_id] if not marks_df.empty else pd.DataFrame()
            for _, h_row in hidden_marks_df.iterrows():
                h_sub = h_row["subject_name"]
                if h_sub not in [sub.upper().strip() for sub in subjects]:
                    short_h_sub = SHORT_SUBJECTS_MAP.get(h_sub, h_sub[:4])
                    h_val = h_row['marks_obtained']
                    try:
                        h_val = str(int(float(h_val))) if float(h_val).is_integer() else str(h_val)
                    except ValueError:
                        pass
                    old_marks_badges.append(f"{short_h_sub}: {h_val}")
            
            history_str = ""
            if old_marks_badges:
                history_str = f"<br><span style='color: #d35400; font-size: 11px; font-style: italic;'>Dropped ({', '.join(old_marks_badges)})</span>"
            
            row_subjects_cells = ""
            for lbl in short_subject_labels:
                cell_val = row[lbl]
                
                if isinstance(cell_val, (int, float)):
                    cell_str = str(int(cell_val))
                else:
                    cell_str = str(cell_val)
                    
                cell_style = "color: #e74c3c; font-weight: bold;" if cell_str in ["A", "FAIL"] else ("color: #7f8c8d; font-weight: bold;" if cell_str == "NC" else "")
                row_subjects_cells += f'<td style="{cell_style}">{cell_str}</td>'
            
            tbody_rows_html += f"""
            <tr>
                <td>{row['ID']}</td>
                <td style="text-align: left; font-weight: bold; padding-left: 12px;">
                    {row['Student Name']} {status_badge} {history_str}
                </td>
                <td>{row['Section']}</td>
                <td>{row['Class']}</td>
                {row_subjects_cells}
                <td style="font-weight: bold; background-color: #fcfcfc; color: #0066cc;">{row['Attendance']}</td>
                <td style="font-weight: bold; background-color: #fcfcfc;">{row['Total (Obt)']}</td>
                <td style="font-weight: bold; color: #555; background-color: #fcfcfc;">{row['Total Max']}</td>
            </tr>
            """
            
        logo_url = "https://raw.githubusercontent.com/mirfanshakirpgc-art/Academics-Reports/main/logo.png"
        
        analytics_html_payload = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: "Segoe UI", Arial, sans-serif; color: #333; background-color: #fff; margin: 0; padding: 10px; }}
            .report-wrapper-container {{ max-width: 100%; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 6px; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            .action-panel-bar {{ display: flex; gap: 12px; margin-bottom: 22px; }}
            .btn-action {{ padding: 10px 22px; font-weight: bold; font-size: 14px; border: none; border-radius: 4px; cursor: pointer; transition: background 0.2s; }}
            .btn-print {{ background: #222; color: #fff; }}
            .btn-image {{ background: #0066cc; color: #fff; }}
            .btn-action:hover {{ opacity: 0.9; }}
            .header-banner {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #222; padding-bottom: 15px; margin-bottom: 20px; }}
            .header-branding {{ text-align: left; }}
            .inst-title {{ font-size: 24px; font-weight: 800; color: #111; letter-spacing: 0.5px; margin: 0; }}
            .doc-subtitle {{ font-size: 15px; color: #555; margin: 4px 0 0 0; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
            .brand-logo-img {{ max-height: 55px; width: auto; object-fit: contain; }}
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
                        <b>Session:</b> {selected_session}<br>
                        <b>System Framework:</b> {academic_system}<br>
                        <b>Class Level / Scope:</b> {selected_class}<br>
                        <b>Discipline Category:</b> {sel_disc}<br>
                        <b>Section Identifier:</b> {sel_sec}<br>
                        <b>Exam Target:</b> {sel_exam}
                    </div>
                </div>
                
                <table class="analytics-grid-table">
                    <thead>
                        <tr>
                            <th style="width: 6%;">ID</th>
                            <th style="text-align: left; padding-left: 12px; width: 22%;">Student Name</th>
                            <th style="width: 7%;">Section</th>
                            <th style="width: 6%;">Class</th>
                            {thead_subjects_html}
                            <th style="background-color: #e6f2ff; color: #0055b3; width: 7%;">Att %</th>
                            <th style="background-color: #f1f3f5; width: 9%;">Total (Obt)</th>
                            <th style="background-color: #f1f3f5; width: 8%;">Total Max</th>
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
                    const filenameStr = "Summary_Report_{sel_sec}_{selected_class}_{selected_session}.png";
                    
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
        components.html(analytics_html_payload, height=750, scrolling=True)
# ----------------- 📈 MULTI-TEST PROGRESS REPORT -----------------
if menu_choice == "📈 Multi-Test Progress Report":
    st.title("📈 Multi-Test Progress Analytics")
    st.markdown("Select your reporting scope below to generate high-fidelity, print-ready student progress cards.")

    # CSS Injection for Print Isolation
    st.markdown("""
        <style>
        @media print {
            .no-print { display: none !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # --- MASTER TEST FRAMEWORK DYNAMIC SYNC ---
    try:
        # Pulls active exam codes straight from your database dynamically
        active_cycles_df = run_query("SELECT exam_code FROM exam_cycles WHERE status = 'ACTIVE'")
        all_frameworks = active_cycles_df["exam_code"].tolist() if not active_cycles_df.empty else []
    except Exception as e:
        # Fallback list to prevent application downtime if database has a brief latency hiccup
        all_frameworks = [
            "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "SEND_UP", "MT_5",
            "T_1", "T_2", "T_3", "T_4", "T_5", "T_6", "T_7", "T_8", "T_9", "T_10",
            "HALF_BOOK01", "HALF_BOOK02", "PRE_BOARD", "BISE-11th", "BISE-12th", 
            "PBTE_1", "PBTE_2", "PBTE_3", "PBTE_4"
        ]

    # --- DYNAMIC SESSION SYNCHRONIZATION ---
    synchronized_sessions = []
    
    # 1. Primary Sync: Read directly from your Settings table so newly added sessions show up instantly
    try:
        db_settings_sessions = run_query("""
            SELECT session_name 
            FROM sessions 
            WHERE status = 'ACTIVE' OR status IS NULL OR status = ''
        """)
        if not db_settings_sessions.empty:
            synchronized_sessions = db_settings_sessions['session_name'].dropna().astype(str).tolist()
    except Exception:
        pass  

    # 2. Secondary Sync: Collect unique session codes from student profiles
    if not synchronized_sessions:
        try:
            db_active_sessions = run_query("""
                SELECT DISTINCT session 
                FROM students 
                WHERE session IS NOT NULL 
                  AND session != ''
                  AND (status IS NULL OR UPPER(TRIM(status)) NOT IN ('LEFT', 'INACTIVE', 'DROPOUT'))
            """)
            if not db_active_sessions.empty:
                synchronized_sessions = db_active_sessions['session'].dropna().astype(str).tolist()
        except Exception:
            pass

    # 3. Global Fallback Sync: If database checks are entirely empty, pull from global application list
    if not synchronized_sessions:
        if "AVAILABLE_SESSIONS" in locals() or "AVAILABLE_SESSIONS" in globals():
            synchronized_sessions = list(AVAILABLE_SESSIONS)
        else:
            synchronized_sessions = ["2025-27", "2026-28", "2027-29"]

    # 4. Global Hardcoded Overrides & Formatting Safety Policies
    synchronized_sessions = [str(s).strip() for s in synchronized_sessions]
    
    # Force inject your newly configured session so it is guaranteed to show up regardless of empty tables
    if "2027-29" not in synchronized_sessions:
        synchronized_sessions.append("2027-29")
        
    # Force eliminate old structural legacy values from showing up in dropdown lists
    if "2024-26" in synchronized_sessions:
        synchronized_sessions.remove("2024-26")
        
    # Re-sort clean options sequentially
    synchronized_sessions = sorted(list(set(synchronized_sessions)))

    # Fallback safety handler for selectbox indexing context
    default_session_index = 0 if len(synchronized_sessions) > 0 else None

    # --- GLOBAL INTERFACE FILTER PANEL ---
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    st.markdown('##### 🎛️ Filter Configuration Panel')
    
    # 1. Base Configuration Options (System & Session)
    col_base1, col_base2 = st.columns(2)
    with col_base1:
        sel_session_global = st.selectbox("Select Session Context:", synchronized_sessions, index=default_session_index, key="global_sel_sess")
    with col_base2:
        academic_system = st.selectbox("Select Academic System:", ["Annual System", "Semester System"], key="mt_system_type")

    st.markdown("<div style='margin: 5px 0;'></div>", unsafe_allow_html=True)

    # 2. Sequential Options based on Academic System Choice
    col_dyn1, col_dyn2, col_dyn3 = st.columns(3)

    if academic_system == "Annual System":
        with col_dyn1:
            sel_class_global = st.selectbox("Select Class Level:", ["11th", "12th"], index=0, key="global_sel_class")
            
        with col_dyn2:
            annual_sections = []
            for discipline, class_data in DISCIPLINE_SECTIONS_MAP.items():
                if "DIT" not in discipline.upper():
                    sections_list = class_data.get(sel_class_global, [])
                    annual_sections.extend(sections_list)
            
            annual_sections = sorted(list(set(annual_sections)))
            if not annual_sections:
                annual_sections = ["MG_BLUE", "EG_BLUE", "CG_WHITE", "CB_WHITE"]
                
            sel_sec = st.selectbox("Select Target Class Section:", options=annual_sections, index=0, key="global_sel_sec")
            
        with col_dyn3:
            selected_exams_list = st.multiselect("🎯 Select Tests:", options=all_frameworks, default=["MT_1", "MT_2", "MT_3"], key="global_exams")

    else:  # --- SEMESTER SYSTEM BRANCH ---
        with col_dyn1:
            sel_class_global = st.selectbox("Select Semester Context:", ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester"], key="global_sel_class")
            
        with col_dyn2:
            semester_sections = ["DIT_G", "DIT_B"]
            sel_sec = st.selectbox("Select Target Section:", options=semester_sections, index=0, key="global_sel_sec")
            
        with col_dyn3:
            selected_exams_list = st.multiselect("🎯 Select Tests:", options=all_frameworks, default=["MT_1", "MT_2", "MT_3"], key="global_exams")
    st.markdown("---")

    # Scope Selector Strategy
    scope_choice = st.radio(
        "𖨾 Select Scope:",
        options=["👤 Single Student Card", "👥 Complete Section Cards"],
        index=0,
        horizontal=True,
        key="mt_reporting_scope"
    )

    months_list = ["May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.", "Jan.", "Feb.", "March", "April"]
    students_to_process = []
    
    rendered_section = str(sel_sec).strip()

    # --- SCOPE LOGIC 1: SINGLE PROFILE ---
    if scope_choice == "👤 Single Student Card":
        with st.form("single_student_secure_form"):
            st.markdown(f"##### 👤 Single Profile Verification Panel ({sel_class_global} - {rendered_section})")
            search_id = st.text_input("🔍 Enter Student Roll Number / ID:", value="", key="form_search_id_single")
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
                          AND session = :session
                          AND UPPER(TRIM(class)) = UPPER(TRIM(:class_level))
                          AND UPPER(TRIM(section)) LIKE UPPER(TRIM(:section))
                    """, {"sid": query_id, "session": sel_session_global, "class_level": sel_class_global, "section": f"%{rendered_section}%"})
                    
                    if not student_df.empty:
                        students_to_process = student_df.to_dict('records')
                        rendered_section = student_df.iloc[0]["section"]
                    else:
                        st.error(f"❌ Student ID #{clean_id} was not found inside Section {rendered_section} ({sel_class_global}).")
                except Exception as e:
                    st.error(f"⚠️ Student verification query failed: {str(e)}.")

    # --- SCOPE LOGIC 2: BULK SECTION COMPLETE CARDS ---
    else:
        st.markdown(f'<div style="border:1px solid #d3d3d3; padding: 20px; border-radius: 5px; margin-bottom: 20px; background-color: rgba(240, 242, 246, 0.3);">', unsafe_allow_html=True)
        st.markdown(f"##### 👥 Complete Section Processing Panel")
        st.info(f"Ready to compile all student cards for **{sel_class_global}** under Section **{rendered_section}**.")
        
        submit_bulk = st.button("🚀 Compile All Section Cards", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
            
        if submit_bulk:
            section_students_df = run_query("""
                SELECT id, name, section, class 
                FROM students 
                WHERE UPPER(TRIM(section)) LIKE UPPER(TRIM(:section))
                  AND session = :session
                  AND UPPER(TRIM(class)) = UPPER(TRIM(:class_level))
                ORDER BY id ASC
            """, {"section": f"%{rendered_section}%", "session": sel_session_global, "class_level": sel_class_global})
            
            if not section_students_df.empty:
                students_to_process = section_students_df.to_dict('records')
            else:
                st.error(f"💡 No registered student profiles found matching section '{rendered_section}' for Session {sel_session_global} ({sel_class_global}).")

    st.markdown('</div>', unsafe_allow_html=True)

    # --- DATA PROCESSING AND RENDERING PIPELINE ENGINE ---
    if students_to_process and not selected_exams_list:
        st.warning("⚠️ Select at least one metric from the configuration panel to compile report views.")
        
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

        # 1. Performance Marks Fetching Segment
        try:
            sample_marks = run_query("SELECT * FROM marks LIMIT 1", {})
            cols_marks = [c.lower() for c in sample_marks.columns] if not sample_marks.empty else []
            
            sub_col = "subject_name" if "subject_name" in cols_marks else ("subject" if "subject" in cols_marks else "subject_name")
            exam_col = "exam_type" if "exam_type" in cols_marks else ("exam" if "exam" in cols_marks else "exam_type")
            obt_col = "marks_obtained" if "marks_obtained" in cols_marks else ("obtained_marks" if "obtained_marks" in cols_marks else "marks_obtained")
            tot_col = "total_marks" if "total_marks" in cols_marks else "total_marks"

            marks_df = run_query(f"""
                SELECT student_id, {sub_col} as subject_name, {exam_col} as exam_type, {obt_col} as marks_obtained, {tot_col} as total_marks
                FROM marks
                WHERE student_id IN ({placeholders_str})
            """, params_dict)
            
            if not marks_df.empty:
                marks_df.columns = [c.lower() for c in marks_df.columns]
                marks_df["student_id"] = marks_df["student_id"].astype(str).str.strip()
                marks_df["exam_type"] = marks_df["exam_type"].astype(str).str.strip().str.upper()
                
                # --- FLAWLESS STRING SANITIZATION & UNIFICATION ---
                # 1. Cast to string, strip whitespace, and normalize case
                # Clean, strip whitespaces, and force standard Title Case
                marks_df["subject_name"] = marks_df["subject_name"].astype(str).str.strip()
                
                # Convert underscores to spaces right at the source database level
                marks_df["subject_name"] = marks_df["subject_name"].str.replace('_', ' ')
                
                # Normalize any multi-spaces or casing, then fix standalone "Computer"
                marks_df["subject_name"] = marks_df["subject_name"].str.replace(r'\s+', ' ', regex=True).str.title()
                marks_df["subject_name"] = marks_df["subject_name"].replace({"Computer": "Computer Science"})
                # 2. Aggressively clean up any multi-space or trailing text hidden artifacts
                marks_df["subject_name"] = marks_df["subject_name"].str.replace(r'\s+', ' ', regex=True)
                # 3. Unify alternative values securely at the data frame root level
                marks_df["subject_name"] = marks_df["subject_name"].replace({"Computer": "Computer Science"})
        except Exception as e:
            st.error(f"⚠️ Failed fetching performance records. Details: {str(e)}")

        # 2. Attendance Scanner Segment (Absolute Type Override)
        try:
            # Fetch all attendance rows to ensure no SQL parameter casting issues drop records
            attendance_df = run_query("""
                SELECT student_id, month_name, total_days, present_days 
                FROM attendance
            """, {})
            
            if not attendance_df.empty:
                # Force exact column name layout strings
                attendance_df.columns = ['student_id', 'month_name', 'total_days', 'present_days']
                
                # CRITICAL: Clean, convert, and store student_id as plain text strings 
                # to guarantee matching with frontend tracking keys
                attendance_df["student_id"] = attendance_df["student_id"].fillna(0).astype(float).astype(int).astype(str).str.strip()
                attendance_df["month_name"] = attendance_df["month_name"].astype(str).str.strip()
            else:
                attendance_df = pd.DataFrame(columns=['student_id', 'month_name', 'total_days', 'present_days'])
                
        except Exception as e:
            st.error(f"⚠️ Failed fetching attendance matrix records: {str(e)}")
        # --- RE-ENGINEERED ATTENDANCE MATRIX AGGREGATOR ---
        # (Replace your current matrix loop down in the code with this safer datetime parse)

        # CSS Styling Configurations
        css_rules = "body { background-color: #ffffff; margin: 0; padding: 10px; }"
        css_rules += " .action-dashboard-panel { display: flex; flex-wrap: wrap; gap: 12px; max-width: 850px; margin: 10px auto 25px auto; font-family: 'Arial', sans-serif; }"
        css_rules += " .action-control-btn { flex: 1; min-width: 180px; color: white; border: none; padding: 12px 18px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: background 0.2s, transform 0.1s, opacity 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px; }"
        css_rules += " .action-control-btn:active { transform: scale(0.97); } .btn-print-single { background-color: #2e7d32; } .btn-print-single:hover { background-color: #1b5e20; }"
        css_rules += " .btn-print-bulk { background-color: #1565c0; } .btn-print-bulk:hover { background-color: #0d47a1; }"
        css_rules += " .btn-img-single { background-color: #e65100; } .btn-img-single:hover { background-color: #b33900; }"
        css_rules += " .btn-img-bulk { background-color: #6a1b9a; } .btn-img-bulk:hover { background-color: #4a148c; }"
        css_rules += " .cck-container { background-color: #ffffff; border: 1px solid #000000; padding: 30px; margin: 0 auto 30px auto; max-width: 850px; color: #000000; font-family: 'Arial', sans-serif; page-break-after: always; box-sizing: border-box; }"
        css_rules += " .cck-header-wrapper { display: flex; align-items: center; justify-content: center; margin-bottom: 5px; position: relative; }"
        css_rules += " .cck-logo-image-container { width: 75px; height: 100px; position: absolute; left: 20px; display: flex; align-items: center; justify-content: center; }"
        css_rules += " .cck-logo-image { max-width: 100%; max-height: 100%; object-fit: contain; }"
        css_rules += " .cck-logo-fallback-text { background-color: #e67e22; color: #ffffff; font-weight: bold; font-size: 22px; width: 75px; height: 75px; display: flex; align-items: center; justify-content: center; border-radius: 4px; }"
        css_rules += " .cck-title-block { text-align: center; } .cck-main-title { font-size: 24px; font-weight: bold; margin: 15px; letter-spacing: 0.5px; }"
        css_rules += " .cck-sub-title { font-size: 13px; color: #444444; margin: 2px 0 0 0; } .cck-badge-wrapper { text-align: center; margin: 15px 0; }"
        css_rules += " .cck-doc-badge { display: inline-block; background-color: #d1d5db; color: #000000; font-weight: bold; font-size: 16px; padding: 4px 20px; border-radius: 2px; }"
        css_rules += " .cck-meta-row { display: flex; flex-wrap: wrap; justify-content: space-between; margin-bottom: 20px; font-size: 14px; }"
        css_rules += " .cck-meta-field { margin-right: 15px; margin-bottom: 8px; } .cck-line-fill { border-bottom: 1px solid #000000; display: inline-block; min-width: 120px; padding-left: 5px; font-weight: bold; }"
        css_rules += " .cck-report-table { width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 13px; }"
        css_rules += " .cck-report-table th, .cck-report-table td { border: 1px solid #000000; padding: 6px 4px; text-align: center; }"
        css_rules += " .cck-report-table th { background-color: #ffffff; font-weight: normal; } .cck-report-table td:first-child { text-align: left; padding-left: 8px; }"
        css_rules += " .cck-remarks-area { margin-top: 100px; font-size: 14px; display: flex; align-items: flex-end; }"
        css_rules += " .cck-remarks-line { flex-grow: 1; border-bottom: 1px solid #000000; margin-left: 8px; padding-left: 5px; font-style: italic; }"
        css_rules += " .cck-footer-sign { margin-top: 25px; text-align: right; font-size: 14px; padding-right: 20px; }"
        css_rules += " @media print { .action-dashboard-panel { display: none !important; } .cck-single-print-isolation { display: block !important; } .cck-single-print-hide { display: none !important; } .cck-container { border: none !important; padding: 0 !important; margin-bottom: 0 !important; } }"

        css_styles = f"<style>{css_rules}</style>".replace('\xa0', ' ')

        composite_html_payload = f"""
        <html>
        <head>
        <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
        {css_styles}
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
            s_section = " ".join(raw_section.replace("\n", " ").split()).upper().strip()
            
            raw_class = str(s_meta["class"]) if s_meta.get("class") else sel_class_global
            s_class = " ".join(raw_class.replace("\n", " ").split())
            
            # --- START ACADEMIC MARK MATRIX COMPUTER LOOP ---
            table_rows_html = ""
            total_row_html = ""
            grand_total_percentages = [0]

            if not marks_df.empty:
                s_marks = marks_df[marks_df["student_id"] == s_id].copy()
                
                if not s_marks.empty:
                    # ------------------------------------------------------------------
                    # ⚡ DYNAMIC ELECTIVE TRANSLATION & COLLAPSING UNIFICATION ENGINE
                    # ------------------------------------------------------------------
                    is_stats_section = s_section in ["CG_STATS", "CB_STATS", "CQ3", "CK3"]
                    
                    # Ensure absolute string purity for this iteration slice
                    s_marks['display_subject'] = s_marks['subject_name'].astype(str).str.strip().str.title()
                    s_marks['display_subject'] = s_marks['display_subject'].str.replace(r'\s+', ' ', regex=True)
                    s_marks['display_subject'] = s_marks['display_subject'].replace({"Computer": "Computer Science"})
                    s_marks['label_suffix'] = ""
                    
                    if is_stats_section:
                        for m_idx, m_row in s_marks.iterrows():
                            if str(m_row['subject_name']).strip().title() == "Physics":
                                s_marks.at[m_idx, 'display_subject'] = "Statistics"
                                s_marks.at[m_idx, 'label_suffix'] = " (Phy)"
                    
                    # Unique array will now strictly yield a single unified "Computer Science" row index
                    distinct_subjects = sorted(list(set(s_marks["display_subject"].dropna().tolist())))
                    
                    exam_totals_obtained = {exam: 0.0 for exam in selected_exams_list}
                    exam_totals_possible = {exam: 0.0 for exam in selected_exams_list}
                    
                    for sub in distinct_subjects:
                        # Slice data belonging to this specific unified subject name string
                        sub_marks = s_marks[s_marks["display_subject"] == sub]
                        row_tds = f"<td style='text-align: left; padding-left: 8px;'><strong>{sub}</strong></td>"
                        subject_pct_accum = 0
                        valid_exams_count = 0
                        
                        for exam in selected_exams_list:
                            if academic_system == "Semester System":
                                match_row = sub_marks[sub_marks["display_subject"].str.upper() == str(exam).strip().upper()]
                            else:
                                match_row = sub_marks[sub_marks["exam_type"] == str(exam).strip().upper()]
                                
                            if not match_row.empty:
                                try:
                                    # Fallback safely to highest or first available metric if multiple rows intersect
                                    target_record = match_row.iloc[0]
                                    obt = float(target_record["marks_obtained"])
                                    tot = float(target_record["total_marks"])
                                    pct = int((obt / tot) * 100) if tot > 0 else 0
                                    
                                    suffix_tag = target_record.get('label_suffix', '')
                                    row_tds += f"<td>{pct}%{suffix_tag}</td>"
                                    
                                    exam_totals_obtained[exam] += obt
                                    exam_totals_possible[exam] += tot
                                    subject_pct_accum += pct
                                    valid_exams_count += 1
                                except:
                                    row_tds += "<td>-</td>"
                            else:
                                row_tds += "<td>-</td>"
                        
                        sub_avg = int(subject_pct_accum / valid_exams_count) if valid_exams_count > 0 else 0
                        row_tds += f"<td><strong>{sub_avg}%</strong></td>"
                        table_rows_html += f"<tr>{row_tds}</tr>"
                    
                    total_title = "Overall Course Avg %" if academic_system == "Semester System" else "Total Average %"
                    total_obt_tds = f"<td style='text-align: left; padding-left: 8px;'><strong>{total_title}</strong></td>"
                    total_pct_accum = 0
                    total_counted = 0
                    
                    for exam in selected_exams_list:
                        e_obt = exam_totals_obtained[exam]
                        e_tot = exam_totals_possible[exam]
                        if e_tot > 0:
                            e_pct = int((e_obt / e_tot) * 100)
                            total_obt_tds += f"<td><strong>{e_pct}%</strong></td>"
                            total_pct_accum += e_pct
                            total_counted += 1
                        else:
                            total_obt_tds += "<td>-</td>"
                            
                    grand_avg = int(total_pct_accum / total_counted) if total_counted > 0 else 0
                    grand_total_percentages = [grand_avg]
                    total_obt_tds += f"<td><span style='font-size:14px;'><strong>{grand_avg}%</strong></span></td>"
                    total_row_html = f"<tr style='background-color:#fafafa;'>{total_obt_tds}</tr>"

            if not table_rows_html:
                table_rows_html = f"<tr><td colspan='{len(selected_exams_list) + 2}' style='padding:15px; color:#666;'>No registered academic records found.</td></tr>"

            # =========================================================================
            # --- ATTENDANCE REPORT MATRIX (DIRECT DAILY_ATTENDANCE TRACKER) ---
            # =========================================================================
            tot_days_row, att_days_row, pct_days_row = "", "", ""
            overall_tot_days, overall_att_days = 0, 0

            # Months tracking dictionary mapped precisely to your formatting outputs
            month_map = {
                "May": 5, "June": 6, "July": 7, "Aug.": 8, "Sept.": 9, "Oct.": 10, 
                "Nov.": 11, "Dec.": 12, "Jan.": 1, "Feb.": 2, "March": 3, "April": 4
            }
            attendance_matrix = {m: {"total": 0, "present": 0} for m in month_map.keys()}

            # 1. Fetch raw calendar logs directly matching your working summary ledger logic
            try:
                raw_logs_df = run_query("""
                    SELECT attendance_date, UPPER(TRIM(status)) as att_status
                    FROM daily_attendance
                    WHERE CAST(student_id AS TEXT) = TRIM(:st_id)
                """, {"st_id": str(s_id).strip()})
            except Exception:
                raw_logs_df = pd.DataFrame()

            # 2. Process logs on the fly into months dynamically if rows are fetched
            if not raw_logs_df.empty:
                try:
                    # Coerce dates safely to datetime entries
                    raw_logs_df["attendance_date"] = pd.to_datetime(raw_logs_df["attendance_date"])
                    
                    for _, log_row in raw_logs_df.iterrows():
                        log_date = log_row["attendance_date"]
                        if pd.isna(log_date):
                            continue
                            
                        log_month_int = log_date.month
                        log_status = str(log_row["att_status"]).strip()

                        # Reverse match month integer back to your map keys ("Aug.", "Sept.", etc.)
                        matched_month_key = None
                        for m_name, m_int in month_map.items():
                            if m_int == log_month_int:
                                matched_month_key = m_name
                                break

                        if matched_month_key:
                            attendance_matrix[matched_month_key]["total"] += 1
                            if log_status in ["P", "PRESENT"]:
                                attendance_matrix[matched_month_key]["present"] += 1
                except Exception:
                    pass

            # --- GENERATE CELL HTML CODES FOR THIS CARD ---
            for m_name in month_map.keys():
                t_d = attendance_matrix[m_name].get("total", 0)
                a_d = attendance_matrix[m_name].get("present", 0)
                overall_tot_days += t_d
                overall_att_days += a_d

                tot_days_row += f"<td>{f'{t_d:02d}' if t_d > 0 else '-'}</td>"
                att_days_row += f"<td>{f'{a_d:02d}' if t_d > 0 else '-'}</td>"
                pct_days_row += f"<td>{f'{int((a_d/t_d)*100)}%' if t_d > 0 else '-'}</td>"

            if overall_tot_days > 0:
                tot_days_row += f"<td>{overall_tot_days:02d}</td>"
                att_days_row += f"<td>{overall_att_days:02d}</td>"
                pct_days_row += f"<td><strong>{int((overall_att_days / overall_tot_days) * 100)}%</strong></td>"
            else:
                tot_days_row += "<td>-</td>"
                att_days_row += "<td>-</td>"
                pct_days_row += "<td><strong>0%</strong></td>"

            remarks_text = "Satisfactory academic progress observed."
            if grand_total_percentages and grand_total_percentages[-1] >= 85:
                remarks_text = "Excellent effort! An outstanding performer with exceptional academic discipline."

            column_header_title = "Course Modules" if academic_system == "Semester System" else "Subjects"
            thead_exams_th = "".join([f"<th style='font-weight: bold;'>{exam}</th>" for exam in selected_exams_list])
            thead_sub_tds = "".join(["<td>Obt.%</td>" for _ in selected_exams_list])

            l_b64 = logo_base64 if ('logo_base64' in locals() or 'logo_base64' in globals()) else ""
            logo_markup = f'<img class="cck-logo-image" src="{l_b64}" alt="Logo" />' if l_b64 else '<div class="cck-logo-fallback-text">CC</div>'

            composite_html_payload += f"""
            <div class="cck-container student-card-record" data-index="{index}" data-name="{s_name.replace(' ', '_')}" data-id="{s_id}">
                <div class="cck-header-wrapper">
                    <div class="cck-logo-image-container">{logo_markup}</div>
                    <div class="cck-title-block"><div class="cck-main-title">CONCORDIA COLLEGE KASUR</div></div>
                </div>
                <div class="cck-badge-wrapper"><div class="cck-doc-badge">Result Card</div></div>
                <div class="cck-meta-row">
                    <div class="cck-meta-field">Name: <span class="cck-line-fill">{s_name}</span></div>
                    <div class="cck-meta-field">ID: <span class="cck-line-fill">{s_id}</span></div>
                    <div class="cck-meta-field">Section: <span class="cck-line-fill">{s_section}</span></div>
                    <div class="cck-meta-field">Class / Term: <span class="cck-line-fill">{s_class}</span></div>
                </div>
                <table class="cck-report-table">
                    <thead>
                        <tr><th style="width: 25%;"></th>{thead_exams_th}<th></th></tr>
                        <tr><th style="text-align: left; padding-left: 8px; font-weight: bold;">{column_header_title}</th>{thead_sub_tds}<td style="font-weight: bold;">Avg.%</td></tr>
                    </thead>
                    <tbody>{table_rows_html}{total_row_html}</tbody>
                </table>
                <div class="cck-badge-wrapper" style="margin-top: 10px; margin-bottom: 5px;"><div class="cck-doc-badge" style="background-color: transparent; font-size: 15px; text-decoration: underline;">Attendance Report</div></div>
                <table class="cck-report-table" style="font-size: 11px; margin-top: 5px;">
                    <thead>
                        <tr><th style="width: 14%;"></th><th>May</th><th>June</th><th>July</th><th>Aug.</th><th>Sept.</th><th>Oct.</th><th>Nov.</th><th>Dec.</th><th>Jan.</th><th>Feb.</th><th>March</th><th>April</th><th style="font-weight: bold;">Overall</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Open Total Days</td>{tot_days_row}</tr>
                        <tr><td>Att. Days</td>{att_days_row}</tr>
                        <tr><td>Att.%</td>{pct_days_row}</tr>
                    </tbody>
                </table>
                <div class="cck-remarks-area"><strong>Remarks:</strong><div class="cck-remarks-line">{remarks_text}</div></div>
                <div class="cck-footer-sign"><strong>Principal Sign</strong></div>
            </div>
            """

        # =========================================================================
        # --- OUTSIDE THE FOR LOOP: FINAL RENDERING ---
        # =========================================================================
        composite_html_payload += """
            </div> <script>
            function executeTargetPrint(isSingleTarget) {
                var cards = document.querySelectorAll('.student-card-record');
                if (cards.length === 0) return;
                cards.forEach(function(card, idx) {
                    if (isSingleTarget) {
                        if (idx === 0) { card.classList.add('cck-single-print-isolation'); card.classList.remove('cck-single-print-hide'); }
                        else { card.classList.add('cck-single-print-hide'); card.classList.remove('cck-single-print-isolation'); }
                    } else { card.classList.remove('cck-single-print-hide'); card.classList.remove('cck-single-print-isolation'); }
                });
                setTimeout(function() { window.print(); }, 200);
            }

            function exportDossierToImage(isSingleTarget) {
                var cards = document.querySelectorAll('.student-card-record');
                if (cards.length === 0) { alert('No student cards available.'); return; }
                var targetList = [];
                if (isSingleTarget) { targetList.push(cards[0]); } 
                else { cards.forEach(function(c) { targetList.push(c); }); }
                
                var currentBatchIdx = 0;
                function processNextImageDownload() {
                    if (currentBatchIdx >= targetList.length) return;
                    var card = targetList[currentBatchIdx];
                    var sName = card.getAttribute('data-name') || 'student';
                    var sId = card.getAttribute('data-id') || 'id';
                    
                    html2canvas(card, { scale: 2, useCORS: true }).then(function(canvas) {
                        var link = document.createElement('a');
                        link.download = 'Report_' + sId + '_' + sName + '.png';
                        link.href = canvas.toDataURL('image/png');
                        link.click();
                        currentBatchIdx++;
                        setTimeout(processNextImageDownload, 500);
                    }).catch(function(err) {
                        console.error('Image processing exception occurred:', err);
                    });
                }
                processNextImageDownload();
            }
            </script>
        </body>
        </html>
        """

        import streamlit.components.v1 as components
        components.html(composite_html_payload, height=900, scrolling=True)

# --- END OF MULTI-TEST REPORT LOGIC ---

# ==============================================================================
# 🪪 SUB-MODULE: STUDENT RESULT CARDS — PRINT ENGINE (FULLY DYNAMIC)
# ==============================================================================
elif menu_choice == "🪪 Student Result Cards":
    import streamlit.components.v1 as components
    import pandas as pd
    import streamlit as st
    import numpy as np

    st.title("🪪 Student Result Cards — Print Engine")

    # --------------------------------------------------------------------------
    # PART 1: GLOBAL ACADEMIC ENVIRONMENT FILTERS
    # --------------------------------------------------------------------------
    try:
        db_sessions = run_query("SELECT DISTINCT session_name FROM academic_sessions WHERE status = 'ACTIVE' ORDER BY session_name DESC")
        session_list = db_sessions['session_name'].tolist() if not db_sessions.empty else ["2024-2026", "2025-2027"]
    except Exception:
        session_list = ["2024-2026", "2025-2027"]

    col_sel1, col_sel2, col_sel3, col_sel4 = st.columns(4)
    with col_sel1:
        selected_session = st.selectbox("📅 Select Session:", options=session_list)
    with col_sel2:
        selected_system = st.selectbox("⚙️ Select Academic System:", options=["Annual System", "Semester System"])
    with col_sel3:
        class_options = ["11th", "12th"] if selected_system == "Annual System" else ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester"]
        selected_class = st.selectbox("🏫 Select Class:", options=class_options)
    with col_sel4:
        try:
            db_exams = run_query(f"SELECT exam_code, exam_display_name FROM exam_cycles WHERE system_type = '{selected_system}' AND status = 'ACTIVE' ORDER BY exam_code ASC")
        except Exception:
            db_exams = pd.DataFrame()

        if not db_exams.empty:
            exam_options = [f"{row['exam_code']} ({row['exam_display_name']})" for _, row in db_exams.iterrows()]
            selected_combined_label = st.selectbox("🎯 Select Test Term:", options=exam_options)
            selected_test_code = selected_combined_label.split(" (")[0].strip()
            selected_test_label = selected_test_code
        else:
            fallback_options = ["MT_1 (Monthly Test 1)", "MT_2 (Monthly Test 2)", "SEND_UP (Send-Up Exam)"]
            selected_combined_label = st.selectbox("🎯 Select Test Term:", options=fallback_options)
            selected_test_code = selected_combined_label.split(" (")[0].strip()
            selected_test_label = selected_test_code

    # --------------------------------------------------------------------------
    # PART 2: DYNAMIC FILTER SELECTION (LINKED TO GLOBAL DICTIONARIES)
    # --------------------------------------------------------------------------
    st.markdown("---")
    print_scope = st.radio("𖨾 Select Print Scope:", ["👤 Single Student Card", "👥 Complete Section Cards"], horizontal=True)
    
    search_id = ""
    selected_discipline = ""
    active_section = ""

    # Normalize UI class selection to align with mapping dictionary keys
    normalized_class_input = str(selected_class).strip()
    if "1ST SEMESTER" in normalized_class_input.upper(): normalized_class_input = "Semester 1"
    elif "2ND SEMESTER" in normalized_class_input.upper(): normalized_class_input = "Semester 2"
    elif "3RD SEMESTER" in normalized_class_input.upper(): normalized_class_input = "Semester 3"
    elif "4TH SEMESTER" in normalized_class_input.upper(): normalized_class_input = "Semester 4"

    if print_scope == "👤 Single Student Card":
        search_id = st.text_input("🔍 Enter Student Roll Number / ID:")
    else:
        col_sec1, col_sec2 = st.columns(2)
        with col_sec1:
            selected_discipline = st.selectbox("🧬 Select Discipline:", options=list(DISCIPLINE_SECTIONS_MAP.keys()))
        with col_sec2:
            sections_pool = DISCIPLINE_SECTIONS_MAP.get(selected_discipline, {}).get(normalized_class_input, [])
            active_section = st.selectbox("📋 Select Section:", options=sections_pool)

    st.markdown("<br>", unsafe_allow_html=True)
    submit_execution = st.button("🚀 Generate Result Cards", type="primary", use_container_width=True)

    # --------------------------------------------------------------------------
    # PART 3: DATA EXTRACTION ENGINE (CLEAN RECORD FETCHING)
    # --------------------------------------------------------------------------
    students_to_print = pd.DataFrame()

    if submit_execution:
        st.write(f"Searching for ID: {search_id} | Session: {selected_session}")
    
        if print_scope == "👤 Single Student Card":
            # Remove the session constraint for single student lookups
            sql_single = """
                SELECT id, name, section, class, session 
                FROM students
                WHERE id = :sid 
            """
            students_to_print = run_query(sql_single, {"sid": int(search_id.strip())})
            
            # 3. Add a fallback check if empty
            if students_to_print.empty:
                total_check = run_query("SELECT session, class FROM students WHERE id = :id", {"id": search_id.strip()})
                st.write("Database shows student exists in these sessions:", total_check)
            
            # Auto-override active workspace context parameters if record is found
        if not students_to_print.empty:
            active_section = str(students_to_print.iloc[0]['section']).strip()
            selected_class = str(students_to_print.iloc[0]['class']).strip()
            
            # CRITICAL: We must also update the session if it differs
            # to ensure the subsequent marks/attendance lookups use the correct session
            selected_session = str(students_to_print.iloc[0]['session']).strip()
            
            st.success(f"✅ Found student in session: {selected_session}. Proceeding to generate card...")
        
        elif print_scope == "👥 Complete Section Cards" and active_section:
            # 2. Execute the fetch for the whole section
            sql_section = """
                SELECT id, name, section, class 
                FROM students 
                WHERE TRIM(session) = TRIM(:session) 
                AND UPPER(TRIM(class)) = UPPER(TRIM(:cls))
                AND UPPER(TRIM(section)) = UPPER(TRIM(:sec))
                ORDER BY id ASC
            """
            students_to_print = run_query(sql_section, {
                "session": selected_session.strip(), 
                "cls": normalized_class_input,
                "sec": active_section.strip()
            })
    # ==============================================================================
    # PART 4: COMPILATION LOOP & RENDERING ENGINE
    # ==============================================================================
    if submit_execution and not students_to_print.empty:
        # --- Inside "🪪 Student Result Cards" section ---
    if submit_execution and not students_to_print.empty:
        
        # --- PLACE DIAGNOSTIC CODE HERE ---
        current_id_str = str(students_to_print.iloc[0]['id']).strip()
        
        st.write("DEBUG: Fetching logs for student_id:", int(current_id_str))
        
        debug_logs = run_query("""
            SELECT student_id, attendance_date, status 
            FROM daily_attendance 
            WHERE student_id = :sid
        """, {"sid": int(current_id_str)})
        
        st.write("DEBUG: Attendance table rows found:", len(debug_logs))
        st.dataframe(debug_logs.head())
        # ----------------------------------

        # ... then your existing compiled_html generation logic follows ...
        # Safe Fallback Cache Layers: Compile marks and logs frames dynamically if missing
        if 'marks_df' not in locals() or marks_df.empty:
            exam_table = f"marks_{selected_session.replace('-', '_').lower()}_{selected_test_code.lower()}"
            try:
                marks_df = run_query(f"SELECT * FROM {exam_table}")
                if not marks_df.empty:
                    marks_df.columns = [c.lower() for c in marks_df.columns]
            except Exception:
                marks_df = pd.DataFrame()

        if 'logs_df' not in locals() or logs_df.empty:
            try:
                logs_df = run_query("SELECT student_id, attendance_date, att_status FROM attendance_logs")
                if not logs_df.empty:
                    logs_df.columns = [c.lower() for c in logs_df.columns]
            except Exception:
                logs_df = pd.DataFrame()

        # --------------------------------------------------------------------------
        # MODULE A: CARD VIEW BOILERPLATE, MEDIA STYLES & INTERACTION INTERFACES
        # --------------------------------------------------------------------------
        html_header_and_styles = """
        <!DOCTYPE html>
        <html>
        <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
        <style>
            body { font-family: "Times New Roman", Times, serif; color: #000; background-color: #fff; margin: 0; padding: 10px; }
            .official-card-container { max-width: 850px; margin: 10px auto; padding: 25px; border: 1px solid #000; background: #fff; position: relative; }
            
            .logo-row { width: 100%; text-align: left; margin-bottom: 10px; }
            .logo-img { max-height: 65px; width: auto; display: block; }
            
            .title-row { width: 100%; text-align: center; margin-bottom: 20px; }
            .inst-main-header { font-weight: bold; font-size: 30px; text-transform: uppercase; margin: 0; }
            
            .banner-row { width: 100%; text-align: center; margin-bottom: 25px; }
            .doc-type-banner { font-weight: bold; font-size: 18px; text-transform: uppercase; letter-spacing: 1.5px; margin: 0; }
            
            .meta-layout-table { width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 15px; }
            .meta-layout-table td { border: none; padding: 4px 2px; vertical-align: bottom; white-space: nowrap; }
            .underlined-value-span { border-bottom: 1px solid #000; font-weight: bold; padding: 0 4px; display: inline-block; text-transform: uppercase; }
            .doc-data-table { width: 100%; border-collapse: collapse; margin-top: 5px; margin-bottom: 25px; font-size: 14px; }
            .doc-data-table th, .doc-data-table td { border: 1px solid #000; padding: 7px 5px; text-align: center; }
            .doc-data-table th { font-weight: bold; text-transform: uppercase; }
            .section-header-title { font-size: 15px; font-weight: bold; margin: 25px 0 8px 0; text-align: left; text-transform: uppercase; padding-bottom: 3px; }
            .attendance-matrix-table { width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 13px; }
            .attendance-matrix-table th, .attendance-matrix-table td { border: 1px solid #000; padding: 6px 4px; text-align: center; }
            .attendance-matrix-table td.row-title-cell { font-weight: bold; text-align: left; padding-left: 5px; }
            .action-controls-bar { max-width: 850px; margin: 0 auto 20px auto; display: flex; gap: 10px; flex-wrap: wrap; }
            .print-btn { background: #222; color: #fff; padding: 10px 20px; font-weight: bold; border: none; cursor: pointer; border-radius: 4px; }
            .image-single-btn { background: #0066cc; color: #fff; padding: 10px 20px; font-weight: bold; border: none; cursor: pointer; border-radius: 4px; }
            .image-section-btn { background: #198754; color: #fff; padding: 10px 20px; font-weight: bold; border: none; cursor: pointer; border-radius: 4px; }
            button:disabled { background: #6c757d !important; cursor: not-allowed; }
            @media print {
                .action-controls-bar { display: none !important; }
                .official-card-container { border: none !important; margin: 0 auto 15mm auto !important; page-break-inside: avoid !important; }
                .print-page-break-divider { page-break-after: always !important; }
            }
        </style>
        </head>
        <body>
            <div class="action-controls-bar">
                <button class="print-btn" onclick="window.print();">🖨️ Print Cards (Ctrl+P)</button>
                <button class="image-single-btn" id="save-single-card-trigger">📸 Save Current Card as Image</button>
                <button class="image-section-btn" id="save-section-cards-trigger">🗂️ Save All Section Cards (ZIP)</button>
            </div>
        """
        compiled_html = html_header_and_styles
        DISPLAY_MONTHS = ["May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.", "Jan.", "Feb.", "March", "April"]
        
        month_map = {
            "May": 5, "June": 6, "July": 7, "Aug.": 8, "Sept.": 9, "Oct.": 10, 
            "Nov.": 11, "Dec.": 12, "Jan.": 1, "Feb.": 2, "March": 3, "April": 4
        }

        # Conversion to Dict format to perform stable record rendering loops
        students_to_process_list = students_to_print.to_dict('records')

        for idx, student_row in enumerate(students_to_process_list):
            current_id_str = str(student_row['id']).strip()
            name = str(student_row['name']).upper()
            section = str(student_row['section']).upper().strip()
            grade_class = str(student_row['class']).strip()
            test_name = locals().get('selected_test_label', 'MULTI-TEST REPORT').upper()
            
            # Class configuration layer resolution
            lookup_class_key = grade_class
            if "1ST SEMESTER" in grade_class.upper(): lookup_class_key = "Semester 1"
            elif "2ND SEMESTER" in grade_class.upper(): lookup_class_key = "Semester 2"
            elif "3RD SEMESTER" in grade_class.upper(): lookup_class_key = "Semester 3"
            elif "4TH SEMESTER" in grade_class.upper(): lookup_class_key = "Semester 4"

            # Reverse map discipline layout context
            detected_discipline_key = None
            for discipline, class_layers in DISCIPLINE_SECTIONS_MAP.items():
                sections_list = class_layers.get(lookup_class_key, [])
                if section in [str(s).upper().strip() for s in sections_list]:
                    detected_discipline_key = discipline
                    break
            
            subject_mapping_key = detected_discipline_key
            if detected_discipline_key == "ICS (PHYSICS)": subject_mapping_key = "ICS_PHYSICS"
            elif detected_discipline_key == "ICS (STATS)": subject_mapping_key = "ICS_STATS"

            subjects_list = CLASS_SUBJECTS_MASTER_MAP.get(lookup_class_key, {}).get(subject_mapping_key, None)
            if not subjects_list:
                try: subjects_list = list(CLASS_SUBJECTS_MASTER_MAP.get(lookup_class_key, {}).values())[0]
                except Exception: subjects_list = ["English", "Urdu"]

            # 🔄 STEP 4A: SAFE LOCAL DATA SLICING 
            if not marks_df.empty:
                # Standardize column comparison to strings
                student_marks_df = marks_df[marks_df['student_id'].astype(str).str.strip() == current_id_str].copy()
                if 'subject_name' in student_marks_df.columns:
                    student_marks_df = student_marks_df.rename(columns={'subject_name': 'subject'})
                raw_marks = student_marks_df
            else:
                raw_marks = pd.DataFrame(columns=['subject', 'marks_obtained', 'total_marks', 'exam_type'])

            if not logs_df.empty:
                raw_logs_df = logs_df[logs_df['student_id'].astype(str).str.strip() == current_id_str].copy()
            else:
                raw_logs_df = pd.DataFrame()

            # 📊 ATTENDANCE MATRIX PROCESSING PIPELINE
            # We initialize a clean matrix for every student
            attendance_matrix = {m: {"total": 0, "present": 0} for m in DISPLAY_MONTHS}

            if not raw_logs_df.empty:
                try:
                    # Ensure date parsing works even with mixed formats
                    raw_logs_df["attendance_date"] = pd.to_datetime(raw_logs_df["attendance_date"], errors='coerce')
                    
                    for _, log_row in raw_logs_df.iterrows():
                        log_date = log_row["attendance_date"]
                        if pd.isna(log_date): continue
                        
                        # Extract month name directly from the datetime object
                        month_key = log_date.strftime('%B') # e.g., 'May', 'June'
                        
                        # Handle potential naming mismatches (e.g., your display uses "Aug.")
                        if month_key == "August": month_key = "Aug."
                        elif month_key == "September": month_key = "Sept."
                        
                        log_status = str(log_row["att_status"]).strip().upper()

                        if month_key in attendance_matrix:
                            attendance_matrix[month_key]["total"] += 1
                            if log_status in ["P", "PRESENT"]:
                                attendance_matrix[month_key]["present"] += 1
                except Exception as e:
                    st.error(f"Log processing error: {e}")

            # Build the display cells
            att_cells = {}
            tot_sum, pres_sum = 0, 0
            
            for m in DISPLAY_MONTHS:
                td = attendance_matrix[m]["total"]
                pd_val = attendance_matrix[m]["present"]
                tot_sum += td
                pres_sum += pd_val
                
                pct = f"{int((pd_val / td) * 100)}%" if td > 0 else "-"
                att_cells[m] = {"td": str(td) if td > 0 else "-", 
                                "pd": str(pd_val) if td > 0 else "-", 
                                "pct": pct}
                
            overall_pct_str = f"{int((pres_sum / tot_sum) * 100)}%" if tot_sum > 0 else "-"
            att_cells["Over All Att."] = {"td": str(tot_sum), "pd": str(pres_sum), "pct": overall_pct_str}

            # MODULE C: ACADEMIC RENDERING ENGINE
            logo_base64 = "https://raw.githubusercontent.com/mirfanshakirpgc-art/Academics-Reports/main/logo.png"
            grand_total_marks, grand_obtained_marks = 0.0, 0.0
            
            compiled_html += f"""
            <div class="official-card-container" id="card-{current_id_str}" data-student-name="{name.replace(' ', '_')}">
                <div class="logo-row">
                    <img class="logo-img" src="{logo_base64}" alt="Logo">
                </div>
                <div class="title-row">
                    <div class="inst-main-header">CONCORDIA COLLEGE KASUR</div>
                </div>
                <div class="banner-row">
                    <div class="doc-type-banner">RESULT CARD</div>
                </div>
                <table class="meta-layout-table">
                    <tr>
                        <td style="width: 38%;">Name: <span class="underlined-value-span" style="width: 82%;">{name}</span></td>
                        <td style="width: 15%;">ID: <span class="underlined-value-span" style="width: 70%;">{current_id_str}</span></td>
                        <td style="width: 20%;">Section: <span class="underlined-value-span" style="width: 62%;">{section}</span></td>
                        <td style="width: 14%;">Class: <span class="underlined-value-span" style="width: 55%;">{grade_class}</span></td>
                        <td style="width: 13%;">Test: <span class="underlined-value-span" style="width: 60%;">{test_name}</span></td>
                    </tr>
                </table>
                <table class="doc-data-table">
                    <thead>
                        <tr>
                        <th style="text-align: left; width: 45%; padding-left: 10px;">Subjects</th>
                        <th style="width: 11%;">Obt. Marks</th>
                        <th style="width: 11%;">Total Marks</th>
                        <th style="width: 11%;">Pass Marks</th>
                        <th style="width: 11%;">Age%</th>
                        <th style="width: 11%;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            student_failed_any_subject = False
            has_valid_marks_data = False

            for sub in subjects_list:
                sub_clean = sub.upper().strip()
                match = pd.DataFrame()
                if not raw_marks.empty:
                    match = raw_marks[raw_marks['subject'].astype(str).str.upper().str.strip() == sub_clean]
                    if match.empty:
                        match = raw_marks[raw_marks['subject'].astype(str).str.upper().str.contains(sub_clean[:4], regex=False, na=False)]

                obt_disp, tot_marks_num, pass_marks_num, per_disp, status_disp = "-", 100, 40, "-", "-"
                
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
                            status_disp = "Pass" if num_obt >= pass_marks_num else "Fail"
                            if num_obt < pass_marks_num: student_failed_any_subject = True
                    except Exception: pass
                else:
                    grand_total_marks += 100
                
                compiled_html += f"""
                <tr>
                    <td style="text-align: left; padding-left: 10px;">{sub}</td>
                    <td>{obt_disp}</td>
                    <td>{tot_marks_num}</td>
                    <td>{pass_marks_num}</td>
                    <td>{per_disp}</td>
                    <td style="font-weight: bold;">{status_disp}</td>
                </tr>
                """
            
            grand_per_disp = f"{int((grand_obtained_marks / grand_total_marks) * 100)}%" if has_valid_marks_data and grand_total_marks > 0 else "0%"
            grand_status_disp = "Fail" if student_failed_any_subject else "Pass" if has_valid_marks_data else "-"

            remarks_text = "No academic metrics verified for current exam context."
            if has_valid_marks_data:
                if student_failed_any_subject:
                    remarks_text = f"Unsatisfactory academic status for {test_name}. Performance deficiencies detected."
                else:
                    grand_percentage = (grand_obtained_marks / grand_total_marks) * 100 if grand_total_marks > 0 else 0
                    if grand_percentage >= 80: remarks_text = "Excellent work! Highly commendable progress achievement."
                    elif grand_percentage >= 60: remarks_text = "Good overall score. Capable of higher distinctions with systematic preparation."
                    else: remarks_text = "Fair tracking evaluation. Operational margins exist for improvement."

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
                
                <div class="section-header-title" style="border-bottom: 1px dashed #000;">ATTENDANCE REPORT</div>
                <table class="attendance-matrix-table">
                    <thead>
                        <tr>
                            <th style="width: 14%;">Metric</th>
                            {''.join([f'<th style="width: 6.5%;">{m}</th>' for m in DISPLAY_MONTHS])}
                            <th style="width: 8%;">Over All Att.</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="row-title-cell">Total Days</td>
                            {''.join([f'<td>{att_cells[m]["td"]}</td>' for m in DISPLAY_MONTHS])}
                            <td style="font-weight: bold;">{att_cells["Over All Att."]["td"]}</td>
                        </tr>
                        <tr>
                            <td class="row-title-cell">Att. Days</td>
                            {''.join([f'<td>{att_cells[m]["pd"]}</td>' for m in DISPLAY_MONTHS])}
                            <td style="font-weight: bold;">{att_cells["Over All Att."]["pd"]}</td>
                        </tr>
                        <tr>
                            <td class="row-title-cell">Age%</td>
                            {''.join([f'<td>{att_cells[m]["pct"]}</td>' for m in DISPLAY_MONTHS])}
                            <td style="font-weight: bold;">{att_cells["Over All Att."]["pct"]}</td>
                        </tr>
                    </tbody>
                </table>
                
                <div style="font-size:14px; margin-top:30px; margin-bottom:15px;">
                    Remarks: <span style="font-weight: bold; border-bottom: 1px solid #000; padding-bottom: 2px; display: inline-block; width: 90%; font-style: italic;">{remarks_text}</span>
                </div>
                
                <table style="width:100%; margin-top:40px;">
                    <tr>
                        <td style="text-align: left; width: 40%; font-weight: bold; border-top:1px solid #000; padding-top:5px;">Class Incharge Signature</td>
                        <td style="width:30%;"></td>
                        <td style="text-align: right; width: 30%; font-weight: bold; border-top:1px solid #000; padding-top:5px;">Principal</td>
                    </tr>
                </table>
            </div>
            <div class="print-page-break-divider"></div>
            """

        # --------------------------------------------------------------------------
        # MODULE D: EXPORT ACTIONS SCRIPT & EXTERNAL UI DISPLAY HOOKS
        # --------------------------------------------------------------------------
        compiled_html += """
        <script>
            document.getElementById('save-single-card-trigger').addEventListener('click', function() {
                const targetCard = document.querySelector('.official-card-container');
                if (!targetCard) return alert("No layout configuration found.");
                const sName = targetCard.getAttribute('data-student-name') || "student";
                const sId = targetCard.id || "result";
                html2canvas(targetCard, { scale: 2, useCORS: true }).then(canvas => {
                    const dlLink = document.createElement('a');
                    dlLink.download = `${sId}_${sName}.png`;
                    dlLink.href = canvas.toDataURL('image/png');
                    dlLink.click();
                });
            });

            document.getElementById('save-section-cards-trigger').addEventListener('click', async function() {
                const allCards = document.querySelectorAll('.official-card-container');
                if (allCards.length === 0) return alert("No active cards to compile.");
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
                    alert("An error occurred compiling image packages.");
                } finally {
                    actionBtn.innerText = primaryLabel;
                    actionBtn.disabled = false;
                }
            });
        </script>
        </body>
        </html>
        """
        components.html(compiled_html, height=950, scrolling=True)

    elif submit_execution and students_to_print.empty:
        if print_scope == "👤 Single Student Card":
            st.warning("⚠️ No student records match the given Roll ID and Session selection details.")
        else:
            st.warning(f"⚠️ No active student rows found matching section group: '{active_section}' for {selected_class} ({selected_session}).")
# ==============================================================================
# ROUTER INTEGRATION: 👨‍🏫 TEACHER MANAGEMENT MODULE
# ==============================================================================
if menu_choice == "👨‍🏫 Teacher Management":
    st.title("👨‍🏫 Teacher Allocation & Performance Engine")
    
    # Safely acquire access credentials
    current_user = st.session_state.get('username', 'admin')
    current_role = st.session_state.get('role', 'controller') 
    
    # Updated menu options keeping allocations, marks portal, and analysis
    menu_options = [
        "Subject Allocations", 
        "Class Incharge Allocations", 
        "Teacher Marks Portal", 
        "Teacher Analysis"
    ]
    sub_menu = st.sidebar.radio("Navigate Module:", menu_options, key="teacher_sub_menu")

    # ---------------------------------------------------------
    # SUB-MODULE ROUTING (Fixed Syntax & Indentation)
    # ---------------------------------------------------------
    
    # CRITICAL FIX: The first option must start with a clean 'if' statement
    if sub_menu == "Subject Allocations":
        st.subheader("📋 Subject Allocation Matrix")
        st.markdown("Map faculty members to their respective subjects and class tracking matrices.")
        # ⬇️ PASTE YOUR ORIGINAL "SUBJECT ALLOCATIONS" CODE HERE ⬇️
        
    elif sub_menu == "Class Incharge Allocations":
        st.subheader("👑 Class Incharge Allocations")
        st.markdown("Assign master class incharge responsibilities to registered faculty profiles.")
        # ⬇️ PASTE YOUR ORIGINAL "CLASS INCHARGE ALLOCATIONS" CODE HERE ⬇️
        
    elif sub_menu == "Teacher Marks Portal":
        st.subheader("📝 Faculty Marks Entry Portal")
        # ⬇️ PASTE YOUR ORIGINAL "TEACHER MARKS PORTAL" CODE HERE ⬇️
        
    elif sub_menu == "Teacher Analysis":
        st.subheader("📊 Performance Analytics Dashboard")
        # ⬇️ PASTE YOUR ORIGINAL "TEACHER ANALYSIS" CODE HERE ⬇️

        
# ----------------- 📈 ACADEMIC ANALYSIS REPORTS -----------------
elif menu_choice == "📈 Academic Analysis Reports":
    st.title("📊 Advanced Academic Analytics")
    
    # 1. Fetch raw underlying dataset matrix
    raw_df = fetch_analytics_data() 
    
    if not raw_df.empty:
        # Pre-process, format data types and align base structures safely
        raw_df['marks_obtained'] = pd.to_numeric(raw_df['marks_obtained'], errors='coerce').fillna(0.0)
        raw_df['total_marks'] = pd.to_numeric(raw_df['total_marks'], errors='coerce').fillna(1.0)
        
        # Reverse map DISCIPLINE_SECTIONS_MAP to decode underlying structural data patterns
        section_to_discipline_map = {}
        for disc_name, class_dict in DISCIPLINE_SECTIONS_MAP.items():
            for class_level, sections_list in class_dict.items():
                for sec in sections_list:
                    section_to_discipline_map[str(sec).strip().upper()] = disc_name

        # Assign calculated values directly to columns 
        raw_df['discipline'] = raw_df['section'].apply(
            lambda x: section_to_discipline_map.get(str(x).strip().upper(), 'OTHER')
        )

        # ==============================================================================
        # ⚙️ STRICT SEQUENTIAL FILTER CASCADE MATRIX
        # ==============================================================================
        st.markdown("### ⚙️ Filter Configuration Hierarchy")
        
        # Row 1: Session & Academic System Structure Selection Nodes
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            session_options = sorted(list(raw_df['session'].unique()))
            selected_sessions = st.multiselect("1️⃣ Select Active Sessions:", session_options, default=session_options, key="an_sess_filt")
            
        # Filter down dataset to isolate classes based on system patterns
        session_filtered_df = raw_df[raw_df['session'].isin(selected_sessions if selected_sessions else session_options)]
        
        with col_f2:
            def determine_system(row_class):
                return "🎓 Semester System" if "SEMESTER" in str(row_class).upper() else "🗓️ Annual System"
            
            session_filtered_df['academic_system'] = session_filtered_df['class'].apply(determine_system)
            system_options = sorted(list(session_filtered_df['academic_system'].unique()))
            selected_systems = st.multiselect("2️⃣ Select Academic System:", system_options, default=system_options, key="an_sys_filt")

        system_filtered_df = session_filtered_df[session_filtered_df['academic_system'].isin(selected_systems if selected_systems else system_options)]

        # Row 2: Cascading Discipline & Bound Sections Options Layout Nodes
        col_f3, col_f4 = st.columns(2)
        with col_f3:
            discipline_options = sorted(list(system_filtered_df['discipline'].unique()))
            selected_disciplines = st.multiselect("3️⃣ Filter Disciplines:", discipline_options, default=discipline_options, key="an_disc_filt")
            
        disc_filtered_df = system_filtered_df[system_filtered_df['discipline'].isin(selected_disciplines if selected_disciplines else discipline_options)]
        
        with col_f4:
            section_options = sorted(list(disc_filtered_df['section'].unique()))
            selected_sections = st.multiselect("4️⃣ Filter Sections:", section_options, default=section_options, key="an_sec_filt")

        # Core operational dataframe generated dynamically downstream
        df = disc_filtered_df[disc_filtered_df['section'].isin(selected_sections if selected_sections else section_options)]

        # ==============================================================================
        # 📊 ANALYTICS DASHBOARD TABS
        # ==============================================================================
        st.markdown("---")
        if df.empty:
            st.warning("⚠️ No records match the current filter configuration hierarchy selected above.")
        else:
            tab1, tab2, tab3, tab4 = st.tabs(["🏆 Toppers", "⚠️ Bottom Performers", "🏢 Discipline Analysis", "🎓 Comparison Engine"])
            
            with tab1:
                st.subheader("🏆 Section Toppers Directory")
                agg = df.groupby(['id', 'name', 'discipline', 'section'])[['marks_obtained', 'total_marks']].sum().reset_index()
                agg['Percentage'] = (agg['marks_obtained'] / agg['total_marks'].replace(0, 1)) * 100
                st.dataframe(
                    agg.sort_values('Percentage', ascending=False).head(10), 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={"Percentage": st.column_config.NumberColumn(format="%.2f%%")}
                )

            with tab2:
                st.subheader("⚠️ Bottom Performers Focus List")
                agg_b = df.groupby(['id', 'name', 'discipline', 'section'])[['marks_obtained', 'total_marks']].sum().reset_index()
                agg_b['Percentage'] = (agg_b['marks_obtained'] / agg_b['total_marks'].replace(0, 1)) * 100
                st.dataframe(
                    agg_b.sort_values('Percentage', ascending=True).head(10), 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={"Percentage": st.column_config.NumberColumn(format="%.2f%%")}
                )

            with tab3:
                st.subheader("🏢 Discipline Performance & Grade Distribution Overview")
                
                if not df.empty:
                    # 1. Aggregate total marks at the individual student level
                    student_perf = df.groupby(['id', 'name', 'discipline'])[['marks_obtained', 'total_marks']].sum().reset_index()
                    student_perf['Final_Percentage'] = (student_perf['marks_obtained'] / student_perf['total_marks'].replace(0, 1)) * 100

                    # 2. Assign Grades strictly based on your specified grading tiers
                    def assign_grade_details(pct):
                        if 95.0 <= pct <= 100.0:
                            return "A++"
                        elif 80.0 <= pct < 95.0:
                            return "A+"
                        elif 70.0 <= pct < 80.0:
                            return "A"
                        elif 60.0 <= pct < 70.0:
                            return "B"
                        elif 50.0 <= pct < 60.0:
                            return "C"
                        elif 40.0 <= pct < 50.0:
                            return "D"
                        elif 33.0 <= pct < 40.0:
                            return "E"
                        else:
                            return "F"

                    student_perf['Grade'] = student_perf['Final_Percentage'].apply(assign_grade_details)

                    # 3. Dropdown filter to select specific Academic Disciplines
                    available_disciplines = sorted(list(student_perf['discipline'].unique()))
                    selected_analysis_disc = st.selectbox("🎯 Select Discipline to Analyze:", available_disciplines, key="disc_analysis_select")
                    
                    # Filter dataset to the chosen discipline
                    filtered_students = student_perf[student_perf['discipline'] == selected_analysis_disc]
                    total_discipline_students = len(filtered_students)

                    # 4. Generate the complete breakdown table mapping
                    grade_order = ["A++", "A+", "A", "B", "C", "D", "E", "F"]
                    grade_scale_mapped = {
                        "A++": {"Percentage": "95% – 100%",  "Marks": "1140 – 1200", "Remarks": "Outstanding"},
                        "A+":  {"Percentage": "80% – 94.99%", "Marks": "960 – 1139",  "Remarks": "Exceptional"},
                        "A":   {"Percentage": "70% – 79.99%", "Marks": "840 – 959",   "Remarks": "Excellent"},
                        "B":   {"Percentage": "60% – 69.99%", "Marks": "720 – 839",   "Remarks": "Very Good"},
                        "C":   {"Percentage": "50% – 59.99%", "Marks": "600 – 719",   "Remarks": "Good"},
                        "D":   {"Percentage": "40% – 49.99%", "Marks": "480 – 599",   "Remarks": "Fair"},
                        "E":   {"Percentage": "33% – 39.99%", "Marks": "396 – 479",   "Remarks": "Satisfactory"},
                        "F":   {"Percentage": "Below 33%",     "Marks": "Below 396",   "Remarks": "Fail"}
                    }

                    grade_counts = filtered_students['Grade'].value_counts()
                    
                    analysis_report_data = []
                    for grade in grade_order:
                        count = int(grade_counts.get(grade, 0))
                        analysis_report_data.append({
                            "Percentage": grade_scale_mapped[grade]["Percentage"],
                            "Marks (out of 1200)": grade_scale_mapped[grade]["Marks"],
                            "Grade": grade,
                            "Remarks": grade_scale_mapped[grade]["Remarks"],
                            "Student Count": count
                        })

                    # Convert to DataFrame
                    analysis_df = pd.DataFrame(analysis_report_data)

                    # 5. Create a clean display copy and append the TOTAL row at the bottom
                    display_df = analysis_df.copy()
                    
                    # Append structural summary total row
                    total_row = pd.DataFrame([{
                        "Percentage": "—",
                        "Marks (out of 1200)": "—",
                        "Grade": "TOTAL STUDENTS",
                        "Remarks": "—",
                        "Student Count": total_discipline_students
                    }])
                    display_df = pd.concat([display_df, total_row], ignore_index=True)

                    # --- UI Columns Rendering ---
                    col_chart, col_stats = st.columns([3, 2])
                    
                    with col_chart:
                        st.markdown(f"##### 📊 Grade Distribution Histogram ({selected_analysis_disc})")
                        chart_payload = analysis_df.set_index("Grade")[["Student Count"]]
                        st.bar_chart(chart_payload)
                        
                    with col_stats:
                        st.markdown(f"##### 📋 Performance Metrics")
                        st.metric(label="Total Evaluated Cohort Size", value=total_discipline_students)
                        if total_discipline_students > 0:
                            passed = len(filtered_students[filtered_students['Grade'] != 'F'])
                            st.metric(label="Passing Student Volume (Grade E or above)", value=f"{passed} / {total_discipline_students}")

                    # Render the final data table matrix with the total summary row cleanly visible
                    st.markdown("##### 📝 Structured Grade Distribution Table")
                    st.dataframe(
                        display_df, 
                        use_container_width=True, 
                        hide_index=True
                    )
                else:
                    st.info("No underlying dataset matched your current query filters.")

            with tab4:
                st.subheader("🎓 Comparison Engine")
                c_a, c_b = st.columns(2)
                test_1 = c_a.selectbox("Exam 1:", AVAILABLE_EXAMS, key="c_t1")
                test_2 = c_b.selectbox("Exam 2:", AVAILABLE_EXAMS, key="c_t2")
                
                comp = df[df['exam_type'].isin([test_1, test_2])]
                if not comp.empty:
                    pivot = comp.pivot_table(
                        index=['id', 'name', 'discipline', 'section'], 
                        columns='exam_type', 
                        values='marks_obtained', 
                        aggfunc='sum'
                    ).reset_index()
                    st.dataframe(pivot, use_container_width=True, hide_index=True)
                else: 
                    st.info("Select two exams to see data comparison.")
    else:
        st.info("No data available to analyze inside database.")

# ====================================================================================
# UNIFIED CENTRAL MODULE: 👥 STUDENT OPERATIONS MANAGEMENT
# ====================================================================================
elif menu_choice == "👥 Student Operations Management":
    st.title("👥 Student Operations Management Console")
    st.markdown("Centralized workflow for profile records, status adjustments, audit trails, and batch promotions.")
    st.markdown("---")
    
    # --------------------------------------------------------------------------------
    # NATIVE SQLALCHEMY EXECUTOR ENGINE (Bypasses st.connection requirements)
    # --------------------------------------------------------------------------------
    def local_engine_query(sql_str, param_dict=None):
        """Safely executes data reads using raw connection contexts directly."""
        import pandas as pd
        if param_dict is None: param_dict = {}
        try:
            # 1. Try finding 'engine' or 'db_engine' globally from your app's main script core
            for engine_var in ['engine', 'db_engine', 'conn']:
                if engine_var in globals() and hasattr(globals()[engine_var], "connect"):
                    with globals()[engine_var].connect() as ctx:
                        return pd.read_sql_query(text(sql_str), ctx, params=param_dict)
            
            # 2. Try looking for pre-existing utility functions
            for func_name in ['run_query', 'execute_query', 'db_query']:
                if func_name in globals() and func_name != 'local_engine_query':
                    try:
                        return globals()[func_name](sql_str, param_dict)
                    except Exception:
                        pass
                        
            st.error("🚨 Active database connector instance ('engine' or 'db_engine') could not be discovered automatically.")
            return pd.DataFrame()
        except Exception as err:
            st.error(f"Execution Error: {str(err)}")
            return pd.DataFrame()

    def local_engine_update(sql_str, param_dict=None):
        """Safely executes transactional record mutations directly."""
        if param_dict is None: param_dict = {}
        try:
            # 1. Try updating via raw SQLAlchemy context managers
            for engine_var in ['engine', 'db_engine', 'conn']:
                if engine_var in globals() and hasattr(globals()[engine_var], "begin"):
                    with globals()[engine_var].begin() as ctx:
                        ctx.execute(text(sql_str), param_dict)
                    return True
            
            # 2. Try mapping to custom mutation tools
            for func_name in ['run_action', 'execute_update', 'execute_action', 'db_update']:
                if func_name in globals():
                    globals()[func_name](sql_str, param_dict)
                    return True
                    
            st.error("🚨 Transaction Engine instance could not be found.")
            return False
        except Exception as err:
            st.error(f"Mutation Error: {str(err)}")
            return False

    # ====================================================================================
    # FLOW CHART LEVEL 1 & 2: GLOBAL CONTEXT SELECTION MATRIX (Dynamic Track Routing)
    # ====================================================================================
    st.markdown("### 🌐 Step 1 & 2: Global Configuration Parameters")

    col_g1, col_g2, col_g3 = st.columns(3)

    session_options = st.session_state.get("available_sessions", ["2024-26", "2025-27", "2026-28", "2027-29"])
    active_session = st.session_state.get("current_session", "2026-28")
    default_session_idx = session_options.index(active_session) if active_session in session_options else 0

    with col_g1:
        global_session = st.selectbox("📅 Select Long-Term Cohort Session:", session_options, index=default_session_idx, key="global_stud_sess_filter")

    with col_g2:
        global_system_display = st.selectbox("🎓 Select Academic System:", ["Annual System", "Semester System"], key="global_stud_sys_filter")
        global_system = "annual" if global_system_display == "Annual System" else "semester"

    with col_g3:
        # ADVANCED LOGIC: Fetch real options present in database to prevent missing mixed classifications
        db_classes_df = local_engine_query("""
            SELECT DISTINCT class FROM students 
            WHERE session = :sess AND LOWER(TRIM(system_type)) LIKE LOWER(TRIM(:sys)) || '%'
        """, {"sess": global_session, "sys": global_system})
        
        db_classes = [str(c).strip() for c in db_classes_df['class'].tolist() if c] if not db_classes_df.empty else []
        
        # Merge database entries with default presets so choices are never completely empty
        if global_system == "annual":
            global_term_label = "🏫 Current Grade Level Focus:"
            global_term_options = sorted(list(set(db_classes + ["11th", "12th", "Semester 1"])))
        else:
            global_term_label = "⏱️ Current Semester Focus:"
            global_term_options = sorted(list(set(db_classes + ["Semester 1", "Semester 2", "Semester 3", "Semester 4"])))
            
        global_term = st.selectbox(global_term_label, global_term_options, key="global_stud_term_filter")
        
    st.markdown("---")

    workspace_mode = st.radio(
        "**Choose target operational workflow path:**",
        ["🔍 Single Student Records Hub", "🗂️ Whole Section Batch Operations"],
        horizontal=True,
        key="ops_hub_split_path"
    )
    st.markdown("###")

    # --------------------------------------------------------------------------------
    # BRANCH A: SINGLE STUDENT WORKSPACE (Sub-Modules 1, 2, 3, 4, 5 & 7)
    # --------------------------------------------------------------------------------
    if workspace_mode == "🔍 Single Student Records Hub":
        st.markdown("### 👤 Single Student Operations Workspace")
        search_id = st.text_input("🔍 Search Student by ID:", key="single_search_id_input").strip()
        
        if search_id:
            if not search_id.isdigit():
                st.error("❌ Invalid Format: Student ID must contain numbers only.")
            else:
                # UNIQUE ID LOOKUP: Matches strictly on unique ID + Session key boundary
                stu_df = local_engine_query("""
                    SELECT id, name, class, section, session, status, system_type 
                    FROM students 
                    WHERE id = :id AND session = :sess
                """, {"id": int(search_id), "sess": global_session})
                
                is_mismatched = False
                if not stu_df.empty:
                    actual_sys = str(stu_df.iloc[0]['system_type']).lower()
                    actual_class = str(stu_df.iloc[0]['class']).lower()
                    if (global_system not in actual_sys) or (global_term.lower() != actual_class):
                        is_mismatched = True

                if stu_df.empty:
                    st.warning(f"⚠️ No matching student profile found with ID '{search_id}' within Session {global_session}.")
                else:
                    student = stu_df.iloc[0]
                    s_id = int(student['id'])
                    s_name = str(student['name']).upper()
                    
                    if is_mismatched:
                        st.warning(f"⚠️ **Data Classification Conflict Discovered:** Student is registered as **{student['system_type']} ({student['class']})**, but your global search headers are set to **{global_system_display} ({global_term})**.")
                    
                    st.info(f"📂 **Active Workspace:** {s_name} (ID: {s_id}) | Current Setup: **{student['class']} - Section {student['section']}**")
                    
                    global_remarks = st.text_input("📝 Action Audit Log Remarks *", placeholder="Provide explicit reason context for these adjustments", key="global_mut_remarks")
                    st.markdown("###")

                    col_sub_left, col_sub_right = st.columns(2)

                    with col_sub_left:
                        # ----------------------------------------------------------------------------
                        # SUB-MODULE 1: SESSION CHANGE (Cohort Re-assignment)
                        # ----------------------------------------------------------------------------
                        with st.container(border=True):
                            st.markdown("#### 1️⃣ Session Track Migration")
                            st.caption(f"Current Permanent Cohort Cycle: `{student['session']}`")
                            target_sess = st.selectbox("Migrate to Different Multi-Year Session:", session_options, index=session_options.index(student['session']) if student['session'] in session_options else 0, key="sub_mod_sess_drop")
                            
                            if st.button("🔄 Change Session Track", use_container_width=True):
                                local_engine_update("UPDATE students SET session = :session WHERE id = :id", {"session": target_sess, "id": s_id})
                                local_engine_update("""
                                    INSERT INTO student_logs (student_id, change_type, old_value, new_value, log_date, remarks) 
                                    VALUES (:id, 'SESSION_CHANGE', :old, :new, CURRENT_DATE, :rem)
                                """, {"id": s_id, "old": student['session'], "new": target_sess, "rem": global_remarks.strip() if global_remarks.strip() else "Session Relocation"})
                                st.toast("✅ Student cohort group shifted successfully!")
                                st.rerun()

                        # ----------------------------------------------------------------------------
                        # SUB-MODULE 3: SECTION CHANGE
                        # ----------------------------------------------------------------------------
                        with st.container(border=True):
                            st.markdown("#### 3️⃣ Section Re-allocation")
                            st.caption(f"Current Assigned Section: `{student['section']}`")
                            
                            section_pool_df = local_engine_query("""
                                SELECT DISTINCT section FROM students 
                                WHERE LOWER(TRIM(class)) = LOWER(TRIM(:cls)) AND session = :sess
                            """, {"cls": student['class'], "sess": global_session})
                            
                            fallback_sections = ["A", "B", "C", "MQ1", "MQ2", "EK1", "EQ1"]
                            available_sections = sorted(list(set([str(s) for s in section_pool_df['section'].tolist() if s] + fallback_sections)))
                            
                            target_sec = st.selectbox("Select Target Section:", available_sections, index=available_sections.index(student['section']) if student['section'] in available_sections else 0, key="sub_mod_sec_drop")
                            
                            if st.button("📐 Update Section Allocation", use_container_width=True):
                                local_engine_update("UPDATE students SET section = :section WHERE id = :id", {"section": target_sec, "id": s_id})
                                local_engine_update("""
                                    INSERT INTO student_logs (student_id, change_type, old_value, new_value, log_date, remarks) 
                                    VALUES (:id, 'SECTION_TRANSFER', :old, :new, CURRENT_DATE, :rem)
                                """, {"id": s_id, "old": student['section'], "new": target_sec, "rem": global_remarks.strip() if global_remarks.strip() else "Section Reallocation"})
                                st.toast("✅ Section reassigned successfully!")
                                st.rerun()

                        # ----------------------------------------------------------------------------
                        # SUB-MODULE 5: DELETE FROM SYSTEM
                        # ----------------------------------------------------------------------------
                        with st.container(border=True):
                            st.markdown("#### 5️⃣ Delete from System")
                            st.caption("⚠️ Permanent eviction mechanism. This data completely drops out of the operational database.")
                            confirm_eviction = st.checkbox("Verify authorization to purge entry rows permanently", key="evict_check_box_gate")
                            
                            if st.button("🗑️ Permanent Eviction Trigger", type="primary", use_container_width=True, disabled=not confirm_eviction):
                                local_engine_update("DELETE FROM students WHERE id = :id", {"id": s_id})
                                st.error("Record row purged permanently from database.")
                                st.rerun()

                    with col_sub_right:
                        # ----------------------------------------------------------------------------
                        # SUB-MODULE 2: STUDENT STATUS
                        # ----------------------------------------------------------------------------
                        with st.container(border=True):
                            st.markdown("#### 2️⃣ Student Status (Left / Re-Active)")
                            st.caption(f"Current profile operational flag: `{student['status']}`")
                            
                            status_c1, status_c2 = st.columns(2)
                            with status_c1:
                                if st.button("🚪 Flag Profile: LEFT", use_container_width=True):
                                    local_engine_update("UPDATE students SET status = 'LEFT' WHERE id = :id", {"id": s_id})
                                    local_engine_update("""
                                        INSERT INTO student_logs (student_id, change_type, old_value, new_value, log_date, remarks) 
                                        VALUES (:id, 'STATUS_CHANGE', :old, 'LEFT', CURRENT_DATE, :rem)
                                    """, {"id": s_id, "old": student['status'], "rem": global_remarks.strip() if global_remarks.strip() else "Marked as Departed"})
                                    st.warning("Profile state flagged as Left.")
                                    st.rerun()
                            with status_c2:
                                if st.button("🟢 Flag Profile: ACTIVE", use_container_width=True):
                                    local_engine_update("UPDATE students SET status = 'ACTIVE' WHERE id = :id", {"id": s_id})
                                    local_engine_update("""
                                        INSERT INTO student_logs (student_id, change_type, old_value, new_value, log_date, remarks) 
                                        VALUES (:id, 'STATUS_CHANGE', :old, 'ACTIVE', CURRENT_DATE, :rem)
                                    """, {"id": s_id, "old": student['status'], "rem": global_remarks.strip() if global_remarks.strip() else "Manually Re-activated"})
                                    st.toast("Profile status restored to Active.")
                                    st.rerun()

                        # ----------------------------------------------------------------------------
                        # SUB-MODULE 4: STUDENT DATA & SYSTEM EDIT
                        # ----------------------------------------------------------------------------
                        with st.container(border=True):
                            st.markdown("#### 4️⃣ Data Registry & Academic System Editor")
                            st.caption("🔄 Use this module to repair classification mistakes directly.")
                            
                            edit_name = st.text_input("Edit Legal Full Name:", value=str(student['name']))
                            edit_sys_display = st.selectbox("Target Academic System Track:", ["Annual System", "Semester System"], index=0 if "annual" in str(student['system_type']).lower() else 1)
                            edit_sys_value = "Annual System" if edit_sys_display == "Annual System" else "Semester System"
                            
                            edit_term_options = ["11th", "12th", "Semester 1", "Semester 2", "Semester 3", "Semester 4"]
                            current_class_string = str(student['class'])
                            default_cls_idx = edit_term_options.index(current_class_string) if current_class_string in edit_term_options else 0
                            
                            edit_term = st.selectbox("Update Level/Term Assignment:", edit_term_options, index=default_cls_idx)
                            
                            if st.button("💾 Save Profile Matrix Edits", use_container_width=True):
                                local_engine_update("""
                                    UPDATE students SET name = :name, system_type = :sys, class = :cls WHERE id = :id
                                """, {"name": edit_name.strip(), "sys": edit_sys_value, "cls": edit_term, "id": s_id})
                                st.toast("✅ Master registration parameters corrected successfully!")
                                st.rerun()

                    # --------------------------------------------------------------------------------
                    # SUB-MODULE 7: HISTORY OF ACTIVITIES
                    # --------------------------------------------------------------------------------
                    st.markdown("---")
                    with st.container(border=True):
                        st.markdown("### 7️⃣ History of Activities Log")
                        st.caption(f"Showing localized transaction and profile mutation logs for Student ID: {s_id}")
                        
                        logs_df = local_engine_query("""
                            SELECT change_type AS "Action Type", old_value AS "Prior Value", 
                                   new_value AS "Assigned Value", log_date AS "Timestamp", 
                                   remarks AS "Context/Justification"
                            FROM student_logs WHERE student_id = :id ORDER BY id DESC
                        """, {"id": s_id})
                        
                        if logs_df.empty:
                            st.info("💡 No historical system modifications found for this student.")
                        else:
                            st.dataframe(logs_df, use_container_width=True)

    # --------------------------------------------------------------------------------
    # BRANCH B: WHOLE SECTION COHORT ACTIONS (Sub-Module 6: Promotion Engine)
    # --------------------------------------------------------------------------------
    elif workspace_mode == "🗂️ Whole Section Batch Operations":
        st.markdown("### 📦 Bulk Section Operations Matrix")
        
        sections_data = local_engine_query("""
            SELECT DISTINCT section FROM students 
            WHERE session = :sess 
              AND LOWER(TRIM(class)) = LOWER(TRIM(:term))
              AND status = 'ACTIVE' 
            ORDER BY section
        """, {"sess": global_session, "term": global_term})
        
        found_sections = [str(sec) for sec in sections_data['section'].tolist() if sec] if not sections_data.empty else []
        
        if not found_sections:
            st.info(f"💡 No active student groups found inside data focus group '{global_term}' for the `{global_session}` session pool.")
        else:
            with st.container(border=True):
                st.markdown("### 6️⃣ Cohort Class/Term Promotion Engine")
                st.info(f"🔄 Promoting students will shift their active lifecycle step but preserve their permanent **{global_session}** session footprint.")
                
                selected_source_sec = st.selectbox("📁 Select Source Section to Update:", found_sections)
                
                if "11" in global_term:
                    inferred_next_term = "12th"
                elif "12" in global_term:
                    inferred_next_term = "Graduated/Alumni"
                else:
                    semester_progression_map = {
                        "Semester 1": "Semester 2",
                        "Semester 2": "Semester 3",
                        "Semester 3": "Semester 4",
                        "Semester 4": "Graduated/Alumni"
                    }
                    inferred_next_term = semester_progression_map.get(global_term, "Graduated/Alumni")
                
                st.markdown(f"##### 🎯 Destination Section Setup (Advancing to: **{inferred_next_term}**)")
                
                dest_sections_df = local_engine_query("""
                    SELECT DISTINCT section FROM students 
                    WHERE session = :sess AND LOWER(TRIM(class)) = LOWER(TRIM(:next_term))
                """, {"sess": global_session, "next_term": inferred_next_term})
                
                base_options = ["A", "B", "C", "MQ1", "MQ2", "EK1", "EQ1"]
                final_dest_options = sorted(list(set([str(s) for s in dest_sections_df['section'].tolist() if s] + base_options)))
                
                target_dest_section = st.selectbox("Select Target Destination Section Assignment:", final_dest_options)
                
                if st.button("🚀 Execute Mass Class Cohort Promotion", type="primary", use_container_width=True):
                    cohort_roster = local_engine_query("""
                        SELECT id, class, section, session FROM students 
                        WHERE session = :sess 
                          AND section = :sec 
                          AND LOWER(TRIM(class)) = LOWER(TRIM(:term))
                          AND status = 'ACTIVE'
                    """, {"sess": global_session, "sec": selected_source_sec, "term": global_term})
                    
                    import uuid
                    promotion_batch_id = f"PROMO-{str(uuid.uuid4())[:6].upper()}"
                    
                    for _, student_row in cohort_roster.iterrows():
                        local_engine_update("""
                            INSERT INTO promotion_history (student_id, old_class, old_section, old_session, new_class, new_section, batch_id)
                            VALUES (:s_id, :old_cls, :old_sec, :old_sess, :new_cls, :new_sec, :b_id)
                        """, {
                            "s_id": int(student_row['id']), "old_cls": student_row['class'], 
                            "old_sec": student_row['section'], "old_sess": student_row['session'], 
                            "new_cls": inferred_next_term, "new_sec": target_dest_section.upper(), 
                            "b_id": promotion_batch_id
                        })
                    
                    local_engine_update("""
                        UPDATE students 
                        SET class = :next_term, section = :next_sec
                        WHERE session = :sess 
                          AND section = :sec 
                          AND LOWER(TRIM(class)) = LOWER(TRIM(:term))
                          AND status = 'ACTIVE'
                    """, {
                        "next_term": inferred_next_term, "next_sec": target_dest_section.upper(), 
                        "sess": global_session, "sec": selected_source_sec, "term": global_term
                    })
                    
                    st.success(f"🎉 Success! Whole section advanced to **{inferred_next_term} ({target_dest_section})**.")
                    st.rerun()
        
   # ==============================================================================
# ROUTER INTEGRATION: ⚙️ ADMINISTRATIVE SYSTEM SETTINGS
# ==============================================================================
elif menu_choice == "⚙️ Settings":
    st.title("⚙️ Global Academic & Core Settings")
    st.markdown("Centralized administrative control console to manage institutional profiles, calendars, and evaluation tracks.")
    
    # Safely acquire access credentials
    current_user = st.session_state.get('username', 'admin')
    current_role = st.session_state.get('role', 'controller') 
    
    # Enforce role-based structural routing arrays (Appended new modules)
    if current_role == 'controller':
        settings_options = [
            "📝 Faculty Registration", 
            "📅 Sessions & Terms", 
            "🗂️ Section Master", 
            "📑 Test & Exam Frameworks",
            "🧬 Add Disciplines",
            "📚 Add Subject Mapping"
        ]
    else:
        settings_options = [
            "📝 Faculty Registration", 
            "📅 Sessions & Terms", 
            "🗂️ Section Master", 
            "📑 Test & Exam Frameworks",
            "🧬 Add Disciplines",
            "📚 Add Subject Mapping"
        ]
        
    sub_menu = st.sidebar.radio("Settings Sub-Categories:", settings_options, key="settings_sub_menu")

    # ==============================================================================
    # SUB-TAB HANDLING ENGINE (ROUTER LINKS)
    # ==============================================================================
    if sub_menu == "📅 Sessions & Terms":
        st.subheader("🗓️ Global Academic Session Management")
        st.info("Changing the active session here will instantly update the default values across all registration forms and reporting ledgers.")

        available_options = st.session_state["available_sessions"]
        current_active = st.session_state["current_session"]
        
        default_index = available_options.index(current_active) if current_active in available_options else 0

        chosen_session = st.selectbox(
            "Set Global Active Session Track:",
            options=available_options,
            index=default_index,
            key="global_settings_session_selector"
        )
        
        if st.button("💾 Apply Configuration Changes", type="primary"):
            st.session_state["current_session"] = chosen_session
            st.success(f"🚀 System configuration updated! Active session is now set to **{chosen_session}**.")
            st.rerun()

    elif sub_menu == "📝 Faculty Registration":
        pass 
        
    elif sub_menu == "🗂️ Section Master":
        pass 
        
    elif sub_menu == "📑 Test & Exam Frameworks":
        pass

    elif sub_menu == "🧬 Add Disciplines":
        pass

    elif sub_menu == "📚 Add Subject Mapping":
        pass

    # ==============================================================================
    # SUB-MODULE 1: FACULTY REGISTRATION TRACK
    # ==============================================================================
    if sub_menu == "📝 Faculty Registration":
        st.write("### ➕ Register New Faculty Member")

        with st.form("teacher_reg_form", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                new_teacher_id = st.number_input("Teacher ID Number (Numeric Only):", min_value=1, step=1, value=None, placeholder="e.g. 101")
                new_teacher_name = st.text_input("Teacher Full Name:", placeholder="e.g. Prof. Muhammad Ali").strip()
            with col_f2:
                new_teacher_phone = st.text_input("Contact Number:", placeholder="e.g. +923001234567").strip()
                new_teacher_email = st.text_input("Email Address:", placeholder="e.g. ali@institution.edu").strip()
                
            submit_faculty = st.form_submit_button("💾 Register Faculty Member", type="primary")
            
            if submit_faculty:
                if not new_teacher_id or not new_teacher_name:
                    st.error("❌ Both 'Teacher ID Number' and 'Teacher Full Name' are mandatory entries.")
                else:
                    try:
                        check_id = run_query("SELECT teacher_id FROM system_teachers WHERE teacher_id = :code", {"code": int(new_teacher_id)})
                        if not check_id.empty:
                            st.error(f"❌ A faculty member with the ID '{new_teacher_id}' is already registered.")
                        else:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO system_teachers (teacher_id, teacher_name, phone_number, email_address, status)
                                    VALUES (:code, :name, :phone, :email, 'ACTIVE')
                                """), {
                                    "code": int(new_teacher_id),
                                    "name": new_teacher_name,
                                    "phone": new_teacher_phone,
                                    "email": new_teacher_email
                                })
                            st.success(f"🎉 Successfully registered {new_teacher_name} with ID '{new_teacher_id}'!")
                            st.rerun()
                    except Exception as err:
                        st.error(f"❌ Failed to write record to the database: {err}")

        st.markdown("---")
        st.write("#### Registered Institutional Faculty")
        
        current_faculty = pd.DataFrame()
        try:
            current_faculty = run_query('SELECT teacher_id as "Teacher ID", teacher_name as "Teacher Name", phone_number as "Phone Number", email_address as "Email", status as "Status" FROM system_teachers ORDER BY teacher_name ASC')
        except Exception as e:
            st.error(f"⚠️ Failed to read faculty profiles from database: {e}")
            
        if not current_faculty.empty:
            st.dataframe(current_faculty, use_container_width=True, hide_index=True)
            
            st.markdown("### 🛠️ Manage Existing Faculty Members")
            faculty_list = [f"{row['Teacher ID']} - {row['Teacher Name']}" for _, row in current_faculty.iterrows()]
            selected_fac_str = st.selectbox("Select a Teacher Profile to Modify or Remove:", faculty_list, key="manage_fac_select")
            
            if selected_fac_str:
                selected_fac_id = int(selected_fac_str.split(" - ")[0])
                target_fac_row = current_faculty[current_faculty['Teacher ID'] == selected_fac_id].iloc[0]
                
                with st.form("edit_faculty_form"):
                    updated_fac_id = st.number_input("Modify Teacher ID Number:", min_value=1, step=1, value=int(target_fac_row['Teacher ID']))
                    updated_fac_name = st.text_input("Change Teacher Full Name:", value=str(target_fac_row['Teacher Name'])).strip()
                    updated_fac_phone = st.text_input("Update Contact Number:", value=str(target_fac_row['Phone Number'])).strip()
                    updated_fac_email = st.text_input("Update Email Address:", value=str(target_fac_row['Email'])).strip()
                    updated_fac_status = st.selectbox("Change Employment Status:", ["ACTIVE", "INACTIVE"], index=0 if target_fac_row['Status'] == 'ACTIVE' else 1)
                    
                    col_fu, col_fd = st.columns(2)
                    with col_fu:
                        save_fac = st.form_submit_button("💾 Save Profile Changes", type="primary", use_container_width=True)
                    with col_fd:
                        confirm_fac_del = st.checkbox("⚠️ Confirm complete deletion", key="del_fac_chk")
                        delete_fac = st.form_submit_button("🗑️ Delete Profile Permanently", type="secondary", use_container_width=True)
                        
                if save_fac:
                    if not updated_fac_id or not updated_fac_name:
                        st.error("❌ Teacher ID and Teacher Name cannot be left blank.")
                    else:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE system_teachers 
                                    SET teacher_id = :new_id, teacher_name = :name, phone_number = :phone, email_address = :email, status = :status 
                                    WHERE teacher_id = :old_id
                                """), {
                                    "new_id": int(updated_fac_id),
                                    "name": updated_fac_name, 
                                    "phone": updated_fac_phone, 
                                    "email": updated_fac_email, 
                                    "status": updated_fac_status, 
                                    "old_id": selected_fac_id
                                })
                            st.success(f"🎉 Successfully updated profile details for {updated_fac_name}!")
                            st.rerun()
                        except Exception as err:
                            st.error(f"❌ Modification failed. The ID might conflict with another teacher's record: {err}")
                        
                if delete_fac:
                    if not confirm_fac_del:
                        st.error("Please check the confirmation box to authorize permanent deletion.")
                    else:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("DELETE FROM system_teachers WHERE teacher_id = :id"), {"id": selected_fac_id})
                            st.success("Faculty profile completely removed from system records.")
                            st.rerun()
                        except Exception as err:
                            st.error(f"❌ Cannot delete this teacher because they are currently assigned to active course allocations: {err}")
        else:
            st.info("No faculty profiles are currently registered.")

    # ==============================================================================
    # SUB-MODULE 2: SESSIONS & TERMS
    # ==============================================================================
    elif sub_menu == "📅 Sessions & Terms":
        st.subheader("📅 Academic Session Management")
        
        if current_role == 'controller':
            with st.form("session_reg_form", clear_on_submit=True):
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    new_session_name = st.text_input("Session Code/Year:", placeholder="e.g. 2025-27")
                with col_s2:
                    new_session_status = st.selectbox("Session Status:", options=["ACTIVE", "INACTIVE"])
                    
                submit_session = st.form_submit_button("💾 Save Session to Registry")
                
                if submit_session:
                    if new_session_name.strip() == "":
                        st.error("Session Name is required.")
                    else:
                        check_existing = run_query("SELECT id FROM academic_sessions WHERE UPPER(TRIM(session_name)) = UPPER(TRIM(:name))", {"name": new_session_name.strip()})
                        
                        if check_existing.empty:
                            run_update("""
                                INSERT INTO academic_sessions (session_name, status)
                                VALUES (:name, :status)
                            """, {
                                "name": new_session_name.strip(),
                                "status": new_session_status
                            })
                            st.success(f"🎉 Successfully registered session '{new_session_name.strip()}'!")
                            st.rerun()
                        else:
                            st.warning("A session with this name already exists.")
                            
        st.markdown("---")
        st.write("#### Registered Academic Sessions")
        
        current_sessions = pd.DataFrame()
        try:
            current_sessions = run_query('SELECT id as "ID", session_name as "Session Name", status as "Status" FROM academic_sessions ORDER BY session_name DESC')
        except Exception as e:
            st.error(f"⚠️ Failed to read session records from database: {e}")
            
        if not current_sessions.empty:
            st.dataframe(current_sessions, use_container_width=True, hide_index=True)
            
            st.markdown("### 🛠️ Manage Existing Academic Sessions")
            session_list = [f"{row['ID']} - {row['Session Name']}" for _, row in current_sessions.iterrows()]
            selected_sess_str = st.selectbox("Select a Session to Modify or Remove:", session_list, key="manage_sess_select")
            
            if selected_sess_str:
                selected_sess_id = int(selected_sess_str.split(" - ")[0])
                target_sess_row = current_sessions[current_sessions['ID'] == selected_sess_id].iloc[0]
                
                with st.form("edit_session_form"):
                    updated_sess_name = st.text_input("Change Session Code/Year:", value=str(target_sess_row['Session Name'])).strip()
                    updated_sess_status = st.selectbox("Change Session Status:", ["ACTIVE", "INACTIVE"], index=0 if target_sess_row['Status'] == 'ACTIVE' else 1)
                    
                    col_su, col_sd = st.columns(2)
                    with col_su:
                        save_sess = st.form_submit_button("💾 Save Session Changes", type="primary", use_container_width=True)
                    with col_sd:
                        confirm_sess_del = st.checkbox("⚠️ Confirm complete deletion", key="del_sess_chk")
                        delete_sess = st.form_submit_button("🗑️ Delete Session Permanently", type="secondary", use_container_width=True)
                        
                if save_sess:
                    if not updated_sess_name:
                        st.error("Session Code/Year cannot be left blank.")
                    else:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE academic_sessions SET session_name = :name, status = :status WHERE id = :id"), 
                                             {"name": updated_sess_name, "status": updated_sess_status, "id": selected_sess_id})
                            st.success("Session information successfully updated!")
                            st.rerun()
                        except Exception as err:
                            st.error(f"❌ Modification failed. The session name might already exist: {err}")
                        
                if delete_sess:
                    if not confirm_sess_del:
                        st.error("Please check the confirmation box to authorize permanent deletion.")
                    else:
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM academic_sessions WHERE id = :id"), {"id": selected_sess_id})
                        st.success("Session removed from system registers completely.")
                        st.rerun()
        else:
            st.info("No academic sessions currently configured.")

    # ==============================================================================
    # SUB-MODULE 3: SECTION MASTER
    # ==============================================================================
    elif sub_menu == "🗂️ Section Master":
        st.subheader("🗂️ Class Section Configuration")
        
        if current_role == 'controller':
            with st.form("section_reg_form", clear_on_submit=True):
                col_sec1, col_sec2 = st.columns(2)
                with col_sec1:
                    new_section_name = st.text_input("Section Structural Label:", placeholder="e.g. Section A")
                with col_sec2:
                    new_section_status = st.selectbox("Section Status:", options=["ACTIVE", "INACTIVE"])
                    
                submit_section = st.form_submit_button("💾 Save Section to Registry")
                
                if submit_section:
                    if new_section_name.strip() == "":
                        st.error("Section Name is required.")
                    else:
                        check_existing = run_query("SELECT id FROM system_sections WHERE UPPER(TRIM(section_name)) = UPPER(TRIM(:name))", {"name": new_section_name.strip()})
                        
                        if check_existing.empty:
                            execute_db_command("""
                                INSERT INTO system_sections (section_name, status)
                                VALUES (:name, :status)
                            """, {
                                "name": new_section_name.strip(),
                                "status": new_section_status
                            })
                            st.success(f"🎉 Successfully registered section '{new_section_name}'!")
                            st.rerun()
                        else:
                            st.warning("A section with this name already exists.")
                            
        st.markdown("---")
        st.write("#### Registered Class Sections")
        
        current_sections = pd.DataFrame()
        try:
            current_sections = run_query('SELECT id as "ID", section_name as "Section Name", status as "Status" FROM system_sections ORDER BY section_name ASC')
        except Exception as e:
            st.error(f"⚠️ Failed to read section configurations from database: {e}")
            
        if not current_sections.empty:
            st.dataframe(current_sections, use_container_width=True, hide_index=True)
            
            st.markdown("### 🛠️ Manage Existing Sections")
            section_list = [f"{row['ID']} - {row['Section Name']}" for _, row in current_sections.iterrows()]
            selected_sec_str = st.selectbox("Select a Section to Modify or Remove:", section_list, key="manage_sec_select")
            
            if selected_sec_str:
                selected_sec_id = int(selected_sec_str.split(" - ")[0])
                target_row = current_sections[current_sections['ID'] == selected_sec_id].iloc[0]
                
                with st.form("edit_section_form"):
                    updated_name = st.text_input("Change Section Label:", value=str(target_row['Section Name'])).upper().strip()
                    updated_status = st.selectbox("Change Section Status:", ["ACTIVE", "INACTIVE"], index=0 if target_row['Status'] == 'ACTIVE' else 1)
                    
                    col_u, col_d = st.columns(2)
                    with col_u:
                        save_sec = st.form_submit_button("💾 Save Section Changes", type="primary", use_container_width=True)
                    with col_d:
                        confirm_sec_del = st.checkbox("⚠️ Confirm complete deletion", key="del_sec_chk")
                        delete_sec = st.form_submit_button("🗑️ Delete Section", type="secondary", use_container_width=True)
                        
                if save_sec:
                    if not updated_name:
                        st.error("Section label cannot be left blank.")
                    else:
                        execute_db_command("UPDATE system_sections SET section_name = :name, status = :status WHERE id = :id", 
                                           {"name": updated_name, "status": updated_status, "id": selected_sec_id})
                        st.success("Section updated successfully!")
                        st.rerun()
                        
                if delete_sec:
                    if not confirm_sec_del:
                        st.error("Please check the confirmation box to authorize permanent deletion.")
                    else:
                        execute_db_command("DELETE FROM system_sections WHERE id = :id", {"id": selected_sec_id})
                        st.success("Section removed from registry permanently.")
                        st.rerun()
        else:
            st.info("No class sections currently configured.")

    # ==============================================================================
    # SUB-MODULE 4: TEST & EXAM FRAMEWORKS
    # ==============================================================================
    elif sub_menu == "📑 Test & Exam Frameworks":
        st.subheader("📑 Evaluation Type & Test Profile Settings")
        
        if "settings_initialized" not in st.session_state:
            st.session_state.settings_initialized = False
        if "configured_system_type" not in st.session_state:
            st.session_state.configured_system_type = "Annual System"

        if not st.session_state.settings_initialized:
            st.info("⚙️ **Platform Settings Required**: Please select the active Academic System track before defining or managing test frameworks.")
            
            with st.container(border=True):
                st.markdown("#### 🛠️ Core Environment Settings")
                sys_selection = st.selectbox(
                    "Select Academic System:", 
                    ["Annual System", "Semester System"], 
                    key="wizard_system_type"
                )
                
                if st.button("💾 Apply Configuration Parameters", use_container_width=True):
                    st.session_state.configured_system_type = sys_selection
                    st.session_state.settings_initialized = True
                    st.success(f"🎯 Track set to {sys_selection}! Initializing layout modules...")
                    st.rerun()

        else:
            with st.expander(f"⚙️ Active Track Profile: {st.session_state.configured_system_type}", expanded=False):
                if st.button("🔄 Change Active Academic System Track", use_container_width=True):
                    st.session_state.settings_initialized = False
                    st.rerun()
            
            if current_role == 'controller':
                with st.form("test_reg_form", clear_on_submit=True):
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        new_test_name = st.text_input("Test / Exam Display Title:", placeholder="e.g. Mid-Term Examination")
                        new_test_code = st.text_input("System Reference Key (No Spaces):", placeholder="e.g. MID_TERM").upper().strip()
                    with col_t2:
                        system_routing = st.selectbox(
                            "Academic Stream Association:", 
                            options=["Annual System", "Semester System"],
                            index=0 if st.session_state.configured_system_type == "Annual System" else 1
                        )
                        new_test_status = st.selectbox("Configuration Status:", options=["ACTIVE", "INACTIVE"])
                        
                    submit_test = st.form_submit_button("💾 Save Test Framework Type")
                    
                    if submit_test:
                        if new_test_name.strip() == "" or new_test_code == "":
                            st.error("Both Test Name and Reference Key are mandatory entries.")
                        else:
                            check_existing = run_query("SELECT exam_code FROM exam_cycles WHERE UPPER(TRIM(exam_code)) = :code", {"code": new_test_code})
                            
                            if check_existing.empty:
                                try:
                                    with engine.begin() as conn:
                                        conn.execute(text("""
                                            INSERT INTO exam_cycles (exam_code, exam_display_name, system_type, status)
                                            VALUES (:code, :name, :sys, :status)
                                        """), {
                                            "code": new_test_code,
                                            "name": new_test_name.strip(),
                                            "sys": system_routing,
                                            "status": new_test_status
                                        })
                                    st.success(f"🎉 Successfully registered evaluation framework rule '{new_test_name}'!")
                                    st.rerun()
                                except Exception as err:
                                    st.error(f"❌ Failed to insert framework record: {err}")
                            else:
                                st.warning("An evaluation pattern with this code identifier already exists.")
                                        
            st.markdown("---")
            st.write("#### Registered Evaluation Profiles")
            
            current_tests = pd.DataFrame()
            try:
                current_tests = run_query('SELECT exam_code as "System Code", exam_display_name as "Evaluation Name", system_type as "System Track", status as "Status" FROM exam_cycles ORDER BY system_type ASC, exam_display_name ASC')
            except Exception as e:
                st.error(f"⚠️ Failed to read evaluation configurations: {e}")
                
            if not current_tests.empty:
                st.dataframe(current_tests, use_container_width=True, hide_index=True)
                
                st.markdown("### 🛠️ Manage Existing Evaluation Profiles")
                test_list = [f"{row['Evaluation Name']} ({row['System Code']})" for _, row in current_tests.iterrows()]
                selected_test_str = st.selectbox("Select a Profile to Modify or Remove:", test_list, key="manage_test_select")
                
                if selected_test_str:
                    selected_test_code = selected_test_str.split("(")[-1].replace(")", "").strip()
                    target_test_row = current_tests[current_tests['System Code'] == selected_test_code].iloc[0]
                    
                    with st.form("edit_exam_form"):
                        updated_test_name = st.text_input("Change Display Title:", value=str(target_test_row['Evaluation Name'])).strip()
                        updated_test_status = st.selectbox("Change Evaluation Status:", ["ACTIVE", "INACTIVE"], index=0 if target_test_row['Status'] == 'ACTIVE' else 1)
                        
                        col_fu, col_fd = st.columns(2)
                        with col_fu:
                            save_test_mod = st.form_submit_button("💾 Save Profile Changes", type="primary", use_container_width=True)
                        with col_fd:
                            confirm_test_del = st.checkbox("⚠️ Confirm complete deletion", key="del_test_chk")
                            delete_test_mod = st.form_submit_button("🗑️ Delete Evaluation Profile", type="secondary", use_container_width=True)
                            
                    if save_test_mod:
                        if not updated_test_name:
                            st.error("Evaluation title cannot be left blank.")
                        else:
                            try:
                                with engine.begin() as conn:
                                    conn.execute(text("""
                                        UPDATE exam_cycles 
                                        SET exam_display_name = :name, status = :status 
                                        WHERE exam_code = :code
                                    """), {"name": updated_test_name, "status": updated_test_status, "code": selected_test_code})
                                st.success("Evaluation profile configuration updated successfully!")
                                st.rerun()
                            except Exception as err:
                                st.error(f"❌ Failed to update evaluation item: {err}")
                            
                    if delete_test_mod:
                        if not confirm_test_del:
                            st.error("Please check the confirmation box to authorize permanent deletion.")
                        else:
                            try:
                                with engine.begin() as conn:
                                    conn.execute(text("DELETE FROM exam_cycles WHERE exam_code = :code"), {"code": selected_test_code})
                                st.success("Evaluation profile removed from system registers.")
                                st.rerun()
                            except Exception as err:
                                st.error(f"❌ Complete removal failed: {err}")
            else:
                st.info("ℹ️ No evaluation profiles or exam cycles are currently configured.")

    # ==============================================================================
    # 🧬 SUB-MODULE 5: ACADEMIC DISCIPLINES & AUTOMATIC SYNC TERMINAL
    # ==============================================================================
    elif sub_menu == "🧬 Add Disciplines":
        st.subheader("🧬 Academic Disciplines & Program Entries")
        st.info("Centralized console to view existing structural disciplines, modify active tracking setups, or initialize new program frameworks.")

        # --- AUTOMATIC BACKGROUND DICTIONARY SYNC ENGINE ---
        dict_disciplines = set()
        for yr, mappings in CLASS_SUBJECTS_MASTER_MAP.items():
            for disc in mappings.keys():
                dict_disciplines.add(disc.upper().strip())
        for disc in DISCIPLINE_SECTIONS_MAP.keys():
            cleaned_key = disc.replace(" (", "_").replace(")", "").upper().strip()
            dict_disciplines.add(cleaned_key)

        try:
            with engine.begin() as conn:
                for disc_name in dict_disciplines:
                    # Automatically determine whether it belongs to Semester or Annual track
                    is_semester = any("Semester" in str(yr) for yr in CLASS_SUBJECTS_MASTER_MAP.keys() if disc_name in [k.upper() for k in CLASS_SUBJECTS_MASTER_MAP[yr].keys()])
                    track_system = "Semester System" if is_semester else "Annual System"
                    
                    conn.execute(text("""
                        INSERT INTO system_disciplines (discipline_name, academic_system, status)
                        VALUES (:name, :sys, 'ACTIVE')
                        ON CONFLICT (discipline_name) DO NOTHING
                    """), {"name": disc_name, "sys": track_system})
        except Exception as sync_err:
            st.write(f"⚙️ Database structural background initialization status: {sync_err}")

        if 'discipline_deep_sync' not in st.session_state:
            st.cache_data.clear()
            st.session_state['discipline_deep_sync'] = True

        # --- DATABASE READ: FETCH SYNCHRONIZED DISCIPLINE RECORDS ---
        current_disciplines = pd.DataFrame()
        try:
            current_disciplines = run_query('''
                SELECT 
                    id as "ID", 
                    discipline_name as "Discipline Name", 
                    academic_system as "Academic System",
                    status as "Status" 
                FROM system_disciplines 
                ORDER BY discipline_name ASC
            ''')
        except Exception as e:
            st.error(f"❌ Error communicating with database infrastructure: {e}")

        tab_view, tab_new = st.tabs(["📋 View & Edit Existing Disciplines", "➕ Add New Discipline Record"])

        with tab_view:
            if not current_disciplines.empty:
                st.markdown("### 📋 Current Synchronized Institutional Disciplines")
                st.dataframe(current_disciplines, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.markdown("### ✏️ Edit or Modify an Existing Discipline")
                
                disp_options = [f"{row['ID']} - {row['Discipline Name']} ({row['Academic System']})" for _, row in current_disciplines.iterrows()]
                selected_disp_str = st.selectbox("Select target discipline parameter row to alter:", options=disp_options, key="edit_selector_node")
                
                if selected_disp_str:
                    selected_id = int(selected_disp_str.split(" - ")[0])
                    target_row = current_disciplines[current_disciplines['ID'] == selected_id].iloc[0]
                    sys_choices = ["Annual System", "Semester System"]

                    with st.form(f"modify_discipline_form_{selected_id}"):
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            edit_name = st.text_input("Modify Discipline Code/Title:", value=str(target_row['Discipline Name'])).upper().strip()
                            current_track = target_row['Academic System'] if 'Academic System' in target_row else "Annual System"
                            edit_sys = st.selectbox("Assigned System Track Framework:", options=sys_choices, index=sys_choices.index(current_track) if current_track in sys_choices else 0)
                        with col_m2:
                            edit_status = st.selectbox("Discipline Status Flag:", options=["ACTIVE", "INACTIVE"], index=0 if target_row['Status'] == 'ACTIVE' else 1)
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            commit_update = st.form_submit_button("💾 Save Structural Modifications", type="primary", use_container_width=True)
                        with col_btn2:
                            confirm_delete = st.checkbox("⚠️ Confirm complete historical removal", key=f"del_lock_{selected_id}")
                            commit_delete = st.form_submit_button("🗑️ Drop Track Permanently", type="secondary", use_container_width=True)

                        if commit_update:
                            if not edit_name:
                                st.error("❌ Discipline identity text cannot be blank.")
                            else:
                                try:
                                    with engine.begin() as conn:
                                        conn.execute(text("""
                                            UPDATE system_disciplines 
                                            SET discipline_name = :name, academic_system = :sys, status = :status 
                                            WHERE id = :id
                                        """), {"name": edit_name, "sys": edit_sys, "status": edit_status, "id": selected_id})
                                    st.cache_data.clear() 
                                    st.success("🎉 Database entry updated successfully!")
                                    st.rerun()
                                except Exception as err:
                                    st.error(f"❌ Transaction failed: {err}")

                        if commit_delete:
                            if not confirm_delete:
                                st.error("❌ You must check the validation box checkpoint to execute deletion.")
                            else:
                                try:
                                    with engine.begin() as conn:
                                        conn.execute(text("DELETE FROM system_disciplines WHERE id = :id"), {"id": selected_id})
                                    st.cache_data.clear()
                                    st.success("🗑️ Track deleted from records.")
                                    st.rerun()
                                except Exception as err:
                                    st.error(f"❌ Deletion restriction encountered: {err}")
            else:
                st.info("ℹ️ No customized disciplines discovered in configuration records.")

        with tab_new:
            st.markdown("### ➕ Register a New Program Classification Track")
            sys_choices = ["Annual System", "Semester System"]

            with st.form("new_discipline_entry_form", clear_on_submit=True):
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    new_name = st.text_input("New Discipline Title/Code:", placeholder="e.g. COMMERCE, ICS_PHYSICS, MEDICAL").upper().strip()
                    new_sys = st.selectbox("Target Academic System Association:", options=sys_choices)
                with col_n2:
                    new_status = st.selectbox("Initial Discipline Operational Status:", options=["ACTIVE", "INACTIVE"])
                
                submit_new = st.form_submit_button("🚀 Commit New Entry to Database", type="primary")

                if submit_new:
                    if not new_name:
                        st.error("❌ Entry field input cannot be blank.")
                    else:
                        try:
                            duplicate_check = run_query("SELECT id FROM system_disciplines WHERE UPPER(TRIM(discipline_name)) = :name", {"name": new_name})
                            if duplicate_check.empty:
                                with engine.begin() as conn:
                                    conn.execute(text("""
                                        INSERT INTO system_disciplines (discipline_name, academic_system, status)
                                        VALUES (:name, :sys, :status)
                                    """), {"name": new_name, "sys": new_sys, "status": new_status})
                                st.cache_data.clear()
                                st.success(f"🎉 Track '{new_name}' successfully added!")
                                st.rerun()
                            else:
                                st.warning("⚠️ This specific discipline title variant is already registered.")
                        except Exception as ex:
                            st.error(f"❌ Failed to submit structural row matrix: {ex}")


    # ==============================================================================
    # 📚 SUB-MODULE 6: SUBJECT MAPPING MATRIX (LIVE DECOUPLED CASCADE)
    # ==============================================================================
    elif sub_menu == "📚 Add Subject Mapping":
        st.subheader("📚 Subject & Course Curriculum Matrix Mapping")
        st.info("Map individual operational subjects dynamically sourced from your active master institutional configuration dictionaries.")

        # --- STEP 1: LIVE INTERACTIVE CASCADE SELECTORS (OUTSIDE THE FORM) ---
        col_select1, col_select2 = st.columns(2)
        
        with col_select1:
            # 1. Select the Academic Year Class Layer
            available_layers = list(CLASS_SUBJECTS_MASTER_MAP.keys())
            chosen_layer = st.selectbox(
                "1️⃣ Select Target Academic Class / Year Layer:", 
                options=available_layers, 
                key="live_map_layer_selector"
            )

            # 2. Extract matching tracks for the chosen layer dynamically
            layer_tracks = list(CLASS_SUBJECTS_MASTER_MAP[chosen_layer].keys())
            chosen_track = st.selectbox(
                "2️⃣ Select Program Discipline Track:", 
                options=layer_tracks, 
                key="live_map_track_selector"
            )

        # 🔍 LIVE FETCH: Pull the exact dictionary entries matching the user's selection in real-time
        dict_pulled_subjects = CLASS_SUBJECTS_MASTER_MAP[chosen_layer][chosen_track]

        with col_select2:
            st.write("### 🎯 Context Tracker Verified")
            
            # Safe native container rendering - eliminates python f-string/HTML bracket compilation errors
            with st.container(border=True):
                st.markdown(f"**Active Layer:** :red[`{chosen_layer}`]")
                st.markdown(f"**Active Track:** :red[`{chosen_track}`]")
                st.markdown("**📖 Available Curriculum Pool:**")
                
                # Render clean bullet points safely
                for sub in dict_pulled_subjects:
                    st.markdown(f"- `{sub}`")

        st.markdown("---")
        
        # --- STEP 2: SECURE SUBMISSION MATRIX FORM ---
        if current_role == 'controller':
            st.markdown("### 💾 Record Mapping Association")
            
            with st.form("smart_subject_mapping_form", clear_on_submit=True):
                # Interactive toggle allows selecting dictionary pools OR adding brand new courses
                input_mode = st.radio(
                    "Choose Subject Input Variant:",
                    options=["Pick from Code Dictionary Pool", "Type a Brand New Subject entirely"],
                    horizontal=True
                )

                if input_mode == "Pick from Code Dictionary Pool":
                    selected_subject_to_map = st.selectbox(
                        "3️⃣ Select Existing Subject to Map:", 
                        options=dict_pulled_subjects
                    )
                else:
                    selected_subject_to_map = st.text_input(
                        "3️⃣ Type New Custom Subject Name:", 
                        placeholder="e.g. SOCIOLOGY, ARABIC, CIVICS"
                    ).upper().strip()

                submit_subject = st.form_submit_button("🚀 Save Course Mapping Parameters", type="primary")
                
                # --- STEP 3: DATABASE INSERT TRANSACTION WRITER ---
                if submit_subject:
                    if not selected_subject_to_map:
                        st.error("❌ Target subject selection value cannot be empty.")
                    else:
                        try:
                            # Standardize casing parameters for clean PostgreSQL lookups
                            db_disp = str(chosen_track).upper().strip()
                            db_layer = str(chosen_layer).strip()
                            db_sub = str(selected_subject_to_map).upper().strip()

                            # Guard Clause: Prevent identical duplicate matrix allocations
                            check_existing = run_query("""
                                SELECT id FROM system_subjects_mapping 
                                WHERE UPPER(TRIM(discipline_name)) = :disp 
                                AND UPPER(TRIM(class_name)) = :cls
                                AND UPPER(TRIM(subject_name)) = :sub
                            """, {"disp": db_disp, "cls": db_layer, "sub": db_sub})
                            
                            if check_existing.empty:
                                with engine.begin() as conn:
                                    conn.execute(text("""
                                        INSERT INTO system_subjects_mapping (discipline_name, class_name, subject_name)
                                        VALUES (:disp, :cls, :sub)
                                    """), {"disp": db_disp, "cls": db_layer, "sub": db_sub})
                                
                                st.cache_data.clear() # Clear internal display cache instantly
                                st.success(f"🎉 Successfully mapped verified course: '{db_sub}' inside '{db_disp} ({db_layer})' structure!")
                                st.rerun()
                            else:
                                st.warning("⚠️ This exact subject tracking arrangement already exists inside your active database.")
                        except Exception as e:
                            st.error(f"❌ Could not write subject mapping parameter row: {e}")

        # --- STEP 4: GRID DISPLAY & DELETION PROCESSING MANAGEMENT ---
        st.markdown("---")
        st.write("#### Registered Structural Curriculum Maps")
        
        current_maps = pd.DataFrame()
        try:
            current_maps = run_query('''
                SELECT 
                    id as "ID", 
                    discipline_name as "Discipline Track", 
                    class_name as "Academic Term", 
                    subject_name as "Allocated Course" 
                FROM system_subjects_mapping 
                ORDER BY discipline_name ASC, class_name ASC, subject_name ASC
            ''')
        except Exception:
            st.warning("⚠️ Connected backend routing index table is empty or resetting.")

        if not current_maps.empty:
            st.dataframe(current_maps, use_container_width=True, hide_index=True)
            
            st.markdown("### 🛠️ Delete or Remove Matrix Rules")
            mapping_list = [f"{row['ID']} - [{row['Discipline Track']}] ({row['Academic Term']}) ➔ {row['Allocated Course']}" for _, row in current_maps.iterrows()]
            selected_map_str = st.selectbox("Select Course Rule Block to Delete:", mapping_list, key="manage_map_select")
            
            if selected_map_str:
                selected_map_id = int(selected_map_str.split(" - ")[0])
                
                with st.form("edit_mapping_form"):
                    st.warning(f"Confirm complete deletion actions for Allocation Rule Row reference ID #{selected_map_id}")
                    confirm_map_del = st.checkbox("⚠️ Confirm complete historical removal from database", key="del_map_chk")
                    delete_map = st.form_submit_button("🗑️ Drop Subject Route Row", type="secondary", use_container_width=True)
                        
                if delete_map:
                    if not confirm_map_del:
                        st.error("❌ You must check the validation box to drop this curriculum row assignment link.")
                    else:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("DELETE FROM system_subjects_mapping WHERE id = :id"), {"id": selected_map_id})
                            st.cache_data.clear()
                            st.success("🎉 Curriculum routing row deleted successfully.")
                            st.rerun()
                        except Exception as err:
                            st.error(f"❌ Deletion process failure: {err}")
        else:
            st.info("ℹ️ No curriculum course mapping records structured inside table setups yet.")
