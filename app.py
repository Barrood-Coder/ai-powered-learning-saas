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

@app.route('/student/register', methods=['POST'])
@csrf.exempt
def student_register():
    """學生註冊 - 修復版本"""
    name = request.form.get('name', '').strip()
    grade = request.form.get('grade', '')
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    print(f"🔍 註冊嘗試: 姓名='{name}', 年級='{grade}'")
    
    # 驗證表單數據
    if not all([name, grade, password, confirm_password]):
        flash('請填寫所有必填欄位', 'error')
        return redirect('/')
    
    if len(password) < 6:
        flash('密碼長度至少需要6個字符', 'error')
        return redirect('/')
    
    if password != confirm_password:
        flash('兩次輸入的密碼不一致', 'error')
        return redirect('/')
    
    # 檢查姓名和年級組合是否已存在 - 添加詳細調試
    existing_student = Student.query.filter_by(name=name, grade=grade).first()
    
    if existing_student:
        print(f"❌ 學生已存在: {name} ({grade}) - ID: {existing_student.id}")
        # 找出所有同名但不同年級的學生
        same_name_students = Student.query.filter_by(name=name).all()
        print(f"📊 同名學生: {[f'{s.name}({s.grade})' for s in same_name_students]}")
        
        flash(f'該姓名在{grade}年級中已被註冊，請使用其他姓名或選擇其他年級', 'error')
        return redirect('/')
    
    # 創建新學生
    new_student = Student(
        name=name,
        grade=grade
    )
    new_student.set_password(password)
    
    try:
        db.session.add(new_student)
        db.session.commit()
        print(f"✅ 註冊成功: {name} ({grade})")
        flash('註冊成功！請使用姓名和密碼登入', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"❌ 註冊失敗: {str(e)}")
        flash(f'註冊失敗：{str(e)}', 'error')
    
    return redirect('/')

@app.route('/dashboard')
@student_login_required
def student_dashboard():
    """學生登入後的儀表板"""
    try:
        # 再次驗證學生存在
        student_id = session.get('student_id')
        student = Student.query.get(student_id)
        
        if not student:
            # 學生不存在，清除 session 並重定向
            session.clear()
            flash('學生帳戶不存在，請重新登入', 'error')
            return redirect('/')

        # 獲取學生的弱項統計
        weaknesses = StudentWeakness.query.filter_by(student_id=student_id).all()

        # 獲取最近的AI會話
        recent_sessions = AISession.query.filter_by(student_id=student_id).order_by(AISession.created_at.desc()).limit(5).all()
        
        # 獲取學生所在年級的題目統計
        student_grade = session.get('student_grade')
        grade_questions_count = Question.query.filter_by(grade=student_grade).count()
        
        # 獲取學生的作業提交統計
        submitted_works_count = StudentWork.query.filter_by(student_id=student_id).count()
        reviewed_works_count = StudentWork.query.filter_by(student_id=student_id, status='reviewed').count()
        
        # 檢查測驗狀態
        quiz_status = get_quiz_status()

        # 傳入當前時間
        from datetime import datetime
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
        print(f"❌ 儀表板錯誤: {e}")
        # 發生錯誤時清除 session 避免循環
        session.clear()
        flash(f'系統錯誤: {e}', 'error')
        return redirect('/')
    
