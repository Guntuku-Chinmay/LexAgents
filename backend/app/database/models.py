import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(String(100), primary_key=True)
    query = Column(Text, nullable=False)
    final_answer = Column(Text, nullable=True)
    iterations = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Log(Base):
    __tablename__ = "logs"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    step_name = Column(String(200), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(Text, nullable=False)  # JSON-serialized payload
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Query(Base):
    __tablename__ = "queries"
    query_id = Column(String(100), primary_key=True)
    session_id = Column(String(100), nullable=False)
    query_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AgentTask(Base):
    __tablename__ = "agent_tasks"
    task_id = Column(String(100), primary_key=True)
    session_id = Column(String(100), nullable=False)
    query_text = Column(Text, nullable=False)
    agent_name = Column(String(100), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AgentRun(Base):
    __tablename__ = "agent_runs"
    run_id = Column(String(100), primary_key=True)
    session_id = Column(String(100), nullable=False)
    task_id = Column(String(100), nullable=True)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # 'started', 'completed', 'failed'
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)
    retrieval_iteration = Column(Integer, default=1)
    source_count = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    doc_id = Column(String(100), primary_key=True)
    filename = Column(String(255), nullable=False)
    doc_type = Column(String(50), nullable=False)  # 'case', 'statute', 'user_upload'
    metadata_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Source(Base):
    __tablename__ = "sources"
    source_id = Column(String(100), primary_key=True)
    doc_id = Column(String(100), nullable=False)
    text = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Claim(Base):
    __tablename__ = "claims"
    claim_id = Column(String(100), primary_key=True)
    session_id = Column(String(100), nullable=False)
    claim_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class VerificationResultModel(Base):
    __tablename__ = "verification_results"
    verification_id = Column(String(100), primary_key=True)
    session_id = Column(String(100), nullable=False)
    claim_text = Column(Text, nullable=False)
    supported = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    issues_json = Column(Text, nullable=True)  # List of issues serialized
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ClaimSourceLink(Base):
    __tablename__ = "claim_source_links"
    link_id = Column(String(100), primary_key=True)
    verification_id = Column(String(100), nullable=False)
    source_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ReflectionCycle(Base):
    __tablename__ = "reflection_cycles"
    cycle_id = Column(String(100), primary_key=True)
    session_id = Column(String(100), nullable=False)
    iteration = Column(Integer, nullable=False)
    reasoning = Column(Text, nullable=True)
    sufficient = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Evaluation(Base):
    __tablename__ = "evaluations"
    eval_id = Column(String(100), primary_key=True)
    run_timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    system_type = Column(String(100), nullable=False)
    metrics_json = Column(Text, nullable=False)
    config_json = Column(Text, nullable=False)

class EvaluationResultModel(Base):
    __tablename__ = "evaluation_results"
    result_id = Column(String(100), primary_key=True)
    eval_id = Column(String(100), nullable=False)
    query_id = Column(String(100), nullable=False)
    system_type = Column(String(100), nullable=False)
    latency = Column(Float, nullable=False)
    iterations = Column(Integer, nullable=False)
    metrics_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
