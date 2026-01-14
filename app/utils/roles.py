from flask import session, redirect, url_for

def requiere_login():
    return "usuario" in session

def requiere_admin():
    return session.get("rol") == "admin"





