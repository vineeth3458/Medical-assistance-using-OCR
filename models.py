from datetime import datetime
import json
from extensions import db  # ✅ Use extensions instead of importing from app directly

class User(db.Model):
    """User model for managing access to documents."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with documents
    documents = db.relationship('Document', backref='owner', lazy='dynamic')


class Document(db.Model):
    """Document model for storing medical documents."""
    id = db.Column(db.String(36), primary_key=True)  # UUID as string
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # prescription, lab_report, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    raw_text = db.Column(db.Text)
    processed_data = db.Column(db.Text)  # JSON string of extracted medical entities
    image_data = db.Column(db.Text)  # Base64 encoded image

    # Foreign key to user
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for guest users

    def set_processed_data(self, data_dict):
        """Convert dictionary to JSON string for storage."""
        self.processed_data = json.dumps(data_dict)

    def get_processed_data(self):
        """Convert JSON string to dictionary."""
        if self.processed_data:
            return json.loads(self.processed_data)
        return {}
