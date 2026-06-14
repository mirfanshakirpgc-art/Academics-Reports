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
        
        try:
            conn.execute(text("ALTER TABLE students ADD COLUMN IF NOT EXISTS system_type VARCHAR(50) DEFAULT 'Annual System';"))
        except Exception: pass

        try:
            conn.execute(text("ALTER TABLE students ADD COLUMN IF NOT EXISTS discipline VARCHAR(100);"))
        except Exception: pass
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_teachers (
                teacher_id SERIAL PRIMARY KEY,
                teacher_name VARCHAR(255) NOT NULL UNIQUE,
                phone_number VARCHAR(50),
                email_address VARCHAR(255),
                status VARCHAR(50) DEFAULT 'ACTIVE'
            );
        """))

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

# ==============================================================================
# --- DATABASE COMMAND UTILITIES ---
# ==============================================================================
def run_query(query, params=None):
    if params is None:
        params = {}
    clean_query = query.replace("[Session Name]", '"Session Name"')
    try:
        with engine.connect() as conn:
            return pd.read_sql_query(text(clean_query), conn, params=params)
    except Exception as original_error:
        try:
            with engine.begin() as txn_conn:
                try:
                    txn_conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS academic_sessions (
                            id SERIAL PRIMARY KEY,
                            session_name VARCHAR(50) UNIQUE NOT NULL,
                            status VARCHAR(20) DEFAULT 'ACTIVE'
                        );
                    """))
                except Exception: pass

                for table_name in ["academic_sessions", "system_sections", "exam_cycles"]:
                    try:
                        txn_conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE';"))
                    except Exception: pass 

            with engine.connect() as retry_conn:
                return pd.read_sql_query(text(clean_query), retry_conn, params=params)
        except Exception:
            raise original_error

def execute_db_command(query, params=None):
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
            st.markdown("#### 🏢 Section-Based Batch Promotion")
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
                st.info("No active sections tracked for this criteria setup.")
            else:
                st.selectbox("Select Target Section to Batch Move:", available_sections)

# ==============================================================================
# 🪪 SUB-MODULE: STUDENT RESULT CARDS — PRINT ENGINE (MONTH-WISE SUMMARY LINKED)
# ==============================================================================
elif menu_choice == "🪪 Student Result Cards":
    st.title("🪪 Student Result Cards — Print Engine")

    # 1. Global Filter Tiers
    try:
        db_sessions = run_query("SELECT DISTINCT session FROM students ORDER BY session DESC")
        session_list = db_sessions['session'].tolist() if not db_sessions.empty else ["2024-26", "2025-27", "2026-28"]
    except Exception:
        session_list = ["2024-26", "2025-27", "2026-28"]

    col_sel1, col_sel2, col_sel3, col_sel4 = st.columns(4)
    with col_sel1:
        selected_session = st.selectbox("📅 Select Session:", options=session_list)
    with col_sel2:
        selected_system = st.selectbox("⚙️ Select Academic System:", options=["Annual System", "Semester System"])
    with col_sel3:
        class_options = ["11th", "12th"] if selected_system == "Annual System" else ["Semester 1", "Semester 2", "Semester 3", "Semester 4"]
        selected_class = st.selectbox("🏫 Select Class:", options=class_options)
    with col_sel4:
        fallback_options = ["MT_1", "MT_2", "SEND_UP", "HALF_BOOK01", "PRE_BOARD"]
        selected_test_code = st.selectbox("🎯 Select Test Term:", options=fallback_options)
        selected_test_label = selected_test_code

    st.markdown("---")
    print_scope = st.radio("𖨾 Select Print Scope:", ["👤 Single Student Card", "👥 Complete Section Cards"], horizontal=True)
    
    search_id = ""
    selected_discipline = ""
    active_section = ""

    normalized_class_input = str(selected_class).strip()

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

    students_to_print = pd.DataFrame()

    if submit_execution:
        if print_scope == "👤 Single Student Card" and search_id:
            students_to_print = run_query(f"SELECT id, name, section, class FROM students WHERE session = '{selected_session}' AND id = '{search_id.strip()}'")
        elif print_scope == "👥 Complete Section Cards" and active_section:
            students_to_print = run_query(f"""
                SELECT id, name, section, class FROM students 
                WHERE session = '{selected_session}' 
                AND class = '{selected_class}' 
                AND UPPER(TRIM(section)) = '{str(active_section).upper().strip()}'
                ORDER BY id ASC
            """)

    if submit_execution and not students_to_print.empty:
        compiled_html = """
        <!DOCTYPE html>
        <html>
        <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
        <style>
            body { font-family: "Times New Roman", Times, serif; color: #000; background-color: #fff; margin: 0; padding: 10px; }
            .official-card-container { max-width: 850px; margin: 10px auto; padding: 25px; border: 1px solid #000; background: #fff; position: relative; }
            .header-block { display: flex; align-items: center; justify-content: center; position: relative; margin-bottom: 20px; width: 100%; gap: 20px; }
            .logo-img { max-height: 65px; width: auto; display: block; }
            .inst-main-header { font-weight: bold; font-size: 30px; text-transform: uppercase; text-align: center; }
            .doc-type-banner { text-align: center; font-weight: bold; font-size: 18px; text-transform: uppercase; margin: 25px 0 20px 0; letter-spacing: 1.5px; }
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

        DISPLAY_MONTHS = ["May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.", "Jan.", "Feb.", "March", "April"]

        for idx, student_row in students_to_print.iterrows():
            current_id_str = str(student_row['id']).strip()
            name = str(student_row['name']).upper()
            section = str(student_row['section']).upper().strip()
            grade_class = str(student_row['class']).strip()
            test_name = selected_test_label.upper()
            
            lookup_class_key = grade_class

            detected_discipline_key = None
            for discipline, class_layers in DISCIPLINE_SECTIONS_MAP.items():
                sections_list = class_layers.get(lookup_class_key, [])
                if section in [str(s).upper().strip() for s in sections_list]:
                    detected_discipline_key = discipline
                    break
            
            subject_mapping_key = detected_discipline_key
            if detected_discipline_key == "ICS (PHYSICS)":
                subject_mapping_key = "ICS_PHYSICS"
            elif detected_discipline_key == "ICS (STATS)":
                subject_mapping_key = "ICS_STATS"

            subjects_list = CLASS_SUBJECTS_MASTER_MAP.get(lookup_class_key, {}).get(subject_mapping_key, None)
            if not subjects_list:
                try:
                    subjects_list = list(CLASS_SUBJECTS_MASTER_MAP.get(lookup_class_key, {}).values())[0]
                except Exception:
                    subjects_list = ["English", "Urdu"]

            raw_marks = run_query(f"SELECT UPPER(TRIM(subject)) as subject, marks_obtained, total_marks FROM marks WHERE student_id = '{current_id_str}' AND exam_type = '{selected_test_code}'")
            
            # 🛠️ ATTENDANCE RE-ENGINEERING: Fetch month summaries directly
            db_att = run_query(f"""
                SELECT UPPER(TRIM(month_name)) as m_name, 
                       MAX(total_days) as total_days, 
                       MAX(present_days) as present_days 
                FROM attendance 
                WHERE student_id = '{current_id_str}'
                GROUP BY UPPER(TRIM(month_name))
            """)
            
            att_cells = {}
            tot_sum, pres_sum = 0, 0
            
            for m in DISPLAY_MONTHS:
                clean_m_prefix = m.upper().replace('.', '').strip()[:3]
                match_att = pd.DataFrame()
                
                if not db_att.empty:
                    match_att = db_att[db_att['m_name'].str.replace('.', '', regex=False).str.strip().str.startswith(clean_m_prefix)]
                
                if not match_att.empty:
                    td = int(match_att['total_days'].iloc[0])
                    pd_val = int(match_att['present_days'].iloc[0])
                    tot_sum += td
                    pres_sum += pd_val
                    pct = f"{int((pd_val / td) * 100)}%" if td > 0 else "0%"
                    att_cells[m] = {"td": str(td), "pd": str(pd_val), "pct": pct}
                else:
                    att_cells[m] = {"td": "0", "pd": "0", "pct": "0%"}
            
            overall_pct_str = f"{int((pres_sum / tot_sum) * 100)}%" if tot_sum > 0 else "0%"
            att_cells["Over All Att."] = {"td": str(tot_sum), "pd": str(pres_sum), "pct": overall_pct_str}

            logo_placeholder = "https://raw.githubusercontent.com/mirfanshakirpgc-art/Academics-Reports/main/logo.png"
            grand_total_marks, grand_obtained_marks = 0.0, 0.0
            
            compiled_html += f"""
            <div class="official-card-container" id="card-{current_id_str}" data-student-name="{name.replace(' ', '_')}">
                <div class="header-block">
                    <div><img class="logo-img" src="{logo_placeholder}" alt="Logo"></div>
                    <div class="inst-main-header">CONCORDIA COLLEGE KASUR</div>
                </div>
                
                <div class="doc-type-banner">RESULT CARD</div>
                
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
                    match = raw_marks[raw_marks['subject'] == sub_clean]
                    if match.empty:
                        match = raw_marks[raw_marks['subject'].str.contains(sub_clean[:4], regex=False, na=False)]

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
                            if num_obt < pass_marks_num:
                                student_failed_any_subject = True
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
    
    elif submit_execution:
        if print_scope == "👤 Single Student Card":
            st.warning("⚠️ No student records match the given Roll ID and Session selection details.")
        else:
            st.warning(f"⚠️ No active student rows found matching section group: '{active_section}' for {selected_class} ({selected_session}).")

else:
    st.title("Concordia Academic Analytics")
    st.info("Select a module from the sidebar navigation menu to display contents.")
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
