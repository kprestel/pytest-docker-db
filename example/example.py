from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

engine = create_engine("postgresql+psycopg2://test:test@localhost:5411/test")

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
)

metadata.create_all(engine)
