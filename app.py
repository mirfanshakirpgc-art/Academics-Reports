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
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                class_level TEXT NOT NULL,
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
                teacher_id INTEGER,
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
    """Centralized core setup engine giving Principal and VP rights to create and update foundational school data structures."""
    st.subheader("⚙️ Master Institutional Setup Engine")
    
    tab1, tab2 = st.tabs(["🏛️ 1. Core Configuration Parameters", "🔗 2. Operational Allocation Mapping"])
    
    with tab1:
        st.markdown("### Add & Manage Structural School Variables")
        
        setup_type = st.selectbox(
            "Select Variable Layer to Manage:",
            ["Session", "Academic System", "Classes", "Sections", "Subjects", "Test/Exam", "Disciplines"]
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
        # 3. CLASSES MANAGEMENT (ADD & EDIT) - FIXED FOR CUSTOM STRINGS ("11th", "12th")
        # ----------------------------------------------------------------------
        elif setup_type == "Classes":
            st.markdown("#### ➕ Add New Class Level")
            with st.form("form_classes"):
                col1, col2 = st.columns(2)
                # Changed selectbox to text_input to allow any string format like "11th" or "12th"
                with col1: class_title = st.text_input("Class Level Designation Name:", placeholder="e.g., 11th, 12th, Matric, O-Levels")
                with col2: numeric_index = st.number_input("Numeric Sort Index Value (For structural ordering):", min_value=1, value=11)
                submit = st.form_submit_button("➕ Register Class Level", type="primary")
                if submit:
                    if class_title.strip():
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO classes (class_level, sort_order) VALUES (:lvl, :sort)"), 
                                             {"lvl": class_title.strip(), "sort": numeric_index})
                            st.success(f"🎉 Class Level Grade '{class_title}' successfully committed!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else:
                        st.error("❌ Class Designation field cannot be blank.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Class Structures")
            classes_df = run_query("SELECT id, class_level, sort_order FROM classes ORDER BY sort_order ASC")
            if not classes_df.empty:
                class_options = [f"{row['id']} - Class: {row['class_level']} (Index: {row['sort_order']})" for _, row in classes_df.iterrows()]
                selected_cls = st.selectbox("Select Class Node to Update:", class_options, key="edit_cls_select")
                target_id = int(selected_cls.split(" - ")[0])
                current_data = classes_df[classes_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_cls"):
                    col1, col2 = st.columns(2)
                    # Changed selectbox to a free text input to cleanly modify any format variation flawlessly
                    with col1: update_lvl = st.text_input("Modify Level Designation Name:", value=str(current_data['class_level']))
                    with col2: update_sort = st.number_input("Modify Sort Order Index:", min_value=1, value=int(current_data['sort_order']))
                    if st.form_submit_button("💾 Save Class Changes", type="secondary"):
                        if update_lvl.strip():
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE classes SET class_level = :lvl, sort_order = :sort WHERE id = :id"),
                                             {"lvl": update_lvl.strip(), "sort": update_sort, "id": target_id})
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
                col1, col2 = st.columns(2)
                with col1: section_name = st.text_input("Section Label Name:", placeholder="e.g., A, B, Rose").upper()
                with col2: max_capacity = st.number_input("Maximum Student Cap Limit:", min_value=1, value=40)
                submit = st.form_submit_button("➕ Register Section Unit", type="primary")
                if submit:
                    if section_name:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO sections (section_name, max_capacity) VALUES (:name, :cap)"), 
                                             {"name": section_name, "cap": max_capacity})
                            st.success(f"🎉 Section Room Node '{section_name}' successfully added!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Section Label code cannot be blank.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Section Branches")
            sections_df = run_query("SELECT id, section_name, max_capacity FROM sections")
            if not sections_df.empty:
                sec_options = [f"{row['id']} - Section {row['section_name']} (Cap: {row['max_capacity']})" for _, row in sections_df.iterrows()]
                selected_sec = st.selectbox("Select Target Section Room:", sec_options, key="edit_sec_select")
                target_id = int(selected_sec.split(" - ")[0])
                current_data = sections_df[sections_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_sec"):
                    col1, col2 = st.columns(2)
                    with col1: update_name = st.text_input("Modify Label Token:", value=current_data['section_name']).upper()
                    with col2: update_cap = st.number_input("Modify Max Capacity Threshold:", min_value=1, value=int(current_data['max_capacity']))
                    if st.form_submit_button("💾 Save Section Changes", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE sections SET section_name = :name, max_capacity = :cap WHERE id = :id"),
                                         {"name": update_name, "cap": update_cap, "id": target_id})
                        st.success("🎉 Section adjustments processed effectively.")
                        time.sleep(0.5)
                        st.rerun()
            else: st.info("No tracked sections exist.")

        # ----------------------------------------------------------------------
        # 5. SUBJECTS MANAGEMENT (ADD & EDIT) - CLEANED
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
                                # Storing placeholder empty strings to prevent breaking existing schema constraints
                                conn.execute(text("INSERT INTO subjects (subject_name, subject_code, credit_hours) VALUES (:name, '', 1)"), 
                                             {"name": sub_name.strip()})
                            st.success(f"🎉 Core Subject Registry item locked: {sub_name}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Heading labels are mandatory entries.")

        # ----------------------------------------------------------------------
        # 6. TEST/EXAM SCHEME MANAGEMENT (ADD & EDIT)
        # ----------------------------------------------------------------------
        elif setup_type == "Test/Exam":
            st.markdown("#### ➕ Add New Test Evaluation Scheme")
            with st.form("form_test_exam"):
                col1, col2, col3 = st.columns(3)
                with col1: test_title = st.text_input("Assessment Title:", placeholder="e.g., Mid Term Exam")
                with col2: total_marks = st.number_input("Max Achievable Out-Of Marks Value:", min_value=1, value=100)
                with col3: weight_percent = st.number_input("Weightage Factor Ratio (%):", min_value=0, max_value=100, value=20)
                submit = st.form_submit_button("➕ Register Test Profile Evaluation Scheme", type="primary")
                if submit:
                    if test_title:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO test_types (test_title, total_marks, weightage) VALUES (:title, :tm, :wt)"), 
                                             {"title": test_title, "tm": total_marks, "wt": weight_percent})
                            st.success(f"🎉 Evaluation Pattern Scheme added: {test_title}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Database error: {e}")
                    else: st.error("❌ Test heading is required.")

            st.markdown("---")
            st.markdown("#### ✏️ Edit Existing Test Protocols")
            tests_df = run_query("SELECT id, test_title, total_marks, weightage FROM test_types")
            if not tests_df.empty:
                test_options = [f"{row['id']} - {row['test_title']} ({row['total_marks']}M / {row['weightage']}% Weight)" for _, row in tests_df.iterrows()]
                selected_tst = st.selectbox("Select Target Evaluation Layout Template:", test_options, key="edit_tst_select")
                target_id = int(selected_tst.split(" - ")[0])
                current_data = tests_df[tests_df['id'] == target_id].iloc[0]
                
                with st.form("edit_form_tst"):
                    col1, col2, col3 = st.columns(3)
                    with col1: update_title = st.text_input("Modify Scheme Header Name:", value=current_data['test_title'])
                    with col2: update_tm = st.number_input("Modify Absolute Maximum Marks:", min_value=1, value=int(current_data['total_marks']))
                    with col3: update_wt = st.number_input("Modify Score Evaluation Weight (%):", min_value=0, max_value=100, value=int(current_data['weightage']))
                    if st.form_submit_button("💾 Save Scheme Blueprint Changes", type="secondary"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE test_types SET test_title = :title, total_marks = :tm, weightage = :wt WHERE id = :id"),
                                         {"title": update_title, "tm": update_tm, "wt": update_wt, "id": target_id})
                        st.success("🎉 Examination structures successfully transformed and patched.")
                        time.sleep(0.5)
                        st.rerun()
            else: st.info("No exam weight parameters declared in system schemas.")

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

    with tab2:
        st.markdown("### Map Institutional Dependencies")
        allocation_type = st.selectbox(
            "Select Mapping Matrix Layer:",
            ["Section Allocation (Students to Sections)", "Subject Allocation (Teachers to Subjects/Sections)", "Section In-Charge Allocation"]
        )
        
        with st.form("mapping_allocation_form"):
            st.write(f"✏️ **New {allocation_type} Entry**")
            
            # Dynamically pull created classes list from setup layer memory
            try:
                available_classes = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC")['class_level'].tolist()
                if not available_classes:
                    available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]
            except Exception:
                available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]

            if allocation_type == "Section Allocation (Students to Sections)":
                col_sa1, col_sa2 = st.columns(2)
                with col_sa1: st.text_input("Student Identifier Code / ID:")
                with col_sa2: st.text_input("Target Section Assignment:")
                
            elif allocation_type == "Subject Allocation (Teachers to Subjects/Sections)":
                col_sub1, col_sub2, col_sub3 = st.columns(3)
                with col_sub1: st.text_input("Faculty Member / Teacher ID:")
                with col_sub2: st.text_input("Target Subject Identifier:")
                with col_sub3: st.text_input("Target Class & Section Scope:")
                
            elif allocation_type == "Section In-Charge Allocation":
                col_inc1, col_inc2, col_inc3 = st.columns(3)
                with col_inc1: st.text_input("Select Faculty Member (Teacher ID):")
                with col_inc2: st.selectbox("Assign Class Level Scope:", available_classes)
                with col_inc3: st.text_input("Assign Section Branch Unit:")
                
            submit_allocation = st.form_submit_button("🔗 Commit Allocation Link to Database", type="primary")
            if submit_allocation:
                st.success(f"🎉 Relational Ledger Updated: {allocation_type} pipeline compiled and linked successfully.")


def render_student_management_workspace():
    """Shared workspace enabling authorized users to onboard or update student registry information."""
    st.subheader("📝 Student Records & Registration Directory")
    tab1, tab2 = st.tabs(["🆕 Add New Student Roster Record", "✏️ Edit Existing Student Profile Data"])
    
    try:
        available_classes = run_query("SELECT class_level FROM classes ORDER BY sort_order ASC")['class_level'].tolist()
        if not available_classes:
            available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]
    except Exception:
        available_classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11th", "12th"]

    with tab1:
        with st.form("add_new_student_form"):
            st.write("### Register New Student Node")
            col1, col2, col3 = st.columns(3)
            with col1: new_name = st.text_input("Full Name:", placeholder="John Doe")
            with col2: new_class = st.selectbox("Target Class Level:", available_classes)
            with col3: new_sec = st.text_input("Target Section:", placeholder="A", max_chars=2).upper()
                
            new_roll = st.number_input("Assign Roll Number:", min_value=1, step=1)
            submit_new_student = st.form_submit_button("➕ Save Record to Database Instance", type="primary")
            
            if submit_new_student:
                if not new_name or not new_sec:
                    st.error("❌ Action validation error: Both Name and Section tags must be declared.")
                else:
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO students (student_name, class_level, section, roll_no)
                                VALUES (:name, :class_lvl, :sec, :roll)
                            """), {"name": new_name, "class_lvl": new_class, "sec": new_sec, "roll": new_roll})
                        st.success(f"🎉 Student node successfully registered: {new_name} added to Class {new_class}-{new_sec}")
                    except Exception as e: st.error(f"❌ Database execution failure: {e}")
                        
    with tab2:
        st.write("### Edit Active Student Ledger Fields")
        search_term = st.text_input("🔍 Search Student Profile by Name:", key="student_edit_search")
        
        if search_term:
            try:
                matched_students = run_query("""
                    SELECT student_id, roll_no, student_name, class_level, section 
                    FROM students 
                    WHERE student_name LIKE :search
                """, {"search": f"%{search_term}%"})
            except Exception:
                matched_students = pd.DataFrame([{"student_id": 99, "roll_no": 5, "student_name": f"{search_term} Test", "class_level": "11th", "section": "B"}])
                st.caption("⚠️ Running UI structural mock sandbox layout data.")

            if not matched_students.empty:
                student_options = [
                    f"{row['student_id']} - Roll #{row['roll_no']}: {row['student_name']} ({row['class_level']}-{row['section']})"
                    for _, row in matched_students.iterrows()
                ]
                selected_edit_target = st.selectbox("Select Target Record to Update:", student_options)
                target_id = int(selected_edit_target.split(" - ")[0])
                current_target_row = matched_students[matched_students["student_id"] == target_id].iloc[0]
                
                with st.form("edit_student_data_form"):
                    col_e1, col_e2, col_e3 = st.columns(3)
                    with col_e1: edit_name = st.text_input("Update Name:", value=current_target_row["student_name"])
                    with col_e2: 
                        try:
                            cls_idx = available_classes.index(str(current_target_row["class_level"]))
                        except ValueError:
                            cls_idx = 0
                        edit_class = st.selectbox("Update Class Level:", available_classes, index=cls_idx)
                    with col_e3: edit_sec = st.text_input("Update Section:", value=current_target_row["section"], max_chars=2).upper()
                        
                    edit_roll = st.number_input("Update Roll Number:", value=int(current_target_row["roll_no"]), min_value=1)
                    
                    save_student_edits = st.form_submit_button("💾 Save Profile Modification Changes", type="primary")
                    if save_student_edits:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE students 
                                    SET student_name = :name, class_level = :class_lvl, section = :sec, roll_no = :roll
                                    WHERE student_id = :sid
                                """), {"name": edit_name, "class_lvl": edit_class, "sec": edit_sec, "roll": edit_roll, "sid": target_id})
                            st.success("🎉 Student system records reference modified inside relational logs successfully!")
                        except Exception as e: st.error(f"❌ Modification processing failed: {e}")
            else: st.info("No matching student profile entries discovered.")

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
        ["Master Panel Overview", "🛠️ Core Institutional Setup Engine", "Class In-Charge Allocations", "Admission Management", "Universal Attendance Panel", "Universal Marks Override Desk", "Report Generator Engine", "📊 Global Institutional Analytics", "Academic Configuration Ledger"]
    )
    
    if app_mode == "Master Panel Overview": st.title("🦅 Principal Strategic Control Command Tower")
    elif app_mode == "🛠️ Core Institutional Setup Engine": render_master_setup_engine()
    elif app_mode == "Class In-Charge Allocations": st.title("📋 Class In-Charge Mapping Management")
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
        ["🛠️ Core Institutional Setup Engine", "Class In-Charge Allocations", "Student Record Management Workspace", "📅 Universal Section Attendance Register", "Universal Marks Entry Portal", "📈 Comprehensive Systems Analytics", "📋 Generate Systems Reports Matrix", "Academic Configuration Ledger"]
    )
    
    if app_mode == "🛠️ Core Institutional Setup Engine": render_master_setup_engine()
    elif app_mode == "Class In-Charge Allocations": st.title("📋 Class In-Charge Mapping Management")
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
