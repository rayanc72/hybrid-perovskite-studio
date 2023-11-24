import streamlit as st
import hashlib
import hmac

from contextlib import contextmanager

@contextmanager
def connect_to_db():
    connection = None
    try:
        connection = st.connection("hpame_users", type="sql", autocommit=True)
        yield connection
    except Exception as e:
        st.error(f"Error while connecting to MySQL: {e}")

def check_password():
    """Returns `True` if the user had a correct password."""
    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False

# Function to hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to check user credentials in the database
def verify_login(username, password):
    with connect_to_db() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT password FROM users WHERE user_id = %s", (username,))
        record = cursor.fetchone()
        return record and hashlib.sha256(password.encode()).hexdigest() == record[0]

def register_user(user_id, email, hashed_password):
    with connect_to_db() as connection:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO users (user_id, email, password) VALUES (%s, %s, %s)",
                       (user_id, email, hashed_password))
        connection.commit()
        return cursor.rowcount == 1

def login_form():
    """Form with widgets to collect user information"""
    with st.form("Credentials"):
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.form_submit_button("Log in", on_click=password_entered)

def password_entered():
    """Checks whether a password entered by the user is correct."""
    if verify_login(st.session_state["username"], st.session_state["password"]):
        st.session_state["password_correct"] = True
    else:
        st.session_state["password_correct"] = False

def registration_form():
    """Form to register a new user"""
    with st.form("Registration"):
        new_username = st.text_input("Choose a Username", key="new_username")
        new_email = st.text_input("Your Email", key="new_email")
        new_password = st.text_input("Choose a Password", type="password", key="new_password")
        if st.form_submit_button("Register"):
            hashed_password = hash_password(new_password)
            if register_user(new_username, new_email, hashed_password):
                st.success("Registered successfully! Please log in.")
            else:
                st.error("Registration failed. Please try again.")


