from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from .db import get_db
import mysql.connector

bp = Blueprint('items', __name__, url_prefix='/items')

print(session['current_order_id'])