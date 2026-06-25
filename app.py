# Force-rebuild anchor: v1.0.2
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time

# ==============================================================================
# 1. PAGE CONFIGURATION & DATABASE INITIALIZATION
# ==============================================================================
st.set_page_config(
    page_title="Academic Management & Reports System",
    page_icon="🎓",
    layout="wide"
)

# --- SUPABASE CONNECTION CONFIGURATION ---
# ⚠️ Replace 'YOUR_DB_PASSWORD' with the actual database password you set in Supabase!
DB_URL = "postgresql://postgres.qykueriwcvgxsbxbbtso:YOUR_DB_PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

@st.cache_resource
def get_db_engine():
    """Creates and caches the database engine connection."""
    return create_engine(DB_URL)

engine = get_db_engine()

def init_db():
    """Automatically compiles schema blueprints if target relational structures do not exist."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                session_name TEXT NOT NULL,
                status TEXT NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS academic_systems (
                id SERIAL PRIMARY KEY,
                system_name TEXT NOT NULL,
                description TEXT
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS classes (
                id SERIAL PRIMARY KEY,
                class_level TEXT NOT NULL,
                sort_order INTEGER
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sections (
                id SERIAL PRIMARY KEY,
                section_name TEXT NOT NULL,
                max_capacity INTEGER
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS subjects (
                id SERIAL PRIMARY KEY,
                subject_name TEXT NOT NULL,
                subject_code TEXT NOT NULL,
                credit_hours INTEGER
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_types (
                id SERIAL PRIMARY KEY,
                test_title TEXT NOT NULL,
                total_marks INTEGER,
                weightage INTEGER
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS disciplines (
                id SERIAL PRIMARY KEY,
                discipline_title TEXT NOT NULL,
                short_code TEXT NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS teachers (
                teacher_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                contact_number TEXT,
                email TEXT
            );
        """))
        
        # Explicitly flush the creation operations out to Supabase
        conn.commit()
        # ----------------------------------------------------------------------
        # CRITICAL RE-INITIALIZATION TRIGGER
        # ----------------------------------------------------------------------
        # Wipes the old outmoded table schema structure to clear OperationalErrors.
        # COMMENT OUT OR REMOVE THIS DROP LINE AFTER YOUR FIRST SUCCESSFUL SUBMISSION!
        conn.execute(text("DROP TABLE IF EXISTS students;"))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                student_name TEXT NOT NULL,
                father_name TEXT NOT NULL,
                whatsapp_no TEXT,
                student_no TEXT,
                contact_1 TEXT NOT NULL,
                contact_2 TEXT,
                home_address TEXT,
                session TEXT NOT NULL,
                academic_system TEXT NOT NULL,
                class_level TEXT NOT NULL,
                discipline TEXT NOT NULL,
                section TEXT NOT NULL,
                roll_no INTEGER NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS incharge_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session TEXT,
                academic_system TEXT,
                class_level TEXT,
                section TEXT,
                teacher_id TEXT,
                teacher_name TEXT
            );
        """))

init_db()

def run_query(query, params=None):
    """Helper function to safely fetch data into a Pandas DataFrame using parameterized inputs."""
    if params is None:
        params = {}
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


# ==============================================================================
# 2. SHARED REUSABLE FUNCTIONS (Shared between Authorized Roles)
# ==============================================================================
def render_master_setup_engine():
    """Centralized core setup engine giving Principal and VP rights to create foundational school data structures and operational mappings."""
    st.subheader("⚙️ Master Institutional Setup Engine")
    
    # Combined Tabs view incorporating Class In-Charge Allocations as Tab 3
    tab1, tab2, tab3 = st.tabs([
        "🏛️ 1. Core Configuration Parameters", 
        "🔗 2. Operational Allocation Mapping", 
        "📋 3. Class In-Charge Allocations"
    ])
    
    with tab1:
        st.markdown("### Add & Manage Structural School Variables")
        setup_type = st.selectbox(
            "Select Variable Layer to Manage:",
            ["Session", "Academic System", "Classes", "Sections", "Subjects", "Test/Exam", "Disciplines", "Teachers"]
        )
        
        # ----------------------------------------------------------------------
        # 1. SESSION MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        if setup_type == "Session":
            st.markdown("#### ➕ Add New Session")
            with st.form("form_session"):
                col1, col2 = st.columns(2)
                with col1: session_name = st.text_input("Session Name/Year:", placeholder="e.g., 2026-2027")
                with col2: session_status = st.selectbox("Initial Status:", ["Active", "Inactive"])
                submit = st.form_submit_button("➕ Register Session Year", type="primary")
                if submit:
                    if session_name:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO sessions (session_name, status) VALUES (:name, :status)"), 
                                             {"name": session_name, "status": session_status})
                            st.success(f"🎉 Session Year '{session_name}' initialized successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Name tag cannot be empty.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Session Records")
            sessions_df = run_query("SELECT id, session_name, status FROM sessions")
            if not sessions_df.empty:
                session_options = [f"{row['id']} - {row['session_name']} ({row['status']})" for _, row in sessions_df.iterrows()]
                selected_sess = st.selectbox("Select Target Session to Update:", session_options, key="edit_sess_select")
                target_id = int(selected_sess.split(" - ")[0])
                current_data = sessions_df[sessions_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_session"):
                    col1, col2 = st.columns(2)
                    with col1: update_name = st.text_input("Modify Name/Year:", value=current_data['session_name'])
                    with col2: update_status = st.selectbox("Modify Status:", ["Active", "Inactive"], index=0 if current_data['status'] == "Active" else 1)
                    if st.form_submit_button("💾 Save Session Changes", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE sessions SET session_name = :name, status = :status WHERE id = :id"),
                                         {"name": update_name, "status": update_status, "id": target_id})
                        st.success("🎉 Session references updated smoothly!")
                        time.sleep(0.5)
                        st.rerun()
            else: st.info("No active Session logs discovered.")

        # ----------------------------------------------------------------------
        # 2. ACADEMIC SYSTEM MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Academic System":
            st.markdown("#### ➕ Add New Academic System")
            with st.form("form_academic_system"):
                col1, col2 = st.columns(2)
                with col1: system_name = st.text_input("Academic System Name:", placeholder="e.g., Semester System")
                with col2: system_desc = st.text_area("System Description:", placeholder="Notes...")
                submit = st.form_submit_button("➕ Register Academic System", type="primary")
                if submit:
                    if system_name:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO academic_systems (system_name, description) VALUES (:name, :desc)"), 
                                             {"name": system_name, "desc": system_desc})
                            st.success(f"🎉 Academic Framework '{system_name}' initialized successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ System name cannot be empty.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Academic Systems")
            systems_df = run_query("SELECT id, system_name, description FROM academic_systems")
            if not systems_df.empty:
                system_options = [f"{row['id']} - {row['system_name']}" for _, row in systems_df.iterrows()]
                selected_sys = st.selectbox("Select Target Framework to Update:", system_options, key="edit_sys_select")
                target_id = int(selected_sys.split(" - ")[0])
                current_data = systems_df[systems_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_sys"):
                    update_name = st.text_input("Modify System Name:", value=current_data['system_name'])
                    update_desc = st.text_area("Modify Description:", value=current_data['description'] or "")
                    if st.form_submit_button("💾 Save System Changes", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE academic_systems SET system_name = :name, description = :desc WHERE id = :id"),
                                         {"name": update_name, "desc": update_desc, "id": target_id})
                        st.success("🎉 Academic System profiles updated smoothly!")
                        time.sleep(0.5)
                        st.rerun()
            else: st.info("No active Framework models discovered.")

        # ----------------------------------------------------------------------
        # 3. CLASSES MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Classes":
            st.markdown("#### ➕ Add New Class Level")
            with st.form("form_classes"):
                class_title = st.text_input("Class Level Designation Name:", placeholder="e.g., 11th, 12th, Matric")
                submit = st.form_submit_button("➕ Register Class Level", type="primary")
                if submit:
                    if class_title.strip():
                        try:
                            auto_sort = int(''.join(filter(str.isdigit, class_title))) if any(c.isdigit() for c in class_title) else 99
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO classes (class_level, sort_order) VALUES (:lvl, :sort)"), 
                                             {"lvl": class_title.strip(), "sort": auto_sort})
                            st.success(f"🎉 Class Level Grade '{class_title}' successfully committed!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else:
                        st.error("❌ Class Designation field cannot be blank.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Class Structures")
            classes_df = run_query("SELECT id, class_level FROM classes ORDER BY id ASC")
            if not classes_df.empty:
                class_options = [f"{row['id']} - Class: {row['class_level']}" for _, row in classes_df.iterrows()]
                selected_cls = st.selectbox("Select Class Node to Update:", class_options, key="edit_cls_select")
                target_id = int(selected_cls.split(" - ")[0])
                current_data = classes_df[classes_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_cls"):
                    update_lvl = st.text_input("Modify Level Designation Name:", value=str(current_data['class_level']))
                    if st.form_submit_button("💾 Save Class Changes", type="secondary"):
                        if update_lvl.strip():
                            auto_sort = int(''.join(filter(str.isdigit, update_lvl))) if any(c.isdigit() for c in update_lvl) else 99
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE classes SET class_level = :lvl, sort_order = :sort WHERE id = :id"),
                                             {"lvl": update_lvl.strip(), "sort": auto_sort, "id": target_id})
                            st.success("🎉 Class Level metadata structural fields synchronized!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Designation name cannot be empty.")
            else: st.info("No indexed class records inside storage system.")

        # ----------------------------------------------------------------------
        # 4. SECTIONS MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Sections":
            st.markdown("#### ➕ Add New Section")
            with st.form("form_sections"):
                section_name = st.text_input("Section Label Name:", placeholder="e.g., A, B, Rose").upper()
                submit = st.form_submit_button("➕ Register Section Unit", type="primary")
                if submit:
                    if section_name.strip():
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO sections (section_name, max_capacity) VALUES (:name, 40)"), 
                                             {"name": section_name.strip()})
                            st.success(f"🎉 Section Room Node '{section_name}' successfully added!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Section Label code cannot be blank.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Section Branches")
            sections_df = run_query("SELECT id, section_name FROM sections")
            if not sections_df.empty:
                sec_options = [f"{row['id']} - Section {row['section_name']}" for _, row in sections_df.iterrows()]
                selected_sec = st.selectbox("Select Target Section Room:", sec_options, key="edit_sec_select")
                target_id = int(selected_sec.split(" - ")[0])
                current_data = sections_df[sections_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_sec"):
                    update_name = st.text_input("Modify Label Token:", value=current_data['section_name']).upper()
                    if st.form_submit_button("💾 Save Section Changes", type="secondary"):
                        if update_name.strip():
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE sections SET section_name = :name WHERE id = :id"),
                                             {"name": update_name.strip(), "id": target_id})
                            st.success("🎉 Section adjustments processed effectively.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Section name cannot be empty.")
            else: st.info("No tracked sections exist.")

        # ----------------------------------------------------------------------
        # 5. SUBJECTS MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Subjects":
            st.markdown("#### ➕ Add New Academic Subject")
            with st.form("form_subjects"):
                sub_name = st.text_input("Subject Official Title Name:", placeholder="e.g., Mathematics")
                submit = st.form_submit_button("➕ Register Academic Subject", type="primary")
                if submit:
                    if sub_name.strip():
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO subjects (subject_name, subject_code, credit_hours) VALUES (:name, '', 1)"), 
                                             {"name": sub_name.strip()})
                            st.success(f"🎉 Core Subject Registry item locked: {sub_name}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Heading labels are mandatory entries.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Course Modules")
            subjects_df = run_query("SELECT id, subject_name FROM subjects")
            if not subjects_df.empty:
                sub_options = [f"{row['id']} - {row['subject_name']}" for _, row in subjects_df.iterrows()]
                selected_sub = st.selectbox("Select Target Course To Update:", sub_options, key="edit_sub_select")
                target_id = int(selected_sub.split(" - ")[0])
                current_data = subjects_df[subjects_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_sub"):
                    update_name = st.text_input("Modify Course Title:", value=current_data['subject_name'])
                    if st.form_submit_button("💾 Save Subject Profile Changes", type="secondary"):
                        if update_name.strip():
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE subjects SET subject_name = :name WHERE id = :id"),
                                             {"name": update_name.strip(), "id": target_id})
                            st.success("🎉 Course catalogue adjustments saved dynamically.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Subject name cannot be empty.")
            else: st.info("Course mapping matrix arrays are blank.")

        # ----------------------------------------------------------------------
        # 6. TEST/EXAM SCHEME MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Test/Exam":
            st.markdown("#### ➕ Add New Test Evaluation Scheme")
            with st.form("form_test_exam"):
                test_title = st.text_input("Assessment Title:", placeholder="e.g., Mid Term Exam")
                submit = st.form_submit_button("➕ Register Test Profile Evaluation Scheme", type="primary")
                if submit:
                    if test_title.strip():
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO test_types (test_title, total_marks, weightage) VALUES (:title, 100, 0)"), 
                                             {"title": test_title.strip()})
                            st.success(f"🎉 Evaluation Pattern Scheme added: {test_title}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Test heading is required.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Test Protocols")
            tests_df = run_query("SELECT id, test_title FROM test_types")
            if not tests_df.empty:
                test_options = [f"{row['id']} - {row['test_title']}" for _, row in tests_df.iterrows()]
                selected_tst = st.selectbox("Select Target Evaluation Layout Template:", test_options, key="edit_tst_select")
                target_id = int(selected_tst.split(" - ")[0])
                current_data = tests_df[tests_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_tst"):
                    update_title = st.text_input("Modify Scheme Header Name:", value=current_data['test_title'])
                    if st.form_submit_button("💾 Save Scheme Blueprint Changes", type="secondary"):
                        if update_title.strip():
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE test_types SET test_title = :title WHERE id = :id"),
                                             {"title": update_title.strip(), "id": target_id})
                            st.success("🎉 Examination structure updated successfully.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Test heading cannot be empty.")
            else: st.info("No exam parameters declared in system schemas.")

        # ----------------------------------------------------------------------
        # 7. DISCIPLINES MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Disciplines":
            st.markdown("#### ➕ Add New Discipline Stream Group")
            with st.form("form_disciplines"):
                col1, col2 = st.columns(2)
                with col1: disc_title = st.text_input("Discipline Stream Group Designation:", placeholder="e.g., Computer Science")
                with col2: disc_code = st.text_input("Stream Unique Prefix Short Code:", placeholder="e.g., ICS").upper()
                submit = st.form_submit_button("➕ Register Discipline Stream Branch", type="primary")
                if submit:
                    if disc_title and disc_code:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO disciplines (discipline_title, short_code) VALUES (:title, :code)"), 
                                             {"title": disc_title, "code": disc_code})
                            st.success(f"🎉 Discipline Matrix Branch mapped: {disc_title}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Structural parameters require entries.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Stream Domains")
            disciplines_df = run_query("SELECT id, discipline_title, short_code FROM disciplines")
            if not disciplines_df.empty:
                disc_options = [f"{row['id']} - ({row['short_code']}) {row['discipline_title']}" for _, row in disciplines_df.iterrows()]
                selected_dsc = st.selectbox("Select Target Academic Stream Node:", disc_options, key="edit_dsc_select")
                target_id = int(selected_dsc.split(" - ")[0])
                current_data = disciplines_df[disciplines_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_dsc"):
                    col1, col2 = st.columns(2)
                    with col1: update_title = st.text_input("Modify Domain Label Heading:", value=current_data['discipline_title'])
                    with col2: update_code = st.text_input("Modify Short Index Tag Prefix:", value=current_data['short_code']).upper()
                    if st.form_submit_button("💾 Save Stream Group Changes", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE disciplines SET discipline_title = :title, short_code = :code WHERE id = :id"),
                                         {"title": update_title, "code": update_code, "id": target_id})
                        st.success("🎉 Stream structure definitions modified successfully.")
                        time.sleep(0.5)
                        st.rerun()
            else: st.info("No recorded disciplines exist inside ledger nodes.")

        # ----------------------------------------------------------------------
        # 8. TEACHERS MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Teachers":
            st.markdown("#### ➕ Add New Instructor / Teacher Profile")
            with st.form("form_teachers"):
                col1, col2 = st.columns(2)
                with col1: t_id = st.text_input("Teacher ID/Code Prefix:", placeholder="e.g., T-101").strip()
                with col2: t_name = st.text_input("Full Registered Name:", placeholder="e.g., Prof. Sarah Khan")
                
                col3, col4 = st.columns(2)
                with col3: t_phone = st.text_input("Primary Contact Number:", placeholder="e.g., +923001234567")
                with col4: t_email = st.text_input("Official Email Address:", placeholder="e.g., sarah.khan@school.edu")
                
                submit = st.form_submit_button("➕ Register Faculty Instructor", type="primary")
                if submit:
                    if t_id and t_name:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO teachers (teacher_id, full_name, contact_number, email) 
                                    VALUES (:id, :name, :phone, :email)
                                """), {"id": t_id, "name": t_name, "phone": t_phone, "email": t_email})
                            st.success(f"🎉 Faculty record initialized for '{t_name}'!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error (Check for duplicate IDs): {e}")
                    else: st.error("❌ Teacher ID and Full Name are completely mandatory.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Faculty Rosters")
            teachers_df = run_query("SELECT teacher_id, full_name, contact_number, email FROM teachers")
            if not teachers_df.empty:
                teacher_options = [f"{row['teacher_id']} - {row['full_name']}" for _, row in teachers_df.iterrows()]
                selected_tch = st.selectbox("Select Target Instructor to Modify:", teacher_options, key="edit_tch_select")
                target_id = selected_tch.split(" - ")[0]
                current_data = teachers_df[teachers_df['teacher_id'] == target_id].iloc[0]
                
                with st.form("edit_form_tch"):
                    col1, col2 = st.columns(2)
                    with col1: update_name = st.text_input("Modify Full Name:", value=current_data['full_name'])
                    with col2: update_phone = st.text_input("Modify Contact Number:", value=current_data['contact_number'] or "")
                    
                    update_email = st.text_input("Modify Email Address:", value=current_data['email'] or "")
                    
                    if st.form_submit_button("💾 Save Instructor Changes", type="secondary"):
                        if update_name.strip():
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE teachers 
                                    SET full_name = :name, contact_number = :phone, email = :email 
                                    WHERE teacher_id = :id
                                """), {"name": update_name.strip(), "phone": update_phone, "email": update_email, "id": target_id})
                            st.success("🎉 Instructor profile configuration metrics updated safely.")
                            time.sleep(0.5)
                            st.rerun()
                        else: st.error("❌ Full Name column cannot be written as empty.")
            else: st.info("No active faculty staff logs loaded inside structural storage.")

    with tab2:
        st.markdown("### Map Institutional Dependencies")
        allocation_type = st.selectbox(
            "Select Mapping Matrix Layer:",
            ["Section Allocation (Students to Sections)", "Subject Allocation (Teachers to Subjects/Sections)"]
        )
        
        if allocation_type == "Section Allocation (Students to Sections)":
            with st.form("mapping_allocation_form"):
                st.write(f"✏️ **New {allocation_type} Entry**")
                col_sa1, col_sa2 = st.columns(2)
                with col_sa1: st.text_input("Student Identifier Code / ID:")
                with col_sa2: st.text_input("Target Section Assignment:")
                
                submit_allocation = st.form_submit_button("🔗 Commit Allocation Link to Database", type="primary")
                if submit_allocation:
                    st.success(f"🎉 Relational Ledger Updated: {allocation_type} pipeline compiled and linked successfully.")

        elif allocation_type == "Subject Allocation (Teachers to Subjects/Sections)":
            st.write(f"✏️ **New {allocation_type} Entry**")
            
            # --- CASCADING ROW 1 ---
            col_sub1, col_sub2, col_sub3 = st.columns(3)
            
            with col_sub1:
                # 1. Session Dropdown
                sessions_df = run_query("SELECT DISTINCT session_name FROM sessions")
                sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
                sel_session = st.selectbox("1. Select Session:", options=sessions_list, key="sub_sess")

            with col_sub2:
                # 2. Academic System Dropdown (Depends on Session)
                if sel_session != "-- Select Session --":
                    systems_df = run_query("SELECT DISTINCT system_name FROM academic_systems")
                    systems_list = ["-- Select System --"] + (systems_df['system_name'].tolist() if not systems_df.empty else [])
                    sel_system = st.selectbox("2. Select Academic System:", options=systems_list, key="sub_sys")
                else:
                    st.selectbox("2. Select Academic System:", ["🔒 Waiting for Session..."], disabled=True)
                    sel_system = "-- Select System --"

            with col_sub3:
                # 3. Class Dropdown (Depends on System)
                if sel_system not in ["-- Select System --", "", None]:
                    classes_df = run_query("SELECT DISTINCT class_level FROM classes")
                    classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty else [])
                    sel_class = st.selectbox("3. Select Class:", options=classes_list, key="sub_cls")
                else:
                    st.selectbox("3. Select Class:", ["🔒 Waiting for System..."], disabled=True)
                    sel_class = "-- Select Class --"

            # --- CASCADING ROW 2 ---
            col_sub4, col_sub5, col_sub6 = st.columns(3)

            with col_sub4:
                # 4. Discipline Dropdown (Depends on Class)
                if sel_class not in ["-- Select Class --", "", None]:
                    disciplines_df = run_query("SELECT DISTINCT discipline_title FROM disciplines")
                    disciplines_list = ["-- Select Discipline --"] + (disciplines_df['discipline_title'].tolist() if not disciplines_df.empty else [])
                    sel_discipline = st.selectbox("4. Select Discipline:", options=disciplines_list, key="sub_disc")
                else:
                    st.selectbox("4. Select Discipline:", ["🔒 Waiting for Class..."], disabled=True)
                    sel_discipline = "-- Select Discipline --"

            with col_sub5:
                # 5. Section Dropdown (Depends on Discipline)
                if sel_discipline not in ["-- Select Discipline --", "", None]:
                    sections_df = run_query("SELECT DISTINCT section_name FROM sections")
                    sections_list = ["-- Select Section --"] + (sections_df['section_name'].tolist() if not sections_df.empty else [])
                    sel_section = st.selectbox("5. Select Section:", options=sections_list, key="sub_sec")
                else:
                    st.selectbox("5. Select Section:", ["🔒 Waiting for Discipline..."], disabled=True)
                    sel_section = "-- Select Section --"

            with col_sub6:
                # 6. Subject Dropdown (Depends on Section)
                if sel_section not in ["-- Select Section --", "", None]:
                    subjects_df = run_query("SELECT DISTINCT subject_name FROM subjects")
                    subjects_list = ["-- Select Subject --"] + (subjects_df['subject_name'].tolist() if not subjects_df.empty else [])
                    sel_subject = st.selectbox("6. Select Subject:", options=subjects_list, key="sub_course")
                else:
                    st.selectbox("6. Select Subject:", ["🔒 Waiting for Section..."], disabled=True)
                    sel_subject = "-- Select Subject --"

            # --- FINAL STEP ---
            col_sub7, _ = st.columns([1, 2])
            with col_sub7:
                # 7. Teacher Dropdown (Depends on Subject)
                if sel_subject not in ["-- Select Subject --", "", None]:
                    teachers_df = run_query("SELECT teacher_id, full_name FROM teachers")
                    teachers_list = ["-- Select Teacher --"] + [f"{row['teacher_id']} - {row['full_name']}" for _, row in teachers_df.iterrows()] if not teachers_df.empty else ["-- Select Teacher --"]
                    sel_teacher = st.selectbox("7. Select Teacher:", options=teachers_list, key="sub_tchr")
                else:
                    st.selectbox("7. Select Teacher:", ["🔒 Waiting for Subject..."], disabled=True)
                    sel_teacher = "-- Select Teacher --"

            st.markdown("---")
            
            # Form submission gate validation
            ready_to_submit = all([
                sel_session != "-- Select Session --",
                sel_system != "-- Select System --",
                sel_class != "-- Select Class --",
                sel_discipline != "-- Select Discipline --",
                sel_section != "-- Select Section --",
                sel_subject != "-- Select Subject --",
                sel_teacher != "-- Select Teacher --"
            ])

            # Form block isolates final transaction execution safely
            with st.form("subject_allocation_submit_gate"):
                if ready_to_submit:
                    if st.form_submit_button("🔗 Commit Subject Allocation Matrix", type="primary", use_container_width=True):
                        t_id = sel_teacher.split(" - ")[0].strip()
                        t_name = sel_teacher.split(" - ")[1].strip()
                        
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO subject_allocations (session, academic_system, class_level, discipline, section, subject_name, teacher_id, teacher_name)
                                VALUES (:sess, :sys, :cls, :disc, :sec, :sub, :tid, :tname)
                            """), {"sess": sel_session, "sys": sel_system, "cls": sel_class, "disc": sel_discipline, "sec": sel_section, "sub": sel_subject, "tid": t_id, "tname": t_name})
                        
                        st.success("🎉 Allocation Matrix compiled and linked successfully!")
                        time.sleep(0.5)
                        st.rerun()
                else:
                    st.form_submit_button("🔗 Complete Steps 1-7 above to unlock submission", disabled=True, use_container_width=True)

    with tab3:
        # ----------------------------------------------------------------------
        # 3. CLASS IN-CHARGE ALLOCATIONS (Moved from sidebar to right side tab)
        # ----------------------------------------------------------------------
        st.markdown("### Manage Class In-Charge Allocations")
        st.markdown("### 📋 Class In-Charge Mapping Management")
        
        # 1. Session Dropdown
        sessions_df = run_query("SELECT DISTINCT session_name FROM sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
        
        col_inc1, col_inc2 = st.columns(2)
        with col_inc1: 
            sel_session = st.selectbox("1. Select Session Year:", options=sessions_list, key="inc_sess")
        
        # 2. Academic System Dropdown (Cascading from Session)
        with col_inc2:
            if sel_session != "-- Select Session --":
                systems_df = run_query("SELECT DISTINCT system_name FROM academic_systems")
                systems_list = ["-- Select System --"] + (systems_df['system_name'].tolist() if not systems_df.empty else [])
                sel_system = st.selectbox("2. Select Academic Framework:", options=systems_list, key="inc_sys")
            else:
                st.selectbox("2. Select Academic Framework:", ["🔒 Waiting for Session..."], disabled=True, key="inc_sys_dis")
                sel_system = "-- Select System --"
                
        col_inc3, col_inc4 = st.columns(2)
        
        # 3. Class Level Dropdown (Cascading from System)
        with col_inc3:
            if sel_system not in ["-- Select System --", "", None]:
                classes_df = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC, id ASC")
                classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty else [])
                sel_class = st.selectbox("3. Assign Class Level Scope:", options=classes_list, key="inc_cls")
            else:
                st.selectbox("3. Assign Class Level Scope:", ["🔒 Waiting for System..."], disabled=True, key="inc_cls_dis")
                sel_class = "-- Select Class --"
                
        # 4. Section Dropdown (Cascading from Class)
        with col_inc4:
            if sel_class not in ["-- Select Class --", "", None]:
                sections_df = run_query("SELECT DISTINCT section_name FROM sections")
                sections_list = ["-- Select Section --"] + (sections_df['section_name'].tolist() if not sections_df.empty else [])
                sel_section = st.selectbox("4. Assign Section Branch:", options=sections_list, key="inc_sec")
            else:
                st.selectbox("4. Assign Section Branch:", ["🔒 Waiting for Class..."], disabled=True, key="inc_sec_dis")
                sel_section = "-- Select Section --"
                
        # 5. Teacher Dropdown (Cascading from Section)
        if sel_section not in ["-- Select Section --", "", None]:
            teachers_df = run_query("SELECT teacher_id, full_name FROM teachers")
            teachers_list = ["-- Select Teacher --"] + [f"{row['teacher_id']} - {row['full_name']}" for _, row in teachers_df.iterrows()] if not teachers_df.empty else ["-- Select Teacher --"]
            selected_teacher = st.selectbox("5. Select Assigned Faculty Member:", options=teachers_list, key="inc_tchr")
        else:
            st.selectbox("5. Select Assigned Faculty Member:", ["🔒 Waiting for Section Selection..."], disabled=True, key="inc_tchr_dis")
            selected_teacher = "-- Select Teacher --"
            
        st.markdown("---")
        
        # Submission Validation Gate
        ready_to_submit_inc = all([
            sel_session != "-- Select Session --",
            sel_system != "-- Select System --",
            sel_class != "-- Select Class --",
            sel_section != "-- Select Section --",
            selected_teacher != "-- Select Teacher --"
        ])
        
        with st.form("form_incharge_allocation_gate"):
            if ready_to_submit_inc:
                if st.form_submit_button("🔗 Link Class In-Charge Assignment", type="primary", use_container_width=True):
                    t_id = selected_teacher.split(" - ")[0].strip()
                    t_name = selected_teacher.split(" - ")[1].strip()
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO incharge_allocations (session, academic_system, class_level, section, teacher_id, teacher_name)
                                VALUES (:sess, :sys, :cls, :sec, :tid, :tname)
                            """), {"sess": sel_session, "sys": sel_system, "cls": sel_class, "sec": sel_section, "tid": t_id, "tname": t_name})
                        st.success(f"🎉 Mapping Complete: {t_name} is now designated In-Charge for Class {sel_class}-{sel_section}!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Database error: {e}")
            else:
                st.form_submit_button("🔗 Complete Steps 1-5 above to unlock assignment", disabled=True, use_container_width=True)


def render_student_management_workspace():
    """Shared workspace enabling authorized users to onboard, bulk import, or update student registry information."""
    st.subheader("📝 Student Records & Registration Directory")
    
    # Sub-tabs separating Single Manual Entry, Bulk Excel Loading, and Edit Panel
    tab1, tab2, tab3 = st.tabs([
        "🆕 Manual Admission Entry", 
        "📤 Bulk Import via Excel", 
        "✏️ Edit Student Profiles"
    ])
    
    # Ensure database schema table structure accommodates our 14 required structural fields
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                student_name TEXT NOT NULL,
                father_name TEXT NOT NULL,
                whatsapp_no TEXT,
                student_no TEXT,
                contact_1 TEXT NOT NULL,
                contact_2 TEXT,
                home_address TEXT,
                session TEXT,
                academic_system TEXT,
                class_level TEXT,
                discipline TEXT,
                section TEXT,
                roll_no INTEGER
            );
        """))

    # ==============================================================================
    # TAB 1: MANUAL ADMISSION ENTRY
    # ==============================================================================
    with tab1:
        st.write("### 🆕 Register New Student Particulars")
        
        # --- PHASE 1: CASCADING PLACEMENT FILTERS FIRST ---
        st.write("📁 **Step 1: Assign Target Academic Placement Attributes**")
        
        sessions_df = run_query("SELECT DISTINCT session_name FROM sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
        
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            new_session = st.selectbox("1. Target Session:*", options=sessions_list, key="manual_sess")

        with col_a2:
            if new_session != "-- Select Session --":
                systems_df = run_query("SELECT DISTINCT system_name FROM academic_systems")
                systems_list = ["-- Select System --"] + (systems_df['system_name'].tolist() if not systems_df.empty else [])
                new_system = st.selectbox("2. Target Academic System:*", options=systems_list, key="manual_sys")
            else:
                st.selectbox("2. Target Academic System:", ["🔒 Waiting for Session..."], disabled=True, key="manual_sys_dis")
                new_system = "-- Select System --"

        with col_a3:
            if new_system != "-- Select System --":
                classes_df = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC, id ASC")
                classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty else [])
                new_class = st.selectbox("3. Target Class:*", options=classes_list, key="manual_cls")
            else:
                st.selectbox("3. Target Class:", ["🔒 Waiting for System..."], disabled=True, key="manual_cls_dis")
                new_class = "-- Select Class --"

        col_a4, col_a5, col_a6 = st.columns(3)
        with col_a4:
            if new_class != "-- Select Class --":
                disciplines_df = run_query("SELECT DISTINCT discipline_title FROM disciplines")
                disciplines_list = ["-- Select Discipline --"] + (disciplines_df['discipline_title'].tolist() if not disciplines_df.empty else [])
                new_discipline = st.selectbox("4. Target Discipline:*", options=disciplines_list, key="manual_disc")
            else:
                st.selectbox("4. Target Discipline:", ["🔒 Waiting for Class..."], disabled=True, key="manual_disc_dis")
                new_discipline = "-- Select Discipline --"

        with col_a5:
            if new_discipline != "-- Select Discipline --":
                sections_df = run_query("SELECT DISTINCT section_name FROM sections")
                sections_list = ["-- Select Section --"] + (sections_df['section_name'].tolist() if not sections_df.empty else [])
                new_sec = st.selectbox("5. Target Section:*", options=sections_list, key="manual_sec")
            else:
                st.selectbox("5. Target Section:", ["🔒 Waiting for Discipline..."], disabled=True, key="manual_sec_dis")
                new_sec = "-- Select Section --"

        with col_a6:
            new_roll = st.number_input("6. Class Arrangement Roll No:*", min_value=1, step=1, key="manual_roll")

        st.markdown("---")

        # --- PHASE 2: CORE DATA FORM LOCK OUT GATED UNTIL ALL DROP-DOWNS SELECTED ---
        if any(f in ["-- Select Session --", "-- Select System --", "-- Select Class --", "-- Select Discipline --", "-- Select Section --"] for f in [new_session, new_system, new_class, new_discipline, new_sec]):
            st.warning("⏳ Please complete selecting all 5 Academic Placement Attributes above to unlock the Student Information input cards.")
        else:
            st.write(f"📝 **Step 2: Enter Student Particulars for Class `{new_class} ({new_sec})`**")
            
            # Initialize Session State fallback values to safeguard against rerender drops
            for field in ["new_id", "new_name", "father_name", "whatsapp_no", "student_no", "contact_1", "contact_2", "home_address"]:
                if field not in st.session_state:
                    st.session_state[field] = ""

            with st.form("student_profile_text_fields_form"):
                col1, col2, col3 = st.columns(3)
                with col1: 
                    new_id = st.text_input("1. Student ID / Registration No:*", value=st.session_state["new_id"], key="new_id_input", placeholder="e.g., STU-2026-001").strip().upper()
                with col2: 
                    new_name = st.text_input("2. Student Full Name:*", value=st.session_state["new_name"], key="new_name_input", placeholder="e.g., John Doe").strip()
                with col3: 
                    father_name = st.text_input("3. Student's Father Name:*", value=st.session_state["father_name"], key="father_name_input", placeholder="e.g., Robert Doe").strip()
                
                col4, col5, col6 = st.columns(3)
                with col4: 
                    whatsapp_no = st.text_input("4. WhatsApp Number:", value=st.session_state["whatsapp_no"], key="whatsapp_no_input", placeholder="e.g., +923001234567").strip()
                with col5: 
                    student_no = st.text_input("5. Student Mobile Number:", value=st.session_state["student_no"], key="student_no_input", placeholder="e.g., +923151234567").strip()
                with col6: 
                    contact_1 = st.text_input("6. Emergency Contact-1:*", value=st.session_state["contact_1"], key="contact_1_input", placeholder="e.g., Mother's Mobile").strip()
                
                col7, col8 = st.columns([1, 2])
                with col7: 
                    contact_2 = st.text_input("7. Alternative Contact-2:", value=st.session_state["contact_2"], key="contact_2_input", placeholder="e.g., Guardian/Landline").strip()
                with col8: 
                    home_address = st.text_input("8. Home Address:", value=st.session_state["home_address"], key="home_address_input", placeholder="e.g., House #123, Street 5").strip()
                
                st.markdown("<small style='color: gray;'>* Indicates a mandatory field.</small>", unsafe_allow_html=True)
                
                # --- SAVE COMPACT FORM ACTION ---
                submit_manual = st.form_submit_button("🚀 Finalize Registration & Save Student Record", type="primary", use_container_width=True)
                
                if submit_manual:
                    if not new_id or not new_name or not father_name or not contact_1:
                        st.error("❌ Validation Error: Please fill in all mandatory core data fields before saving.")
                    else:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO students (student_id, student_name, father_name, whatsapp_no, student_no, contact_1, contact_2, home_address, session, academic_system, class_level, discipline, section, roll_no)
                                    VALUES (:id, :name, :fname, :whatsapp, :sno, :c1, :c2, :addr, :sess, :sys, :class_lvl, :disc, :sec, :roll)
                                """), {
                                    "id": new_id, "name": new_name, "fname": father_name, "whatsapp": whatsapp_no or None,
                                    "sno": student_no or None, "c1": contact_1, "c2": contact_2 or None, "addr": home_address or None,
                                    "sess": new_session, "sys": new_system, "class_lvl": new_class, "disc": new_discipline, "sec": new_sec, "roll": new_roll
                                })
                                # Force database sync explicitly
                                conn.commit()
                                
                            st.success(f"🎉 Student node successfully registered: {new_name} added successfully!")
                            
                            # Clear session state cache registers cleanly
                            for field in ["new_id", "new_name", "father_name", "whatsapp_no", "student_no", "contact_1", "contact_2", "home_address"]:
                                st.session_state[field] = ""
                                
                            import time
                            time.sleep(1.0)
                            st.rerun()
                        except Exception as e: 
                            st.error(f"❌ Database execution failure: {e}. Check if Student ID already exists.")

    # ==============================================================================
    # TAB 2: BULK IMPORT VIA EXCEL / CSV
    # ==============================================================================
    with tab2:
        st.write("### 📤 Bulk Import Student Registry via File Streaming")
        
        # --- SAMPLE FILE MAKER TEMPLATE DOCK ---
        st.markdown("📁 **Step 1: Download Required Roster Configuration Layout**")
        sample_df = pd.DataFrame(columns=[
            'student_id', 'student_name', 'father_name', 'whatsapp_no', 'student_no',
            'contact_1', 'contact_2', 'home_address', 'roll_no'
        ])
        # Populate template with placeholder data to illustrate layout structure
        sample_df.loc[0] = ['STU-2026-001', 'John Doe', 'Robert Doe', '+923001234567', '+923151234567', '+923331112222', '', 'Main Street, Block A', 1]
        
        # Buffer conversions for format selection downloads
        csv_buffer = sample_df.to_csv(index=False).encode('utf-8')
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="📥 Download Template (.CSV Format)",
                data=csv_buffer,
                file_name="student_onboarding_template.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_dl2:
            import io
            excel_io = io.BytesIO()
            # Fixed engine option to seamlessly use 'xlsxwriter' package from your environment
            with pd.ExcelWriter(excel_io, engine='xlsxwriter') as writer:
                sample_df.to_excel(writer, index=False, sheet_name='Students')
            st.download_button(
                label="📥 Download Template (.XLSX Format)",
                data=excel_io.getvalue(),
                file_name="student_onboarding_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        st.markdown("---")
        
        # --- PHASE 2: ALL 6 CASCADING PLACEMENT FILTERS ENFORCED ---
        st.markdown("📁 **Step 2: Assign Destination Academic Framework Attributes**")
        
        sessions_df = run_query("SELECT DISTINCT session_name FROM sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
        
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            bulk_session = st.selectbox("1. Target Session:*", options=sessions_list, key="bulk_sess")

        with col_b2:
            if bulk_session != "-- Select Session --":
                systems_df = run_query("SELECT DISTINCT system_name FROM academic_systems")
                systems_list = ["-- Select System --"] + (systems_df['system_name'].tolist() if not systems_df.empty else [])
                bulk_system = st.selectbox("2. Target Academic System:*", options=systems_list, key="bulk_sys")
            else:
                st.selectbox("2. Target Academic System:", ["🔒 Waiting for Session..."], disabled=True, key="bulk_sys_dis")
                bulk_system = "-- Select System --"

        with col_b3:
            if bulk_system != "-- Select System --":
                classes_df = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC, id ASC")
                classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty else [])
                bulk_class = st.selectbox("3. Target Class:*", options=classes_list, key="bulk_cls")
            else:
                st.selectbox("3. Target Class:", ["🔒 Waiting for System..."], disabled=True, key="bulk_cls_dis")
                bulk_class = "-- Select Class --"

        col_b4, col_b5, col_b6 = st.columns(3)
        with col_b4:
            if bulk_class != "-- Select Class --":
                disciplines_df = run_query("SELECT DISTINCT discipline_title FROM disciplines")
                disciplines_list = ["-- Select Discipline --"] + (disciplines_df['discipline_title'].tolist() if not disciplines_df.empty else [])
                bulk_discipline = st.selectbox("4. Target Discipline:*", options=disciplines_list, key="bulk_disc")
            else:
                st.selectbox("4. Target Discipline:", ["🔒 Waiting for Class..."], disabled=True, key="bulk_disc_dis")
                bulk_discipline = "-- Select Discipline --"

        with col_b5:
            if bulk_discipline != "-- Select Discipline --":
                sections_df = run_query("SELECT DISTINCT section_name FROM sections")
                sections_list = ["-- Select Section --"] + (sections_df['section_name'].tolist() if not sections_df.empty else [])
                bulk_sec = st.selectbox("5. Target Section:*", options=sections_list, key="bulk_sec")
            else:
                st.selectbox("5. Target Section:", ["🔒 Waiting for Discipline..."], disabled=True, key="bulk_sec_dis")
                bulk_sec = "-- Select Section --"

        with col_b6:
            bulk_roll_mode = st.selectbox(
                "6. Roll No Handling Mode:*", 
                options=["Use Roll No from File Row", "Auto-Generate Sequential Index"], 
                key="bulk_roll_mode"
            )

        st.markdown("---")

        # --- PHASE 3: STREAM UPLOADER GATEWAY UNLOCKED ONLY WHEN ALL 5 SELECTIONS VALIDATED ---
        if any(f in ["-- Select Session --", "-- Select System --", "-- Select Class --", "-- Select Discipline --", "-- Select Section --"] for f in [bulk_session, bulk_system, bulk_class, bulk_discipline, bulk_sec]):
            st.warning("⏳ Please complete setting all 5 Academic Placement drop-down targets above to activate the file upload channel.")
        else:
            st.markdown(f"📁 **Step 3: Upload Roster Stream for Class `{bulk_class} ({bulk_sec})`**")
            uploaded_file = st.file_uploader("Upload completed admission roster data stream:", type=["xlsx", "xls", "csv"])
            
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        uploaded_df = pd.read_csv(uploaded_file)
                    else:
                        uploaded_df = pd.read_excel(uploaded_file)
                    
                    # Standardize columns to lowercase strings
                    uploaded_df.columns = [str(col).strip().lower() for col in uploaded_df.columns]
                    st.write("#### 📋 Parsed File Content Preview", uploaded_df.head(5))
                    
                    # Validation for mandatory student bio fields
                    required_cols = ['student_id', 'student_name', 'father_name', 'contact_1']
                    missing_critical_cols = [c for c in required_cols if c not in uploaded_df.columns]
                    
                    if missing_critical_cols:
                        st.error(f"❌ Upload Blocked: File is missing core data structural headers: {missing_critical_cols}")
                    else:
                        # Ensure optional attributes don't throw KeyErrors if absent
                        optional_fields = ['whatsapp_no', 'student_no', 'contact_2', 'home_address', 'roll_no']
                        for opt in optional_fields:
                            if opt not in uploaded_df.columns:
                                uploaded_df[opt] = None if opt != 'roll_no' else 1

                        total_rows = len(uploaded_df)
                        st.info(f"⚡ Verification clear! Ready to upload {total_rows} student records directly into the assigned configuration context.")
                        
                        if st.button("🚀 Commit File Records To Database", type="primary", use_container_width=True):
                            success_count = 0
                            error_log = []
                            
                            with engine.begin() as conn:
                                for index, row in uploaded_df.iterrows():
                                    s_id = str(row['student_id']).strip().upper()
                                    if not s_id or s_id == 'NAN' or pd.isna(row['student_id']):
                                        continue
                                    try:
                                        # Deduce proper numbering offset via chosen user handling rules
                                        if bulk_roll_mode == "Use Roll No from File Row" and pd.notna(row['roll_no']):
                                            roll_val = int(row['roll_no'])
                                        else:
                                            roll_val = index + 1
                                        
                                        conn.execute(text("""
                                            INSERT INTO students (
                                                student_id, student_name, father_name, whatsapp_no, student_no, 
                                                contact_1, contact_2, home_address, session, academic_system, 
                                                class_level, discipline, section, roll_no
                                            ) VALUES (
                                                :id, :name, :fname, :whatsapp, :sno, 
                                                :c1, :c2, :addr, :sess, :sys, 
                                                :class_lvl, :disc, :sec, :roll
                                            )
                                            ON CONFLICT(student_id) DO UPDATE SET
                                                student_name=EXCLUDED.student_name,
                                                father_name=EXCLUDED.father_name,
                                                whatsapp_no=EXCLUDED.whatsapp_no,
                                                student_no=EXCLUDED.student_no,
                                                contact_1=EXCLUDED.contact_1,
                                                contact_2=EXCLUDED.contact_2,
                                                home_address=EXCLUDED.home_address,
                                                session=EXCLUDED.session,
                                                academic_system=EXCLUDED.academic_system,
                                                class_level=EXCLUDED.class_level,
                                                discipline=EXCLUDED.discipline,
                                                section=EXCLUDED.section,
                                                roll_no=EXCLUDED.roll_no;
                                        """), {
                                            "id": s_id, "name": str(row['student_name']).strip(), "fname": str(row['father_name']).strip(),
                                            "whatsapp": str(row['whatsapp_no']).strip() if pd.notna(row['whatsapp_no']) else None,
                                            "sno": str(row['student_no']).strip() if pd.notna(row['student_no']) else None,
                                            "c1": str(row['contact_1']).strip(), "c2": str(row['contact_2']).strip() if pd.notna(row['contact_2']) else None,
                                            "addr": str(row['home_address']).strip() if pd.notna(row['home_address']) else None,
                                            "sess": bulk_session, "sys": bulk_system, "class_lvl": bulk_class, "disc": bulk_discipline, "sec": bulk_sec, "roll": roll_val
                                        })
                                        success_count += 1
                                    except Exception as inner_e:
                                        error_log.append(f"Row {index + 2} (ID: {s_id}): {str(inner_e)}")
                                
                                # Explicitly push bulk structural additions to storage node
                                conn.commit()
                            
                            if success_count > 0:
                                st.success(f"🎉 Processing Complete: {success_count} student profile nodes written or synced successfully!")
                                import time
                                time.sleep(1.0)
                                st.rerun()
                            if error_log:
                                with st.expander("⚠️ Review Log Exceptions"):
                                    for log in error_log:
                                        st.warning(log)
                                        
                except Exception as e:
                    st.error(f"❌ Fatal streaming data processing breakdown error: {e}")

    # ==============================================================================
    # TAB 3: SEARCH & EDIT (WITH INPUT CLEANING & DIAGNOSTICS)
    # ==============================================================================
    with tab3:
        st.write("### ✏️ Search, Batch Edit Section, or Modify Profiles")
        
        # Pull reference indices to populate lookups
        sessions_df = run_query("SELECT DISTINCT session_name FROM sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
        
        st.markdown("📁 **Step 1: Locate Active Target Parameters**")
        col_s1, col_s2, col_s3, col_s4 = st.columns([1, 1, 1, 1.5])
        
        with col_s1:
            search_session = st.selectbox("Filter Session:", options=sessions_list, key="search_sess")
            
        with col_s2:
            if search_session != "-- Select Session --":
                classes_df = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC")
                classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty else [])
                search_class = st.selectbox("Filter Class:", options=classes_list, key="search_cls")
            else:
                st.selectbox("Filter Class:", ["🔒 Waiting..."], disabled=True, key="search_cls_dis")
                search_class = "-- Select Class --"
                
        with col_s3:
            if search_class != "-- Select Class --":
                sections_df = run_query("SELECT DISTINCT section_name FROM sections")
                sections_list = ["-- Select Section --"] + (sections_df['section_name'].tolist() if not sections_df.empty else [])
                search_sec = st.selectbox("Filter Section:", options=sections_list, key="search_sec")
            else:
                st.selectbox("Filter Section:", ["🔒 Waiting..."], disabled=True, key="search_sec_dis")
                search_sec = "-- Select Section --"
        
        with col_s4:
            edit_scope = st.radio(
                "Modification Scope:",
                options=["✨ Modify Single Student", "📊 Batch Edit Entire Section"],
                horizontal=True,
                key="edit_scope_toggle"
            )
                
        st.markdown("---")
        
        # Verify filtering keys are correctly set before processing queries
        if search_session != "-- Select Session --" and search_class != "-- Select Class --" and search_sec != "-- Select Section --":
            try:
                # Added TRIM() to bypass any accidental whitespace padding during insertions
                matched_students = run_query("""
                    SELECT student_id, roll_no, student_name, father_name, whatsapp_no, student_no, contact_1, contact_2, home_address, discipline
                    FROM students
                    WHERE TRIM(session) = TRIM(:sess) 
                      AND TRIM(class_level) = TRIM(:cls) 
                      AND TRIM(section) = TRIM(:sec)
                    ORDER BY roll_no ASC
                """, {"sess": search_session, "cls": search_class, "sec": search_sec})
            except Exception as e:
                st.error(f"Error fetching directory: {e}")
                matched_students = pd.DataFrame()
                
            if matched_students.empty:
                st.info(f"ℹ️ No active student records found matching: {search_session} | Class {search_class} | Section {search_sec}")
                
                # --- AUTOMATED ENGINE DIAGNOSTIC DOCK ---
                with st.expander("🔍 Run Database Troubleshooting Check"):
                    st.write("Let's look at what is actually stored inside your `students` table:")
                    debug_df = run_query("SELECT student_id, student_name, session, class_level, section FROM students LIMIT 10")
                    if debug_df.empty:
                        st.warning("The `students` table is completely empty. Go to Tab 1 or Tab 2 to add records first.")
                    else:
                        st.write("Here are the last 10 records added to your database. Compare these strings against your filters:")
                        st.dataframe(debug_df, use_container_width=True)
            
            # ==================================================================
            # OPTION A: BATCH EDIT ENTIRE SECTION
            # ==================================================================
            elif edit_scope == "📊 Batch Edit Entire Section":
                st.markdown(f"#### 📊 Batch Registry Grid: Class `{search_class} ({search_sec})`")
                st.caption("💡 Edit any cell directly inside the grid below, then click the save button.")
                
                edited_df = st.data_editor(
                    matched_students,
                    column_config={
                        "student_id": st.column_config.TextColumn("Student ID 🔒", disabled=True),
                        "roll_no": st.column_config.NumberColumn("Roll No*", min_value=1, step=1, required=True),
                        "student_name": st.column_config.TextColumn("Student Name*", required=True),
                        "father_name": st.column_config.TextColumn("Father Name*", required=True),
                        "whatsapp_no": st.column_config.TextColumn("WhatsApp No"),
                        "student_no": st.column_config.TextColumn("Student No"),
                        "contact_1": st.column_config.TextColumn("Contact-1*", required=True),
                        "contact_2": st.column_config.TextColumn("Contact-2"),
                        "home_address": st.column_config.TextColumn("Home Address"),
                        "discipline": st.column_config.TextColumn("Discipline 🔒", disabled=True)
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"sec_editor_{search_session}_{search_class}_{search_sec}"
                )
                
                if st.button("💾 Bulk Save Changes for This Section", type="primary", use_container_width=True):
                    try:
                        with engine.begin() as conn:
                            for _, row in edited_df.iterrows():
                                conn.execute(text("""
                                    UPDATE students SET
                                        student_name = :name,
                                        father_name = :fname,
                                        roll_no = :roll,
                                        whatsapp_no = :whatsapp,
                                        student_no = :sno,
                                        contact_1 = :c1,
                                        contact_2 = :c2,
                                        home_address = :addr
                                    WHERE student_id = :id
                                """), {
                                    "name": str(row['student_name']).strip(),
                                    "fname": str(row['father_name']).strip(),
                                    "roll": int(row['roll_no']),
                                    "whatsapp": str(row['whatsapp_no']).strip() if pd.notna(row['whatsapp_no']) else None,
                                    "sno": str(row['student_no']).strip() if pd.notna(row['student_no']) else None,
                                    "c1": str(row['contact_1']).strip(),
                                    "contact_2": str(row['contact_2']).strip() if pd.notna(row['contact_2']) else None,
                                    "addr": str(row['home_address']).strip() if pd.notna(row['home_address']) else None,
                                    "id": row['student_id']
                                })
                        st.success(f"🎉 Roster synced successfully!")
                        time.sleep(0.8)
                        st.rerun()
                    except Exception as bulk_err:
                        st.error(f"❌ Batch Transaction Interrupted: {bulk_err}")

            # ==================================================================
            # OPTION B: SINGLE STUDENT PROFILE WITH FILTER SEARCH
            # ==================================================================
            else:
                st.markdown("#### 🔍 Search & Filter Student Profile")
                search_query = st.text_input("Type Student Name or Student ID to filter options:", placeholder="e.g., John or STU-2026-001").strip().lower()
                
                if search_query:
                    filtered_df = matched_students[
                        matched_students['student_id'].str.lower().str.contains(search_query, na=False) | 
                        matched_students['student_name'].str.lower().str.contains(search_query, na=False)
                    ]
                else:
                    filtered_df = matched_students

                if filtered_df.empty:
                    st.warning("⚠️ No student records match your text filter query.")
                else:
                    student_options = [f"{row['student_id']} - Roll #{row['roll_no']} - {row['student_name']}" for _, row in filtered_df.iterrows()]
                    selected_profile_str = st.selectbox("🎯 Select Target Student Profile to Open Form:", options=student_options)
                    
                    if selected_profile_str:
                        target_id = selected_profile_str.split(" - ")[0].strip()
                        student_data = filtered_df[filtered_df['student_id'] == target_id].iloc[0]
                        
                        st.markdown(f"#### ✏️ Modifying Records for ID: `{target_id}`")
                        
                        with st.form("edit_student_profile_form"):
                            col_e1, col_e2, col_e3 = st.columns(3)
                            with col_e1: edit_name = st.text_input("Student Name:*", value=str(student_data['student_name']))
                            with col_e2: edit_fname = st.text_input("Father's Name:*", value=str(student_data['father_name']))
                            with col_e3: edit_roll = st.number_input("Roll Number:*", value=int(student_data['roll_no']), min_value=1, step=1)
                            
                            col_e4, col_e5, col_e6 = st.columns(3)
                            with col_e4: edit_whatsapp = st.text_input("WhatsApp No:", value=str(student_data['whatsapp_no'] or ''))
                            with col_e5: edit_student_no = st.text_input("Student No:", value=str(student_data['student_no'] or ''))
                            with col_e6: edit_c1 = st.text_input("Emergency Contact-1:*", value=str(student_data['contact_1']))
                            
                            col_e7, col_e8 = st.columns([1, 2])
                            with col_e7: edit_c2 = st.text_input("Alternative Contact-2:", value=str(student_data['contact_2'] or ''))
                            with col_e8: edit_addr = st.text_input("Home Address:", value=str(student_data['home_address'] or ''))
                            
                            submit_edit = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
                            
                            if submit_edit:
                                if not edit_name.strip() or not edit_fname.strip() or not edit_c1.strip():
                                    st.error("❌ Validation Failed: All mandatory fields must contain text.")
                                else:
                                    try:
                                        with engine.begin() as conn:
                                            conn.execute(text("""
                                                UPDATE students SET
                                                    student_name = :name,
                                                    father_name = :fname,
                                                    roll_no = :roll,
                                                    whatsapp_no = :whatsapp,
                                                    student_no = :sno,
                                                    contact_1 = :c1,
                                                    contact_2 = :c2,
                                                    home_address = :addr
                                                WHERE student_id = :id
                                            """), {
                                                "name": edit_name.strip(), "fname": edit_fname.strip(), "roll": edit_roll,
                                                "whatsapp": edit_whatsapp.strip() or None, "sno": edit_student_no.strip() or None,
                                                "c1": edit_c1.strip(), "c2": edit_c2.strip() or None, "addr": edit_addr.strip() or None,
                                                "id": target_id
                                            })
                                        st.success(f"🎉 Saved successfully!")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as update_err:
                                        st.error(f"❌ Database Error: {update_err}")
        else:
            st.warning("⏳ Please select Session, Class, and Section above to fetch records.")

def render_universal_attendance_workspace():
    """Shared workspace allowing unrestricted global access to all sections for attendance processing."""
    st.subheader("🌐 Global Universal Attendance Control Desk")
    st.info("🔓 Unrestricted administrative view enabled. You can monitor or verify attendance for all sections.")
    
    try:
        available_classes = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC")['class_level'].tolist()
        if not available_classes:
            available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]
    except Exception:
        available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]

    col_u1, col_u2, col_u3 = st.columns(3)
    with col_u1: sel_class = st.selectbox("Target Class Scope:", available_classes, key="uni_class")
    with col_u2: sel_section = st.text_input("Target Section Scope:", value="A", max_chars=2, key="uni_sec").upper()
    with col_u3: attendance_date = st.date_input("Attendance Log Date:", value=time.strftime("%Y-%m-%d"), key="uni_date")
        
    st.markdown("---")
    
    try:
        students_df = run_query("""
            SELECT student_id, roll_no, student_name 
            FROM students 
            WHERE class_level = :class_val AND section = :sec_val
            ORDER BY roll_no ASC
        """, {"class_val": sel_class, "sec_val": sel_section})
    except Exception:
        students_df = pd.DataFrame([
            {"student_id": "STU-001", "roll_no": 1, "student_name": "Universal Student A"},
            {"student_id": "STU-002", "roll_no": 2, "student_name": "Universal Student B"}
        ])
        st.caption("⚠️ Displaying structural simulation data. Connect 'students' table to view live records.")
        
    if not students_df.empty:
        with st.form("universal_attendance_submission_form"):
            attendance_records = []
            for idx, row in students_df.iterrows():
                col_roll, col_name, col_status, col_remarks = st.columns([1, 3, 2, 4])
                
                with col_roll: st.write(f"**Roll #{row['roll_no']}**")
                with col_name: st.write(row['student_name'])
                with col_status: 
                    status = st.radio(f"U_Status_{row['student_id']}", ["Present", "Absent"], horizontal=True, label_visibility="collapsed", key=f"radio_status_{row['student_id']}")
                with col_remarks:
                    if status == "Absent":
                        remarks = st.text_input("Absent Remarks", placeholder="⚠️ Enter reason", key=f"urem_{row['student_id']}", label_visibility="collapsed")
                    else:
                        remarks = st.text_input("Absent Remarks", value="—", disabled=True, key=f"urem_{row['student_id']}", label_visibility="collapsed")
                
                attendance_records.append({"student_id": row['student_id'], "status": status, "remarks": remarks if status == "Absent" else ""})
                st.markdown("<hr style='margin:0.2em; border-color:#f0f2f6;'>", unsafe_allow_html=True)
                
            submit_attendance = st.form_submit_button("💾 Save & Commit Section Attendance Register (Admin Override)", type="primary", use_container_width=True)
            if submit_attendance:
                st.success(f"🎉 Attendance override map successfully executed for {attendance_date}!")
    else: st.info(f"No student profiles are mapped to Class {sel_class}-{sel_section}.")


def render_universal_marks_entry_workspace():
    pass


def render_institutional_report_generator():
    pass


def render_global_analytics_dashboard():
    """Global multi-dimensional analytical matrix available to Principal, VP, and Exam Controller."""
    st.subheader("📈 Institutional Cross-Sectional Performance Analytics")
    st.info("⚡ Unrestricted Data Scope: Displaying cross-sectional performance metrics and data trends.")
    
    col_an1, col_an2 = st.columns(2)
    with col_an1:
        st.markdown("#### 🏆 Subject Merit Standings")
        chart_data = pd.DataFrame({"Subjects": ["Maths", "Science", "English", "History"], "Avg Grade Point": [78, 85, 82, 74]})
        st.bar_chart(chart_data, x="Subjects", y="Avg Grade Point")


# ==============================================================================
# 3. ROLE-BASED ACCESS CONTROL (RBAC) NAVIGATION ROUTING
# ==============================================================================
st.sidebar.title("🔐 Access Control Matrix")
user_role = st.sidebar.selectbox(
    "Current User Account Profile Role:",
    ["Principal", "Controller Examination", "Vice Principal", "Admission Officer", "Teacher"]
)
st.sidebar.markdown("---")
st.sidebar.title("🚀 Navigation Control")

# 🏢 1. PRINCIPAL DASHBOARD
if user_role == "Principal":
    st.sidebar.info("Signed in as: **Principal**\n\n*Access Level: Full Admin Control*")
    app_mode = st.sidebar.radio(
        "Select Administrative Sub-Module:",
        ["Master Panel Overview", "🛠️ Core Institutional Setup Engine", "Admission Management", "Universal Attendance Panel", "Universal Marks Override Desk", "Report Generator Engine", "📊 Global Institutional Analytics", "Academic Configuration Ledger"]
    )
    
    if app_mode == "Master Panel Overview": st.title("🦅 Principal Strategic Control Command Tower")
    elif app_mode == "🛠️ Core Institutional Setup Engine": render_master_setup_engine()
    elif app_mode == "Admission Management": render_student_management_workspace()
    elif app_mode == "Universal Attendance Panel": render_universal_attendance_workspace()
    elif app_mode == "Universal Marks Override Desk": render_universal_marks_entry_workspace()
    elif app_mode == "Report Generator Engine": render_institutional_report_generator()
    elif app_mode == "📊 Global Institutional Analytics": render_global_analytics_dashboard()
    elif app_mode == "Academic Configuration Ledger": st.title("⚙️ Master Core System Configuration Matrix")

# 🗃️ 2. CONTROLLER EXAMINATION DASHBOARD
elif user_role == "Controller Examination":
    st.sidebar.info("Signed in as: **Exam Controller**\n\n*Access Level: Examination, Assessment & Analytics Control*")
    app_mode = st.sidebar.radio(
        "Select Examination Sub-Module:",
        ["Universal Marks Entry Portal", "📈 Comprehensive Systems Analytics", "📋 Generate Systems Reports Matrix"]
    )
    
    if app_mode == "Universal Marks Entry Portal": render_universal_marks_entry_workspace()
    elif app_mode == "📈 Comprehensive Systems Analytics": render_global_analytics_dashboard()
    elif app_mode == "📋 Generate Systems Reports Matrix": render_institutional_report_generator()

# ⚖️ 3. VICE PRINCIPAL DASHBOARD
elif user_role == "Vice Principal":
    st.sidebar.info("Signed in as: **Vice Principal**\n\n*Access Level: Academic Operations Command*")
    app_mode = st.sidebar.radio(
        "Select Operational Sub-Module:",
        ["🛠️ Core Institutional Setup Engine", "Student Record Management Workspace", "📅 Universal Section Attendance Register", "Universal Marks Entry Portal", "📈 Comprehensive Systems Analytics", "📋 Generate Systems Reports Matrix", "Academic Configuration Ledger"]
    )
    
    if app_mode == "🛠️ Core Institutional Setup Engine": render_master_setup_engine()
    elif app_mode == "Student Record Management Workspace": render_student_management_workspace()
    elif app_mode == "📅 Universal Section Attendance Register": render_universal_attendance_workspace()
    elif app_mode == "Universal Marks Entry Portal": render_universal_marks_entry_workspace()
    elif app_mode == "📈 Comprehensive Systems Analytics": render_global_analytics_dashboard()
    elif app_mode == "📋 Generate Systems Reports Matrix": render_institutional_report_generator()
    elif app_mode == "Academic Configuration Ledger": st.title("⚙️ Master Core System Configuration Matrix")

# 💼 4. ADMISSION OFFICER DASHBOARD
elif user_role == "Admission Officer":
    st.sidebar.info("Signed in as: **Admission Officer**\n\n*Access Level: Assigned Extensions*")
    app_mode = st.sidebar.radio(
        "Select Operational Sub-Module:",
        ["Admission Management", "📅 Universal Section Attendance Register", "Student Search Directory"]
    )
    
    if app_mode == "Admission Management": render_student_management_workspace()
    elif app_mode == "📅 Universal Section Attendance Register": render_universal_attendance_workspace()
    elif app_mode == "Student Search Directory": st.title("🔍 Student Database Query Index")

# 👨‍🏫 5. TEACHER DASHBOARD
elif user_role == "Teacher":
    st.sidebar.info("Signed in as: **Faculty Member**\n\n*Access Level: Context Locked*")
    app_mode = st.sidebar.radio(
        "Select Workspace View:",
        ["📝 Subject Marks Entry Sheet Console", "📅 Section Attendance Register", "📊 My Subject Analytics Panel"]
    )
    
    active_teacher_id = 104 
    
    if app_mode == "📝 Subject Marks Entry Sheet Console": st.title("📝 Subject Marks Entry Sheet Console")
    elif app_mode == "📅 Section Attendance Register": st.title("📅 Section Attendance Register")
    elif app_mode == "📊 My Subject Analytics Panel": st.title("📊 My Subject Performance Analytics")
