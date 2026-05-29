from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json  # 用於解析 weak_areas 等 JSON 欄位

# Note: 'db' represents the SQLAlchemy instance 
# Typically imported from an extensions file or main app inside production
# For open-source demonstration, it assumes: from app import db

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(20), default='multiple_choice')
    option_a = db.Column(db.String(100))
    option_b = db.Column(db.String(100))
    option_c = db.Column(db.String(100))
    option_d = db.Column(db.String(100))
    correct_answer = db.Column(db.String(200), nullable=False)
    explanation = db.Column(db.Text)
    grade = db.Column(db.String(10), default='P1')
    image_filename = db.Column(db.String(500))
    has_image = db.Column(db.Boolean, default=False)
    is_math_content = db.Column(db.Boolean, default=False)  # 新增字段

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    grade = db.Column(db.String(10), nullable=False)  # 學生所屬年級
    password_hash = db.Column(db.String(200), nullable=False)  # 改為密碼哈希
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 設定密碼屬性
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 新增唯一約束，確保同一姓名和年級的組合唯一
    __table_args__ = (db.UniqueConstraint('name', 'grade', name='unique_student'),)

class StudentWork(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    image_filename = db.Column(db.String(200))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    
    # AI 批改相關字段
    ai_feedback = db.Column(db.Text)  # AI批改反饋
    ai_score = db.Column(db.Float)    # AI評分 (0-100)
    weak_areas = db.Column(db.Text)   # 弱項領域 (JSON格式)
    corrected_at = db.Column(db.DateTime)  # 批改時間
    correction_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    
    student = db.relationship('Student', backref='works')
    question = db.relationship('Question', backref='student_works')

class StudentWeakness(db.Model):
    """學生弱項記錄 - 匹配現有PostgreSQL表結構"""
    __tablename__ = 'student_weakness'  # 確保表名匹配
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    weakness_category = db.Column(db.String(100), nullable=False)  # 原來的 weakness_type
    strength_level = db.Column(db.Float, default=1.0)  # 熟練度級別 (0-1)
    last_practiced = db.Column(db.DateTime)  # 最後練習時間
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 創建時間
    topic = db.Column(db.String(100))  # 主題
    subtopic = db.Column(db.String(100))  # 子主題
    practice_count = db.Column(db.Integer, default=0)  # 練習次數
    correct_count = db.Column(db.Integer, default=0)  # 正確次數
    
    # 計算字段屬性
    @property
    def accuracy_rate(self):
        """計算正確率"""
        if self.practice_count == 0:
            return 0.0
        return (self.correct_count / self.practice_count) * 100
    
    @property
    def needs_practice(self):
        """判斷是否需要加強練習"""
        if self.practice_count < 5:
            return True  # 練習次數太少
        if self.accuracy_rate < 70:
            return True  # 正確率低於70%
        return False
    
    student = db.relationship('Student', backref='weaknesses')
# 在現有app.py的模型部分添加
class Tutor(db.Model):
    """導師模型（簡化版）"""
    __tablename__ = 'tutors'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    real_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # 擴展字段（JSON格式）
    tutor_metadata = db.Column(db.JSON, default=dict)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AISession(db.Model):
    """AI 分析會話模型"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    original_question = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    ai_analysis = db.Column(db.Text)  # JSON 格式的AI分析結果
    practice_questions = db.Column(db.Text)  # JSON 格式的練習題
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('Student', backref='ai_sessions')

class PracticeResult(db.Model):
    """練習題結果模型"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    ai_session_id = db.Column(db.Integer, db.ForeignKey('ai_session.id'), nullable=False)
    question_index = db.Column(db.Integer)  # 練習題索引
    user_answer = db.Column(db.String(500))
    is_correct = db.Column(db.Boolean)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('Student', backref='practice_results')
    ai_session = db.relationship('AISession', backref='practice_results')
