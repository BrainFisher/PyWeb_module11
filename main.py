from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import create_engine, Column, Integer, String, Date, extract
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from datetime import date, timedelta  # Додано timedelta до імпортів
from pydantic import BaseModel

# SQLAlchemy models
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String)
    birthday = Column(Date)
    additional_info = Column(String, nullable=True)

# Pydantic schemas


class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birthday: date
    additional_info: Optional[str] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(ContactBase):
    pass


class Contact(ContactBase):
    id: int

    class Config:
        from_attributes = True


# FastAPI app
app = FastAPI()

# Dependency


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/contacts/", response_model=Contact)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    db_contact = Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


@app.get("/contacts/", response_model=List[Contact])
def read_contacts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(Contact).offset(skip).limit(limit).all()


@app.get("/contacts/{contact_id}", response_model=Contact)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact


@app.put("/contacts/{contact_id}", response_model=Contact)
def update_contact(contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in contact.dict().items():
        setattr(db_contact, key, value)
    db.commit()
    db.refresh(db_contact)
    return db_contact


@app.delete("/contacts/{contact_id}", response_model=Contact)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(db_contact)
    db.commit()
    return db_contact


@app.get("/contacts/search/", response_model=List[Contact])
def search_contacts(query: str = Query(None, min_length=3), db: Session = Depends(get_db)):
    if query is None:
        return []
    return db.query(Contact).filter(
        (Contact.first_name.ilike(f"%{query}%")) |
        (Contact.last_name.ilike(f"%{query}%")) |
        (Contact.email.ilike(f"%{query}%"))
    ).all()


@app.get("/contacts/birthdays/", response_model=List[Contact])
def upcoming_birthdays(db: Session = Depends(get_db)):
    today = date.today()
    end_date = today + timedelta(days=7)
    return db.query(Contact).filter(
        (extract('month', Contact.birthday) == today.month) &
        (extract('day', Contact.birthday) >= today.day) &
        (extract('day', Contact.birthday) <= end_date.day)
    ).all()
