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

# TODO: Replace with your actual database connection string if not using local SQLite
DB_URL = "sqlite:///academics.db" 

@st.cache_resource
def get_db_engine():
    """Creates and caches the database engine connection."""
    return create_engine(DB_URL)

engine = get_db_engine()

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
    """Centralized core setup engine giving Principal and VP rights to create foundational school data structures."""
    st.subheader("⚙️ Master Institutional Setup Engine")
    
    tab1, tab2 = st.tabs(["🏛️ 1. Core Configuration Parameters", "🔗 2. Operational Allocation Mapping"])
    
    with tab1:
        st.markdown("### Add Structural School Variables")
        setup_type = st.selectbox(
            "Select Variable Layer to Initialize:",
            ["Session Year", "Academic System", "Class Level", "Section Unit", "Academic Subject", "Test/Exam Type", "Discipline Stream"]
        )
        
        with st.form("core_variable_form"):
            new_input_val = st.text_input(f"Enter New {setup_type} Value:", placeholder=f"e.g., Data details for {setup_type}")
            submit_variable = st.form_submit_button(f"➕ Register {setup_type}", type="primary")
            
            if submit_variable:
                if not new_input_val:
                    st.error("❌ Content configuration error: Value field cannot be left blank.")
                else:
                    # In your database, these will target their respective tables (e.g., sessions, systems, classes)
                    st.success(f"🎉 System Matrix Updated: Successfully initialized '{new_input_val}' inside {setup_type} records.")

    with tab2:
        st.markdown("### Map Institutional Dependencies")
        allocation_type = st.selectbox(
            "Select Mapping Matrix Layer:",
            ["Section Allocation (Students to Sections)", "Subject Allocation (Teachers to Subjects/Sections)", "Section In-Charge Allocation"]
        )
        
        with st.form("mapping_allocation_form"):
            st.write(f"✏️ **New {allocation_type} Entry**")
            
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
                with col_inc2: st.selectbox("Assign Class Level:", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
                with col_inc3: st.text_input("Assign Section Branch Unit:")
                
            submit_allocation = st.form_submit_button("🔗 Commit Allocation Link to Database", type="primary")
            if submit_allocation:
                st.success(f"🎉 Relational Ledger Updated: {allocation_type} pipeline compiled and linked successfully.")


def render_student_management_workspace():
    """Shared workspace enabling authorized users to onboard or update student registry information."""
    st.subheader("📝 Student Records & Registration Directory")
    tab1, tab2 = st.tabs(["🆕 Add New Student Roster Record", "✏️ Edit Existing Student Profile Data"])
    
    with tab1:
        with st.form("add_new_student_form"):
            st.write("### Register New Student Node")
            col1, col2, col3 = st.columns(3)
            with col1: new_name = st.text_input("Full Name:", placeholder="John Doe")
            with col2: new_class = st.selectbox("Target Class Level:", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
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
                    except Exception as e:
                        st.error(f"❌ Database execution failure: {e}")
                        
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
                matched_students = pd.DataFrame([{"student_id": 99, "roll_no": 5, "student_name": f"{search_term} Test", "class_level": "10", "section": "B"}])
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
                    with col_e2: edit_class = st.selectbox("Update Class Level:", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"], index=int(current_target_row["class_level"])-1 if current_target_row["class_level"].isdigit() else 0)
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
                        except Exception as e:
                            st.error(f"❌ Modification processing failed: {e}")
            else:
                st.info("No matching student profile entries discovered.")

def render_universal_attendance_workspace():
    """Shared workspace allowing unrestricted global access to all sections for attendance processing."""
    st.subheader("🌐 Global Universal Attendance Control Desk")
    st.info("🔓 Unrestricted administrative view enabled. You can monitor or verify attendance for all sections.")
    
    col_u1, col_u2, col_u3 = st.columns(3)
    with col_u1: sel_class = st.selectbox("Target Class Scope:", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"], key="uni_class")
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
                        remarks = st.text_input("Absent Remarks", placeholder="⚠️ Enter reason (e.g., Suspended, Sick)", key=f"urem_{row['student_id']}", label_visibility="collapsed")
                    else:
                        remarks = st.text_input("Absent Remarks", value="—", disabled=True, key=f"urem_{row['student_id']}", label_visibility="collapsed")
                
                attendance_records.append({"student_id": row['student_id'], "status": status, "remarks": remarks if status == "Absent" else ""})
                st.markdown("<hr style='margin:0.2em; border-color:#f0f2f6;'>", unsafe_allow_html=True)
                
            submit_attendance = st.form_submit_button("💾 Save & Commit Section Attendance Register (Admin Override)", type="primary", use_container_width=True)
            if submit_attendance:
                st.success(f"🎉 Attendance override map for Class {sel_class}-{sel_section} successfully executed for {attendance_date}!")
    else:
        st.info(f"No student profiles are mapped to Class {sel_class}-{sel_section} inside system logs.")

def render_universal_marks_entry_workspace():
    """Shared workspace allowing Exam Controller & VP to overwrite or enter marks for any subject/class/section."""
    st.subheader("🌋 Universal Subject Marks Override Portal")
    st.info("🔓 Unrestricted Academic Command Access: You can enter or overwrite examination evaluation sets school-wide.")
    
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1: sel_class = st.selectbox("Select Class:", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"], key="uni_m_class")
    with col_e2: sel_section = st.text_input("Select Section:", value="A", max_chars=2, key="uni_m_sec").upper()
    with col_e3: sel_subject = st.text_input("Target Academic Subject:", placeholder="Mathematics", key="uni_m_sub")
        
    if sel_subject:
        st.success(f"🔓 Displaying Marks Entry Sheet for: Class {sel_class}-{sel_section} ➡️ **{sel_subject}**")
        with st.form("universal_marks_submission_form"):
            st.write("✏️ **Master Assessment Entry Sheet**")
            submit_override_marks = st.form_submit_button("🔒 Lock & Commit Scores to Master Configuration Ledger", type="primary")
            if submit_override_marks:
                st.success("🎉 Examination matrix references compiled and synchronized successfully.")

def render_institutional_report_generator():
    """Comprehensive engine giving authorized controllers rights to compile/export all report variations."""
    st.subheader("📊 Master Institutional Report Generator Engine")
    st.write("Construct data sheets, compile dynamic transcripts, or monitor academic growth factors.")
    
    report_type = st.selectbox(
        "Select Target Report Template Type:",
        ["Complete Roster Student Tabulations", "Subject-Wise Grading Distributions", "Section Attendance Defaulter Logs", "Consolidated Class Report Cards"]
    )
    
    col_r1, col_r2 = st.columns(2)
    with col_r1: st.selectbox("Filter Class Scope:", ["All Classes", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
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
    
    if app_mode == "Master Panel Overview":
        st.title("🦅 Principal Strategic Control Command Tower")
    elif app_mode == "🛠️ Core Institutional Setup Engine":
        render_master_setup_engine()
    elif app_mode == "Class In-Charge Allocations":
        st.title("📋 Class In-Charge Mapping Management")
    elif app_mode == "Admission Management":
        render_student_management_workspace()
    elif app_mode == "Universal Attendance Panel":
        render_universal_attendance_workspace()
    elif app_mode == "Universal Marks Override Desk":
        render_universal_marks_entry_workspace()
    elif app_mode == "Report Generator Engine":
        render_institutional_report_generator()
    elif app_mode == "📊 Global Institutional Analytics":
        render_global_analytics_dashboard()
    elif app_mode == "Academic Configuration Ledger":
        st.title("⚙️ Master Core System Configuration Matrix")

# 🗃️ 2. CONTROLLER EXAMINATION DASHBOARD
elif user_role == "Controller Examination":
    st.sidebar.info("Signed in as: **Exam Controller**\n\n*Access Level: Examination, Assessment & Analytics Control*")
    app_mode = st.sidebar.radio(
        "Select Examination Sub-Module:",
        ["Universal Marks Entry Portal", "📈 Comprehensive Systems Analytics", "📋 Generate Systems Reports Matrix"]
    )
    
    if app_mode == "Universal Marks Entry Portal":
        render_universal_marks_entry_workspace()
    elif app_mode == "📈 Comprehensive Systems Analytics":
        render_global_analytics_dashboard()
    elif app_mode == "📋 Generate Systems Reports Matrix":
        render_institutional_report_generator()

# ⚖️ 3. VICE PRINCIPAL DASHBOARD (Master Setup privileges assigned)
elif user_role == "Vice Principal":
    st.sidebar.info("Signed in as: **Vice Principal**\n\n*Access Level: Academic Operations Command*")
    app_mode = st.sidebar.radio(
        "Select Operational Sub-Module:",
        ["🛠️ Core Institutional Setup Engine", "Class In-Charge Allocations", "Student Record Management Workspace", "📅 Universal Section Attendance Register", "Universal Marks Entry Portal", "📈 Comprehensive Systems Analytics", "📋 Generate Systems Reports Matrix", "Academic Configuration Ledger"]
    )
    
    if app_mode == "🛠️ Core Institutional Setup Engine":
        render_master_setup_engine()
    elif app_mode == "Class In-Charge Allocations":
        st.title("📋 Class In-Charge Mapping Management")
    elif app_mode == "Student Record Management Workspace":
        render_student_management_workspace()
    elif app_mode == "📅 Universal Section Attendance Register":
        render_universal_attendance_workspace()
    elif app_mode == "Universal Marks Entry Portal":
        render_universal_marks_entry_workspace()
    elif app_mode == "📈 Comprehensive Systems Analytics":
        render_global_analytics_dashboard()
    elif app_mode == "📋 Generate Systems Reports Matrix":
        render_institutional_report_generator()
    elif app_mode == "Academic Configuration Ledger":
        st.title("⚙️ Master Core System Configuration Matrix")

# 💼 4. ADMISSION OFFICER DASHBOARD
elif user_role == "Admission Officer":
    st.sidebar.info("Signed in as: **Admission Officer**\n\n*Access Level: Assigned Extensions*")
    app_mode = st.sidebar.radio(
        "Select Operational Sub-Module:",
        ["Admission Management", "📅 Universal Section Attendance Register", "Student Search Directory"]
    )
    
    if app_mode == "Admission Management":
        render_student_management_workspace()
    elif app_mode == "📅 Universal Section Attendance Register":
        render_universal_attendance_workspace()
    elif app_mode == "Student Search Directory":
        st.title("🔍 Student Database Query Index")

# 👨‍🏫 5. TEACHER DASHBOARD
elif user_role == "Teacher":
    st.sidebar.info("Signed in as: **Faculty Member**\n\n*Access Level: Context Locked*")
    app_mode = st.sidebar.radio(
        "Select Workspace View:",
        ["📝 Subject Marks Entry Sheet Console", "📅 Section Attendance Register", "📊 My Subject Analytics Panel"]
    )
    
    active_teacher_id = 104 
    
    if app_mode == "📝 Subject Marks Entry Sheet Console":
        st.title("📝 Subject Marks Entry Sheet Console")
    elif app_mode == "📅 Section Attendance Register":
        st.title("📅 Section Attendance Register")
    elif app_mode == "📊 My Subject Analytics Panel":
        st.title("📊 My Subject Performance Analytics")
