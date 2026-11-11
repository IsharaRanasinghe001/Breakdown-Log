from extensions import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_address = db.Column(db.String(150), nullable=False)
    customer_name = db.Column(db.String(150))
    contact_number = db.Column(db.String(50))
    devices = db.relationship('Device', backref='customer', lazy=True)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    unit_description = db.Column(db.String(100))
    brand = db.Column(db.String(50))
    model = db.Column(db.String(50))
    serial_number = db.Column(db.String(50))
    work_orders = db.relationship('WorkOrder', backref='device', lazy=True)

class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    work_order_no = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.String(30), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    
    breakdown = db.Column(db.Text)
    work_carried_out = db.Column(db.Text)
    spare_item = db.Column(db.Text)
    
    customer = db.relationship('Customer', backref='work_orders')