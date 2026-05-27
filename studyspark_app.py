from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json
import pymysql
import os
pymysql.install_as_MySQLdb()

app = Flask(__name__)
CORS(app)

# ✅ Reads from Railway environment variable
db_url = os.environ.get('DATABASE_URL', '')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'studyspark_secret'

db = SQLAlchemy(app)


# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name       = db.Column(db.String(255), nullable=False)
    email      = db.Column(db.String(255), unique=True, nullable=False)
    phone      = db.Column(db.String(50),  nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    course     = db.Column(db.String(255), default='')
    year       = db.Column(db.String(50),  default='')
    roll_no    = db.Column(db.String(100), default='')
    college    = db.Column(db.String(255), default='')
    dob        = db.Column(db.String(50),  default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActiveSession(db.Model):
    __tablename__ = 'active_sessions'
    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email    = db.Column(db.String(255), nullable=False)
    login_at = db.Column(db.DateTime, default=datetime.utcnow)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name       = db.Column(db.String(255), nullable=False)
    code       = db.Column(db.String(50),  default='')
    professor  = db.Column(db.String(255), default='')
    credits    = db.Column(db.Integer, default=3)
    color      = db.Column(db.String(20),  default='#6C63FF')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    status     = db.Column(db.String(10), nullable=False)
    date       = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TimetableEntry(db.Model):
    __tablename__ = 'timetable'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject    = db.Column(db.String(255), nullable=False)
    day        = db.Column(db.String(10),  nullable=False)
    start_time = db.Column(db.String(10),  nullable=False)
    end_time   = db.Column(db.String(10),  nullable=False)
    room       = db.Column(db.String(100), default='')
    type       = db.Column(db.String(50),  default='Lecture')
    color      = db.Column(db.String(20),  default='#6C63FF')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Exam(db.Model):
    __tablename__ = 'exams'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject    = db.Column(db.String(255), nullable=False)
    type       = db.Column(db.String(50),  default='Internal')
    venue      = db.Column(db.String(255), default='')
    syllabus   = db.Column(db.String(500), default='')
    exam_date  = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Mark(db.Model):
    __tablename__ = 'marks'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject    = db.Column(db.String(255), nullable=False)
    exam_name  = db.Column(db.String(255), nullable=False)
    marks      = db.Column(db.Integer, nullable=False)
    total      = db.Column(db.Integer, nullable=False)
    exam_date  = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Note(db.Model):
    __tablename__ = 'notes'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title      = db.Column(db.String(255), nullable=False)
    content    = db.Column(db.Text, default='')
    subject    = db.Column(db.String(255), default='General')
    color      = db.Column(db.String(20),  default='#6C63FF')
    is_pinned  = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PomodoroSession(db.Model):
    __tablename__ = 'pomodoro_sessions'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task         = db.Column(db.String(255), default='')
    focus_mins   = db.Column(db.Integer, default=25)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data     = request.get_json()
        required = ['name', 'email', 'phone', 'password', 'confirm_password']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        if data['password'] != data['confirm_password']:
            return jsonify({'error': 'Passwords do not match'}), 400
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        new_user = User(
            name=data['name'], email=data['email'], phone=data['phone'],
            password=generate_password_hash(data['password']),
            course=data.get('course', ''), year=data.get('year', ''),
            roll_no=data.get('roll_no', ''), college=data.get('college', '')
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password required'}), 400
        user = User.query.filter_by(email=data['email']).first()
        if not user or not check_password_hash(user.password, data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        session = ActiveSession(email=user.email)
        db.session.add(session)
        db.session.commit()
        return jsonify({'message': 'Login successful', 'user': {
            'id': user.id, 'name': user.name, 'email': user.email,
            'phone': user.phone, 'course': user.course,
            'year': user.year, 'roll_no': user.roll_no, 'college': user.college
        }}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/get_current_user', methods=['GET'])
def get_current_user():
    try:
        last = ActiveSession.query.order_by(ActiveSession.id.desc()).first()
        if not last:
            return jsonify({'error': 'No active user found'}), 404
        user = User.query.filter_by(email=last.email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({
            'id': user.id, 'name': user.name, 'email': user.email,
            'phone': user.phone, 'course': user.course,
            'year': user.year, 'roll_no': user.roll_no, 'college': user.college
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    try:
        data  = request.get_json()
        email = data.get('email') if data else None
        if not email:
            return jsonify({'error': 'Email required'}), 400
        ActiveSession.query.filter_by(email=email).delete()
        db.session.commit()
        return jsonify({'message': 'Logged out successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────

@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({
            'id': user.id, 'name': user.name, 'email': user.email,
            'phone': user.phone, 'course': user.course, 'year': user.year,
            'roll_no': user.roll_no, 'college': user.college, 'dob': user.dob,
            'created_at': user.created_at.strftime('%d %b %Y')
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profile/<int:user_id>', methods=['PUT'])
def update_profile(user_id):
    try:
        data = request.get_json()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user.name    = data.get('name',    user.name)
        user.phone   = data.get('phone',   user.phone)
        user.course  = data.get('course',  user.course)
        user.year    = data.get('year',    user.year)
        user.roll_no = data.get('roll_no', user.roll_no)
        user.college = data.get('college', user.college)
        user.dob     = data.get('dob',     user.dob)
        db.session.commit()
        return jsonify({'message': 'Profile updated'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# SUBJECTS
# ─────────────────────────────────────────

@app.route('/subjects/<int:user_id>', methods=['GET'])
def get_subjects(user_id):
    try:
        subjects = Subject.query.filter_by(user_id=user_id)\
            .order_by(Subject.created_at.asc()).all()
        return jsonify([{
            'id': s.id, 'name': s.name, 'code': s.code,
            'professor': s.professor, 'credits': s.credits, 'color': s.color
        } for s in subjects]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/subjects', methods=['POST'])
def add_subject():
    try:
        data     = request.get_json()
        required = ['user_id', 'name']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        subject = Subject(
            user_id=data['user_id'], name=data['name'],
            code=data.get('code', ''), professor=data.get('professor', ''),
            credits=data.get('credits', 3), color=data.get('color', '#6C63FF')
        )
        db.session.add(subject)
        db.session.commit()
        return jsonify({'message': 'Subject added', 'id': subject.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/subjects/<int:subject_id>', methods=['PUT'])
def update_subject(subject_id):
    try:
        data    = request.get_json()
        subject = Subject.query.get(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404
        subject.name      = data.get('name',      subject.name)
        subject.code      = data.get('code',      subject.code)
        subject.professor = data.get('professor', subject.professor)
        subject.credits   = data.get('credits',   subject.credits)
        subject.color     = data.get('color',     subject.color)
        db.session.commit()
        return jsonify({'message': 'Subject updated'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/subjects/<int:subject_id>', methods=['DELETE'])
def delete_subject(subject_id):
    try:
        subject = Subject.query.get(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404
        db.session.delete(subject)
        db.session.commit()
        return jsonify({'message': 'Subject deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────

@app.route('/attendance/<int:user_id>', methods=['GET'])
def get_attendance(user_id):
    try:
        subjects = Subject.query.filter_by(user_id=user_id).all()
        result   = []
        for s in subjects:
            records  = AttendanceRecord.query.filter_by(
                user_id=user_id, subject_id=s.id).all()
            attended = sum(1 for r in records if r.status == 'present')
            total    = len(records)
            pct      = round((attended / total) * 100, 1) if total > 0 else 0.0
            needed   = 0
            if pct < 75 and total > 0:
                while ((attended + needed) / (total + needed)) * 100 < 75:
                    needed += 1
            result.append({
                'subject_id': s.id, 'subject': s.name, 'color': s.color,
                'attended': attended, 'total': total,
                'percentage': pct, 'classes_needed': needed
            })
        overall_attended = sum(r['attended'] for r in result)
        overall_total    = sum(r['total']    for r in result)
        overall_pct      = round((overall_attended / overall_total) * 100, 1) \
            if overall_total > 0 else 0.0
        return jsonify({'overall': overall_pct, 'subjects': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/attendance', methods=['POST'])
def mark_attendance():
    try:
        data     = request.get_json()
        required = ['user_id', 'subject_id', 'status']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        if data['status'] not in ('present', 'absent'):
            return jsonify({'error': "status must be 'present' or 'absent'"}), 400
        rec_date = datetime.strptime(data['date'], '%Y-%m-%d').date() \
            if data.get('date') else date.today()
        record = AttendanceRecord(
            user_id=data['user_id'], subject_id=data['subject_id'],
            status=data['status'], date=rec_date
        )
        db.session.add(record)
        db.session.commit()
        return jsonify({'message': 'Attendance marked', 'id': record.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/attendance/<int:record_id>', methods=['DELETE'])
def delete_attendance(record_id):
    try:
        record = AttendanceRecord.query.get(record_id)
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        db.session.delete(record)
        db.session.commit()
        return jsonify({'message': 'Record deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# TIMETABLE
# ─────────────────────────────────────────

@app.route('/timetable/<int:user_id>', methods=['GET'])
def get_timetable(user_id):
    try:
        day     = request.args.get('day')
        query   = TimetableEntry.query.filter_by(user_id=user_id)
        if day:
            query = query.filter_by(day=day)
        entries = query.order_by(TimetableEntry.day, TimetableEntry.start_time).all()
        return jsonify([{
            'id': e.id, 'subject': e.subject, 'day': e.day,
            'start_time': e.start_time, 'end_time': e.end_time,
            'room': e.room, 'type': e.type, 'color': e.color
        } for e in entries]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/timetable', methods=['POST'])
def add_timetable_entry():
    try:
        data     = request.get_json()
        required = ['user_id', 'subject', 'day', 'start_time', 'end_time']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        entry = TimetableEntry(
            user_id=data['user_id'], subject=data['subject'],
            day=data['day'], start_time=data['start_time'],
            end_time=data['end_time'], room=data.get('room', ''),
            type=data.get('type', 'Lecture'), color=data.get('color', '#6C63FF')
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({'message': 'Class added', 'id': entry.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/timetable/<int:entry_id>', methods=['DELETE'])
def delete_timetable_entry(entry_id):
    try:
        entry = TimetableEntry.query.get(entry_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'message': 'Class deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# EXAMS
# ─────────────────────────────────────────

@app.route('/exams/<int:user_id>', methods=['GET'])
def get_exams(user_id):
    try:
        today = date.today()
        exams = Exam.query.filter_by(user_id=user_id)\
            .filter(Exam.exam_date >= today)\
            .order_by(Exam.exam_date.asc()).all()
        return jsonify([{
            'id': e.id, 'subject': e.subject, 'type': e.type,
            'venue': e.venue, 'syllabus': e.syllabus,
            'exam_date': e.exam_date.strftime('%d %b %Y'),
            'days_left': (e.exam_date - today).days
        } for e in exams]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/exams', methods=['POST'])
def add_exam():
    try:
        data     = request.get_json()
        required = ['user_id', 'subject', 'exam_date']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        exam_date = datetime.strptime(data['exam_date'], '%Y-%m-%d').date()
        exam = Exam(
            user_id=data['user_id'], subject=data['subject'],
            type=data.get('type', 'Internal'), venue=data.get('venue', ''),
            syllabus=data.get('syllabus', ''), exam_date=exam_date
        )
        db.session.add(exam)
        db.session.commit()
        return jsonify({'message': 'Exam added', 'id': exam.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/exams/<int:exam_id>', methods=['DELETE'])
def delete_exam(exam_id):
    try:
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        db.session.delete(exam)
        db.session.commit()
        return jsonify({'message': 'Exam deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# MARKS
# ─────────────────────────────────────────

@app.route('/marks/<int:user_id>', methods=['GET'])
def get_marks(user_id):
    try:
        all_marks = Mark.query.filter_by(user_id=user_id)\
            .order_by(Mark.created_at.desc()).all()
        return jsonify([{
            'id': m.id, 'exam_name': m.exam_name,
            'marks': m.marks, 'total': m.total,
            'percentage': round((m.marks / m.total) * 100, 1) if m.total > 0 else 0.0
        } for m in all_marks]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/marks', methods=['POST'])
def add_mark():
    try:
        data     = request.get_json()
        required = ['user_id', 'subject', 'exam_name', 'marks', 'total']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        exam_date = datetime.strptime(data['exam_date'], '%Y-%m-%d').date() \
            if data.get('exam_date') else None
        mark = Mark(
            user_id=data['user_id'], subject=data['subject'],
            exam_name=data['exam_name'], marks=data['marks'],
            total=data['total'], exam_date=exam_date
        )
        db.session.add(mark)
        db.session.commit()
        return jsonify({'message': 'Marks saved', 'id': mark.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/marks/<int:mark_id>', methods=['DELETE'])
def delete_mark(mark_id):
    try:
        mark = Mark.query.get(mark_id)
        if not mark:
            return jsonify({'error': 'Mark not found'}), 404
        db.session.delete(mark)
        db.session.commit()
        return jsonify({'message': 'Mark deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/marks/summary/<int:user_id>', methods=['GET'])
def marks_summary(user_id):
    try:
        all_marks    = Mark.query.filter_by(user_id=user_id).all()
        total_scored = sum(m.marks for m in all_marks)
        total_max    = sum(m.total  for m in all_marks)
        overall_pct  = round((total_scored / total_max) * 100, 1) if total_max > 0 else 0.0
        subject_map  = {}
        for m in all_marks:
            if m.subject not in subject_map:
                subject_map[m.subject] = {'scored': 0, 'max': 0}
            subject_map[m.subject]['scored'] += m.marks
            subject_map[m.subject]['max']    += m.total
        at_risk   = sum(1 for v in subject_map.values()
                        if v['max'] > 0 and (v['scored'] / v['max']) * 100 < 50)
        excellent = sum(1 for v in subject_map.values()
                        if v['max'] > 0 and (v['scored'] / v['max']) * 100 >= 75)
        def grade(pct):
            if pct >= 90: return 'O'
            if pct >= 80: return 'A+'
            if pct >= 70: return 'A'
            if pct >= 60: return 'B+'
            if pct >= 50: return 'B'
            if pct >= 40: return 'C'
            return 'F'
        return jsonify({
            'overall_percentage': overall_pct,
            'overall_grade': grade(overall_pct),
            'at_risk_count': at_risk,
            'excellent_count': excellent,
            'subject_count': len(subject_map)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# NOTES
# ─────────────────────────────────────────

@app.route('/notes/<int:user_id>', methods=['GET'])
def get_notes(user_id):
    try:
        subject = request.args.get('subject')
        search  = request.args.get('q')
        query   = Note.query.filter_by(user_id=user_id)
        if subject:
            query = query.filter_by(subject=subject)
        if search:
            query = query.filter(Note.title.ilike(f'%{search}%'))
        notes = query.order_by(Note.is_pinned.desc(), Note.updated_at.desc()).all()
        return jsonify([{
            'id': n.id, 'title': n.title, 'content': n.content,
            'subject': n.subject, 'color': n.color, 'is_pinned': n.is_pinned,
            'created_at': n.created_at.strftime('%d %b %Y'),
            'updated_at': n.updated_at.strftime('%d %b %Y') if n.updated_at else None
        } for n in notes]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/notes', methods=['POST'])
def add_note():
    try:
        data     = request.get_json()
        required = ['user_id', 'title']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        note = Note(
            user_id=data['user_id'], title=data['title'],
            content=data.get('content', ''), subject=data.get('subject', 'General'),
            color=data.get('color', '#6C63FF'), is_pinned=data.get('is_pinned', False)
        )
        db.session.add(note)
        db.session.commit()
        return jsonify({'message': 'Note saved', 'id': note.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    try:
        data = request.get_json()
        note = Note.query.get(note_id)
        if not note:
            return jsonify({'error': 'Note not found'}), 404
        note.title     = data.get('title',     note.title)
        note.content   = data.get('content',   note.content)
        note.subject   = data.get('subject',   note.subject)
        note.color     = data.get('color',     note.color)
        note.is_pinned = data.get('is_pinned', note.is_pinned)
        db.session.commit()
        return jsonify({'message': 'Note updated'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    try:
        note = Note.query.get(note_id)
        if not note:
            return jsonify({'error': 'Note not found'}), 404
        db.session.delete(note)
        db.session.commit()
        return jsonify({'message': 'Note deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/notes/<int:note_id>/pin', methods=['POST'])
def toggle_pin(note_id):
    try:
        note = Note.query.get(note_id)
        if not note:
            return jsonify({'error': 'Note not found'}), 404
        note.is_pinned = not note.is_pinned
        db.session.commit()
        return jsonify({'message': 'Pin toggled', 'is_pinned': note.is_pinned}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# POMODORO
# ─────────────────────────────────────────

@app.route('/pomodoro/<int:user_id>', methods=['GET'])
def get_pomodoro_stats(user_id):
    try:
        today       = date.today()
        total       = PomodoroSession.query.filter_by(user_id=user_id).count()
        today_count = PomodoroSession.query.filter_by(user_id=user_id).filter(
            db.func.date(PomodoroSession.completed_at) == today
        ).count()
        rows = db.session.execute(db.text("""
            SELECT DATE(completed_at) AS day, COUNT(*) AS sessions
            FROM pomodoro_sessions
            WHERE user_id = :uid
              AND completed_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY day ORDER BY day ASC
        """), {'uid': user_id}).fetchall()
        return jsonify({
            'total_sessions': total,
            'today_sessions': today_count,
            'weekly_chart': [{'day': str(r[0]), 'sessions': r[1]} for r in rows]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pomodoro', methods=['POST'])
def log_pomodoro():
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'user_id required'}), 400
        session = PomodoroSession(
            user_id=data['user_id'],
            task=data.get('task', ''),
            focus_mins=data.get('focus_mins', 25)
        )
        db.session.add(session)
        db.session.commit()
        return jsonify({'message': 'Session logged', 'id': session.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

@app.route('/dashboard/<int:user_id>', methods=['GET'])
def get_dashboard(user_id):
    try:
        today = date.today()
        subjects      = Subject.query.filter_by(user_id=user_id).all()
        total_present = total_classes = 0
        low_attendance = []
        for s in subjects:
            records  = AttendanceRecord.query.filter_by(user_id=user_id, subject_id=s.id).all()
            attended = sum(1 for r in records if r.status == 'present')
            total    = len(records)
            total_present += attended
            total_classes += total
            if total > 0 and (attended / total) * 100 < 75:
                low_attendance.append({
                    'subject': s.name,
                    'percentage': round((attended / total) * 100, 1)
                })
        overall_attendance = round((total_present / total_classes) * 100, 1) \
            if total_classes > 0 else 0.0

        all_marks    = Mark.query.filter_by(user_id=user_id).all()
        total_scored = sum(m.marks for m in all_marks)
        total_max    = sum(m.total  for m in all_marks)
        avg_marks    = round((total_scored / total_max) * 100, 1) if total_max > 0 else 0.0

        streak = 0
        check  = today
        while True:
            count = PomodoroSession.query.filter_by(user_id=user_id).filter(
                db.func.date(PomodoroSession.completed_at) == check
            ).count()
            if count > 0:
                streak += 1
                if check.day > 1:
                    check = date(check.year, check.month, check.day - 1)
                else:
                    break
            else:
                break

        day_name       = today.strftime('%a')
        todays_classes = TimetableEntry.query.filter_by(
            user_id=user_id, day=day_name
        ).order_by(TimetableEntry.start_time).all()

        upcoming_exams = Exam.query.filter_by(user_id=user_id).filter(
            Exam.exam_date >= today
        ).order_by(Exam.exam_date.asc()).limit(3).all()

        recent_notes = Note.query.filter_by(user_id=user_id)\
            .order_by(Note.updated_at.desc()).limit(3).all()

        return jsonify({
            'overall_attendance': overall_attendance,
            'avg_marks': avg_marks,
            'streak': streak,
            'low_attendance': low_attendance,
            'todays_classes': [{
                'id': c.id, 'subject': c.subject,
                'start_time': c.start_time, 'end_time': c.end_time,
                'room': c.room, 'type': c.type, 'color': c.color
            } for c in todays_classes],
            'upcoming_exams': [{
                'id': e.id, 'subject': e.subject, 'type': e.type,
                'exam_date': e.exam_date.strftime('%d %b %Y'),
                'days_left': (e.exam_date - today).days
            } for e in upcoming_exams],
            'recent_notes': [{
                'id': n.id, 'title': n.title, 'subject': n.subject, 'color': n.color
            } for n in recent_notes]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
