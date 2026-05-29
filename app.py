import os
import io
import re
import json
import time
import base64
import traceback
import requests
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

# Note: genai (Google Gemini) is initialized here
# import google.generativeai as genai


def setup_gemini():
    """設置 Gemini API"""
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_api_key:
        print("⚠️ 未設置 GEMINI_API_KEY")
        return False
    
    genai.configure(api_key=gemini_api_key)
    print("✅ Gemini API 配置成功")
    return True


# 安全標頭中間件
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

import logging

# 初始化日誌系統（代替 print，生產環境標配）
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/student/register', methods=['POST'])
# 🛡️ 安全修復 1：移除 @csrf.exempt，強制啟用 CSRF 防護
def student_register():
    """學生註冊 - 安全加固版"""
    name = request.form.get('name', '').strip()
    grade = request.form.get('grade', '')
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # 使用日誌代替敏感的明文 print
    logging.info(f"Registration attempt matching Grade: {grade}")
    
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
        # 🛡️ 安全修復 2：敏感錯誤紀錄在伺服器日誌（黑客看不到），前端只給予模糊提示
        logging.error(f"Database error during registration: {traceback.format_exc()}")
        flash('系統處理失敗，請聯繫管理員協助。', 'error')
    
    return redirect(url_for('index'))


@app.route('/dashboard')
@student_login_required
def student_dashboard():
    """學生登入後的儀表板 - 安全加固版"""
    try:
        student_id = session.get('student_id')
        student = Student.query.get(student_id)
        
        if not student:
            session.clear()
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
        # 🛡️ 安全修復 3：儀表板異常不洩漏敏感架構訊息
        logging.error(f"Dashboard structural failure: {traceback.format_exc()}")
        session.clear()
        flash('加載儀表板時系統出錯，請重新登入。', 'error')
        return redirect(url_for('index'))

