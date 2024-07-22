import streamlit as st
import sqlite3
import hashlib
from streamlit import session_state as state
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode

# Global variables
logged_in_users = []

# Function to create a connection to SQLite database
def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
    except sqlite3.Error as e:
        st.error(f"Error connecting to database: {e}")
    return conn

# Function to create tables in the database if they do not exist
def create_tables(conn):
    if conn is not None:
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            user_type TEXT NOT NULL,
            is_logged_in INTEGER DEFAULT 0
        );
        """
        try:
            c = conn.cursor()
            c.execute(create_users_table)
        except sqlite3.Error as e:
            st.error(f"Error creating table: {e}")

        create_messages_table = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            c = conn.cursor()
            c.execute(create_messages_table)
        except sqlite3.Error as e:
            st.error(f"Error creating messages table: {e}")
        
        create_prescriptions_table = """
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor TEXT NOT NULL,
            patient TEXT NOT NULL,
            prescription TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        );
        """
        try:
            c = conn.cursor()
            c.execute(create_prescriptions_table)
        except sqlite3.Error as e:
            st.error(f"Error creating prescriptions table: {e}")

# Function to insert user data into the database
def insert_user(conn, username, password, user_type):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    sql = """
    INSERT INTO users (username, password_hash, user_type)
    VALUES (?, ?, ?)
    """
    try:
        cur = conn.cursor()
        cur.execute(sql, (username, hashed_password, user_type))
        conn.commit()
        st.success("Registration successful. Please login.")
    except sqlite3.Error as e:
        st.error(f"Error inserting user: {e}")

# Function to retrieve user data from the database
def get_user(conn, username):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    return cur.fetchone()

# Function to check if a username already exists in the database
def username_exists(conn, username):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE username=?", (username,))
    count = cur.fetchone()[0]
    return count > 0

# Function to log in a user
def login_user(conn, username, password):
    user = get_user(conn, username)
    if user:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if hashed_password == user[2]:
            # Update user's login status in the database
            update_login_status(conn, username, 1)
            return (username, user[3])  # Return tuple (username, user_type)
        else:
            st.error("Incorrect username or password.")
    else:
        st.error("User not found.")
    return None

# Function to log out a user
def logout_user(conn, username):
    update_login_status(conn, username, 0)
    global logged_in_users
    logged_in_users = [user for user in logged_in_users if user[0] != username]

# Function to update user's login status in the database
def update_login_status(conn, username, status):
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_logged_in=? WHERE username=?", (status, username))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Error updating login status: {e}")

# Function to get all logged-in users of a specific type
def get_logged_in_users(conn, user_type):
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE user_type=? AND is_logged_in=1", (user_type,))
    return [row[0] for row in cur.fetchall()]

# Function to get user type based on username
def get_user_type(conn, username):
    cur = conn.cursor()
    cur.execute("SELECT user_type FROM users WHERE username=?", (username,))
    result = cur.fetchone()
    if result:
        return result[0]
    return None

# Function to send a message
def send_message(conn, sender, receiver, message):
    sql = """
    INSERT INTO messages (sender, receiver, message)
    VALUES (?, ?, ?)
    """
    try:
        cur = conn.cursor()
        cur.execute(sql, (sender, receiver, message))
        conn.commit()
        st.success(f"Message sent to {receiver}")
    except sqlite3.Error as e:
        st.error(f"Error sending message: {e}")

# Function to retrieve chat history between two users
def get_chat_history(conn, user1, user2):
    sql = """
    SELECT sender, message, timestamp FROM messages
    WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
    ORDER BY timestamp ASC
    """
    try:
        cur = conn.cursor()
        cur.execute(sql, (user1, user2, user2, user1))
        return cur.fetchall()
    except sqlite3.Error as e:
        st.error(f"Error retrieving chat history: {e}")
        return []

# Function to give a prescription
def give_prescription(conn, doctor, patient, prescription):
    sql = """
    INSERT INTO prescriptions (doctor, patient, prescription)
    VALUES (?, ?, ?)
    """
    try:
        cur = conn.cursor()
        cur.execute(sql, (doctor, patient, prescription))
        conn.commit()
        st.success(f"Prescription given to {patient}")
    except sqlite3.Error as e:
        st.error(f"Error giving prescription: {e}")

# Function to get prescriptions for a patient
def get_prescriptions(conn, patient):
    cur = conn.cursor()
    cur.execute("SELECT * FROM prescriptions WHERE patient=?", (patient,))
    return cur.fetchall()

# Function to update prescription status
def update_prescription_status(conn, prescription_id, status):
    try:
        cur = conn.cursor()
        cur.execute("UPDATE prescriptions SET status=? WHERE id=?", (status, prescription_id))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Error updating prescription status: {e}")

# Define SessionState class
class SessionState:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @staticmethod
    def get(**kwargs):
        session_id = 'session'
        if session_id not in st.session_state:
            st.session_state[session_id] = SessionState(**kwargs)
        return st.session_state[session_id]

# Function to display chat history
def display_chat_history(conn, user1, user2):
    chat_history = get_chat_history(conn, user1, user2)
    if chat_history:
        st.subheader("Chat History")
        displayed_messages = set()  # To keep track of displayed messages

        for chat in chat_history:
            message_key = f"{chat[0]}-{chat[1]}-{chat[2]}"  # Unique identifier for each message
            if message_key not in displayed_messages:
                st.write(f"{chat[0]}: {chat[1]} ({chat[2]})")
                displayed_messages.add(message_key)
    else:
        st.write("No chat history available.")

# Function to display prescriptions
def display_prescriptions(conn, patient):
    prescriptions = get_prescriptions(conn, patient)
    if prescriptions:
        st.subheader("Prescriptions")
        for prescription in prescriptions:
            st.write(f"Prescription from Dr. {prescription[1]}: {prescription[3]}")
            if prescription[4] == 'pending':
                st.write(f"Status: {prescription[4]}")
                if st.button(f"Can you afford this prescription? Yes", key=f"yes_{prescription[0]}"):
                    update_prescription_status(conn, prescription[0], 'affordable')
                    st.success("Prescription status updated to affordable.")
                elif st.button(f"Can you afford this prescription? No", key=f"no_{prescription[0]}"):
                    update_prescription_status(conn, prescription[0], 'unaffordable')
                    forward_chat_to_asha_worker(conn, patient, prescription[0])
                    st.success("Prescription forwarded to Asha Worker.")
            else:
                st.write(f"Status: {prescription[4]}")

# Function to forward chat to Asha Worker
def forward_chat_to_asha_worker(conn, patient, prescription_id):
    asha_workers = get_logged_in_users(conn, "Aasha Worker")
    if asha_workers:
        for asha_worker in asha_workers:
            send_message(conn, "System", asha_worker, f"Patient {patient} needs assistance with prescription ID {prescription_id}.")
        st.success("Chat forwarded to Asha Worker.")
    else:
        st.error("No Asha Workers available to assist.")

# Main function to run the Streamlit app
def main():
    # Add CSS for styling and background image
    #background: url('https://www.example.com/path/to/your/image.jpg') no-repeat center center fixed;
#                background: 'Cartoon-Doctor.jpeg' no-repeat center center fixed;

    st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
     """, unsafe_allow_html=True)
    background_image = """
       <style>
       [data-testid="stAppViewContainer"] > .main {
       background: url('https://t4.ftcdn.net/jpg/06/32/90/79/360_F_632907942_M6CVHD1ivhUrWK1X49PkBlSH3ooNPsog.jpg');
       background-size: 100vw 100vh;  # This sets the size to cover 100% of the viewport width and height
       background-position: center;  
       background-repeat: repeat;
       }
       </style>
       """

    st.markdown(background_image, unsafe_allow_html=True)
    st.markdown("""
        <style>
        body {
            font-family: 'Arial', sans-serif;
            background-size: cover;
        }
        .main {
            background-color: rgba(255, 255, 255, 0.8);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .stButton button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 8px;
        }
        .stButton button:hover {
            background-color: #45a049;
        }
        .stTextInput input {
            border-radius: 8px;
            padding: 8px;
            width: 100%;
            box-sizing: border-box;
        }
        .stSidebar {
            background-color: #333;
            color: white;
        }
        .stSidebar .stButton button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 8px;
        }
        .stSidebar .stButton button:hover {
            background-color: #45a049;
        }
        .stSidebar .stTextInput input {
            border-radius: 8px;
            padding: 8px;
            width: 100%;
            box-sizing: border-box;
        }
        .stSidebar h2 {
            font-size: 20px;
        }
        .stSidebar h3 {
            font-size: 16px;
        }
        .stSidebar p {
            font-size: 14px;
        }
        .stSidebar .stMarkdown {
            font-size: 14px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Create or connect to the SQLite database
    conn = create_connection("healthcare.db")
    if conn is not None:
        # Create necessary tables
        create_tables(conn)
    else:
        st.error("Error: Could not connect to database.")

    # Initialize Streamlit app
    st.title("WebRTC Video and Web Chat App")

    # Initialize SessionState
    session_state = SessionState.get(logged_in=False, username='', user_type='', chat_with='', chat_mode='')

    # Sidebar menu
    menu = ["Home", "Login", "Register", "Logout"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Home":
        st.subheader("Home")
        if session_state.logged_in:
            st.write(f"Welcome {session_state.username} ({session_state.user_type})")
        else:
            st.write("Please login to use the chat features.")

    elif choice == "Login":
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login_user(conn, username, password)
            if user:
                session_state.logged_in = True
                session_state.username = user[0]
                session_state.user_type = user[1]
                st.success(f"Logged in as {username}")
                st.write(f"User Type: {user[1]}")

    elif choice == "Register":
        st.subheader("Register")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        user_type = st.selectbox("User Type", ["Doctor", "Patient", "Aasha Worker"])
        if st.button("Register"):
            if username_exists(conn, username):
                st.warning("Username already exists. Please choose a different username.")
            else:
                insert_user(conn, username, password, user_type)

    elif choice == "Logout":
        if session_state.logged_in:
            logout_user(conn, session_state.username)
            session_state.logged_in = False
            session_state.username = ''
            session_state.user_type = ''
            st.success("Successfully logged out.")
        else:
            st.warning("You are not logged in.")

    # Display available Doctors and Asha Workers for logged-in Patients
    if session_state.logged_in and session_state.user_type == "Patient":
        st.sidebar.title("Available Doctors")
        doctors = get_logged_in_users(conn, "Doctor")
        if doctors:
            st.sidebar.write("\n".join(doctors))
        else:
            st.sidebar.write("No doctors available.")

        st.sidebar.title("Available Asha Workers")
        asha_workers = get_logged_in_users(conn, "Aasha Worker")
        if asha_workers:
            st.sidebar.write("\n".join(asha_workers))
        else:
            st.sidebar.write("No Asha workers available.")

    # Display logged-in users by user type
    st.sidebar.title("Logged-in Users")
    if logged_in_users:
        for user_type in ["Doctor", "Patient", "Aasha Worker"]:
            st.sidebar.subheader(user_type)
            for user in logged_in_users:
                if user[1] == user_type:
                    st.sidebar.write(user[0])

    st.sidebar.title("About")
    st.sidebar.info(
        "This app allows different types of users (Doctors, Patients, Aasha Workers) to chat with each other."
    )

    # Chat interface
    if session_state.logged_in:
#        st.markdown("[disease Prognosis](human-disease-prediction_V3.py)")
        st.markdown("[Click here for Disease Prognosis and Virtual Prescription](http://localhost:9000)")
            
        st.subheader("Chat Interface")
        if session_state.user_type == "Doctor":
            st.info("Select a patient to chat with from the sidebar.")
            selected_patient = st.sidebar.selectbox("Patients", get_logged_in_users(conn, "Patient"))
            state.chat_with = selected_patient
        elif session_state.user_type == "Patient":
            st.info("Select a doctor or Aasha Worker to chat with from the sidebar.")
            selected_user = st.sidebar.selectbox("Doctors/Aasha Workers", get_logged_in_users(conn, "Doctor") + get_logged_in_users(conn, "Aasha Worker"))
            state.chat_with = selected_user
        elif session_state.user_type == "Aasha Worker":
            st.info("Select a patient to chat with from the sidebar.")
            selected_patient = st.sidebar.selectbox("Patients", get_logged_in_users(conn, "Patient"))
            state.chat_with = selected_patient

        if state.chat_with:
            # Select communication mode
            chat_mode = st.radio("Choose communication mode", ["Web Chat", "Video Chat"])
            session_state.chat_mode = chat_mode
            
            if chat_mode == "Web Chat":
                display_chat_history(conn, session_state.username, state.chat_with)
                message = st.text_input("Message:")
                if st.button("Send"):
                    send_message(conn, session_state.username, state.chat_with, message)
                if session_state.user_type == "Doctor":
                    prescription = st.text_area("Prescription:")
                    if st.button("Give Prescription"):
                        give_prescription(conn, session_state.username, state.chat_with, prescription)
                elif session_state.user_type == "Patient":
                    display_prescriptions(conn, session_state.username)
            elif chat_mode == "Video Chat":
                st.write(f"Initiating video chat with {state.chat_with}...")
                # Use webrtc_streamer to start video chat
                webrtc_streamer(key="example", mode=WebRtcMode.SENDRECV)

    # Disconnect from database
    if conn is not None:
        conn.close()

if __name__ == "__main__":
    main()
