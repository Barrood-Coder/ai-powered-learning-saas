import os
import io
import re
import json
import time
import base64
import traceback
import requests
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from typing import Dict, Optional
from PIL import Image

# Flask Core & Extensions
from flask import Flask, jsonify, render_template, render_template_string, request, flash, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_wtf.csrf import CSRFProtect, CSRFError
from wtforms import RadioField, SubmitField, StringField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape
from urllib.parse import urlparse

# Third-Party Cloud & Utilities
import secrets
from dotenv import load_dotenv
from functools import wraps
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# Configure global production-grade logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_gemini():
    """設置 Gemini API - 安全與日誌加固版"""
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_api_key:
        logging.warning("Environment configurations missing: GEMINI_API_KEY is not set.")
        return False
    
    # Assuming genai is configured via third-party package wrapper
    try:
        genai.configure(api_key=gemini_api_key)
        logging.info("Generative AI Engine (Gemini) successfully initialized.")
        return True
    except Exception as e:
        logging.error(f"Failed to configure Generative AI Core: {str(e)}")
        return False


# 安全標頭中間件 (Hardened Security Middleware)
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.route('/student/register', methods=['POST'])
def student_register():
    """學生註冊 - 安全加固與 OWASP 標準版"""
    name = request.form.get('name', '').strip()
    grade = request.form.get('grade', '')
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    logging.info(f"Registration validation invoked for Grade category: {grade}")
    
    if not all([name, grade, password, confirm_password]):
        flash('請填寫所有必填欄位', 'error')
        return redirect(url_for('index'))
    
    if len(password) < 6:
        flash('密碼長度至少需要6個字符', 'error')
        return redirect(url_for('index'))
    
    if password != confirm_password:
        flash('兩次輸入的密碼不一致', 'error')
        return redirect(url_for('index'))
    
    try:
        existing_student = Student.query.filter_by(name=name, grade=grade).first()
        if existing_student:
            flash(f'該姓名在{grade}年級中已被註冊，請更換姓名或聯絡導師。', 'error')
            return redirect(url_for('index'))
        
        new_student = Student(name=name, grade=grade)
        new_student.set_password(password)
        
        db.session.add(new_student)
        db.session.commit()
        
        flash('註冊成功！請使用姓名和密碼登入', 'success')
    except Exception as e:
        db.session.rollback()
        # Secure isolation of internal database exception logs from raw frontend layers
        logging.error(f"Database insertion exception during student registration: {traceback.format_exc()}")
        flash('系統處理失敗，請聯繫管理員協助。', 'error')
    
    return redirect(url_for('index'))


@app.route('/dashboard')
@student_login_required
def student_dashboard():
    """學生登入後的儀表板 - 安全加固與 Session 生命週期管理"""
    try:
        student_id = session.get('student_id')
        student = Student.query.get(student_id)
        
        if not student:
            session.clear() # Active circuit-breaker to prevent polluted session loops
            flash('學生帳戶不存在，請重新登入', 'error')
            return redirect(url_for('index'))

        weaknesses = StudentWeakness.query.filter_by(student_id=student_id).all()
        recent_sessions = AISession.query.filter_by(student_id=student_id).order_by(AISession.created_at.desc()).limit(5).all()
        
        student_grade = session.get('student_grade')
        grade_questions_count = Question.query.filter_by(grade=student_grade).count()
        submitted_works_count = StudentWork.query.filter_by(student_id=student_id).count()
        reviewed_works_count = StudentWork.query.filter_by(student_id=student_id, status='reviewed').count()
        
        quiz_status = get_quiz_status()
        current_time = datetime.now()
        
        return render_template('student_dashboard.html',
                             student=student,
                             weaknesses=weaknesses,
                             recent_sessions=recent_sessions,
                             student_grade=student_grade,
                             grade_questions_count=grade_questions_count,
                             submitted_works_count=submitted_works_count,
                             reviewed_works_count=reviewed_works_count,
                             quiz_status=quiz_status)
    
    except Exception as e:
        # Prevent layout schema leakage on unhandled route processing failures
        logging.error(f"Render state crash within dashboard routing pipeline: {traceback.format_exc()}")
        session.clear()
        flash('加載儀表板時系統出錯，請重新登入。', 'error')
        return redirect(url_for('index'))
