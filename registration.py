import hashlib
import streamlit as st

conn = st.connection('mysql', type='sql', db='hpame_users')

def verify_login(username, password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    query = 'SELECT password FROM users WHERE user_id = %s'
    result = conn.query(query, (username,), ttl=600)

    if result.rowcount == 1 and result.iloc[0]['password'] == hashed_password:
        return True
    else:
        return False
