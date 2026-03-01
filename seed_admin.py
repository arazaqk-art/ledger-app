from database import SessionLocal, engine, Base
from models import User
from auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

username = "admin"
password = "1234"

existing = db.query(User).filter(User.username == username).first()
if existing:
    print("✅ Admin already exists")
else:
    db.add(User(username=username, password_hash=hash_password(password), role="admin"))
    db.commit()
    print("✅ Admin created: admin / 1234")

db.close()