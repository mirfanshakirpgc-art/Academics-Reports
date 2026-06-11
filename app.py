# ==============================================================================
# 1. ABSOLUTE TOP OF APP.PY: GLOBAL INITIALIZATIONS
# ==============================================================================
import os
import base64
import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import streamlit.components.v1 as components
from datetime import date
import datetime
import io

st.set_page_config(layout="wide", page_title="Concordia Academic Analytics")

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
    if logo_base64:
        st.markdown(f'<img src="{logo_base64}" width="120">', unsafe_allow_html=True)
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
        # ... (keep your other table creations here) ...
        
        # ADD THIS BLOCK to your initialize_database function:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_attendance (
                id SERIAL PRIMARY KEY,
                student_id INT REFERENCES students(id) ON DELETE CASCADE,
                attendance_date DATE NOT NULL,
                status VARCHAR(10) NOT NULL,
                UNIQUE(student_id, attendance_date)
            );
        """))
        
        # 2. Teachers Registry Table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_teachers (
                teacher_id SERIAL PRIMARY KEY,
                teacher_name VARCHAR(255) NOT NULL UNIQUE,
                phone_number VARCHAR(50),
                email_address VARCHAR(255),
                status VARCHAR(50) DEFAULT 'ACTIVE'
            );
        """))

        # 3. Master Allocation Matrix Table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS academic_allocations (
                allocation_id SERIAL PRIMARY KEY,
                session_term VARCHAR(50) NOT NULL,
                class_level VARCHAR(100) NOT NULL,
                section_name VARCHAR(100) NOT NULL,
                subject_title VARCHAR(100) NOT NULL,
                assigned_teacher_name VARCHAR(255) REFERENCES system_teachers(teacher_name) ON DELETE CASCADE,
                is_class_incharge VARCHAR(10) DEFAULT 'No',
                UNIQUE(session_term, class_level, section_name, subject_title, assigned_teacher_name)
            );
        """))
        
        # 4. Marks Table
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
        
        # 5. Attendance Table
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
        
        # 6. Daily Attendance Table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_attendance (
                id SERIAL PRIMARY KEY,
                student_id INT REFERENCES students(id) ON DELETE CASCADE,
                attendance_date DATE NOT NULL,
                status VARCHAR(10) NOT NULL,
                UNIQUE(student_id, attendance_date)
            );
        """))
        
        # 7. Promotion History
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS promotion_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                student_id INTEGER,
                old_class TEXT,
                old_section TEXT,
                old_session TEXT,
                new_class TEXT,
                new_section TEXT,
                batch_id TEXT
            );
        """))
        
        # 8. Student Logs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS student_logs (
                id SERIAL PRIMARY KEY,
                student_id INT, 
                change_type TEXT, 
                old_value TEXT, 
                new_value TEXT, 
                log_date TEXT, 
                remarks TEXT
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
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)

def run_update(query, params=None):
    if params is None:
        params = {}
    with engine.begin() as conn:
        conn.execute(text(query), params)

def execute_db_command(command, params=None):
    if params is None:
        params = {}
    with engine.begin() as conn:
        conn.execute(text(command), params)

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
    }
}

AVAILABLE_DISCIPLINE = list(DISCIPLINE_SUBJECTS_MAP.keys())
AVAILABLE_EXAMS = [
    "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "SEND_UP", "MT_5",
    "T_1", "T_2", "T_3", "T_4", "T_5", "T_6", "T_7", "T_8", f"T_9", "T_10",
    "HALF_BOOK01", "HALF_BOOK02", "PRE_BOARD"
]
AVAILABLE_MONTHS = ["May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.", "Jan.", "Feb.", "March", "April"]
AVAILABLE_SESSIONS = ["2024-26", "2025-27", "2026-28", "2027-29"]

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
        "Student Management", 
        "👨‍🏫 Teacher Management",  
        "🎓 Promote Students"
    ]
)

# ==============================================================================
# ----------------- 📊 HOME DASHBOARD -----------------
# ==============================================================================
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

# ==============================================================================
# ----------------- ➕ ADD STUDENTS -----------------
# ==============================================================================
elif menu_choice == "➕ Add Students":
    st.title("➕ Student Profile Registration Portal")
    
    try:
        session_options = AVAILABLE_SESSIONS
        if "2024-26" in session_options:
            session_options = [s for s in session_options if s != "2024-26"]
        if "2027-29" not in session_options:
            session_options.append("2027-29")
    except NameError:
        session_options = ["2025-27", "2026-28", "2027-29"]
        
    discipline_options = ["MEDICAL", "ENGINEERING", "ICS (PHYSICS)", "ICS (STATS)", "COMMERCE", "HUMANITIES"]

    c1, c2 = st.columns(2)
    with c1: 
        selected_session = st.selectbox("🎯 1. Select Session:", session_options, index=0, key="add_stu_sess")
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
                normalized_discipline = "ICS_STATISTICS"

            local_sections_map = {
                "MEDICAL": {"11th": ["MG_BLUE", "MG_WHITE", "MB_BLUE"], "12th": ["MQ1", "MQ2", "MK"]},
                "ENGINEERING": {"11th": ["EG_BLUE", "EB_BLUE"], "12th": ["EQ", "EK"]},
                "ICS_PHYSICS": {"11th": ["CG_WHITE", "CG_GREEN", "CB_WHITE", "CB_GREEN"], "12th": ["CQ1", "CQ2", "CK1", "CK2"]},
                "ICS_STATISTICS": {"11th": ["CG_STATS", "CB_STATS"], "12th": ["CQ3", "CK3"]},
                "COMMERCE": {"11th": ["IG", "IB"], "12th": ["IK", "IQ"]},
                "HUMANITIES": {"11th": ["FB", "FG"], "12th": ["FK", "FQ"]}
            }
            
            available_sections = local_sections_map.get(normalized_discipline, {}).get(selected_class, [])
            cleaned_sections = [str(sec).strip().upper() for sec in available_sections]
            
            if cleaned_sections:
                selected_section = st.selectbox("📋 4. Select Target Section:", cleaned_sections, key="add_stu_sec_annual")
            else:
                selected_section = st.text_input("📋 4. Enter Target Section Manually:", value="CK2", key="add_stu_sec_annual_manual").strip().upper()
    
    else:
        c3, c4 = st.columns(2)
        with c3: 
            selected_class = st.selectbox("⏳ 2. Select Semester:", ["Semester 1", "Semester 2", "Semester 3", "Semester 4"], key="add_stu_semester")
        with c4: 
            selected_section = st.selectbox("📋 3. Select Target Section:", ["DIT_G", "DIT_B"], key="add_stu_sec_semester")
        
        selected_discipline = "N/A"

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
                        
                        execute_db_command("""
                            INSERT INTO students (id, name, class, section, session, status)
                            VALUES (:id, :name, :class, :section, :session, :status)
                        """, {
                            "id": clean_id,
                            "name": clean_name,
                            "class": selected_class,
                            "section": selected_section,
                            "session": selected_session,
                            "status": input_status
                        })
                        
                        st.success(f"🎉 Success! Profile for {clean_name} has been formally registered.")
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
                        
                        for index, row in bulk_df.iterrows():
                            raw_id = str(row['ID']).strip().split('.')[0]
                            raw_name = str(row['NAME']).strip().upper()
                            
                            if raw_id.isdigit() and raw_name != "":
                                try:
                                    execute_db_command("""
                                        INSERT INTO students (id, name, class, section, session, status)
                                        VALUES (:id, :name, :class, :section, :session, 'ACTIVE')
                                    """, {
                                        "id": int(raw_id),
                                        "name": raw_name,
                                        "class": selected_class,
                                        "section": selected_section,
                                        "session": selected_session
                                    })
                                    success_count += 1
                                except Exception:
                                    error_count += 1
                            else:
                                error_count += 1
                                
                        st.success(f"🎉 Import complete! Successfully processed and committed {success_count} student records to database.")
                        if error_count > 0:
                            st.warning(f"⚠️ Skipped {error_count} row records because of primary key ID duplication conflicts or empty cells.")
                        st.balloons()
                        
            except Exception as read_err:
                st.error(f"❌ Failed to parse data file payload accurately: {read_err}")

    else:
        st.subheader(f"🛠️ Update or Remove Records — {selected_class} | Section: {selected_section}")
        
        try:
            query = """
                SELECT id, name, status FROM students 
                WHERE class = :class AND section = :section AND session = :session
                ORDER BY id ASC
            """
            students_query_df = run_query(query, params={"class": selected_class, "section": selected_section, "session": selected_session})
                
        except Exception as query_err:
            st.error(f"Error fetching directory lookup: {query_err}")
            students_query_df = pd.DataFrame()

        if students_query_df.empty:
            st.warning("⚠️ No active student profile records found registered under this specific Filter Option layout.")
        else:
            student_selector_list = [
                f"{int(row['id'])} - {str(row['name']).upper()}" for _, row in students_query_df.iterrows()
            ]
            
            chosen_stu_string = st.selectbox("🔍 Select Student Profile to Modify:", student_selector_list)
            
            if chosen_stu_string:
                selected_student_id = int(chosen_stu_string.split(" - ")[0])
                target_student_row = students_query_df[students_query_df['id'] == selected_student_id].iloc[0]
                
                st.markdown("### Modify Student Record Data")
                
                with st.form("student_profile_edit_form"):
                    edit_name = st.text_input("👤 Change Student Full Name Identity:", value=str(target_student_row['name']).upper())
                    
                    status_options = ["ACTIVE", "PENDING", "LEAVE"]
                    current_status = str(target_student_row['status']).upper()
                    init_status_idx = status_options.index(current_status) if current_status in status_options else 0
                    
                    edit_status = st.selectbox("📌 Change Registration Status Enrollment:", status_options, index=init_status_idx)
                    
                    st.markdown("---")
                    col_update, col_delete = st.columns(2)
                    
                    with col_update:
                        save_changes = st.form_submit_button("💾 Save Profile Changes", type="primary", use_container_width=True)
                    with col_delete:
                        confirm_delete = st.checkbox("⚠️ Check this box to confirm complete removal.")
                        erase_record = st.form_submit_button("🗑️ Delete Student From System", type="secondary", use_container_width=True)
                
                if save_changes:
                    if not edit_name.strip():
                        st.error("❌ Action Rejected: Name field cannot be saved blank.")
                    else:
                        try:
                            execute_db_command("""
                                UPDATE students 
                                SET name = :name, status = :status
                                WHERE id = :id
                            """, {
                                "name": edit_name.strip().upper(),
                                "status": edit_status,
                                "id": selected_student_id
                            })
                            st.success(f"⚡ Success! Profile record details for ID: {selected_student_id} have been updated.")
                            st.rerun()
                        except Exception as update_err:
                            st.error(f"❌ Failed to commit database updates: {update_err}")
                
                if erase_record:
                    if not confirm_delete:
                        st.error("❌ Action Blocked: You must check the confirmation safety box before deleting records.")
                    else:
                        try:
                            execute_db_command("DELETE FROM students WHERE id = :id", {"id": selected_student_id})
                            st.success(f"🗑️ The record for Student ID `{selected_student_id}` has been permanently dropped.")
                            st.rerun()
                        except Exception as delete_err:
                            st.error(f"❌ Database error encountered: {delete_err}")

# ====================================================================================
# MODULE 1: ACADEMIC EXAM MARKS ENTRY
# ====================================================================================
elif menu_choice == "📝 Academic Exam Marks Entry":
    st.title("📝 Academic Exam Marks Entry Workspace")
    entry_mode = st.radio("🎯 Select Entry Workflow Mode:", ["📋 By Complete Section", "👤 By Single Student Roll Number", "📤 Bulk Excel/CSV Import"], horizontal=True, key="marks_workflow_mode")
    st.markdown("---")

    all_frameworks = [
        "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "SEND_UP", "MT_5",
        "T_1", "T_2", "T_3", "T_4", "T_5", "T_6", "T_7", "T_8", "T_9", "T_10",
        "HALF_BOOK01", "HALF_BOOK02", "PRE_BOARD"
    ]

    try:
        session_options = AVAILABLE_SESSIONS
        if "2024-26" in session_options:
            session_options = [s for s in session_options if s != "2024-26"]
        if "2027-29" not in session_options:
            session_options.append("2027-29")
    except NameError:
        session_options = ["2025-27", "2026-28", "2027-29"]

    if entry_mode == "📋 By Complete Section":
        c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 2, 1.5, 2])
        
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
                with c3: sel_subject = st.selectbox("Select Subject:", allowed_subs, key="entry_sub_filter_teacher")
                with c4: sel_section = st.selectbox("Select Section:", allowed_secs, key="entry_sec_filter_teacher")
                with c5: st.info("🔒 Bound to Profile")
                sel_class = "ALL"
            else:
                st.warning("🚨 You do not have any active subjects or sections assigned yet.")
                sel_subject, sel_section, sel_session, sel_class = None, None, None, None
        else:
            with c1: 
                sel_session = st.selectbox("Select Session:", session_options, key="entry_sess_a")
            
            with c2:
                academic_system = st.selectbox("Select Academic System:", ["Annual System", "Semester System"], key="marks_sys_type_a")

            with c3: 
                if academic_system == "Annual System":
                    discipline_ui_options = ["MEDICAL", "ENGINEERING", "ICS (PHYSICS)", "ICS (STATS)", "COMMERCE", "HUMANITIES"]
                    selected_ui_discipline = st.selectbox("Select Discipline:", discipline_ui_options, key="marks_disc_sel")
                    sel_discipline = selected_ui_discipline.upper().replace(" ", "_").replace("(", "").replace(")", "")
                    if "PHYSIC" in sel_discipline: sel_discipline = "ICS_PHYSICS"
                    elif "STAT" in sel_discipline: sel_discipline = "ICS_STATISTICS"
                    
                    sel_class = st.selectbox("Select Class Level:", ["11th", "12th", "ALL"], key="entry_class_filter_a")
                else:
                    sel_discipline = "DIPLOMA_IN_IT_DIT"
                    sel_class = st.selectbox("Select Semester Context:", ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester", "ALL"], key="entry_sem_filter_a")

            with c4: 
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
                
            with c5: 
                if academic_system == "Annual System":
                    DISCIPLINE_SUBJECTS_MAP_LOCAL = {
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

                    if sel_class == "ALL":
                        list_11th = DISCIPLINE_SUBJECTS_MAP_LOCAL.get(f"{sel_discipline}_11TH", [])
                        list_12th = DISCIPLINE_SUBJECTS_MAP_LOCAL.get(f"{sel_discipline}_12TH", [])
                        available_subjects = list(dict.fromkeys(list_11th + list_12th))
                    else:
                        suffix = "_12TH" if sel_class == "12th" else "_11TH"
                        lookup_key = f"{sel_discipline}{suffix}"
                        available_subjects = DISCIPLINE_SUBJECTS_MAP_LOCAL.get(lookup_key, ["English", "Urdu", "Physics"])
                else:
                    if "1st Semester" in sel_class:
                        available_subjects = ["Information Technology", "Office Automation", "Networking", "C-Programming", "Operating System", "Project"]
                    elif "2nd Semester" in sel_class:
                        available_subjects = ["Data Base System", "Video Editing", "Web Development Essential", "Graphics Design", "Project"]
                    else: 
                        available_subjects = ["English", "Urdu", "Mathematics", "Statistics", "T_Quran", "Islamic_Studies"]
                
                sel_subject = st.selectbox("Select Course/Subject:", available_subjects, key="entry_sub_filter_a")
        
        if sel_subject and sel_section and sel_session:
            row2_1, row2_2 = st.columns(2)
            with row2_1: 
                sel_exam = st.selectbox("Select Examination Cycle:", all_frameworks, index=1, key="entry_exam_sel")
            with row2_2: 
                total_marks = st.number_input("Set Total Marks:", min_value=1, max_value=200, value=100, key="sec_global_marks")
            
            try:
                query_params = {
                    "subject": str(sel_subject).strip().upper(),
                    "exam": str(sel_exam).strip().upper(),
                    "section": str(sel_section).strip().upper(),
                    "session": str(sel_session).strip()
                }

                roster_df = run_query("""
                    SELECT s.id AS "ID", s.name AS "Student Name", m.marks_obtained AS "Marks"
                    FROM students s
                    LEFT JOIN marks m ON s.id = m.student_id 
                        AND UPPER(TRIM(m.subject)) = :subject
                        AND UPPER(TRIM(m.exam_type)) = :exam
                    WHERE UPPER(TRIM(s.section)) = :section
                      AND UPPER(TRIM(CAST(s.session AS VARCHAR))) = :session
                      AND (s.status IS NULL OR UPPER(TRIM(s.status)) NOT IN ('LEFT', 'INACTIVE', 'DROPOUT'))
                    ORDER BY s.id ASC
                """, query_params)
                
                if roster_df.empty:
                    st.info(f"💡 No active student records found in Section '{sel_section}' under Session {sel_session}.")
                else:
                    st.markdown(f"##### 📝 Enter Obtained Marks for {sel_section} — {sel_subject} ({sel_exam})")
                    
                    col_b1, col_b2, col_b3 = st.columns([3, 1, 1])
                    with col_b2:
                        if st.button("🏁 Mark All Absent", use_container_width=True, key="bulk_absent_btn"):
                            for r_idx, r_row in roster_df.iterrows():
                                st.session_state[f"abs_{r_row['ID']}"] = True
                                st.session_state[f"nc_{r_row['ID']}"] = False
                            st.rerun()
                    with col_b3:
                        if st.button("🚫 Mark All NC", use_container_width=True, key="bulk_nc_btn"):
                            for r_idx, r_row in roster_df.iterrows():
                                st.session_state[f"abs_{r_row['ID']}"] = False
                                st.session_state[f"nc_{r_row['ID']}"] = True
                            st.rerun()
                    
                    with st.form("bulk_marks_form"):
                        updated_marks = {}
                        
                        h_c1, h_c2, h_c3, h_c4 = st.columns([3, 1, 0.6, 0.6])
                        h_c2.caption("🔢 **Obtained**")
                        h_c3.caption("❌ **Absent**")
                        h_c4.caption("➖ **NC**")
                        st.markdown("<hr style='margin:0px 0px 10px 0px; padding:0px;'>", unsafe_allow_html=True)

                        for idx, row in roster_df.iterrows():
                            col_s1, col_s2, col_s3, col_s4 = st.columns([3, 1, 0.6, 0.6])
                            col_s1.write(f"👤 **{row['ID']}** — {row['Student Name']}")
                            
                            db_val = str(row['Marks']).strip().upper() if pd.notna(row['Marks']) else ""
                            
                            if f"abs_{row['ID']}" not in st.session_state:
                                st.session_state[f"abs_{row['ID']}"] = (db_val in ['A', 'ABSENT'])
                            if f"nc_{row['ID']}" not in st.session_state:
                                st.session_state[f"nc_{row['ID']}"] = (db_val == 'NC')

                            chk_absent = col_s3.checkbox("", key=f"abs_{row['ID']}", label_visibility="collapsed")
                            chk_nc = col_s4.checkbox("", key=f"nc_{row['ID']}", label_visibility="collapsed")
                            
                            initial_score = "" if db_val in ['A', 'ABSENT', 'NC'] else db_val
                            is_disabled = chk_absent or chk_nc
                            display_score = "A" if chk_absent else ("NC" if chk_nc else initial_score)
                            
                            score_input = col_s2.text_input(
                                "Obtained", 
                                value=display_score if is_disabled else initial_score, 
                                key=f"marks_{row['ID']}", 
                                label_visibility="collapsed",
                                disabled=is_disabled
                            )
                            
                            updated_marks[row['ID']] = "A" if chk_absent else ("NC" if chk_nc else score_input)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.form_submit_button("💾 Save Examination Marks Ledger", type="primary", use_container_width=True):
                            for s_id, score in updated_marks.items():
                                score_clean = str(score).strip().upper()
                                execute_db_command("DELETE FROM marks WHERE student_id = :s_id AND UPPER(TRIM(subject)) = UPPER(TRIM(:subject)) AND UPPER(TRIM(exam_type)) = UPPER(TRIM(:exam))", {"s_id": int(s_id), "subject": sel_subject, "exam": sel_exam})
                                if score_clean != "":
                                    execute_db_command("INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:s_id, :subject, :exam, :score, :total)", 
                                                      {"s_id": int(s_id), "subject": sel_subject.strip().upper(), "exam": sel_exam.strip().upper(), "score": score_clean, "total": float(total_marks)})
                            
                            for s_id in updated_marks.keys():
                                st.session_state.pop(f"abs_{s_id}", None)
                                st.session_state.pop(f"nc_{s_id}", None)
                                
                            st.success("🎉 Section marks recorded successfully!")
                            st.rerun()
            except Exception as e:
                st.error(f"Database sync issue: {e}")

    elif entry_mode == "👤 By Single Student Roll Number":
        st.subheader("👤 Single Student Marks Record Manager")
        
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            s_system = st.selectbox("Academic System:", ["Annual System", "Semester System"], key="single_sys_type")
        with sc2:
            s_session_sel = st.selectbox("Session Context:", session_options, key="single_sess_type")
        with sc3:
            if s_system == "Annual System":
                s_class_sel = st.selectbox("Class Level:", ["11th", "12th", "ALL"], key="single_class_type")
            else:
                s_class_sel = st.selectbox("Semester Context:", ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester", "ALL"], key="single_class_type")

        single_id = st.text_input("🔍 Enter Student Roll Number / ID:", key="single_marks_id_input")
        
        if single_id and single_id.isdigit():
            query_conds = {
                "id": int(single_id), 
                "sess": str(s_session_sel).strip()
            }
            
            base_sql = """
                SELECT name, section, session, class FROM students 
                WHERE id = :id AND UPPER(TRIM(CAST(session AS VARCHAR))) = :sess
            """
            
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
                                cleaned_sections = [str(sec).upper().strip() for sec in sections]
                                if s_section in cleaned_sections:
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
                
                if s_system == "Annual System":
                    DISCIPLINE_SUBJECTS_MAP_LOCAL = {
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
                    
                    if "12" in s_class:
                        cls_suffix = "_12TH"
                    elif "11" in s_class:
                        cls_suffix = "_11TH"
                    else:
                        cls_suffix = "_11TH" 
                        
                    single_sub_options = DISCIPLINE_SUBJECTS_MAP_LOCAL.get(f"{detected_discipline}{cls_suffix}", None)
                    
                    if not single_sub_options:
                        if detected_discipline == "ENGINEERING":
                            single_sub_options = ["English", "Urdu", "Physics", "Chemistry", "Mathematics", "Islamic Studies", "T_Quran", "Pak_St"]
                        elif "ICS" in detected_discipline:
                            single_sub_options = ["English", "Urdu", "Physics", "Computer Science", "Mathematics", "Islamic Studies", "T_Quran", "Pak_St"]
                        elif detected_discipline == "COMMERCE":
                            single_sub_options = ["English", "Urdu", "Principles of Accounting", "Islamic Studies", "T_Quran", "Pak_St"]
                        elif detected_discipline == "HUMANITIES":
                            single_sub_options = ["English", "Urdu", "Education", "Islamic Studies", "T_Quran", "Pak_St"]
                        else:
                            single_sub_options = ["English", "Urdu", "Physics", "Chemistry", "Biology", "Islamic Studies", "T_Quran", "Pak_St"]
                else:
                    if "1ST" in s_class or "1" in s_class:
                        single_sub_options = ["Information Technology", "Office Automation", "Networking", "C-Programming", "Operating System", "Project"]
                    elif "2ND" in s_class or "2" in s_class:
                        single_sub_options = ["Data Base System", "Video Editing", "Web Development Essential", "Graphics Design", "Project"]
                    else: 
                        single_sub_options = ["Information Technology", "Office Automation", "Networking", "Data Base System", "Web Development Essential"]
                
                c_m1, c_m2, c_m3, c_m4 = st.columns([1.5, 1.2, 1, 1.3])
                with c_m1: 
                    single_sub = st.selectbox("Course/Subject:", single_sub_options, key="s_sub_val")
                
                with c_m2: 
                    single_exam = st.selectbox("Exam Type:", all_frameworks, index=1, key="s_exam_val")
                with c_m3: 
                    single_total = st.number_input("Total Marks:", min_value=1, value=100, key="s_tot_val")
                
                existing_m = run_query("""
                    SELECT marks_obtained FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND UPPER(TRIM(exam_type)) = UPPER(TRIM(:exam))
                """, {"id": int(single_id), "sub": single_sub, "exam": single_exam})
                init_m_val = str(existing_m['marks_obtained'].iloc[0]) if not existing_m.empty else ""
                
                with c_m4: 
                    single_obtained = st.text_input("Obtained (or A / NC):", value=init_m_val, key="s_obt_val")
                
                if st.button("💾 Save Individual Marks Record", type="primary", use_container_width=True):
                    execute_db_command("""
                        DELETE FROM marks WHERE student_id = :id AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND UPPER(TRIM(exam_type)) = UPPER(TRIM(:exam))
                    """, {"id": int(single_id), "sub": single_sub, "exam": single_exam})
                    
                    if single_obtained.strip() != "":
                        execute_db_command("""
                            INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) VALUES (:id, :sub, :exam, :score, :tot)
                        """, {"id": int(single_id), "sub": single_sub.strip().upper(), "exam": single_exam.strip().upper(), "score": single_obtained.strip().upper(), "tot": float(single_total)})
                    st.success(f"🎉 Marks configuration updated successfully for {s_name}!")
                    st.rerun()

    elif entry_mode == "📤 Bulk Excel/CSV Import":
        st.subheader("📤 Bulk Upload Exam Marks Matrix")
        
        with st.expander("ℹ️ View Expected File Schema & Rules", expanded=True):
            st.markdown("""
            Your uploaded sheet **must** contain the following exact column headings:
            * `Roll Number` or `Student ID` (Integer corresponding to Student Roll Number)
            * `Subject` (e.g., *Physics, Pak_St, Banking, Education, T_Quran*)
            * `Exam Type` (Must exactly match an entry in the system cycle list below)
            * `Total Marks` (Numeric limit value)
            * `Marks Obtained` (Numeric value, or `A` / `ABSENT` for absent students)
            """)
            st.caption(f"**Valid System Cycles:** {', '.join(all_frameworks)}")

        uploaded_file = st.file_uploader("Choose your Excel or CSV file", type=["xlsx", "csv"], key="marks_file_uploader")
        
        if uploaded_file is not None:
            try:
                import pandas as pd
                if uploaded_file.name.endswith('.csv'):
                    df_raw = pd.read_csv(uploaded_file)
                else:
                    df_raw = pd.read_excel(uploaded_file)
                
                df_raw.columns = [str(c).strip().upper() for c in df_raw.columns]
                
                id_col = next((c for c in ['ROLL NUMBER', 'STUDENT ID', 'ID', 'ROLL_NO'] if c in df_raw.columns), None)
                sub_col = next((c for c in ['SUBJECT', 'COURSE', 'SUBJECT NAME'] if c in df_raw.columns), None)
                exam_col = next((c for c in ['EXAM TYPE', 'EXAMINATION CYCLE', 'EXAM', 'EXAM_TYPE'] if c in df_raw.columns), None)
                tot_col = next((c for c in ['TOTAL MARKS', 'TOTAL_MARKS', 'TOTAL'] if c in df_raw.columns), None)
                obt_col = next((c for c in ['MARKS OBTAINED', 'MARKS', 'OBTAINED', 'OBTAINED MARKS'] if c in df_raw.columns), None)
                
                if not all([id_col, sub_col, exam_col, tot_col, obt_col]):
                    st.error("❌ Failed to parse file. Missing one or more required columns: Roll Number, Subject, Exam Type, Total Marks, and Marks Obtained.")
                elif df_raw.empty:
                    st.warning("⚠️ The uploaded spreadsheet file contains no rows of data.")
                else:
                    st.success(f"📊 Read {len(df_raw)} records successfully. Previewing data below:")
                    st.dataframe(df_raw.head(10), use_container_width=True)
                    
                    with st.form("bulk_import_confirmation"):
                        st.markdown("##### ⚙️ File Import Execution Configurations")
                        dup_strategy = st.radio("Conflict Handling Rule:", ["Overwrite/Update Match Records", "Skip if Marks Exist"], horizontal=True)
                        
                        if st.form_submit_button("🚀 Execute Matrix Import & Database Sync", type="primary"):
                            success_count = 0
                            skipped_count = 0
                            error_logs = []
                            valid_exams_upper = [f.strip().upper() for f in all_frameworks]
                            
                            for index, row in df_raw.iterrows():
                                try:
                                    raw_id = str(row[id_col]).strip().split('.')[0]
                                    if not raw_id.isdigit():
                                        error_logs.append(f"Row {index+2}: Invalid Roll Number structure format '{row[id_col]}'")
                                        continue
                                    
                                    s_id = int(raw_id)
                                    subject_str = str(row[sub_col]).strip().upper()
                                    exam_str = str(row[exam_col]).strip().upper()
                                    
                                    if exam_str not in valid_exams_upper:
                                        error_logs.append(f"Row {index+2}: Invalid Exam Cycle '{exam_str}'. Not found in system framework.")
                                        continue
                                        
                                    total_val = float(row[tot_col])
                                    obtained_val = str(row[obt_col]).strip().upper()
                                    
                                    if obtained_val == "" or pd.isna(row[obt_col]):
                                        skipped_count += 1
                                        continue
                                        
                                    chk_student = run_query("SELECT id FROM students WHERE id = :id", {"id": s_id})
                                    if chk_student.empty:
                                        error_logs.append(f"Row {index+2}: Student ID '{s_id}' does not exist in student database.")
                                        continue
                                        
                                    chk_marks = run_query("""
                                        SELECT student_id FROM marks 
                                        WHERE student_id = :id 
                                          AND UPPER(TRIM(subject)) = :sub 
                                          AND UPPER(TRIM(exam_type)) = :exam
                                    """, {"id": s_id, "sub": subject_str, "exam": exam_str})
                                    
                                    if not chk_marks.empty:
                                        if dup_strategy == "Skip if Marks Exist":
                                            skipped_count += 1
                                            continue
                                        else:
                                            execute_db_command("""
                                                DELETE FROM marks 
                                                WHERE student_id = :id 
                                                  AND UPPER(TRIM(subject)) = :sub 
                                                  AND UPPER(TRIM(exam_type)) = :exam
                                            """, {"id": s_id, "sub": subject_str, "exam": exam_str})
                                            
                                    execute_db_command("""
                                        INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks) 
                                        VALUES (:id, :sub, :exam, :score, :tot)
                                    """, {
                                        "id": s_id, "sub": subject_str, "exam": exam_str, "score": obtained_val, "tot": total_val
                                    })
                                    success_count += 1
                                    
                                except Exception as row_err:
                                    error_logs.append(f"Row {index+2}: Unexpected formatting issue. Detail: {row_err}")
                            
                            st.success(f"🏁 Processing Completed! Successfully added/updated **{success_count}** records.")
                            if skipped_count > 0:
                                st.info(f"ℹ️ Skipped **{skipped_count}** entries based on configuration rules or empty status values.")
                            
                            if error_logs:
                                with st.expander("🚨 View Processing Logs & Mismatches", expanded=True):
                                    for log in error_logs:
                                        st.error(log)
                                        
                            try:
                                st.cache_data.clear()
                            except Exception:
                                pass
                            st.rerun()
                            
            except Exception as e:
                st.error(f"💥 Critical file parsing system breakdown error: {e}")

# ====================================================================================
# MODULE 2: ATTENDANCE ENTRY MANAGEMENT
# ====================================================================================
if menu_choice == "📅 Attendance Entry Management":
    st.title("📅 Attendance Entry Management Panel")
    
    att_sub_type = st.segmented_control(
        "Select Attendance Interval Mode:",
        ["📅 Daily Attendance Entry", "👤 By Single Student Roll Number"],
        default="📅 Daily Attendance Entry",
        key="attendance_interval_segmented_control"
    )
    st.markdown("###")

    session_options = ["2025-27", "2026-28", "2027-29"] 
    try:
        db_sessions = run_query("SELECT DISTINCT session FROM students WHERE session IS NOT NULL AND session != ''")
        if not db_sessions.empty:
            session_options = sorted(db_sessions['session'].dropna().astype(str).tolist())
    except Exception:
        pass

    if att_sub_type == "📅 Daily Attendance Entry":
        st.subheader("📅 Daily Attendance Roster Sheet")
        st.markdown("---")
        
        d1, d2, d3, d4 = st.columns([1.2, 1.3, 1.5, 2.0])
        with d1:
            sel_session = st.selectbox("Select Session:", session_options, key="daily_att_sess")
            
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

                with st.form("interactive_daily_attendance_form"):
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
                            
                        attendance_checkbox_map[row['ID']] = col_s3.checkbox("Present", value=initial_checkbox_state, key=f"chk_student_{row['ID']}", label_visibility="collapsed")

                    st.markdown("###")
                    if st.form_submit_button("💾 Save & Lock Daily Attendance Sheet", type="primary", use_container_width=True):
                        try:
                            for s_id, checked_present in attendance_checkbox_map.items():
                                status_code = "P" if checked_present else "A"
                                param_pack = {"s_id": int(s_id), "att_date": str(target_date), "status": status_code}
                                
                                execute_db_command("DELETE FROM daily_attendance WHERE student_id = :s_id AND attendance_date = :att_date", {"s_id": int(s_id), "att_date": str(target_date)})
                                execute_db_command("INSERT INTO daily_attendance (student_id, attendance_date, status) VALUES (:s_id, :att_date, :status)", param_pack)
                            
                            st.success(f"🎉 Roster saved successfully for section {sel_section}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error encountered during standard write cycle: {e}")

    elif att_sub_type == "👤 By Single Student Roll Number":
        st.subheader("👤 Single Student Attendance Record Manager")
        st.markdown("---")
        
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            s_session_sel = st.selectbox("Select Session Context:", session_options, key="single_att_sess_filter")
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
                        
                        execute_db_command("""
                            DELETE FROM daily_attendance WHERE student_id = :id AND attendance_date = :dt
                        """, {"id": int(single_id), "dt": str(att_date)})
                        
                        execute_db_command("""
                            INSERT INTO daily_attendance (student_id, attendance_date, status) VALUES (:id, :dt, :st)
                        """, {"id": int(single_id), "dt": str(att_date), "st": final_status_code})
                        
                        st.success(f"🎉 Roster update completed successfully for {s_name}!")
                        st.rerun()
                        
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

elif menu_choice == "📋 Daily Attendance Report":
    import datetime
    import pandas as pd
    import streamlit.components.v1 as components
    from io import BytesIO

    st.title("📋 Daily Attendance Report")

    # 1. SETUP
    try:
        session_choices = sorted(list(set(AVAILABLE_SESSIONS)))
    except NameError:
        session_choices = ["2025-27", "2026-28", "2027-29"]
        
    c1, c2 = st.columns(2)
    with c1:
        report_sessions = st.multiselect("🎯 Select Session Grouping(s):", session_choices, default=[session_choices[0]])
    with c2:
        report_date = st.date_input("🗓️ Target Date:", value=datetime.date.today())

    if not report_sessions:
        st.warning("Please select at least one session.")
        st.stop()

    # 2. DATA FETCHING (Robust)
    # Ensure sessions is a tuple for the SQL IN clause
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
            if "11" in cls: return "11th (Girls)" if any(x in sec for x in ["G", "WHITE", "GREEN"]) else "11th (Boys)"
            if "12" in cls: return "12th (Girls)" if any(x in sec for x in ["Q", "G", "WHITE", "GREEN"]) else "12th (Boys)"
            return "Other Tiers (DIT)"
        df['Group_Category'] = df.apply(classify, axis=1)

        summary = df.groupby(['Group_Category', 'Section', 'In_Charge']).agg(
            Total=('id', 'count'), Present=('Attendance_Status', lambda x: x.isin(['P', 'PRESENT', '1']).sum()),
            Absent=('Attendance_Status', lambda x: x.isin(['A', 'ABSENT', '0']).sum())
        ).reset_index()

        # 3. HTML PRINT ENGINE
        table_rows = ""
        grand_total = {"Total": 0, "Present": 0, "Absent": 0}
        
        for cat in ["11th (Girls)", "12th (Girls)", "11th (Boys)", "12th (Boys)", "Other Tiers (DIT)"]:
            cat_data = summary[summary['Group_Category'] == cat]
            if cat_data.empty: continue
            
            sub_total = cat_data.agg({'Total': 'sum', 'Present': 'sum', 'Absent': 'sum'})
            grand_total['Total'] += sub_total['Total']
            grand_total['Present'] += sub_total['Present']
            grand_total['Absent'] += sub_total['Absent']
            
            row_span = len(cat_data)
            for i, (_, row) in enumerate(cat_data.iterrows()):
                pct = f"{int((row['Present']/row['Total'])*100)}%" if row['Total'] > 0 else "0%"
                table_rows += f"<tr>"
                if i == 0: table_rows += f'<td rowspan="{row_span}" style="border:1px solid #000; font-weight:bold;">{cat}</td>'
                table_rows += f'<td>{row["Section"]}</td><td>{row["In_Charge"]}</td><td>{row["Total"]}</td><td>{row["Present"]}</td><td>{row["Absent"]}</td><td>{pct}</td></tr>'
            
            table_rows += f'<tr style="background:#f9f9f9; font-weight:bold;">' \
                          f'<td colspan="3" style="text-align:left; padding-left:10px;">Sub-Total ({cat})</td>' \
                          f'<td>{sub_total["Total"]}</td><td>{sub_total["Present"]}</td><td>{sub_total["Absent"]}</td>' \
                          f'<td>{int((sub_total["Present"]/sub_total["Total"])*100) if sub_total["Total"] > 0 else 0}%</td></tr>'

        grand_pct = int((grand_total['Present']/grand_total['Total'])*100) if grand_total['Total'] > 0 else 0
        table_rows += f'<tr style="background:#ddd; font-weight:bold; font-size:14px;">' \
                      f'<td colspan="3" style="text-align:left; padding-left:10px;">GRAND TOTAL</td>' \
                      f'<td>{grand_total["Total"]}</td><td>{grand_total["Present"]}</td><td>{grand_total["Absent"]}</td><td>{grand_pct}%</td></tr>'

        # Update the HTML block inside the template:
        html_template = f"""
        <html>
        <head>
            <style>
                body {{ font-family: "Times New Roman", serif; padding: 10px; }}
                /* Header Container: Flexbox aligns logo left, text center */
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
            ws.set_column('A:A', 15); ws.set_column('B:B', 12); ws.set_column('C:C', 30)
            ws.set_column('D:G', 10); ws.set_default_row(25)
        st.download_button("📥 Download Excel", output.getvalue(), f"Attendance_{report_date}.xlsx")

# MODULE: 📋 SECTION SUMMARY REPORT
# ====================================================================================
elif menu_choice == "📋 Section Summary Report":
import io
st.title("📋 Section Summary Report Ledger")

    try:
        session_options = list(AVAILABLE_SESSIONS)
        if "2024-26" in session_options:
            session_options = [s for s in session_options if s != "2024-26"]
    except NameError:
        session_options = ["2025-27", "2026-28", "2027-29"]

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
            disc_options = ["MEDICAL", "ENGINEERING", "ICS_PHYSICS", "ICS_STATS", "COMMERCE", "HUMANITIES"]
            raw_disc = st.selectbox("Select Discipline:", disc_options, key="summary_disc")
            sel_disc = str(raw_disc).strip().upper()
        else:
            sel_disc = "DIPLOMA_IN_IT_DIT"
            st.info("⚡ DIT System Active")
        
    with col_b: 
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

        if db_sections:
            if "STATS" in sel_disc:
                sec_options = [s for s in db_sections if "STATS" in s.upper() or "WHITE" in s.upper() or "3" in s]
            elif "PHYSICS" in sel_disc or "ICS" in sel_disc:
                sec_options = [s for s in db_sections if "PHYS" in s.upper() or "GREEN" in s.upper() or "1" in s or "2" in s]
            elif "MEDICAL" in sel_disc:
                sec_options = [s for s in db_sections if "MED" in s.upper() or "M" in s.upper() or "BLUE" in s.upper()]
            elif "ENGINEERING" in sel_disc:
                sec_options = [s for s in db_sections if "ENG" in s.upper() or "E" in s.upper()]
            elif "COMMERCE" in sel_disc:
                sec_options = [s for s in db_sections if "COM" in s.upper() or "I" in s.upper()]
            else:
                sec_options = db_sections
                
            if not sec_options:
                sec_options = db_sections
        else:
            if academic_system == "Semester System":
                sec_options = ["DIT_G", "DIT_B"]
            else:
                sec_options = ["MG_BLUE", "MG_WHITE"] if "11" in selected_class else ["MQ1", "MQ2"]

        dynamic_widget_key = f"summary_sec_adaptive_{selected_class}_{sel_disc}_{db_session_string}_{academic_system}"
        sel_sec = st.selectbox("Select Section:", sec_options, index=0, key="dynamic_widget_key")
        
    with col_c: 
        exam_options = ["MID_TERM", "FINAL_TERM", "ASSIGNMENT", "QUIZ"] if academic_system == "Semester System" else ["MT_1", "MT_2", "PRE_BOARD", "MATRIC", "ACADEMICS"]
        sel_exam = st.selectbox("Select Exam Cycle:", exam_options, key="summary_exam")

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
    
    if academic_system == "Semester System":
        if selected_class == "Semester 1":
            subjects = ["ICT", "Introduction to MS-Office", "Computer Networks", "Operating System", "Introduction to Programming"]
        elif selected_class == "Semester 2":
            subjects = ["Data Base System", "Video Editing", "Web Development Essential", "Graphics Design", "Project"]
        else:
            subjects = ["English", "Urdu", "Isl_Eth", "Stats", "Maths", "T_Quran"]
    else:
        if "STATS" in sel_disc:
            subjects = ["ENGLISH", "URDU", "STATISTICS", "COMPUTER", "MATHEMATICS", "ISL_ETH", "T_QURAN"]
        elif "PHYSICS" in sel_disc or "ICS" in sel_disc:
            subjects = ["ENGLISH", "URDU", "PHYSICS", "COMPUTER", "MATHEMATICS", "ISL_ETH", "T_QURAN"]
        elif "MEDICAL" in sel_disc:
            subjects = ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "BIOLOGY", "ISL_ETH", "T_QURAN"]
        elif "ENGINEERING" in sel_disc:
            subjects = ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "MATHEMATICS", "ISL_ETH", "T_QURAN"]
        elif "COMMERCE" in sel_disc:
            subjects = ["ENGLISH", "URDU", "PRINCIPLES OF ACCOUNTING", "ECONOMICS", "COMMERCE", "ISL_ETH", "T_QURAN"]
        else:
            subjects = ["ENGLISH", "URDU", "ISL_ETH", "T_QURAN"]

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
        components.html(analytics_html_payload, height=750, scrolling=True)  need to work on this code now          

# ====================================================================================
# MODULE: 📈 MULTI-TEST PROGRESS REPORT
# ====================================================================================
if menu_choice == "📈 Multi-Test Progress Report":
    st.title("📈 Multi-Test Progress Analytics")
    st.markdown("Select your reporting scope below to generate high-fidelity, print-ready student progress cards.")

    st.markdown("""
        <style>
        @media print {
            .no-print { display: none !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    all_frameworks = [
        "MATRIC", "MT_1", "MT_2", "MT_3", "MT_4", "SEND_UP", "MT_5",
        "T_1", "T_2", "T_3", "T_4", "T_5", "T_6", "T_7", "T_8", "T_9", "T_10",
        "HALF_BOOK01", "HALF_BOOK02", "PRE_BOARD"
    ]

    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    st.markdown('##### 🎛️ Filter Configuration Panel')
    
    col_base1, col_base2 = st.columns(2)
    with col_base1:
        sel_session_global = st.selectbox("Select Session Context:", AVAILABLE_SESSIONS, index=1, key="global_sel_sess")
    with col_base2:
        academic_system = st.selectbox("Select Academic System:", ["Annual System", "Semester System"], key="mt_system_type")

    st.markdown("<div style='margin: 5px 0;'></div>", unsafe_allow_html=True)

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

    else:  
        with col_dyn1:
            sel_class_global = st.selectbox("Select Semester Context:", ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester"], key="global_sel_class")
            
        with col_dyn2:
            semester_sections = ["DIT_G", "DIT_B"]
            sel_sec = st.selectbox("Select Target Section:", options=semester_sections, index=0, key="global_sel_sec")
            
        with col_dyn3:
            selected_exams_list = st.multiselect("🎯 Select Tests:", options=all_frameworks, default=["MT_1", "MT_2", "MT_3"], key="global_exams")
            
    st.markdown("---")

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
                marks_df["subject_name"] = marks_df["subject_name"].astype(str).str.strip()
        except Exception as e:
            st.error(f"⚠️ Failed fetching performance records. Details: {str(e)}")

        try:
            sample_att = run_query("SELECT * FROM attendance LIMIT 1", {})
            cols_att = [c.lower() for c in sample_att.columns] if not sample_att.empty else []
            
            if "attendance_date" in cols_att: date_col = "attendance_date"
            elif "date_marked" in cols_att: date_col = "date_marked"
            elif "date" in cols_att: date_col = "date"
            elif "att_date" in cols_att: date_col = "att_date"
            else: date_col = cols_att[1] if len(cols_att) > 1 else "date"
            
            status_col = "status" if "status" in cols_att else ("attendance_status" if "attendance_status" in cols_att else "status")

            attendance_df = run_query(f"""
                SELECT student_id, {date_col} as attendance_date, {status_col} as status
                FROM attendance
                WHERE student_id IN ({placeholders_str})
            """, params_dict)
            
            if not attendance_df.empty:
                attendance_df.columns = [c.lower() for c in attendance_df.columns]
                attendance_df["student_id"] = attendance_df["student_id"].astype(str).str.strip()
                
        except Exception as e:
            try:
                attendance_df = run_query(f"SELECT * FROM attendance WHERE student_id IN ({placeholders_str})", params_dict)
                if not attendance_df.empty:
                    attendance_df.columns = [c.lower() for c in attendance_df.columns]
                    attendance_df["student_id"] = attendance_df["student_id"].astype(str).str.strip()
                    
                    for field in ["date_marked", "date", "att_date"]:
                        if field in attendance_df.columns:
                            attendance_df = attendance_df.rename(columns={field: "attendance_date"})
                            break
                    for field in ["status", "attendance_status"]:
                        if field in attendance_df.columns:
                            attendance_df = attendance_df.rename(columns={field: "status"})
                            break
            except Exception as internal_err:
                pass

        css_rules = "body { background-color: #ffffff; margin: 0; padding: 10px; }"
        css_rules += " .action-dashboard-panel { display: flex; flex-wrap: wrap; gap: 12px; max-width: 850px; margin: 10px auto 25px auto; font-family: 'Arial', sans-serif; }"
        css_rules += " .action-control-btn { flex: 1; min-width: 180px; color: white; border: none; padding: 12px 18px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: background 0.2s, transform 0.1s, opacity 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px; }"
        css_rules += " .action-control-btn:active { transform: scale(0.97); } .btn-print-single { background-color: #2e7d32; } .btn-print-single:hover { background-color: #1b5e20; }"
        css_rules += " .btn-print-bulk { background-color: #1565c0; } .btn-print-bulk:hover { background-color: #0d47a1; } .btn-img-single { background-color: #e65100; }"
        css_rules += " .btn-img-single:hover { background-color: #b33900; } .btn-img-bulk { background-color: #6a1b9a; } .btn-img-bulk:hover { background-color: #4a148c; }"
        css_rules += " .cck-container { background-color: #ffffff; border: 1px solid #000000; padding: 30px; margin: 0 auto 30px auto; max-width: 850px; color: #000000; font-family: 'Arial', sans-serif; page-break-after: always; box-sizing: border-box; }"
        css_rules += " .cck-header-wrapper { display: flex; align-items: center; justify-content: center; margin-bottom: 5px; position: relative; }"
        css_rules += " .cck-logo-image-container { width: 75px; height: 75px; position: absolute; left: 20px; display: flex; align-items: center; justify-content: center; }"
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
            s_section = " ".join(raw_section.replace("\n", " ").split())
            
            raw_class = str(s_meta["class"]) if s_meta.get("class") else sel_class_global
            s_class = " ".join(raw_class.replace("\n", " ").split())
            
            table_rows_html = ""
            total_row_html = ""
            grand_total_percentages = [0]

            if not marks_df.empty:
                s_marks = marks_df[marks_df["student_id"] == s_id].copy()
                
                if not s_marks.empty:
                    distinct_subjects = sorted(s_marks["subject_name"].unique())
                    exam_totals_obtained = {exam: 0.0 for exam in selected_exams_list}
                    exam_totals_possible = {exam: 0.0 for exam in selected_exams_list}
                    
                    for sub in distinct_subjects:
                        sub_marks = s_marks[s_marks["subject_name"] == sub]
                        row_tds = f"<td style='text-align: left; padding-left: 8px;'><strong>{sub}</strong></td>"
                        subject_pct_accum = 0
                        valid_exams_count = 0
                        
                        for exam in selected_exams_list:
                            if academic_system == "Semester System":
                                match_row = sub_marks[sub_marks["subject_name"].str.upper() == str(exam).strip().upper()]
                            else:
                                match_row = sub_marks[sub_marks["exam_type"] == str(exam).strip().upper()]
                                
                            if not match_row.empty:
                                try:
                                    obt = float(match_row.iloc[0]["marks_obtained"])
                                    tot = float(match_row.iloc[0]["total_marks"])
                                    pct = int((obt / tot) * 100) if tot > 0 else 0
                                    
                                    row_tds += f"<td>{pct}%</td>"
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

            tot_days_row, att_days_row, pct_days_row = "", "", ""
            overall_tot_days, overall_att_days = 0, 0

            month_map = {
                "May": 5, "June": 6, "July": 7, "Aug.": 8, "Sept.": 9, "Oct.": 10, 
                "Nov.": 11, "Dec.": 12, "Jan.": 1, "Feb.": 2, "March": 3, "April": 4
            }
            attendance_matrix = {m: {"total": 0, "present": 0} for m in month_map.keys()}

            if not attendance_df.empty:
                s_att = attendance_df[attendance_df["student_id"] == s_id].copy()
                if not s_att.empty:
                    s_att['parsed_date'] = pd.to_datetime(s_att['attendance_date'], errors='coerce') if 'attendance_date' in s_att.columns else pd.NaT

                    for m_name, m_num in month_map.items():
                        if 'attendance_date' in s_att.columns:
                            month_records = s_att[s_att['parsed_date'].dt.month == m_num]
                            t_days = len(month_records)
                            p_days = len(month_records[month_records['status'].astype(str).str.strip().str.upper().isin(['P', 'PRESENT', '1'])])
                        else:
                            month_records = s_att[s_att['month_name'].astype(str).str.strip().str.lower() == m_name.lower()]
                            t_days = int(month_records['total_days'].sum()) if not month_records.empty else 0
                            p_days = int(month_records['present_days'].sum()) if not month_records.empty else 0

                        if t_days > 0:
                            attendance_matrix[m_name] = {"total": t_days, "present": p_days}

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
                        <tr><td>Age%</td>{pct_days_row}</tr>
                    </tbody>
                </table>
                <div class="cck-remarks-area"><strong>Remarks:</strong><div class="cck-remarks-line">{remarks_text}</div></div>
                <div class="cck-footer-sign"><strong>Principal Sign</strong></div>
            </div>
            """
        
        composite_html_payload += """
            </div> 
            <script>
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
                triggerImageCaptureSequence(targetList, 0);
            }

            function triggerImageCaptureSequence(targetList, currentIndex) {
                if (currentIndex >= targetList.length) return;
                var element = targetList[currentIndex];
                var studName = element.getAttribute('data-name') || 'student';
                var studId = element.getAttribute('data-id') || 'id';
                
                html2canvas(element, { scale: 2, useCORS: true }).then(function(canvas) {
                    var link = document.createElement('a');
                    link.download = studId + '_' + studName + '_ProgressCard.png';
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                    setTimeout(function() { triggerImageCaptureSequence(targetList, currentIndex + 1); }, 500);
                });
            }
            </script>
        </body>
        </html>
        """
        
        composite_html_payload = composite_html_payload.replace('\xa0', ' ')
        st.components.v1.html(composite_html_payload, height=900, scrolling=True)

# ====================================================================================
# MODULE: 🪪 STUDENT RESULT CARDS 
# ====================================================================================
elif menu_choice == "🪪 Student Result Cards":
    st.cache_data.clear() # <--- ADD THIS LINE TO FORCE REFRESH
    st.title("🪪 Student Result Cards — Print Engine")
    # ... rest of your code
    
    print_scope = st.radio("𖨾 Select Scope:", ["👤 Single Student Card", "👥 Complete Section Cards"], horizontal=True)
    col_c1, col_c2 = st.columns(2)
    with col_c1: search_id = st.text_input("🔍 Enter Student Roll Number / ID:")
    with col_c2: selected_test = st.selectbox("🎯 Select Test Term:", options=AVAILABLE_EXAMS)

    if search_id and search_id.isdigit() and selected_test:
        base_student = run_query("SELECT name, section, class FROM students WHERE id = :id", {"id": int(search_id)})
        if not base_student.empty:
            target_section = base_student['section'].iloc[0].upper().strip()
            grade_class = str(base_student['class'].iloc[0]).upper().strip()
            
            if print_scope == "👥 Complete Section Cards":
                students_to_print = run_query("SELECT id, name, section, class FROM students WHERE UPPER(TRIM(section)) = UPPER(TRIM(:section)) ORDER BY id ASC", {"section": target_section})
            else:
                students_to_print = pd.DataFrame([{"id": int(search_id), "name": base_student['name'].iloc[0], "section": target_section, "class": grade_class}])

            LOCAL_DISCIPLINE_SUBJECTS_MAP = {
            "MEDICAL_11TH": ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "BIOLOGY", "ISLAMIC STUDIES", "T_QURAN"],
            "MEDICAL_12TH": ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "BIOLOGY", "PAK_ST", "T_QURAN"],
            "ENGINEERING_11TH": ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "MATHEMATICS", "ISLAMIC STUDIES", "T_QURAN"],
            "ENGINEERING_12TH": ["ENGLISH", "URDU", "PHYSICS", "CHEMISTRY", "MATHEMATICS", "PAK_ST", "T_QURAN"],
            "ICS_PHYSICS_11TH": ["ENGLISH", "URDU", "PHYSICS", "COMPUTER SCIENCE", "MATHEMATICS", "ISLAMIC STUDIES", "T_QURAN"],
            "ICS_PHYSICS_12TH": ["ENGLISH", "URDU", "PHYSICS", "COMPUTER SCIENCE", "MATHEMATICS", "PAK_ST", "T_QURAN"],
            "ICS_STATISTICS_11TH": ["ENGLISH", "URDU", "STATISTICS", "COMPUTER SCIENCE", "MATHEMATICS", "ISLAMIC STUDIES", "T_QURAN"],
            "ICS_STATISTICS_12TH": ["ENGLISH", "URDU", "STATISTICS", "COMPUTER SCIENCE", "MATHEMATICS", "PAK_ST", "T_QURAN"],
            "HUMANITIES_11TH": ["ENGLISH", "URDU", "EDUCATION", "COMPUTER", "ISLAMIC STUDIES", "T_QURAN"],
            "HUMANITIES_12TH": ["ENGLISH", "URDU", "EDUCATION", "COMPUTER", "PAK_ST", "T_QURAN"],
            "COMMERCE_11TH": ["ENGLISH", "URDU", "ISLAMIC STUDIES", "PRINCIPLES OF ACCOUNTING", "PRINCIPLES OF COMMERCE", "PRINCIPLES OF ECONOMICS", "BUSINESS MATHEMATICS", "T_QURAN"],
            "COMMERCE_12TH": ["ENGLISH", "URDU", "PAK_ST", "PRINCIPLES OF ACCOUNTING", "BANKING", "COMMERCIAL GEOGRAPHY", "BUSINESS STATISTICS", "T_QURAN"]
        }

            compiled_html = """
            <!DOCTYPE html>
            <html>
            <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
            <style>
                body { font-family: "Times New Roman", Times, serif; color: #000; background-color: #fff; margin: 0; padding: 10px; }
                .official-card-container { max-width: 850px; margin: 10px auto; padding: 25px; border: 1px solid #000; background: #fff; position: relative; }
                .header-block { text-align: left; margin-bottom: 20px; width: 100%; }
                .logo-row { display: block; width: 100%; margin-bottom: 12px; }
                .logo-img { max-height: 48px; width: auto; display: block; margin-left: 0; }
                .inst-main-header { font-weight: bold; font-size: 28px; letter-spacing: 0.5px; margin: 0; line-height: 1.1; text-align: center; width: 100%; }
                .inst-sub-header { font-size: 13px; font-weight: normal; margin: 4px 0 0 0; text-align: center; color: #444; width: 100%; }
                .doc-type-banner { text-align: center; font-weight: bold; font-size: 16px; text-transform: uppercase; margin: 25px 0 20px 0; letter-spacing: 1px; }
                .meta-layout-table { width: 100%; border-collapse: collapse; border: none; margin-bottom: 20px; font-size: 14px; }
                .meta-layout-table td { border: none; padding: 3px; vertical-align: bottom; white-space: nowrap; }
                .underlined-value-span { border-bottom: 1px solid #000; font-weight: bold; padding: 0 4px; display: inline-block; text-transform: uppercase; }
                .doc-data-table { width: 100%; border-collapse: collapse; margin-top: 5px; margin-bottom: 15px; font-size: 14px; }
                .doc-data-table th, .doc-data-table td { border: 1px solid #000; padding: 6px 4px; text-align: center; }
                .doc-data-table th { font-weight: bold; background-color: #fff; }
                .section-header-title { font-size: 15px; font-weight: bold; margin: 25px 0 8px 0; text-align: left; text-transform: uppercase; border-bottom: 1px dashed #000; padding-bottom: 3px; }
                .attendance-matrix-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }
                .attendance-matrix-table th, .attendance-matrix-table td { border: 1px solid #000; padding: 5px 3px; text-align: center; }
                .attendance-matrix-table th { font-weight: bold; background-color: #fff; }
                .attendance-matrix-table td.row-title-cell { font-weight: bold; background-color: #fff; text-align: left; padding-left: 5px; font-size: 13px; }
                .footer-signatures-table { width: 100%; margin-top: 45px; font-size: 14px; border: none; }
                .footer-signatures-table td { border: none; }
                .sig-marker-line { border-top: 1px solid #000; width: 150px; text-align: center; padding-top: 4px; display: inline-block; font-weight: bold; }
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
                s_class = str(student_row['class']).upper().strip()
                test_name = selected_test.upper()
                
                matched_disp = "MEDICAL"
                if 'DISCIPLINE_SECTIONS_MAP' in globals():
                    for disp, class_dict in DISCIPLINE_SECTIONS_MAP.items():
                        for c_lvl, secs in class_dict.items():
                            if section in [x.upper().strip() for x in secs]: 
                                matched_disp = disp
                                break

                if "SEM" in s_class:
                    if "1ST" in s_class: subjects_list = ["Information Technology", "Office Automation", "Networking", "C-Programming", "Operating System", "Project"]
                    elif "2ND" in s_class: subjects_list = ["Data Base System", "Video Editing", "Web Development Essential", "Graphics Design", "Project"]
                    else: subjects_list = ["English", "Urdu", "Mathematics", "Statistics", "T_Quran", "Islamic_Studies"]
                else:
                    cls_suffix = "12TH" if "12" in s_class else "11TH"
                    d_clean = matched_disp.upper().replace(" ", "_").replace("(", "").replace(")", "")
                    if "PHYSIC" in d_clean: d_clean = "ICS_PHYSICS"
                    elif "STAT" in d_clean: d_clean = "ICS_STATISTICS"
                    
                    lookup_key = f"{d_clean}_{cls_suffix}"
                    subjects_list = LOCAL_DISCIPLINE_SUBJECTS_MAP.get(lookup_key, ["English", "Urdu"])

                raw_marks = run_query("SELECT UPPER(TRIM(subject)) as subject, TRIM(exam_type) as exam_type, marks_obtained, total_marks FROM marks WHERE student_id = :id", {"id": current_id})
                
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
                        att_cells[m] = {"td": "-", "pd": "-", "pct": "-"}
                
                attendance_percentage = 0.0
                if tot_sum > 0:
                    attendance_percentage = (pres_sum / tot_sum) * 100
                        
                overall_pct_str = f"{int(attendance_percentage)}%" if tot_sum > 0 else "-"
                att_cells["Over All Att."] = {"td": str(tot_sum) if tot_sum > 0 else "-", "pd": str(pres_sum) if tot_sum > 0 else "-", "pct": overall_pct_str}

                logo_base64 = "https://raw.githubusercontent.com/mirfanshakirpgc-art/Academics-Reports/main/logo.png"
                
                grand_total_marks = 0.0
                grand_obtained_marks = 0.0
                
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
                            <td style="width: 14%;"> Class: <span class="underlined-value-span" style="width: 55%;">{s_class}</span></td>
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
                    match = raw_marks[(raw_marks['subject'] == sub.upper().strip()) & (raw_marks['exam_type'] == selected_test)]
                    
                    obt_disp, tot_marks_num, pass_marks_num, per_disp, status_disp = "-", "-", "-", "-", "-"
                    
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
                            elif obt_val.replace('.', '', 1).isdigit() or val.isdigit():
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
                    
                    display_tot = tot_marks_num if obt_disp != "-" else "-"
                    display_pass = pass_marks_num if obt_disp != "-" else "-"
                    
                    compiled_html += f"""
                    <tr>
                        <td style="text-align: left; font-weight: bold; padding-left: 10px;">{sub}</td>
                        <td style="{style_override}">{obt_disp}</td>
                        <td style="{style_override}">{display_tot if obt_disp != "NC" else "NC"}</td>
                        <td style="{style_override}">{display_pass if obt_disp != "NC" else "NC"}</td>
                        <td style="{style_override}">{per_disp}</td>
                        <td style="font-weight: bold; {style_override}">{status_disp}</td>
                    </tr>
                    """
                
                grand_per_disp = "-"
                grand_status_disp = "-"
                grand_obt_disp = "-"
                grand_tot_disp = "-"
                
                if has_valid_marks_data and grand_total_marks > 0:
                    grand_per_disp = f"{int((grand_obtained_marks / grand_total_marks) * 100)}%"
                    grand_status_disp = "Fail" if student_failed_any_subject else "Pass"
                    grand_obt_disp = str(int(grand_obtained_marks)) if grand_obtained_marks.is_integer() else str(grand_obtained_marks)
                    grand_tot_disp = str(int(grand_total_marks))

                remarks_text = "No assessment records found for this term."
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
                                <td>{grand_obt_disp}</td>
                                <td>{grand_tot_disp}</td>
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
            <script>
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
            
            components.html(compiled_html, height=800, scrolling=True)

# ====================================================================================
# MODULE: STUDENT MANAGEMENT 
# ====================================================================================
elif menu_choice == "Student Management":
    st.title("👤 Student Management & Audit Logs")
    
    manage_tab, logs_tab = st.tabs(["🔧 Process Changes", "📋 Left & Transfer Audit Logs"])
    
    with manage_tab:
        st.markdown("Search for a student by ID to process section changes, mark departures, or re-activate profiles.")
        search_id = st.number_input("Enter Student ID:", min_value=1, step=1, key="manage_search_id")
        
        if search_id:
            student_data = run_query("""
                SELECT id, name, section, class 
                FROM students 
                WHERE id = :id
            """, {"id": search_id})
            
            if not student_data.empty:
                s_id = int(student_data.iloc[0]["id"])
                s_name = student_data.iloc[0]["name"]
                s_sec = student_data.iloc[0]["section"]
                s_class = student_data.iloc[0]["class"]
                
                s_status = "Active"
                try:
                    status_check = run_query("SELECT status FROM students WHERE id = :id", {"id": s_id})
                    if not status_check.empty and pd.notna(status_check.iloc[0]["status"]):
                        s_status = str(status_check.iloc[0]["status"]).strip()
                except Exception:
                    pass
                
                st.info(f"""
                **📍 Student Profile Found:**
                * **ID:** {s_id}
                * **Name:** {s_name}
                * **Class:** {s_class}
                * **Section:** {s_sec}
                * **Status:** {s_status}
                """)
                
                st.divider()
                col_status, col_section = st.columns(2)
                
                with col_status:
                    with st.container(border=True):
                        st.subheader("👤 Update Attendance Status")
                        status_options = ["Left", "Re-Active"]
                        default_idx = status_options.index(s_status) if s_status in status_options else 0
                        
                        new_status = st.radio("Select Target Status:", status_options, index=default_idx, key="status_radio_selection")
                        status_date = st.date_input("Status Change Date:", key="status_date_input")
                        req_star = " *" if new_status in ["Left", "Re-Active"] else ""
                        status_remarks = st.text_input(f"Status Remarks{req_star}", placeholder="Required for Left/Re-Active actions", key="status_rem_input")
                        
                        if st.button("💾 Save Profile Status", use_container_width=True, type="secondary"):
                            if new_status in ["Left", "Re-Active"] and not status_remarks.strip():
                                st.error(f"❌ Action Blocked: You must provide **Status Remarks** to mark a student as '{new_status}'.")
                            else:
                                try:
                                    run_update("UPDATE students SET status = :status WHERE id = :id", {"status": new_status, "id": s_id})
                                    run_update("""
                                        INSERT INTO student_logs (student_id, change_type, old_value, new_value, log_date, remarks)
                                        VALUES (:id, 'STATUS_CHANGE', :old, :new, :date, :rem)
                                    """, {"id": s_id, "old": s_status, "new": new_status, "date": str(status_date), "rem": status_remarks.strip()})
                                    st.success(f"✅ Successfully updated status to **{new_status}**!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to update status: {e}")
                
        with col_section:
            with st.container(border=True):
                st.subheader("🏫 Room & Section Transfer")
                
                u_class = str(s_class).upper().strip()
                lookup_key = None
                
                if "MEDICAL" in u_class:
                    lookup_key = "MEDICAL"
                elif "ENGINEERING" in u_class:
                    lookup_key = "ENGINEERING"
                elif "PHYSICS" in u_class or ("ICS" in u_class and "STAT" not in u_class):
                    lookup_key = "ICS_PHYSICS"
                elif "STAT" in u_class:
                    lookup_key = "ICS_STATISTICS"
                elif "COMMERCE" in u_class or "I.COM" in u_class:
                    lookup_key = "COMMERCE"
                elif "HUMANITIES" in u_class or "ARTS" in u_class:
                    lookup_key = "HUMANITIES"
                
                all_sections = []
                if lookup_key and lookup_key in DISCIPLINE_SECTIONS_MAP:
                    all_sections = [str(sec).strip() for sec in DISCIPLINE_SECTIONS_MAP[lookup_key]]
                else:
                    all_sections = ["MQ1", "MQ2", "MK1", "EK1", "EQ1", "CQ1", "CQ2", "CK1", "CK2", "CQ3", "CK3", "IQ1", "IK1", "FQ1", "FK1"]
                
                if s_sec not in all_sections:
                    all_sections.append(s_sec)
                    
                all_sections = sorted(list(set(all_sections)))
                default_sec_idx = all_sections.index(s_sec) if s_sec in all_sections else 0
                    
                new_sec = st.selectbox("Select New Section:", all_sections, index=default_sec_idx, key="section_select_node")
                section_date = st.date_input("Section Transfer Date:", key="sec_date_input")
                section_remarks = st.text_input("Transfer Remarks *", placeholder="Required: Reason for section change?", key="sec_rem_input")
                
                if st.button("🔄 Execute Section Change", use_container_width=True, type="primary"):
                    if new_sec == s_sec:
                        st.warning("⚠️ Student is already assigned to this section.")
                    elif not section_remarks.strip():
                        st.error("❌ Action Blocked: You must provide **Transfer Remarks** before changing sections.")
                    else:
                        try:
                            run_update(
                                "UPDATE students SET section = :new_section WHERE id = :id", 
                                {"new_section": str(new_sec), "id": int(s_id)}
                            )
                            
                            try:
                                run_update("""
                                    INSERT INTO student_logs (student_id, change_type, old_value, new_value, log_date, remarks)
                                    VALUES (:id, 'SECTION_TRANSFER', :old, :new, :date, :rem)
                                """, {"id": int(s_id), "old": str(s_sec), "new": str(new_sec), "date": str(section_date), "rem": section_remarks.strip()})
                            except Exception:
                                pass
                            
                            st.success(f"✅ Successfully transferred student to **{new_sec}**!")
                            if "section_select_node" in st.session_state:
                                del st.session_state["section_select_node"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Database Write Rejected the Change: {e}")
                            
    with logs_tab:
        st.subheader("📋 Institutional Exit & Section Transfer Logs")
        st.markdown("Review running logs of all student profile departures and section allocation changes.")
        
        filter_view = st.selectbox("Filter Log Matrix By Type:", ["All Historical Actions", "Left Students Master List", "Section Transfer Track Log"])
        
        try:
            log_data_df = run_query("""
                SELECT l.id AS "Log ID", l.student_id AS "ID", s.name AS "Student Name", 
                       l.change_type AS "Action", l.old_value AS "From", 
                       l.new_value AS "To", l.log_date AS "Date Stamp", 
                       l.remarks AS "Staff Remarks Context"
                FROM student_logs l
                LEFT JOIN students s ON l.student_id = s.id
                ORDER BY l.id DESC
            """)
        except Exception:
            log_data_df = pd.DataFrame(columns=["Log ID", "ID", "Student Name", "Action", "From", "To", "Date Stamp", "Staff Remarks Context"])
            
        try:
            left_fallback_df = run_query("""
                SELECT NULL AS "Log ID", id AS "ID", name AS "Student Name", 
                       'STATUS_CHANGE' AS "Action", 'Active' AS "From", 
                       UPPER(TRIM(status)) AS "To", 'Legacy Record' AS "Date Stamp", 
                       'Profile marked left before tracking initialized' AS "Staff Remarks Context"
                FROM students
                WHERE UPPER(TRIM(status)) = 'LEFT'
            """)
        except Exception:
            left_fallback_df = pd.DataFrame()
        
        if left_fallback_df is not None and not left_fallback_df.empty:
            existing_logged_ids = log_data_df[log_data_df["To"] == "Left"]["ID"].tolist() if not log_data_df.empty else []
            filtered_fallback = left_fallback_df[~left_fallback_df["ID"].isin(existing_logged_ids)]
            log_data_df = pd.concat([log_data_df, filtered_fallback], ignore_index=True)

        if log_data_df.empty:
            st.info("💡 No history logs or section adjustments have been recorded yet.")
        else:
            log_data_df["To_Clean"] = log_data_df["To"].astype(str).str.strip().str.upper()
            log_data_df["Action_Clean"] = log_data_df["Action"].astype(str).str.strip().str.upper()

            if filter_view == "Left Students Master List":
                filtered_df = log_data_df[log_data_df["To_Clean"] == "LEFT"]
            elif filter_view == "Section Transfer Track Log":
                filtered_df = log_data_df[log_data_df["Action_Clean"] == "SECTION_TRANSFER"]
            else:
                filtered_df = log_data_df
                
            if filtered_df.empty:
                st.info(f"💡 No matching tracking logs found for type selection: '{filter_view}'")
            else:
                display_df = filtered_df.drop(columns=["To_Clean", "Action_Clean"], errors="ignore")
                
                try:
                    export_df = display_df.drop(columns=["Log ID"], errors="ignore")
                    csv_data = export_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Filtered Log Ledger (CSV for Excel)",
                        data=csv_data,
                        file_name=f"student_audit_logs_{filter_view.lower().replace(' ', '_')}.csv",
                        mime="text/csv",
                        type="secondary"
                    )
                except Exception as csv_err:
                    st.error(f"Export Generator failed: {csv_err}")
                
                st.markdown("---")
                
                th_id, th_name, th_act, th_frm, th_to, th_date, th_rem, th_btn = st.columns([1, 2.5, 1.8, 1.2, 1.2, 1.3, 2, 1])
                th_id.markdown("**ID**")
                th_name.markdown("**Student Name**")
                th_act.markdown("**Action**")
                th_frm.markdown("**From**")
                th_to.markdown("**To**")
                th_date.markdown("**Date**")
                th_rem.markdown("**Staff Remarks**")
                th_btn.markdown("**Action**")
                st.markdown("<hr style='margin: 4px 0px 12px 0px; border-color: rgba(49, 51, 63, 0.2);'>", unsafe_allow_html=True)
                
                for idx, row in display_df.iterrows():
                    r_id = row["ID"]
                    r_name = row["Student Name"]
                    r_act = row["Action"]
                    r_frm = row["From"]
                    r_to = row["To"]
                    r_date = row["Date Stamp"]
                    r_rem = row["Staff Remarks Context"]
                    log_id = row["Log ID"]
                    
                    with st.container():
                        c_id, c_name, c_act, c_frm, c_to, c_date, c_rem, c_btn = st.columns([1, 2.5, 1.8, 1.2, 1.2, 1.3, 2, 1])
                        
                        c_id.write(str(r_id))
                        c_name.write(str(r_name))
                        c_act.write(str(r_act))
                        c_frm.write(str(r_frm))
                        c_to.write(str(r_to))
                        c_date.write(str(r_date))
                        c_rem.write(str(r_rem))
                        
                        if pd.notna(log_id):
                            if c_btn.button("🗑️ Delete", key=f"del_inline_{int(log_id)}", type="primary", use_container_width=True):
                                try:
                                    run_update("DELETE FROM student_logs WHERE id = :log_id", {"log_id": int(log_id)})
                                    st.success(f"💥 Purged Log #{int(log_id)}!")
                                    st.rerun()
                                except Exception as inline_err:
                                    st.error(f"Error: {inline_err}")
                        else:
                            c_btn.caption("Legacy")
                        
                        st.markdown("<hr style='margin: 6px 0px; border-color: rgba(49, 51, 63, 0.1);'>", unsafe_allow_html=True)

# ==============================================================================
# ROUTER INTEGRATION: 👨‍🏫 TEACHER MANAGEMENT MODULE
# ==============================================================================
elif menu_choice == "👨‍🏫 Teacher Management":
    st.title("👨‍🏫 Teacher Allocation & Performance Engine")
    
    current_user = st.session_state.get('username', 'admin')
    current_role = st.session_state.get('role', 'controller') 
    
    if current_role == 'controller':
        menu_options = ["📝 Register New Faculty", "Subject Allocations", "Teacher Marks Portal", "Teacher Analysis", "Discipline Analysis"]
    else:
        menu_options = ["Teacher Marks Portal", "Teacher Analysis"]
        
    sub_menu = st.sidebar.radio("Navigate Module:", menu_options, key="teacher_sub_menu")

    if sub_menu == "📝 Register New Faculty":
        st.subheader("📝 Professional Faculty onboarding Registry")
        
        with st.form("teacher_reg_form", clear_on_submit=True):
            col_reg1, col_reg2 = st.columns(2)
            with col_reg1:
                new_teacher_name = st.text_input("Full Name of Teacher:", placeholder="e.g. Professor Smith")
                new_teacher_email = st.text_input("Email Address (Optional):", placeholder="teacher@college.edu")
            with col_reg2:
                new_teacher_phone = st.text_input("Phone Number (Optional):", placeholder="e.g. +923001234567")
                new_teacher_status = st.selectbox("Initial System Status:", options=["ACTIVE", "INACTIVE"])
                
            submit_reg = st.form_submit_button("💾 Save Profile to Registry")
            
            if submit_reg:
                if new_teacher_name.strip() == "":
                    st.error("Teacher Name is required.")
                else:
                    check_existing = run_query("SELECT teacher_id FROM system_teachers WHERE UPPER(TRIM(teacher_name)) = UPPER(TRIM(:name))", {"name": new_teacher_name.strip()})
                    
                    if check_existing.empty:
                        execute_db_command("""
                            INSERT INTO system_teachers (teacher_name, phone_number, email_address, status)
                            VALUES (:name, :phone, :email, :status)
                        """, {
                            "name": new_teacher_name.strip(),
                            "phone": new_teacher_phone.strip(),
                            "email": new_teacher_email.strip(),
                            "status": new_teacher_status
                        })
                        st.success(f"🎉 Successfully registered {new_teacher_name} into the institutional archive!")
                    else:
                        st.warning("An instructor profile with this name already exists.")
                        
        st.markdown("---")
        st.write("#### Current Registered Faculty Roster")
        current_teachers = run_query("SELECT teacher_id as ID, teacher_name as Name, phone_number as Phone, email_address as Email, status as Status FROM system_teachers ORDER BY teacher_name ASC")
        if not current_teachers.empty:
            st.dataframe(current_teachers, use_container_width=True, hide_index=True)
        else:
            st.info("No active faculty profiles currently configured.")

    elif sub_menu == "Subject Allocations":
        st.subheader("🔗 Allocate Subjects & Sections to Registered Faculty")
        
        LOCAL_DISCIPLINE_SUBJECTS_MAP = {
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

        GIRLS_SECTIONS_DB = ["CG_WHITE", "CG_GREEN", "CG_STATS", "IG", "FG", "MG_BLUE", "MG_WHITE", "EG_BLUE", "MQ1", "MQ2", "EQ1", "EQ", "CQ1", "CQ2", "CQ3", "IQ1", "IQ", "FQ1", "FQ", "DIT_G"]
        BOYS_SECTIONS_DB = ["CB_WHITE", "CB_GREEN", "CB_STATS", "IB", "FB", "MB_BLUE", "EB_BLUE", "MK1", "MK", "EK1", "EK", "CK1", "CK2", "CK3", "IK1", "IK", "FK1", "FK", "DIT_B"]

        def get_subject_prefix(disc_name):
            if not disc_name or disc_name == "All Disciplines": return disc_name
            d_clean = disc_name.upper().replace(" ", "_").replace("(", "").replace(")", "")
            if "PHYSIC" in d_clean: return "ICS_PHYSICS"
            if "STAT" in d_clean: return "ICS_STATISTICS"
            return d_clean

        def filter_teachers_by_campus(t_list, campus):
            female_prefixes = ("MS.", "MRS.", "MISS", "MADAM", "MS ", "MRS ")
            male_prefixes = ("MR.", "SIR", "HAFIZ", "MR ", "SIR ")
            if campus == "Girls Campus":
                return [t for t in t_list if not t.upper().startswith(male_prefixes)]
            else:
                return [t for t in t_list if not t.upper().startswith(female_prefixes)]

        def filter_sections_by_campus(s_list, campus):
            filtered = []
            for s in s_list:
                s_clean = s.upper().strip()
                if campus == "Girls Campus":
                    if s_clean in GIRLS_SECTIONS_DB:
                        filtered.append(s)
                else:
                    if s_clean in BOYS_SECTIONS_DB:
                        filtered.append(s)
            return filtered

        teachers_df = run_query("SELECT teacher_name FROM system_teachers WHERE status = 'ACTIVE' ORDER BY teacher_name ASC")
        
        if not teachers_df.empty:
            t_options_raw = teachers_df['teacher_name'].tolist()
            
            tab_subjects, tab_incharge = st.tabs(["📚 Assign Course Subjects", "👑 Assign Class In-Charge"])
            
            with tab_subjects:
                st.markdown("##### Assign specific subjects to sections (Academic Role)")
                
                t1_c1, t1_c2, t1_c3 = st.columns(3)
                with t1_c1: session_t1 = st.selectbox("1. Academic Session:", options=["2025-27", "2026-28", "2027-29"], key="t1_session")
                with t1_c2: campus_t1 = st.selectbox("2. Target Campus:", options=["Girls Campus", "Boys Campus"], key="t1_campus")
                with t1_c3: system_t1 = st.selectbox("3. Academic System:", options=["Annual System", "Semester System"], key="t1_system")
                    
                t1_c4, t1_c5 = st.columns(2)
                with t1_c4: 
                    filtered_teachers_t1 = filter_teachers_by_campus(t_options_raw, campus_t1)
                    if not filtered_teachers_t1: filtered_teachers_t1 = ["No matching staff found"]
                    selected_t1 = st.selectbox("4. Select Teacher:", options=filtered_teachers_t1, key="t1_teacher")
                    
                with t1_c5:
                    if system_t1 == "Annual System":
                        if session_t1 == "2025-27":
                            class_options_t1 = ["12th"]
                        elif session_t1 == "2026-28":
                            class_options_t1 = ["11th"]
                        else:
                            class_options_t1 = ["11th", "12th"]
                        class_t1 = st.selectbox("5. Class Level:", class_options_t1, key="t1_class")
                    else:
                        class_t1 = st.selectbox("5. Semester Context:", ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester"], key="t1_class")
                
                t1_c6, t1_c7, t1_c8 = st.columns(3)
                with t1_c6:
                    if system_t1 == "Annual System":
                        disc_options_t1 = list(DISCIPLINE_SECTIONS_MAP.keys()) if 'DISCIPLINE_SECTIONS_MAP' in globals() else ["MEDICAL", "ENGINEERING", "ICS (PHYSICS)", "ICS (STATS)", "COMMERCE", "HUMANITIES"]
                        disc_t1 = st.selectbox("6. Select Discipline:", disc_options_t1, key="t1_disc")
                    else:
                        disc_t1 = "DIT"
                        st.info("⚡ DIT System Active")

                if system_t1 == "Annual System":
                    raw_secs_t1 = DISCIPLINE_SECTIONS_MAP.get(disc_t1, {}).get(class_t1, []) if 'DISCIPLINE_SECTIONS_MAP' in globals() else []
                    secs_t1 = filter_sections_by_campus(raw_secs_t1, campus_t1)
                    if not secs_t1: secs_t1 = ["No sections available"]
                        
                    lookup_key_t1 = f"{get_subject_prefix(disc_t1)}_{class_t1.upper()}"
                    subs_t1 = LOCAL_DISCIPLINE_SUBJECTS_MAP.get(lookup_key_t1, ["English", "Urdu"])
                    subs_t1 = sorted(list(set([s.upper() for s in subs_t1])))
                else:
                    if session_t1 == "2025-27":
                        raw_secs_t1 = ["DIT_G", "DIT_B"]
                    else:
                        raw_secs_t1 = []
                        
                    secs_t1 = filter_sections_by_campus(raw_secs_t1, campus_t1)
                    if not secs_t1: secs_t1 = ["No DIT sections in this session"]
                    
                    if "1st" in class_t1: subs_t1 = ["INFORMATION TECHNOLOGY", "OFFICE AUTOMATION", "NETWORKING", "C-PROGRAMMING", "OPERATING SYSTEM", "PROJECT"]
                    elif "2nd" in class_t1: subs_t1 = ["DATA BASE SYSTEM", "VIDEO EDITING", "WEB DEVELOPMENT ESSENTIAL", "GRAPHICS DESIGN", "PROJECT"]
                    else: subs_t1 = ["ENGLISH", "URDU", "MATHEMATICS", "STATISTICS", "T_QURAN", "ISLAMIC_STUDIES"]

                with t1_c7:
                    sec_t1 = st.selectbox("7. Assign Target Section:", options=secs_t1, key="t1_sec")
                    
                with t1_c8:
                    sub_t1 = st.selectbox("8. Select Subject Course:", options=subs_t1, key="t1_sub")
                    
                st.markdown("##")
                if st.button("🔒 Authorize Subject Assignment", type="primary", use_container_width=True, key="t1_btn"):
                    if sec_t1 in ["No sections available", "No DIT sections in this session"] or selected_t1 == "No matching staff found":
                        st.error("⚠️ Invalid Section or Teacher selection. Please adjust your filters.")
                    else:
                        check_dup = run_query("""
                            SELECT allocation_id FROM academic_allocations 
                            WHERE session_term = :session AND class_level = :cls 
                            AND section_name = :sec AND subject_title = :sub AND assigned_teacher_name = :teacher
                        """, {"session": session_t1, "cls": class_t1, "sec": sec_t1, "sub": sub_t1, "teacher": selected_t1})
                        
                        if check_dup.empty:
                            execute_db_command("""
                                INSERT INTO academic_allocations (session_term, class_level, section_name, subject_title, assigned_teacher_name, is_class_incharge) 
                                VALUES (:session, :cls, :sec, :sub, :teacher, 'No')
                            """, {"session": session_t1, "cls": class_t1, "sec": sec_t1, "sub": sub_t1, "teacher": selected_t1})
                            
                            st.success(f"✅ Access granted! {selected_t1} is now allocated to teach {sub_t1} in {sec_t1}.")
                            st.rerun()
                        else:
                            st.warning("⚠️ This exact subject allocation already exists for this instructor.")

            with tab_incharge:
                st.markdown("##### Assign overall room management & responsibility (Administrative Role)")
                
                t2_c1, t2_c2, t2_c3 = st.columns(3)
                with t2_c1: session_t2 = st.selectbox("1. Select Session:", options=["2025-27", "2026-28", "2027-29"], key="t2_session")
                with t2_c2: campus_t2 = st.selectbox("2. Target Campus:", options=["Girls Campus", "Boys Campus"], key="t2_campus")
                with t2_c3: 
                    filtered_teachers_t2 = filter_teachers_by_campus(t_options_raw, campus_t2)
                    if not filtered_teachers_t2: filtered_teachers_t2 = ["No matching staff found"]
                    selected_t2 = st.selectbox("3. Select Teacher:", options=filtered_teachers_t2, key="t2_teacher")

                if session_t2 == "2025-27":
                    class_context_t2 = "12th"
                elif session_t2 == "2026-28":
                    class_context_t2 = "11th"
                else:
                    class_context_t2 = "General"

                all_raw_secs_t2 = []
                if 'DISCIPLINE_SECTIONS_MAP' in globals():
                    for class_dict in DISCIPLINE_SECTIONS_MAP.values():
                        if class_context_t2 in class_dict:
                            all_raw_secs_t2.extend(class_dict[class_context_t2])
                        elif class_context_t2 == "General":
                            for sec_list in class_dict.values():
                                all_raw_secs_t2.extend(sec_list)
                
                if session_t2 == "2025-27":
                    all_raw_secs_t2.extend(["DIT_G", "DIT_B"])
                
                secs_t2 = filter_sections_by_campus(all_raw_secs_t2, campus_t2)
                secs_t2 = sorted(list(set(secs_t2))) if secs_t2 else ["No sections available"]

                sec_t2 = st.multiselect("4. Assign Target Section(s):", options=secs_t2, default=[secs_t2[0]] if secs_t2 and secs_t2[0] != "No sections available" else None, key="t2_sec")
                
                st.markdown("##")
                if st.button("🔒 Authorize Class In-Charge", type="primary", use_container_width=True, key="t2_btn"):
                    if not sec_t2 or "No sections available" in sec_t2 or selected_t2 == "No matching staff found":
                        st.error("⚠️ Invalid Section or Teacher selection. Please check your campus filtering.")
                    else:
                        success_count = 0
                        skip_count = 0
                        
                        for sec in sec_t2:
                            db_class_val = "Semester System" if "DIT" in sec else class_context_t2
                            
                            check_dup = run_query("""
                                SELECT allocation_id FROM academic_allocations 
                                WHERE session_term = :session AND class_level = :cls 
                                AND section_name = :sec AND subject_title = '🌟 CLASS IN-CHARGE (ROLE ONLY)' AND assigned_teacher_name = :teacher
                            """, {"session": session_t2, "cls": db_class_val, "sec": sec, "teacher": selected_t2})
                            
                            if check_dup.empty:
                                execute_db_command("""
                                    INSERT INTO academic_allocations (session_term, class_level, section_name, subject_title, assigned_teacher_name, is_class_incharge) 
                                    VALUES (:session, :cls, :sec, '🌟 CLASS IN-CHARGE (ROLE ONLY)', :teacher, 'Yes')
                                """, {"session": session_t2, "cls": db_class_val, "sec": sec, "teacher": selected_t2})
                                success_count += 1
                            else:
                                skip_count += 1
                                
                        if success_count > 0:
                            st.success(f"✅ {selected_t2} is now assigned as Class In-Charge for {success_count} section(s).")
                        if skip_count > 0:
                            st.warning(f"⚠️ {skip_count} assignment(s) skipped because they already exist.")
                        if success_count > 0:
                            st.rerun()

            st.markdown("---")
            st.write("#### Active Master Allocation Matrix Log")
            
            alloc_log = run_query("""
                SELECT allocation_id as ID, session_term as Session, class_level as Class, section_name as Section, 
                       subject_title as Subject, assigned_teacher_name as Instructor, is_class_incharge as InCharge
                FROM academic_allocations
                ORDER BY session_term DESC, is_class_incharge DESC, section_name ASC
            """)
            
            if not alloc_log.empty:
                h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([0.5, 1.2, 1.2, 1.5, 2, 2.5, 1, 1])
                h1.markdown("**ID**")
                h2.markdown("**Session**")
                h3.markdown("**Class**")
                h4.markdown("**Section**")
                h5.markdown("**Subject**")
                h6.markdown("**Instructor**")
                h7.markdown("**In-Charge**")
                h8.markdown("**Action**")
                st.markdown("<hr style='margin:0px; padding:0px; margin-bottom: 8px;'>", unsafe_allow_html=True)
                
                for _, row in alloc_log.iterrows():
                    r1, r2, r3, r4, r5, r6, r7, r8 = st.columns([0.5, 1.2, 1.2, 1.5, 2, 2.5, 1, 1])
                    r1.write(str(row['id']))
                    r2.write(str(row['session']))
                    
                    class_disp = "---" if str(row['class']) == 'General' else str(row['class'])
                    r3.write(class_disp)
                    
                    r4.write(str(row['section']))
                    r5.write(str(row['subject']))
                    r6.write(str(row['instructor']))
                    
                    if str(row['incharge']) == 'Yes':
                        r7.markdown("👑 **Yes**")
                    else:
                        r7.write(str(row['incharge']))
                    
                    if r8.button("🗑️ Del", key=f"del_alloc_{row['id']}", help="Remove this allocation"):
                        try:
                            execute_db_command("DELETE FROM academic_allocations WHERE allocation_id = :aid", {"aid": int(row['id'])})
                            st.success("Allocation deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error removing allocation: {e}")
                            
                    st.markdown("<hr style='margin:0px; padding:0px; border-color: rgba(49, 51, 63, 0.1);'>", unsafe_allow_html=True)
            else:
                st.info("No active master allocations found in the matrix.")
        else:
            st.info("No active records found inside system_teachers table registry.")

    elif sub_menu == "Teacher Marks Portal":
        st.subheader("🔑 Secure Faculty Data Input Gateway")
        
        teachers_df = run_query("SELECT DISTINCT assigned_teacher_name FROM academic_allocations ORDER BY assigned_teacher_name ASC")
        if not teachers_df.empty:
            t_options = teachers_df['assigned_teacher_name'].tolist()
            active_teacher = st.selectbox("View Portal As Assigned Instructor:", options=t_options)
        else:
            st.info("No allocated teachers found in database matrix logs.")
            active_teacher = None
            
        if active_teacher is not None:
            my_rights = run_query("""
                SELECT DISTINCT subject_title, section_name, session_term 
                FROM academic_allocations WHERE assigned_teacher_name = :teacher
            """, {"teacher": active_teacher})
            
            if not my_rights.empty:
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1: 
                    allocated_subs = my_rights['subject_title'].unique()
                    sel_sub = st.selectbox("Assigned Course Subjects:", options=allocated_subs)
                with col_m2:
                    allocated_secs = my_rights[my_rights['subject_title'] == sel_sub]['section_name'].unique()
                    sel_sec = st.selectbox("Assigned Sections:", options=allocated_secs)
                with col_m3:
                    allocated_sessions = my_rights[(my_rights['subject_title'] == sel_sub) & (my_rights['section_name'] == sel_sec)]['session_term'].unique()
                    sel_session = st.selectbox("Target Entry Session:", options=allocated_sessions)
                
                exams_list = AVAILABLE_EXAMS if 'AVAILABLE_EXAMS' in globals() else ["Mid Term", "Final Exam"]
                sel_exam = st.selectbox("Target Assessment Term Type:", options=exams_list)
                
                students = run_query("""
                    SELECT id, name FROM students 
                    WHERE UPPER(TRIM(section)) = UPPER(TRIM(:sec)) 
                    AND UPPER(TRIM(session)) = UPPER(TRIM(:session))
                    ORDER BY id ASC
                """, {"sec": sel_sec, "session": sel_session})
                
                if not students.empty:
                    st.info(f"📋 Roster Sheet for Course: {sel_sub} — Section: {sel_sec} ({sel_session})")
                    
                    marks_data = []
                    for _, s_row in students.iterrows():
                        sid = s_row['id']
                        sname = s_row['name']
                        
                        existing = run_query("""
                            SELECT marks_obtained, total_marks FROM marks 
                            WHERE student_id = :sid AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND exam_type = :exam
                        """, {"sid": sid, "sub": sel_sub, "exam": sel_exam})
                        
                        val_fill = "0"
                        tot_fill = 100
                        if not existing.empty:
                            val_fill = str(existing['marks_obtained'].iloc[0])
                            tot_fill = int(existing['total_marks'].iloc[0])
                            
                        c_left, c_right = st.columns([3, 1])
                        with c_left: 
                            m_val = st.text_input(f"ID {sid} — {sname}:", value=val_fill, key=f"m_{sid}_{sel_sub}_{sel_exam}")
                        with c_right: 
                            t_val = st.number_input("Max Total:", min_value=10, max_value=200, value=tot_fill, key=f"t_{sid}_{sel_sub}_{sel_exam}")
                            
                        marks_data.append({"sid": sid, "obtained": m_val, "total": t_val})
                        
                    if st.button("🎯 Finalize & Commit Marks Values"):
                        for record in marks_data:
                            execute_db_command("""
                                DELETE FROM marks WHERE student_id = :sid 
                                AND UPPER(TRIM(subject)) = UPPER(TRIM(:sub)) AND exam_type = :exam
                            """, {"sid": record['sid'], "sub": sel_sub, "exam": sel_exam})
                            
                            execute_db_command("""
                                INSERT INTO marks (student_id, subject, exam_type, marks_obtained, total_marks)
                                VALUES (:sid, :sub, :exam, :obt, :tot)
                            """, {"sid": record['sid'], "sub": sel_sub, "exam": sel_exam, "obt": record['obtained'].strip().upper(), "tot": record['total']})
                        st.success("Assessment matrix marks records updated dynamically!")
                        st.rerun()
                else:
                    st.error("No active records of student enrollment profiles match this specific criteria mix.")
            else:
                st.warning("🚨 No subject assignments have been allocated to this instructor profile yet.")

    elif sub_menu == "Teacher Analysis":
        st.subheader("📊 Performance Evaluation by Instructor")
        
        teachers_df = run_query("SELECT DISTINCT assigned_teacher_name FROM academic_allocations ORDER BY assigned_teacher_name ASC")
        if not teachers_df.empty:
            t_options = teachers_df['assigned_teacher_name'].tolist()
            selected_t = st.selectbox("Select Instructor Account to Analyze:", options=t_options)
            
            allocations = run_query("""
                SELECT subject_title, section_name, session_term 
                FROM academic_allocations WHERE assigned_teacher_name = :teacher
            """, {"teacher": selected_t})
            
            if not allocations.empty:
                summary_metrics = []
                for _, a_row in allocations.iterrows():
                    sub = a_row['subject_title']
                    sec = a_row['section_name']
                    ses = a_row['session_term']
                    
                    performance_data = run_query("""
                        SELECT m.marks_obtained, m.total_marks FROM marks m
                        JOIN students s ON m.student_id = s.id
                        WHERE UPPER(TRIM(s.section)) = UPPER(TRIM(:sec)) 
                        AND UPPER(TRIM(s.session)) = UPPER(TRIM(:ses))
                        AND UPPER(TRIM(m.subject)) = UPPER(TRIM(:sub))
                    """, {"sec": sec, "ses": ses, "sub": sub})
                    
                    if not performance_data.empty:
                        performance_data['num_obt'] = pd.to_numeric(performance_data['marks_obtained'], errors='coerce')
                        valid_scores = performance_data.dropna(subset=['num_obt'])
                        
                        if not valid_scores.empty:
                            avg_pct = (valid_scores['num_obt'].sum() / valid_scores['total_marks'].sum()) * 100
                            pass_count = sum(valid_scores['num_obt'] >= (valid_scores['total_marks'] * 0.40))
                            pass_ratio = (pass_count / len(valid_scores)) * 100
                            
                            summary_metrics.append({
                                "Subject Class": sub,
                                "Section Group": sec,
                                "Academic Term Session": ses,
                                "Evaluated Scripts": len(valid_scores),
                                "Average Score": f"{avg_pct:.1f}%",
                                "Passing KPI Rate": f"{pass_ratio:.1f}%"
                            })
                            
                if summary_metrics:
                    st.write(f"#### Class Metrics Managed by {selected_t}")
                    st.table(pd.DataFrame(summary_metrics))
                else:
                    st.info("No assessment script entries found for this instructor's active assignment load.")
            else:
                st.warning("This teacher profile holds no active database class allocation nodes.")

    elif sub_menu == "Discipline Analysis" and 'DISCIPLINE_SUBJECTS_MAP' in globals():
        st.subheader("🏢 High-Level Discipline Stream Overview")
        
        exams_list = AVAILABLE_EXAMS if 'AVAILABLE_EXAMS' in globals() else ["Mid Term", "Final Exam"]
        exam_term = st.selectbox("Select Academic Term Focus:", options=exams_list, key="disc_exam_focus")
        
        discipline_summary = []
        for disc_name, subjects in DISCIPLINE_SUBJECTS_MAP.items():
            sections = DISCIPLINE_SECTIONS_MAP.get(disc_name, []) if 'DISCIPLINE_SECTIONS_MAP' in globals() else []
            
            if sections:
                sec_placeholders = ",".join([f"'{s.upper().strip()}'" for s in sections])
                sub_placeholders = ",".join([f"'{sub.upper().strip()}'" for sub in subjects])
                
                query_str = f"""
                    SELECT m.marks_obtained, m.total_marks FROM marks m
                    JOIN students s ON m.student_id = s.id
                    WHERE UPPER(TRIM(s.section)) IN ({sec_placeholders})
                    AND UPPER(TRIM(m.subject)) IN ({sub_placeholders})
                    AND m.exam_type = :exam
                """
                
                disc_data = run_query(query_str, {"exam": exam_term})
                
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
            st.dataframe(pd.DataFrame(discipline_summary), use_container_width=True, hide_index=True)

# ====================================================================================
# MODULE: STUDENT PROMOTION 
# ====================================================================================
elif menu_choice == "🎓 Promote Students":
    st.title("🎓 Advanced End-of-Year Class Promotion Panel")
    st.write("Promote whole sections or select specific individual students while managing their target sections and tracking historical promotion batches.")

    try:
        execute_db_command("""
            CREATE TABLE IF NOT EXISTS promotion_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                student_id INTEGER,
                old_class TEXT,
                old_section TEXT,
                old_session TEXT,
                new_class TEXT,
                new_section TEXT,
                batch_id TEXT
            );
        """)
        try:
            execute_db_command("ALTER TABLE promotion_history ADD COLUMN old_session TEXT;")
        except Exception:
            pass 
    except Exception as table_err:
        st.error(f"Database initialization warning: {table_err}")

    st.subheader("🔍 Step 1: Select Source Student Pool")
    src_c1, src_c2, src_c3 = st.columns(3)
    
    with src_c1:
        promo_session = st.selectbox("Source Academic Session:", AVAILABLE_SESSIONS, index=1, key="promo_src_sess")
    with src_c2:
        source_class = st.selectbox("Current Class Level:", ["11th", "12th"], index=0, key="promo_src_class")
    with src_c3:
        promo_scope = st.radio("Promotion Scope:", ["📋 Complete Section", "👤 Single Student"], horizontal=True)

    sess_prefix = promo_session.split('-')[0] + '%' 
    selected_section = None
    target_student_id = None
    
    if promo_scope == "📋 Complete Section":
        sections_df = run_query(
            """
            SELECT DISTINCT section FROM students 
            WHERE session LIKE :sess 
              AND UPPER(TRIM(class)) = UPPER(TRIM(:cls)) 
            ORDER BY section
            """,
            {"sess": sess_prefix, "cls": source_class}
        )
        available_src_sections = sections_df['section'].tolist() if not sections_df.empty else []
        selected_section = st.selectbox("Select Source Section to Promote:", available_src_sections if available_src_sections else ["No Data Found"])
    else:
        students_roster_df = run_query(
            """
            SELECT id, name FROM students 
            WHERE session LIKE :sess 
              AND UPPER(TRIM(class)) = UPPER(TRIM(:cls)) 
            ORDER BY name
            """,
            {"sess": sess_prefix, "cls": source_class}
        )
        if not students_roster_df.empty:
            student_options = {f"{row['id']} - {row['name']}": row['id'] for _, row in students_roster_df.iterrows()}
            chosen_stu_str = st.selectbox("Search & Select Student:", list(student_options.keys()))
            target_student_id = student_options[chosen_stu_str]
        else:
            st.warning("⚠️ No matching student records found.")

    st.markdown("---")

    st.subheader("🎯 Step 2: Configure Destination Environment")
    
    next_class = "12th" if source_class == "11th" else "Alumni/Left"
    st.info(f"✨ Target Update: Status shifts from **{source_class} ➔ {next_class}** under tracking pool **{promo_session}**.")
    
    tgt_c1, tgt_c2 = st.columns(2)
    
    with tgt_c2:
        selected_discipline = st.selectbox("Select Target Discipline Track:", AVAILABLE_DISCIPLINE, key="promo_tgt_disc")

    with tgt_c1:
        disc_upper = selected_discipline.upper() if selected_discipline else ""
        
        if "MEDICAL" in disc_upper:
            available_tgt_sections = ["MQ1", "MQ2", "MK"]
        elif "ENGINEERING" in disc_upper:
            available_tgt_sections = ["EQ", "EK"]
        elif "PHYSICS" in disc_upper:
            available_tgt_sections = ["CQ1", "CQ2", "CK1", "CK2"]
        elif "STATS" in disc_upper:
            available_tgt_sections = ["CQ3", "CK3"]
        elif "COMMERCE" in disc_upper:
            available_tgt_sections = ["IK", "IQ"]
        elif "HUMANITIES" in disc_upper or "ARTS" in disc_upper:
            available_tgt_sections = ["FK", "FQ"]
        else:
            available_tgt_sections = sorted(list(set([sec for sublist in DISCIPLINE_SECTIONS_MAP.values() for sec in sublist])))

        target_section = st.selectbox("Assign to Destination Section:", available_tgt_sections, key="promo_tgt_sec")

    st.subheader("📊 Step 3: Roster Execution Preview")

    should_show_preview = False
    preview_query = ""
    params = {}

    if promo_scope == "📋 Complete Section" and selected_section and selected_section != "No Data Found":
        should_show_preview = True
        preview_query = """
            SELECT id, name, section, class, session FROM students 
            WHERE session LIKE :sess 
              AND UPPER(TRIM(class)) = UPPER(TRIM(:cls)) 
              AND UPPER(TRIM(section)) = UPPER(TRIM(:sec))
            ORDER BY name ASC
        """
        params = {"sess": sess_prefix, "cls": source_class, "sec": str(selected_section)}
    elif promo_scope == "👤 Single Student" and target_student_id:
        should_show_preview = True
        preview_query = "SELECT id, name, section, class, session FROM students WHERE id = :s_id"
        params = {"s_id": target_student_id}

    if should_show_preview:
        preview_df = run_query(preview_query, params)
        
        if not preview_df.empty:
            selected_student_records = []
            
            if promo_scope == "📋 Complete Section":
                st.markdown("##### 🗳️ Select Students to Include in this Promotion Batch:")
                c_all, _ = st.columns([1, 5])
                with c_all:
                    if st.button("Select All"):
                        st.session_state["promo_select_all"] = True
                
                for idx, row in preview_df.iterrows():
                    chk_key = f"chk_{row['id']}_{idx}"
                    default_val = st.session_state.get("promo_select_all", True)
                    
                    is_selected = st.checkbox(
                        f"🆔 {row['id']} — **{row['name']}** (Current Section: {row['section']})", 
                        value=default_val, 
                        key=chk_key
                    )
                    if is_selected:
                        selected_student_records.append(row)
                        
                if "promo_select_all" in st.session_state:
                    del st.session_state["promo_select_all"]
            else:
                selected_student_records = [preview_df.iloc[0]]
                st.dataframe(preview_df, use_container_width=True)

            total_selected = len(selected_student_records)
            st.markdown(f"📊 **Batch Status:** Ready to promote **{total_selected}** out of **{len(preview_df)}** loaded profiles.")
            
            if total_selected > 0:
                st.warning(f"⚠️ **Action Scope Notice:** Running promotion updates will modify {total_selected} student profiles.")
                
                if st.button(f"🚀 Execute Selected Promotion Pipeline", type="primary", use_container_width=True):
                    import uuid
                    batch_identifier = str(uuid.uuid4())[:8]
                    
                    for row in selected_student_records:
                        s_id = int(row['id'])
                        old_cls = str(row['class']).strip()
                        old_sec = str(row['section']).strip()
                        old_sess = str(row['session']).strip()
                        new_sec = target_section.strip().upper()

                        execute_db_command("""
                            INSERT INTO promotion_history (student_id, old_class, old_section, old_session, new_class, new_section, batch_id)
                            VALUES (:s_id, :old_cls, :old_sec, :old_sess, :new_cls, :new_sec, :b_id)
                        """, {"s_id": s_id, "old_cls": old_cls, "old_sec": old_sec, "old_sess": old_sess, "new_cls": next_class, "new_sec": new_sec, "b_id": batch_identifier})

                        execute_db_command("""
                            UPDATE students 
                            SET class = :next_cls, section = :next_sec, session = :new_sess
                            WHERE id = :s_id
                        """, {"next_cls": next_class, "next_sec": new_sec, "new_sess": promo_session, "s_id": s_id})
                    
                    st.success(f"🎉 Success! {total_selected} records reassigned to Class {next_class} (Batch: {batch_identifier}).")
                    st.rerun()
            else:
                st.error("❌ Cannot execute pipeline. You must leave at least one student checked to run a promotion.")
        else:
            st.info("💡 No student records matching selected parameters found.")
    else:
        st.info("💡 Please complete Step 1 and select a valid source pool to view the roster preview.")

    st.markdown("---")

    st.subheader("⏳ Step 4: Active Promoted Sections Log (Safety Reversal)")
    
    st.markdown("#### ⚙️ Administrative Global & Section Controls")
    st.write("Select a targeted academic track below to purge logs or perform critical data maintenance resets.")
    
    cleanup_col1, cleanup_col2, cleanup_col3 = st.columns([2, 1, 1.2])
    with cleanup_col1:
        try:
            sections_master_df = run_query("SELECT DISTINCT section FROM students WHERE section IS NOT NULL AND section != ''")
            db_sections = sections_master_df['section'].tolist() if not sections_master_df.empty else []
            master_sections_list = sorted(list(set(db_sections + ["IK", "IQ", "CK3", "CK1", "CK2", "EQ", "EK"])))
        except Exception:
            master_sections_list = ["IK", "IQ", "CK3", "CK1", "CK2", "EQ", "EK"]
            
        wipe_target_sec = st.selectbox("🎯 Target Section Selection Matrix:", master_sections_list, key="always_visible_wipe_dropdown")
    
    with cleanup_col2:
        st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🧹 Clear Logs Only", key="clear_logs_btn", use_container_width=True):
            try:
                execute_db_command("DELETE FROM promotion_history WHERE UPPER(TRIM(old_section)) = UPPER(TRIM(:sec)) OR UPPER(TRIM(new_section)) = UPPER(TRIM(:sec))", {"sec": wipe_target_sec})
                st.success(f"Wiped history log entries involving Section {wipe_target_sec}!")
                st.rerun()
            except Exception as clear_err:
                st.error(f"Clear Error: {clear_err}")

    with cleanup_col3:
        st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        confirm_purge = st.checkbox("Confirm Table Purge", key="confirm_purge_check")
        
        if st.button("🔥 DELETE STUDENTS FROM DB", key="purge_db_students_btn", type="primary", use_container_width=True, disabled=not confirm_purge):
            try:
                execute_db_command("""
                    DELETE FROM students 
                    WHERE id IN (
                        SELECT student_id FROM promotion_history 
                        WHERE UPPER(TRIM(old_section)) = UPPER(TRIM(:sec)) 
                           OR UPPER(TRIM(new_section)) = UPPER(TRIM(:sec))
                    )
                """, {"sec": wipe_target_sec})
                
                execute_db_command("DELETE FROM promotion_history WHERE UPPER(TRIM(old_section)) = UPPER(TRIM(:sec)) OR UPPER(TRIM(new_section)) = UPPER(TRIM(:sec))", {"sec": wipe_target_sec})
                st.success(f"💥 Permanent Purge Complete! All students tracked within Section {wipe_target_sec} have been erased from the system.")
                st.rerun()
            except Exception as delete_err:
                st.error(f"Database Purge Failure: {delete_err}")

    st.markdown("---")
    st.write("Below are recent promotions processed. Reverting an action syncs their session tags so they appear back on your 11th grade roster views.")

    try:
        history_batches = run_query("""
            SELECT batch_id, old_section, new_section, COUNT(student_id) as student_count, MAX(timestamp) as log_time
            FROM promotion_history 
            GROUP BY batch_id 
            ORDER BY log_time DESC 
            LIMIT 5
        """)
    except Exception:
        history_batches = pd.DataFrame()

    if not history_batches.empty:
        for idx, row in history_batches.iterrows():
            b_id = row['batch_id']
            sec_old = str(row['old_section']).strip()
            sec_new = str(row['new_section']).strip()
            count = row['student_count']
            
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.markdown(f"📦 **Batch `{b_id}`:** Source `({sec_old})` ➔ Target `({sec_new})` — **{count} Students Traceable**")
            with col_btn:
                if st.button(f"🗑️ Undo Promotion", key=f"db_undo_{b_id}_{idx}"):
                    batch_details = run_query("SELECT student_id, old_class, old_section, old_session FROM promotion_history WHERE batch_id = :b_id", {"b_id": b_id})
                    
                    if not batch_details.empty:
                        for _, record in batch_details.iterrows():
                            log_session_str = str(record['old_session']).strip() if record['old_session'] else ""
                            if not log_session_str or log_session_str == "None":
                                target_session_val = promo_session 
                            else:
                                target_session_val = log_session_str
                            
                            execute_db_command("""
                                UPDATE students 
                                SET class = '11th', 
                                    section = UPPER(TRIM(:old_sec)),
                                    session = :old_sess
                                WHERE id = :s_id
                            """, {
                                "old_sec": str(record['old_section']).strip(), 
                                "old_sess": target_session_val,
                                "s_id": int(record['student_id'])
                            })
                    
                    execute_db_command("DELETE FROM promotion_history WHERE batch_id = :b_id", {"b_id": b_id})
                    st.success(f"↩️ Reversal verified! Batch `{b_id}` completely restored to 11th grade section `{sec_old}`.")
                    st.rerun()
    else:
        st.info("🍃 No active promotions found in the tracking logs.")
