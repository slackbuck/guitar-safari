"""
Script to create a 'people' table and insert a sample record using SQLAlchemy ORM.
Requires DATABASE_URL environment variable set to a PostgreSQL connection string.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, Session

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

Base = declarative_base()

class Person(Base):
    __tablename__ = "people"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

def main():
    engine = create_engine(DATABASE_URL, echo=True, future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        p = Person(name="Bob")
        session.add(p)
        session.commit()
        print("Inserted id:", p.id)

if __name__ == "__main__":
    main()