from datetime import datetime, timezone  # 🛡️ 升級：引入現代時區模組
from werkzeug.security import generate_password_hash, check_password_hash
import json

# Note: 'db' represents the SQLAlchemy instance initialized in your app extensions
# from app import db

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False) # 擴大容錯空間
    question_type = db.Column(db.String(50), default='multiple_choice')
    option_a = db.Column(db.String(500))
    option_b = db.Column(db.String(500))
    option_c = db.Column(db.String(500))
    option_d = db.Column(db.String(500))
    correct_answer = db.Column(db.String(500), nullable=False)
    explanation = db.Column(db.Text(length=20000)) # 🛡️ 安全加固：限制最大 Text 長度防範 DoS
    grade = db.Column(db.String(20), default='P1')
    image_filename = db.Column(db.String(1024)) # 🛡️ 擴大欄位防止 Cloudinary/S3 URL 溢出崩潰
    has_image = db.Column(db.Boolean, default=False)
    is_math_content = db.Column(db.Boolean, default=False)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False) # 🛡️ 安全加固：擴大至 255 防止未來加密算法升級被截斷
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc)) # 🛡️ 升級：現代時區感知 UTC 標準

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    __table_args__ = (db.UniqueConstraint('name', 'grade', name='unique_student'),)

class StudentWork(db.Model):
    __tablename__ = 'student_works'
    id = db.Column(db.Integer, primary_key=True)
    # 🛡️ 最佳實踐：加入 ondelete='CASCADE'，學生刪除時連帶清理作業，防止髒數據
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='SET NULL'))
    image_filename = db.Column(db.String(1024))
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(50), default='pending')
    
    ai_feedback = db.Column(db.Text(length=50000)) # 限制最大深度
    ai_score = db.Column(db.Float)
    weak_areas = db.Column(db.Text(length=10000)) # 儲存 JSON，限制長度防惡意爆破
    corrected_at = db.Column(db.DateTime)
    correction_status = db.Column(db.String(50), default='pending')
    
    student = db.relationship('Student', backref='works')
    question = db.relationship('Question', backref='student_works')

class StudentWeakness(db.Model):
    """學生弱項記錄 - 匹配現有PostgreSQL表結構（經過安全優化）"""
    __tablename__ = 'student_weakness'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    weakness_category = db.Column(db.String(255), nullable=False)
    strength_level = db.Column(db.Float, default=1.0)
    last_practiced = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    topic = db.Column(db.String(255))
    subtopic = db.Column(db.String(255))
    practice_count = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    
    @property
    def accuracy_rate(self):
        if self.practice_count == 0:
            return 0.0
        return (self.correct_count / self.practice_count) * 100
    
    @property
    def needs_practice(self):
        if self.practice_count < 5:
            return True
        return self.accuracy_rate < 70.0
    
    student = db.relationship('Student', backref='weaknesses')

class Tutor(db.Model):
    """導師模型（加固版）"""
    __tablename__ = 'tutors'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False) # 加大密碼長度
    real_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    
    tutor_metadata = db.Column(db.JSON, default=dict)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AISession(db.Model):
    """AI 分析會話模型（安全加固版）"""
    __tablename__ = 'ai_sessions'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    original_question = db.Column(db.Text(length=20000)) # 🛡️ 限制大小防 DoS
    image_url = db.Column(db.String(1024))
    ai_analysis = db.Column(db.Text(length=50000))
    practice_questions = db.Column(db.Text(length=50000))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    student = db.relationship('Student', backref='ai_sessions')

class PracticeResult(db.Model):
    """練習題結果模型"""
    __tablename__ = 'practice_results'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    ai_session_id = db.Column(db.Integer, db.ForeignKey('ai_sessions.id', ondelete='CASCADE'), nullable=False)
    question_index = db.Column(db.Integer)
    user_answer = db.Column(db.String(1000))
    is_correct = db.Column(db.Boolean)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    student = db.relationship('Student', backref='practice_results')
    ai_session = db.relationship('AISession', backref='practice_results')
