from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habits.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy and Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Define Tag model
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name.lower()


# Define Habit model
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    tags = db.relationship('Tag', secondary='habit_tags', backref=db.backref('habits', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'tags': [tag.name for tag in self.tags],
            'deadline': self.deadline.strftime('%Y-%m-%d'),
            'completed': self.completed
        }


# Define many-to-many relationship table between Habit and Tag
habit_tags = db.Table('habit_tags',
                      db.Column('habit_id', db.Integer, db.ForeignKey('habit.id'), primary_key=True),
                      db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
                      )


# Route for the main page
@app.route('/')
def index():
    habits = Habit.query.all()
    return render_template('index.html', habits=habits)


# Route to filter habits based on tags, dates, and status
@app.route('/filter_habits', methods=['POST'])
def filter_habits():
    data = request.get_json()
    tags = [tag.lower() for tag in data.get('tags', [])]
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    status = data.get('status', 'all')

    query = Habit.query

    if tags:
        for tag in tags:
            query = query.filter(Habit.tags.any(Tag.name == tag))

    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        query = query.filter(Habit.deadline >= start_date)

    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        query = query.filter(Habit.deadline <= end_date)

    if status == 'completed':
        query = query.filter(Habit.completed)
    elif status == 'not_completed':
        query = query.filter(not Habit.completed)

    habits = query.all()

    return jsonify({'habits': [habit.to_dict() for habit in habits]})


# Route to add a new habit
@app.route('/add', methods=['POST'])
def add():
    data = request.get_json()
    title = data.get('title')
    tag_names = data.get('tags', [])
    deadline = data.get('deadline')

    if not title or not deadline:
        return jsonify({'error': 'Title and deadline are required'}), 400

    try:
        deadline = datetime.strptime(deadline, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid deadline format'}), 400

    tag_names_set = {name.strip().lower() for name in tag_names if name.strip()}

    if not tag_names_set:
        tag_names_set.add("<unknown>")

    tags = []
    for name in tag_names_set:
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
        tags.append(tag)

    new_habit = Habit(title=title, deadline=deadline, tags=tags)
    db.session.add(new_habit)
    db.session.commit()

    result = {
        'id': new_habit.id,
        'title': new_habit.title,
        'tags': [tag.name for tag in new_habit.tags],
        'deadline': new_habit.deadline.strftime('%Y-%m-%d'),
        'completed': new_habit.completed
    }

    return jsonify({'habit': result})


# Route to toggle habit completion status
@app.route('/toggle_complete/<int:habit_id>', methods=['POST'])
def toggle_complete(habit_id):
    data = request.get_json()
    completed = data.get('completed')

    habit = Habit.query.get(habit_id)
    if habit:
        habit.completed = completed
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Habit not found'}), 404


# Route to delete a habit
@app.route('/delete/<int:habit_id>', methods=['GET'])
def delete(habit_id):
    habit = Habit.query.get(habit_id)
    if habit:
        db.session.delete(habit)
        db.session.commit()
        return redirect(url_for('index'))
    return jsonify({'error': 'Habit not found'}), 404


# Run the app
if __name__ == '__main__':
    app.run(debug=True)
