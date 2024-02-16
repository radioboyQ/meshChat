# from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, Boolean, update, insert, select
# from sqlalchemy.orm import sessionmaker, declarative_base, registry
#
# # Magic sqlalchemy string
# Base = declarative_base()


# class Node(Base):
#     __tablename__ = 'nodes'
#
#     id = Column(Integer, primary_key=True)
#     longName = Column(String(50), unique=False, nullable=False)
#     shortName = Column(String(10), unique=False, nullable=False)
#     macaddr = Column(String(20), unique=True, nullable=False)
#     hwModel = Column(String(100), unique=False, nullable=False)
#     created_at = Column(DateTime, default=func.now())
#     last_seen = Column(DateTime, default=func.now(), onupdate=func.now())
#     # Local radio sent per instance
#     local_radio = Column(Boolean, default=False)