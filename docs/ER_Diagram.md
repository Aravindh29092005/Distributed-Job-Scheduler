"""
ENTITY RELATIONSHIP DIAGRAM
Distributed Job Scheduling Platform

Mermaid ER Diagram - renderable on GitHub
"""

# ```mermaid
# erDiagram
# 
# USERS ||--o{ ORGANIZATIONS : creates
# USERS ||--o{ ORGANIZATION_MEMBERS : has
# USERS ||--o{ PROJECT_MEMBERS : has
# USERS ||--o{ JOB_EXECUTIONS : triggers
# 
# ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERS : has
# ORGANIZATIONS ||--o{ PROJECTS : contains
# ORGANIZATIONS ||--o{ RETRY_POLICIES : defines
# 
# PROJECTS ||--o{ PROJECT_MEMBERS : has
# PROJECTS ||--o{ QUEUES : contains
# PROJECTS ||--o{ JOBS : contains
# PROJECTS ||--o{ SCHEDULED_JOBS : contains
# 
# QUEUES ||--o{ JOBS : receives
# QUEUES ||--o{ RETRY_POLICIES : uses
# 
# RETRY_POLICIES ||--o{ JOBS : configured
# 
# JOBS ||--o{ JOB_EXECUTIONS : has
# JOBS ||--o{ DEAD_LETTER_QUEUE : may_move_to
# JOBS }o--|| WORKERS : claimed_by
# 
# JOB_EXECUTIONS ||--o{ JOB_LOGS : produces
# JOB_EXECUTIONS }o--|| WORKERS : executed_by
# 
# WORKERS ||--o{ WORKER_HEARTBEATS : emits
# WORKERS ||--o{ JOB_EXECUTIONS : executes
# 
# SCHEDULED_JOBS ||--o{ JOBS : spawns
# 
# DEAD_LETTER_QUEUE ||--|| JOBS : references
# 
# USERS : UUID id
# USERS : string email PK
# USERS : string hashed_password
# USERS : timestamp created_at
# USERS : timestamp updated_at
# USERS : timestamp archived_at
# 
# ORGANIZATIONS : UUID id PK
# ORGANIZATIONS : string name
# ORGANIZATIONS : text description
# ORGANIZATIONS : timestamp created_at
# ORGANIZATIONS : timestamp updated_at
# ORGANIZATIONS : timestamp archived_at
# 
# ORGANIZATION_MEMBERS : UUID id PK
# ORGANIZATION_MEMBERS : UUID organization_id FK
# ORGANIZATION_MEMBERS : UUID user_id FK
# ORGANIZATION_MEMBERS : string role
# ORGANIZATION_MEMBERS : timestamp created_at
# ORGANIZATION_MEMBERS : timestamp updated_at
# 
# PROJECTS : UUID id PK
# PROJECTS : UUID organization_id FK
# PROJECTS : string name
# PROJECTS : text description
# PROJECTS : timestamp created_at
# PROJECTS : timestamp updated_at
# PROJECTS : timestamp archived_at
# 
# PROJECT_MEMBERS : UUID id PK
# PROJECT_MEMBERS : UUID project_id FK
# PROJECT_MEMBERS : UUID user_id FK
# PROJECT_MEMBERS : string role
# PROJECT_MEMBERS : timestamp created_at
# PROJECT_MEMBERS : timestamp updated_at
# 
# QUEUES : UUID id PK
# QUEUES : UUID project_id FK
# QUEUES : string name
# QUEUES : text description
# QUEUES : int priority
# QUEUES : int max_concurrent
# QUEUES : boolean paused
# QUEUES : timestamp created_at
# QUEUES : timestamp updated_at
# QUEUES : timestamp archived_at
# 
# RETRY_POLICIES : UUID id PK
# RETRY_POLICIES : UUID organization_id FK
# RETRY_POLICIES : string name
# RETRY_POLICIES : int max_retries
# RETRY_POLICIES : string strategy
# RETRY_POLICIES : int initial_delay_ms
# RETRY_POLICIES : int max_delay_ms
# RETRY_POLICIES : float multiplier
# RETRY_POLICIES : timestamp created_at
# RETRY_POLICIES : timestamp updated_at
# 
# JOBS : UUID id PK
# JOBS : UUID queue_id FK
# JOBS : UUID project_id FK
# JOBS : UUID retry_policy_id FK
# JOBS : UUID worker_id FK
# JOBS : UUID batch_id
# JOBS : string name
# JOBS : string type
# JOBS : string status
# JOBS : jsonb payload
# JOBS : int priority
# JOBS : timestamp run_at
# JOBS : int timeout_seconds
# JOBS : string idempotency_key UK
# JOBS : UUID correlation_id
# JOBS : timestamp claimed_at
# JOBS : timestamp started_at
# JOBS : timestamp completed_at
# JOBS : timestamp created_at
# JOBS : timestamp updated_at
# JOBS : timestamp archived_at
# 
# SCHEDULED_JOBS : UUID id PK
# SCHEDULED_JOBS : UUID project_id FK
# SCHEDULED_JOBS : UUID queue_id FK
# SCHEDULED_JOBS : UUID retry_policy_id FK
# SCHEDULED_JOBS : string name
# SCHEDULED_JOBS : string cron_expression
# SCHEDULED_JOBS : jsonb payload_template
# SCHEDULED_JOBS : timestamp last_run_at
# SCHEDULED_JOBS : timestamp next_run_at
# SCHEDULED_JOBS : timestamp created_at
# SCHEDULED_JOBS : timestamp updated_at
# SCHEDULED_JOBS : timestamp archived_at
# 
# JOB_EXECUTIONS : UUID id PK
# JOB_EXECUTIONS : UUID job_id FK
# JOB_EXECUTIONS : UUID worker_id FK
# JOB_EXECUTIONS : int attempt_number
# JOB_EXECUTIONS : string status
# JOB_EXECUTIONS : jsonb result
# JOB_EXECUTIONS : text error
# JOB_EXECUTIONS : timestamp started_at
# JOB_EXECUTIONS : timestamp completed_at
# JOB_EXECUTIONS : timestamp created_at
# 
# JOB_LOGS : UUID id PK
# JOB_LOGS : UUID job_execution_id FK
# JOB_LOGS : string level
# JOB_LOGS : text message
# JOB_LOGS : jsonb context
# JOB_LOGS : UUID correlation_id
# JOB_LOGS : timestamp created_at
# 
# WORKERS : UUID id PK
# WORKERS : string name
# WORKERS : string host
# WORKERS : int port
# WORKERS : jsonb tags
# WORKERS : timestamp registered_at
# WORKERS : timestamp last_heartbeat
# WORKERS : timestamp created_at
# WORKERS : timestamp updated_at
# WORKERS : timestamp archived_at
# 
# WORKER_HEARTBEATS : UUID id PK
# WORKER_HEARTBEATS : UUID worker_id FK
# WORKER_HEARTBEATS : timestamp created_at
# 
# DEAD_LETTER_QUEUE : UUID id PK
# DEAD_LETTER_QUEUE : UUID job_id FK
# DEAD_LETTER_QUEUE : string job_name
# DEAD_LETTER_QUEUE : UUID queue_id FK
# DEAD_LETTER_QUEUE : int final_attempt_number
# DEAD_LETTER_QUEUE : text final_error
# DEAD_LETTER_QUEUE : jsonb payload
# DEAD_LETTER_QUEUE : timestamp created_at
# ```

# Table structure details below in SQLAlchemy models
