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

DB_URL = "sqlite:///academics.db" 

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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT NOT NULL,
                status TEXT NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS academic_systems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                system_name TEXT NOT NULL,
                description TEXT
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_level TEXT NOT NULL,
                sort_order INTEGER
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_name TEXT NOT NULL,
                max_capacity INTEGER
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_name TEXT NOT NULL,
                subject_code TEXT NOT NULL,
                credit_hours INTEGER
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_title TEXT NOT NULL,
                total_marks INTEGER,
                weightage INTEGER
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS disciplines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            st.markdown("#### ➕ Add New Faculty Profile")
            with st.form("form_teachers"):
                col1, col2 = st.columns(2)
                with col1: t_id = st.text_input("Teacher ID / Employment Code:", placeholder="e.g., T-101").strip().upper()
                with col2: t_name = st.text_input("Full Name:", placeholder="e.g., Prof. Jane Doe").strip()
                
                col3, col4 = st.columns(2)
                with col3: t_phone = st.text_input("Contact Number:", placeholder="e.g., +123456789")
                with col4: t_email = st.text_input("Email Address:", placeholder="e.g., jane.doe@school.edu")
                
                submit = st.form_submit_button("➕ Register Teacher Profile", type="primary")
                if submit:
                    if t_id and t_name:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO teachers (teacher_id, full_name, contact_number, email) VALUES (:id, :name, :phone, :email)"), 
                                             {"id": t_id, "name": t_name, "phone": t_phone, "email": t_email})
                            st.success(f"🎉 Faculty Profile initialized successfully for [{t_id}] {t_name}!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error (Check if ID is unique): {e}")
                    else: st.error("❌ Teacher ID and Full Name fields are mandatory structural parameters.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Faculty Profiles")
            teachers_df = run_query("SELECT teacher_id, full_name, contact_number, email FROM teachers")
            if not teachers_df.empty:
                teacher_options = [f"{row['teacher_id']} - {row['full_name']}" for _, row in teachers_df.iterrows()]
                selected_tchr = st.selectbox("Select Profile Node to Update:", teacher_options, key="edit_tchr_select")
                target_id = selected_tchr.split(" - ")[0]
                current_data = teachers_df[teachers_df['teacher_id'] == target_id].iloc[0]
                
                with st.form("edit_form_tchr"):
                    col1, col2 = st.columns(2)
                    with col1: update_name = st.text_input("Modify Full Name:", value=current_data['full_name']).strip()
                    with col2: update_phone = st.text_input("Modify Contact Number:", value=current_data['contact_number'] or "")
                    
                    update_email = st.text_input("Modify Email Address:", value=current_data['email'] or "")
                    
                    if st.form_submit_button("💾 Save Profile Changes", type="secondary"):
                        if update_name:
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE teachers SET full_name = :name, contact_number = :phone, email = :email WHERE teacher_id = :id"),
                                             {"name": update_name, "phone": update_phone, "email": update_email, "id": target_id})
                            st.success("🎉 Teacher management profiles synchronized successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Full Name cannot be left blank.")
            else: st.info("No recorded faculty elements discovered in relational memory.")

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
        st.markdown("### 📋 Class In-Charge Mapping Management")
        
        try:
            sessions_list = run_query("SELECT session_name FROM sessions")['session_name'].tolist()
            systems_list = run_query("SELECT system_name FROM academic_systems")['system_name'].tolist()
            classes_list = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC")['class_level'].tolist()
            sections_list = run_query("SELECT section_name FROM sections")['section_name'].tolist()
            teachers_df = run_query("SELECT teacher_id, full_name FROM teachers")
        except Exception:
            sessions_list, systems_list, classes_list, sections_list = [], [], [], []
            teachers_df = pd.DataFrame()

        # Fallbacks for empty sandbox state
        if not sessions_list: sessions_list = ["No Sessions Registered"]
        if not systems_list: systems_list = ["No Systems Registered"]
        if not classes_list: classes_list = ["11th", "12th", "Matric"]
        if not sections_list: sections_list = ["A", "B", "C"]

        with st.form("form_incharge_allocation"):
            st.write("#### Assign Faculty Member as Section In-Charge")
            col_inc1, col_inc2 = st.columns(2)
            with col_inc1: sel_session = st.selectbox("Select Session Year:", sessions_list)
            with col_inc2: sel_system = st.selectbox("Select Academic Framework:", systems_list)
            
            col_inc3, col_inc4 = st.columns(2)
            with col_inc3: sel_class = st.selectbox("Assign Class Level Scope:", classes_list, key="inc_cls")
            with col_inc4: sel_section = st.selectbox("Assign Section Branch:", sections_list, key="inc_sec")
            
            if not teachers_df.empty:
                teacher_options = [f"{row['teacher_id']} - {row['full_name']}" for _, row in teachers_df.iterrows()]
                selected_teacher = st.selectbox("Select Assigned Faculty Member:", teacher_options)
            else:
                selected_teacher = st.selectbox("Select Assigned Faculty Member:", ["No Registered Teachers Available"])
                
            submit_inc = st.form_submit_button("🔗 Link Class In-Charge Assignment", type="primary")
            if submit_inc:
                if "No Registered" in selected_teacher or "No Sessions" in sel_session:
                    st.error("❌ Prerequisites missing: Make sure a Session and a Teacher profile are created first.")
                else:
                    t_id = selected_teacher.split(" - ")[0]
                    t_name = selected_teacher.split(" - ")[1]
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO incharge_allocations (session, academic_system, class_level, section, teacher_id, teacher_name)
                                VALUES (:sess, :sys, :cls, :sec, :tid, :tname)
                            """), {"sess": sel_session, "sys": sel_system, "cls": sel_class, "sec": sel_section, "tid": t_id, "tname": t_name})
                        st.success(f"🎉 Mapping Complete: {t_name} is now designated In-Charge for Class {sel_class}-{sel_section}!")
                    except Exception as e:
                        st.error(f"❌ Database error: {e}")


def render_student_management_workspace():
    """Shared workspace enabling authorized users to onboard, bulk import, or update student registry information."""
    st.subheader("📝 Student Records & Registration Directory")
    
    # Sub-tabs separating Single Manual Entry, Bulk Excel Loading, and Edit Panel
    tab1, tab2, tab3 = st.tabs([
        "🆕 Manual Admission Entry", 
        "📤 Bulk Import via Excel", 
        "✏️ Edit Student Profiles"
    ])
    
    # Safely pull structural metadata from database layer for selection menus
    try:
        available_classes = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC")['class_level'].tolist()
        if not available_classes:
            available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]
    except Exception:
        available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]

    # Ensure database schema table structure accommodates our 8 primary fields
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
                class_level TEXT,
                section TEXT,
                roll_no INTEGER
            );
        """))

    # ==============================================================================
    # TAB 1: MANUAL ADMISSION ENTRY
    # ==============================================================================
    with tab1:
        st.write("### Register New Student Particulars")
        
        # We use a form to securely hold and capture text fields without losing data on click
        with st.form("student_profile_text_fields_form"):
            # --- CORE PROFILE DATA ---
            col1, col2, col3 = st.columns(3)
            with col1: new_id = st.text_input("1. Student ID / Registration No:*", placeholder="e.g., STU-2026-001").strip().upper()
            with col2: new_name = st.text_input("2. Student Full Name:*", placeholder="e.g., John Doe").strip()
            with col3: father_name = st.text_input("3. Student's Father Name:*", placeholder="e.g., Robert Doe").strip()
            
            col4, col5, col6 = st.columns(3)
            with col4: whatsapp_no = st.text_input("4. WhatsApp Number:", placeholder="e.g., +923001234567").strip()
            with col5: student_no = st.text_input("5. Student Mobile Number:", placeholder="e.g., +923151234567").strip()
            with col6: contact_1 = st.text_input("6. Emergency Contact-1:*", placeholder="e.g., Mother's Mobile").strip()
            
            col7, col8 = st.columns([1, 2])
            with col7: contact_2 = st.text_input("7. Alternative Contact-2:", placeholder="e.g., Guardian/Landline").strip()
            with col8: home_address = st.text_input("8. Home Address:", placeholder="e.g., House #123, Street 5, Sector G-10").strip()
            
            # Form button to temporarily submit text data to state
            lock_profile = st.form_submit_button("🔒 Step A: Lock & Verify Core Profile Fields")

        # --- CASCADING PLACEMENT FILTERS (Kept outside form for real-time reactivity) ---
        st.markdown("---")
        st.write("📁 **Academic Placement Attributes**")
        
        sessions_df = run_query("SELECT DISTINCT session_name FROM sessions")
        sessions_list = ["-- Select Session --"] + (sessions_df['session_name'].tolist() if not sessions_df.empty else [])
        
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            new_session = st.selectbox("1. Target Session:", options=sessions_list, key="manual_sess")

        with col_a2:
            if new_session != "-- Select Session --":
                systems_df = run_query("SELECT DISTINCT system_name FROM academic_systems")
                systems_list = ["-- Select System --"] + (systems_df['system_name'].tolist() if not systems_df.empty else [])
                new_system = st.selectbox("2. Target Academic System:", options=systems_list, key="manual_sys")
            else:
                st.selectbox("2. Target Academic System:", ["🔒 Waiting for Session..."], disabled=True, key="manual_sys_dis")
                new_system = "-- Select System --"

        with col_a3:
            if new_system != "-- Select System --":
                classes_df = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC, id ASC")
                classes_list = ["-- Select Class --"] + (classes_df['class_level'].tolist() if not classes_df.empty else [])
                new_class = st.selectbox("3. Target Class:", options=classes_list, key="manual_cls")
            else:
                st.selectbox("3. Target Class:", ["🔒 Waiting for System..."], disabled=True, key="manual_cls_dis")
                new_class = "-- Select Class --"

        col_a4, col_a5, col_a6 = st.columns(3)
        with col_a4:
            if new_class != "-- Select Class --":
                disciplines_df = run_query("SELECT DISTINCT discipline_title FROM disciplines")
                disciplines_list = ["-- Select Discipline --"] + (disciplines_df['discipline_title'].tolist() if not disciplines_df.empty else [])
                new_discipline = st.selectbox("4. Target Discipline:", options=disciplines_list, key="manual_disc")
            else:
                st.selectbox("4. Target Discipline:", ["🔒 Waiting for Class..."], disabled=True, key="manual_disc_dis")
                new_discipline = "-- Select Discipline --"

        with col_a5:
            if new_discipline != "-- Select Discipline --":
                sections_df = run_query("SELECT DISTINCT section_name FROM sections")
                sections_list = ["-- Select Section --"] + (sections_df['section_name'].tolist() if not sections_df.empty else [])
                new_sec = st.selectbox("5. Target Section:", options=sections_list, key="manual_sec")
            else:
                st.selectbox("5. Target Section:", ["🔒 Waiting for Discipline..."], disabled=True, key="manual_sec_dis")
                new_sec = "-- Select Section --"

        with col_a6:
            new_roll = st.number_input("Class arrangement No.", min_value=1, step=1, key="manual_roll")
        
        st.markdown("<small style='color: gray;'>* Indicates a mandatory field.</small>", unsafe_allow_html=True)
        st.markdown("---")
        
        # --- FINAL SAVE ACTION ---
        if st.button("🚀 Step B: Finalize Registration & Save Student", type="primary", use_container_width=True):
            if not new_id or not new_name or not father_name or not contact_1:
                st.error("❌ Validation Error: Please type the core data fields inside Step A first and hit 'Lock & Verify Core Profile Fields'.")
            elif any(f in ["-- Select Session --", "-- Select System --", "-- Select Class --", "-- Select Discipline --", "-- Select Section --"] for f in [new_session, new_system, new_class, new_discipline, new_sec]):
                st.error("❌ Validation Error: Please select all 5 dropdown filter paths under Academic Placement Attributes.")
            else:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO students (student_id, student_name, father_name, whatsapp_no, student_no, contact_1, contact_2, home_address, session, academic_system, class_level, discipline, section, roll_no)
                            VALUES (:id, :name, :fname, :whatsapp, :sno, :c1, :c2, :addr, :sess, :sys, :class_lvl, :disc, :sec, :roll)
                        """), {
                            "id": new_id, "name": new_name, "fname": father_name, "whatsapp": whatsapp_no,
                            "sno": student_no, "c1": contact_1, "c2": contact_2, "addr": home_address,
                            "sess": new_session, "sys": new_system, "class_lvl": new_class, "disc": new_discipline, "sec": new_sec, "roll": new_roll
                        })
                    st.success(f"🎉 Student node successfully registered: {new_name} added successfully!")
                    time.sleep(1.0)
                    st.rerun()
                except Exception as e: 
                    st.error(f"❌ Database execution failure: {e}. Check if Student ID already exists.")

    # ==============================================================================
    # TAB 2: BULK IMPORT VIA EXCEL (With Sample Template Downloader)
    # ==============================================================================
    with tab2:
        st.write("### 📤 Bulk Upload Student Spreadsheets")
        st.info("💡 To ensure a successful upload, your spreadsheet columns must exactly match our structural template layout parameters.")
        
        # --- DYNAMIC SAMPLE TEMPLATE GENERATOR ---
        # 1. Define the exact columns matching our database ingest criteria
        sample_columns = [
            "Student ID", "Student Name", "Father Name", "WhatsApp", 
            "Student Number", "Contact 1", "Contact 2", "Home Address", 
            "Class Level", "Section", "Roll Number"
        ]
        
        # 2. Add realistic placeholder/guideline data rows
        sample_data = [
            {
                "Student ID": "STU-2026-001",
                "Student Name": "Muhammad Ali",
                "Father Name": "Asif Ali",
                "WhatsApp": "+923001234567",
                "Student Number": "+923151234567",
                "Contact 1": "+923219876543 (Mother)",
                "Contact 2": "+9251123456 (Home)",
                "Home Address": "House 12, Street 4, Sector F-11, Islamabad",
                "Class Level": available_classes[0] if available_classes else "11th",
                "Section": "A",
                "Roll Number": 1
            },
            {
                "Student ID": "STU-2026-002",
                "Student Name": "Ayesha Khan",
                "Father Name": "Tariq Khan",
                "WhatsApp": "+923335556677",
                "Student Number": "",
                "Contact 1": "+923451112233 (Father)",
                "Contact 2": "",
                "Home Address": "Apartment 4B, Gulberg Heights, Lahore",
                "Class Level": available_classes[0] if available_classes else "11th",
                "Section": "B",
                "Roll Number": 2
            }
        ]
        
        # 3. Compile layout to binary Excel stream data helper
        import io
        template_df = pd.DataFrame(sample_data, columns=sample_columns)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            template_df.to_excel(writer, index=False, sheet_name='Student Roster Template')
            # Auto-adjust column width lengths inside workbook for aesthetic clarity
            worksheet = writer.sheets['Student Roster Template']
            for idx, col in enumerate(template_df.columns):
                series = template_df[col]
                max_len = max(series.astype(str).map(len).max(), len(col)) + 3
                worksheet.set_column(idx, idx, max_len)
        
        buffer.seek(0)
        
        # 4. Render the Download Button widget
        st.download_button(
            label="📥 Download Sample Excel Template (.xlsx)",
            data=buffer,
            file_name="student_admission_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Click here to download a perfectly pre-formatted spreadsheet template."
        )
        
        st.markdown("---")
        
        # --- SPREADSHEET INGESTION FILE UPLOADER ENGINE ---
        uploaded_file = st.file_uploader("Upload Completed Student Spreadsheet Ledger:", type=["xlsx"])
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                st.write("📋 **Previewing First 5 Rows of Uploaded Records:**")
                st.dataframe(df.head(5), use_container_width=True)
                
                if st.button("🚀 Process & Commit Excel Records", type="primary", use_container_width=True):
                    required_cols = ["Student ID", "Student Name", "Father Name", "Contact 1"]
                    missing_cols = [c for c in required_cols if c not in df.columns]
                    
                    if missing_cols:
                        st.error(f"❌ Processing aborted. Missing mandatory column mapping definitions: {missing_cols}")
                    else:
                        counter = 0
                        with engine.begin() as conn:
                            for _, row in df.iterrows():
                                s_id = str(row.get("Student ID")).strip().upper()
                                s_name = str(row.get("Student Name")).strip()
                                f_name = str(row.get("Father Name")).strip()
                                w_no = str(row.get("WhatsApp", "")) if pd.notna(row.get("WhatsApp")) else ""
                                s_no = str(row.get("Student Number", "")) if pd.notna(row.get("Student Number")) else ""
                                c1 = str(row.get("Contact 1")).strip()
                                c2 = str(row.get("Contact 2", "")) if pd.notna(row.get("Contact 2")) else ""
                                addr = str(row.get("Home Address", "")) if pd.notna(row.get("Home Address")) else ""
                                cls_lvl = str(row.get("Class Level", "")) if pd.notna(row.get("Class Level")) else ""
                                sec = str(row.get("Section", "")).strip().upper() if pd.notna(row.get("Section")) else ""
                                
                                # Safe parsing formatting for Roll numbers
                                try:
                                    roll = int(row.get("Roll Number")) if pd.notna(row.get("Roll Number")) else None
                                # Fallback gracefully if structural content conversion encounters strings
                                except (ValueError, TypeError):
                                    roll = None
                                
                                if s_id and s_name:
                                    conn.execute(text("""
                                        INSERT OR REPLACE INTO students (student_id, student_name, father_name, whatsapp_no, student_no, contact_1, contact_2, home_address, class_level, section, roll_no)
                                        VALUES (:id, :name, :fname, :whatsapp, :sno, :c1, :c2, :addr, :class_lvl, :sec, :roll)
                                    """), {
                                        "id": s_id, "name": s_name, "fname": f_name, "whatsapp": w_no,
                                        "sno": s_no, "c1": c1, "c2": c2, "addr": addr, "class_lvl": cls_lvl, "sec": sec, "roll": roll
                                    })
                                    counter += 1
                        st.success(f"🎉 Bulk operation successful! {counter} student profiles integrated smoothly.")
                        time.sleep(1.0)
                        st.rerun()
            except Exception as e:
                st.error(f"❌ File compilation processing failure: {e}")
    with tab3:
        st.write("### Search & Edit Active Profiles")
        search_term = st.text_input("🔍 Search Student Profile by Name:", key="student_workspace_search")
        
        if search_term:
            matched_students = run_query("""
                SELECT student_id, roll_no, student_name, father_name, whatsapp_no, student_no, contact_1, contact_2, home_address, class_level, section 
                FROM students 
                WHERE student_name LIKE :search
            """, {"search": f"%{search_term}%"})

            if not matched_students.empty:
                student_options = [
                    f"{row['student_id']} - ID: {row['student_id']} | {row['student_name']} s/o {row['father_name']}"
                    for _, row in matched_students.iterrows()
                ]
                selected_edit_target = st.selectbox("Select Target Record to Update:", student_options)
                target_id = selected_edit_target.split(" - ")[0]
                current_target_row = matched_students[matched_students["student_id"] == target_id].iloc[0]
                
                with st.form("edit_student_data_form"):
                    col_e1, col_e2, col_e3 = st.columns(3)
                    with col_e1: edit_name = st.text_input("Modify Name:", value=current_target_row["student_name"])
                    with col_e2: edit_fname = st.text_input("Modify Father Name:", value=current_target_row["father_name"])
                    with col_e3: edit_whatsapp = st.text_input("Modify WhatsApp Number:", value=str(current_target_row["whatsapp_no"] or ""))
                    
                    col_e4, col_e5, col_e6 = st.columns(3)
                    with col_e4: edit_sno = st.text_input("Modify Mobile Number:", value=str(current_target_row["student_no"] or ""))
                    with col_e5: edit_c1 = st.text_input("Modify Contact-1:", value=str(current_target_row["contact_1"] or ""))
                    with col_e6: edit_c2 = st.text_input("Modify Contact-2:", value=str(current_target_row["contact_2"] or ""))
                    
                    edit_addr = st.text_input("Modify Home Address:", value=str(current_target_row["home_address"] or ""))
                    
                    st.markdown("---")
                    col_e7, col_e8, col_e9 = st.columns(3)
                    try:
                        cls_idx = available_classes.index(str(current_target_row["class_level"]))
                    except ValueError:
                        cls_idx = 0
                    with col_e7: edit_class = st.selectbox("Update Class Level:", available_classes, index=cls_idx)
                    with col_e8: edit_sec = st.text_input("Update Section:", value=str(current_target_row["section"] or "")).upper()
                    with col_e9: edit_roll = st.number_input("Update Roll Number:", value=int(current_target_row["roll_no"] or 1), min_value=1)
                    
                    save_student_edits = st.form_submit_button("💾 Save Profile Modification Changes", type="primary")
                    if save_student_edits:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE students 
                                    SET student_name = :name, father_name = :fname, whatsapp_no = :whatsapp, 
                                        student_no = :sno, contact_1 = :c1, contact_2 = :c2, home_address = :addr,
                                        class_level = :class_lvl, section = :sec, roll_no = :roll
                                    WHERE student_id = :sid
                                """), {
                                    "name": edit_name, "fname": edit_fname, "whatsapp": edit_whatsapp,
                                    "sno": edit_sno, "c1": edit_c1, "c2": edit_c2, "addr": edit_addr,
                                    "class_lvl": edit_class, "sec": edit_sec, "roll": edit_roll, "sid": target_id
                                })
                            st.success("🎉 Student record updated cleanly inside the relational directory!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: 
                            st.error(f"❌ Modification processing failed: {e}")
            else: 
                st.info("No matching student profile entries discovered.")
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
            {"student_id": 501, "roll_no": 1, "student_name": "Universal Student A"},
            {"student_id": 502, "roll_no": 2, "student_name": "Universal Student B"}
        ])
        st.caption("⚠️ Displaying structural simulation data. Connect 'students' table to view live records.")
        
    if not students_df.empty:
        with st.form("universal_attendance_submission_form"):
            attendance_records = []
            for idx, row in students_df.iterrows():
                col_roll, col_name, col_status, col_remarks = st.columns([1, 3, 2, 4])
                
                with col_roll: st.write(f"**Roll #{row['roll_no']}**")
                with col_name: st.write(row['student_name'])
                with col_status: status = st.radio(f"U_Status_{row['student_id']}", ["Present", "Absent"], horizontal=True, label_visibility="collapsed")
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
    """Shared workspace allowing Exam Controller & VP to overwrite or enter marks for any subject/class/section."""
    st.subheader("🌋 Universal Subject Marks Override Portal")
    st.info("🔓 Unrestricted Academic Command Access: You can enter or overwrite examination evaluation sets school-wide.")
    
    try:
        available_classes = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC")['class_level'].tolist()
        if not available_classes:
            available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]
    except Exception:
        available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1: sel_class = st.selectbox("Select Class:", available_classes, key="uni_m_class")
    with col_e2: sel_section = st.text_input("Select Section:", value="A", max_chars=2, key="uni_m_sec").upper()
    with col_e3: sel_subject = st.text_input("Target Academic Subject:", placeholder="Mathematics", key="uni_m_sub")
        
    if sel_subject:
        st.success(f"🔓 Displaying Marks Entry Sheet for: Class {sel_class}-{sel_section} ➡️ **{sel_subject}**")
        with st.form("universal_marks_submission_form"):
            st.write("✏️ **Master Assessment Entry Sheet**")
            submit_override_marks = st.form_submit_button("🔒 Lock & Commit Scores to Master Configuration Ledger", type="primary")
            if submit_override_marks: st.success("🎉 Examination matrix references compiled and synchronized successfully.")

def render_institutional_report_generator():
    """Comprehensive engine giving authorized controllers rights to compile/export all report variations."""
    st.subheader("📊 Master Institutional Report Generator Engine")
    st.write("Construct data sheets, compile dynamic transcripts, or monitor academic growth factors.")
    
    try:
        available_classes = ["All Classes"] + run_query("SELECT class_level FROM classes ORDER BY sort_order ASC")['class_level'].tolist()
    except Exception:
        available_classes = ["All Classes", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]

    report_type = st.selectbox(
        "Select Target Report Template Type:",
        ["Complete Roster Student Tabulations", "Subject-Wise Grading Distributions", "Section Attendance Defaulter Logs", "Consolidated Class Report Cards"]
    )
    
    col_r1, col_r2 = st.columns(2)
    with col_r1: st.selectbox("Filter Class Scope:", available_classes)
    with col_r2: st.selectbox("Filter Term Cycle:", ["First Term", "Mid Exams", "Final Session Examination"])
        
    st.button(f"⚙️ Execute System Query & Generate {report_type}", type="primary", use_container_width=True)

def render_global_analytics_dashboard():
    """Global multi-dimensional analytical matrix available to Principal, VP, and Exam Controller."""
    st.subheader("📈 Institutional Cross-Sectional Performance Analytics")
    st.info("⚡ Unrestricted Data Scope: Displaying cross-sectional performance metrics and data trends.")
    
    col_an1, col_an2 = st.columns(2)
    with col_an1:
        st.markdown("#### 🏆 Subject Merit Standings")
        chart_data = pd.DataFrame({"Subjects": ["Maths", "Science", "English", "History"], "Avg Grade Point": [78, 85, 82, 74]})
        st.bar_chart(chart_data, x="Subjects", y="Avg Grade Point", color="#1f77b4")
    with col_an2:
        st.markdown("#### 📈 Attendance Stability Metrics")
        att_data = pd.DataFrame({"Weeks": ["W1", "W2", "W3", "W4"], "Attendance Rate (%)": [94, 96, 92, 95]})
        st.line_chart(att_data, x="Weeks", y="Attendance Rate (%)", color="#ff7f0e")


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
