from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class HighBill(db.Model):
    
    __tablename__ = 'high_bills'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    house_id = db.Column(db.String(50), nullable=False, index=True)
    owner_name = db.Column(db.String(100))
    address = db.Column(db.Text)
    month = db.Column(db.String(20), nullable=False, index=True)
    units_consumed = db.Column(db.Integer, default=0)
    bill_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('house_id', 'month', name='unique_house_month'),
    )

    def __repr__(self):
        return f'<HighBill {self.house_id} - {self.month} - ₹{self.bill_amount}>'

    def to_dict(self):
        return {
            "id": self.id,
            "House_ID": self.house_id,
            "Owner_Name": self.owner_name,
            "Address": self.address,
            "Month": self.month,
            "Units_Consumed": self.units_consumed,
            "Bill_Amount": self.bill_amount,
            "Created_At": self.created_at.isoformat() if self.created_at else None,
            "Updated_At": self.updated_at.isoformat() if self.updated_at else None
        }