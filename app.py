import os
import json
import sqlite3
import re
import secrets
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
load_dotenv()

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth

from PyPDF2 import PdfReader

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'resume-analyzer-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['REPORTS_FOLDER'] = 'reports'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf'}

oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

DATABASE = 'resume_analyzer.db'

# ---------------------------------------------------------------------------
# Comprehensive Skills List
# ---------------------------------------------------------------------------
SKILLS_LIST = [
    # Programming Languages & Frameworks
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go',
    'rust', 'swift', 'kotlin', 'php', 'scala', 'r', 'matlab', 'sql', 'html',
    'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
    'express', 'next.js', 'tailwind', 'bootstrap', 'jquery', 'sass',
    # Data / AI / ML
    'machine learning', 'deep learning', 'data science', 'data analysis',
    'natural language processing', 'computer vision', 'tensorflow', 'pytorch',
    'pandas', 'numpy', 'scikit-learn', 'tableau', 'power bi',
    'data visualization', 'big data', 'hadoop', 'spark', 'data engineering',
    'data mining', 'statistical analysis', 'nlp', 'keras',
    # Cloud / DevOps
    'aws', 'azure', 'google cloud', 'docker', 'kubernetes', 'ci/cd',
    'jenkins', 'terraform', 'ansible', 'linux', 'git', 'github', 'devops',
    'microservices', 'serverless', 'nginx', 'apache', 'grafana', 'prometheus',
    # Databases
    'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'firebase',
    'oracle', 'sql server', 'dynamodb', 'cassandra', 'sqlite', 'neo4j',
    # Soft Skills
    'leadership', 'communication', 'teamwork', 'problem solving',
    'project management', 'agile', 'scrum', 'critical thinking',
    'time management', 'presentation', 'negotiation', 'mentoring',
    'strategic planning', 'stakeholder management', 'conflict resolution',
    # Testing / QA
    'unit testing', 'integration testing', 'selenium', 'jest', 'pytest',
    'cypress', 'test automation',
    # Design / UX
    'figma', 'ui/ux', 'wireframing', 'prototyping', 'adobe xd',
    # Security
    'cybersecurity', 'penetration testing', 'oauth', 'encryption', 'sso',
    # Mobile
    'react native', 'flutter', 'android', 'ios',
    # Other
    'rest api', 'graphql', 'websockets', 'rabbitmq', 'kafka',
    'blockchain', 'iot', 'embedded systems',
]

# ---------------------------------------------------------------------------
# Predefined Job Database (15+ roles)
# ---------------------------------------------------------------------------
JOB_DATABASE = [
    {
        'title': 'Backend Developer',
        'required_skills': ['python', 'sql', 'rest api', 'docker', 'git', 'linux', 'postgresql'],
        'description': 'Design and build server-side logic, APIs, and database integrations for scalable web applications.',
    },
    {
        'title': 'Frontend Developer',
        'required_skills': ['javascript', 'react', 'html', 'css', 'typescript', 'git', 'tailwind'],
        'description': 'Build interactive, responsive user interfaces and ensure seamless user experiences.',
    },
    {
        'title': 'Full Stack Developer',
        'required_skills': ['javascript', 'react', 'node.js', 'python', 'sql', 'docker', 'git', 'rest api'],
        'description': 'Develop end-to-end web applications spanning frontend, backend, and database layers.',
    },
    {
        'title': 'Data Scientist',
        'required_skills': ['python', 'machine learning', 'pandas', 'numpy', 'data visualization', 'sql', 'scikit-learn', 'statistical analysis'],
        'description': 'Analyze large datasets, build predictive models, and translate data into actionable insights.',
    },
    {
        'title': 'Machine Learning Engineer',
        'required_skills': ['python', 'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'docker', 'sql'],
        'description': 'Design, train, and deploy production-grade machine learning models and pipelines.',
    },
    {
        'title': 'DevOps Engineer',
        'required_skills': ['docker', 'kubernetes', 'aws', 'ci/cd', 'terraform', 'linux', 'git', 'jenkins'],
        'description': 'Build and maintain CI/CD pipelines, automate infrastructure, and ensure system reliability.',
    },
    {
        'title': 'Cloud Architect',
        'required_skills': ['aws', 'azure', 'google cloud', 'docker', 'kubernetes', 'terraform', 'microservices', 'serverless'],
        'description': 'Design cloud-native architectures that are secure, scalable, and cost-efficient.',
    },
    {
        'title': 'Data Engineer',
        'required_skills': ['python', 'sql', 'spark', 'hadoop', 'aws', 'data engineering', 'kafka', 'docker'],
        'description': 'Build and optimize data pipelines and warehouses to power analytics and ML workflows.',
    },
    {
        'title': 'Mobile Developer',
        'required_skills': ['react native', 'javascript', 'typescript', 'flutter', 'android', 'ios', 'git'],
        'description': 'Create native and cross-platform mobile applications for Android and iOS.',
    },
    {
        'title': 'Cybersecurity Analyst',
        'required_skills': ['cybersecurity', 'linux', 'penetration testing', 'encryption', 'oauth', 'sso', 'python'],
        'description': 'Protect organizational systems by monitoring threats, performing audits, and enforcing policies.',
    },
    {
        'title': 'QA / Test Automation Engineer',
        'required_skills': ['selenium', 'test automation', 'python', 'jest', 'cypress', 'ci/cd', 'git', 'unit testing'],
        'description': 'Design and execute automated test suites to ensure software quality and reliability.',
    },
    {
        'title': 'UI/UX Designer',
        'required_skills': ['figma', 'ui/ux', 'wireframing', 'prototyping', 'adobe xd', 'html', 'css'],
        'description': 'Research, design, and prototype user interfaces that are intuitive and visually compelling.',
    },
    {
        'title': 'Project Manager (Tech)',
        'required_skills': ['project management', 'agile', 'scrum', 'leadership', 'communication', 'stakeholder management', 'time management'],
        'description': 'Plan, execute, and deliver technology projects on time and within budget.',
    },
    {
        'title': 'NLP Engineer',
        'required_skills': ['python', 'natural language processing', 'machine learning', 'deep learning', 'pytorch', 'tensorflow', 'pandas'],
        'description': 'Build systems that understand, interpret, and generate human language at scale.',
    },
    {
        'title': 'Blockchain Developer',
        'required_skills': ['blockchain', 'javascript', 'python', 'rest api', 'docker', 'git', 'cryptography'],
        'description': 'Develop decentralized applications and smart contracts on blockchain platforms.',
    },
    {
        'title': 'Database Administrator',
        'required_skills': ['sql', 'postgresql', 'mysql', 'oracle', 'mongodb', 'linux', 'redis'],
        'description': 'Manage, tune, and secure relational and NoSQL database systems for high availability.',
    },
]

# ---------------------------------------------------------------------------
# Database Helpers
# ---------------------------------------------------------------------------

def get_db():
    """Return a sqlite3 connection with Row factory for the current request."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            DATABASE,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


@app.context_processor
def inject_user():
    """Inject the user object into all Jinja templates automatically."""
    user = None
    if session.get('user_id'):
        try:
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        except Exception:
            pass
    return dict(user=user)


def init_db():
    """Create all tables and seed a default admin user if not present."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            plan TEXT DEFAULT 'free',
            dark_mode INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_text TEXT,
            job_description TEXT,
            ats_score REAL DEFAULT 0,
            matched_skills TEXT,
            missing_skills TEXT,
            suggestions TEXT,
            interview_questions TEXT,
            detailed_analysis TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resume_id INTEGER NOT NULL,
            report_data TEXT,
            pdf_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (resume_id) REFERENCES resumes(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cover_letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resume_id INTEGER,
            job_title TEXT,
            company_name TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Seed admin user
    cur.execute("SELECT id FROM users WHERE username = ?", ('admin',))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
            (
                'admin',
                'admin@resumeai.com',
                generate_password_hash('admin123'),
                'Admin User',
                'admin',
            ),
        )

    # Alter table for Google OAuth fields if they don't exist
    try:
        cur.execute("ALTER TABLE users ADD COLUMN google_id TEXT UNIQUE")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cur.execute("ALTER TABLE users ADD COLUMN profile_picture_url TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
        
    try:
        cur.execute("ALTER TABLE resumes ADD COLUMN detailed_analysis TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Auth Decorators
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# File Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(filepath):
    """Extract all text from a PDF using PyPDF2. Returns empty string on error."""
    try:
        reader = PdfReader(filepath)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return '\n'.join(text_parts)
    except Exception as exc:
        print(f"PDF extraction error: {exc}")
        return ''


# ---------------------------------------------------------------------------
# AI / ML Engine Functions
# ---------------------------------------------------------------------------

def calculate_ats_score(resume_text, job_description):
    """Use TF-IDF + cosine similarity to produce an ATS compatibility score (0-100)."""
    if not resume_text.strip() or not job_description.strip():
        return 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
        score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return round(score * 100, 1)
    except Exception:
        return 0.0


def extract_skills(text):
    """Return a de-duplicated list of skills found in *text* (case-insensitive)."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for skill in SKILLS_LIST:
        # Use word-boundary matching so "r" doesn't match inside every word
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill)
    return list(dict.fromkeys(found))  # preserve order, remove dupes


def get_missing_skills(resume_skills, job_skills):
    """Return skills present in job_skills but absent from resume_skills."""
    resume_set = {s.lower() for s in resume_skills}
    return [s for s in job_skills if s.lower() not in resume_set]


def generate_suggestions(ats_score, matched_skills, missing_skills, resume_text):
    """Return 5-8 specific, actionable suggestions based on the analysis."""
    suggestions = []

    # --- Score-band suggestions ---
    if ats_score < 30:
        suggestions.append(
            "Your ATS score is critically low. Consider rewriting your resume to "
            "align closely with the job description's language and terminology."
        )
        suggestions.append(
            "Add the exact keywords from the job posting — many ATS systems rely on "
            "literal keyword matches to rank candidates."
        )
        suggestions.append(
            "Restructure your resume with clearly labeled sections: Summary, "
            "Experience, Skills, Education, and Certifications."
        )
    elif ats_score < 60:
        suggestions.append(
            "Mirror the job description's phrasing in your summary and bullet points "
            "to increase keyword overlap."
        )
        suggestions.append(
            "Quantify your achievements with numbers (e.g., 'Reduced API latency by "
            "40 %') — this makes impact tangible for reviewers and ATS parsers."
        )
        suggestions.append(
            "Tailor your professional summary to explicitly reference the target role "
            "and its core responsibilities."
        )
    elif ats_score < 80:
        suggestions.append(
            "Fine-tune wording by replacing generic verbs (managed, helped) with "
            "power verbs (orchestrated, spearheaded, optimized)."
        )
        suggestions.append(
            "Add measurable metrics to every bullet point — percentages, dollar "
            "amounts, and team sizes strengthen your narrative."
        )
        suggestions.append(
            "Consider adding a 'Key Achievements' section that showcases your "
            "highest-impact accomplishments."
        )
    else:
        suggestions.append(
            "Excellent alignment! Focus on polishing formatting — consistent fonts, "
            "bullet styles, and spacing improve readability."
        )
        suggestions.append(
            "Proofread carefully for typos and grammatical errors; at this score "
            "level, minor mistakes are the biggest differentiator."
        )
        suggestions.append(
            "Consider adding a brief 'Projects' or 'Publications' section to stand "
            "out from other strong candidates."
        )

    # --- Missing-skills suggestions ---
    if missing_skills:
        top_missing = ', '.join(missing_skills[:5])
        suggestions.append(
            f"You are missing key skills the job requires: {top_missing}. "
            "Add any you genuinely possess, or consider up-skilling."
        )
        if len(missing_skills) > 5:
            suggestions.append(
                f"There are {len(missing_skills)} missing skills total. Prioritize "
                "adding the top 5 most relevant ones to your resume."
            )

    # --- Length check ---
    word_count = len(resume_text.split())
    if word_count < 150:
        suggestions.append(
            "Your resume appears very short. Expand on work experience, projects, "
            "and technical accomplishments to strengthen your profile."
        )
    elif word_count > 1200:
        suggestions.append(
            "Your resume is quite lengthy. Aim for 1-2 pages by removing outdated "
            "or less-relevant experience."
        )

    # --- Matched skills suggestion ---
    if matched_skills:
        suggestions.append(
            f"Good news — you match {len(matched_skills)} skills. Make sure each "
            "appears in context (within a bullet point), not just in a skills list."
        )

    return suggestions[:8]


def generate_interview_questions(job_description, matched_skills):
    """Return up to 12 tailored interview questions: 3 Behavioral, up to 5 Technical (skill+role matched), 4 Situational."""
    questions = []

    # ── 1. Behavioral (3 always included) ────────────────────────────────────
    behavioral_pool = [
        {
            "question": "Tell me about a time you faced a significant technical challenge and how you resolved it.",
            "category": "behavioral",
            "tips": [
                "Use the STAR method (Situation, Task, Action, Result).",
                "Be specific — name the technology and the exact problem.",
                "Quantify the outcome: time saved, errors reduced, performance gained."
            ],
            "answer": "In a previous project our API response times spiked 300% under load. I profiled the endpoints, found N+1 database queries, replaced them with batch fetches, added Redis caching for hot data, and brought average response time from 2.4s down to 180ms — a 92% improvement — within two days."
        },
        {
            "question": "Describe a situation where you disagreed with a team decision. How did you handle it?",
            "category": "behavioral",
            "tips": [
                "Show you voiced your concern professionally and backed it with data.",
                "Demonstrate respect for the final group decision.",
                "Highlight what you learned from the experience."
            ],
            "answer": "My team chose a monolithic approach for a feature I felt would need independent scaling. I prepared a one-page comparison of pros/cons and cost projections and presented it in sprint planning. The team still chose the monolith but agreed to expose the module via an internal API so it could be extracted later — a sensible compromise."
        },
        {
            "question": "Give an example of a time you proactively improved a process or product without being asked.",
            "category": "behavioral",
            "tips": [
                "Demonstrate ownership and initiative beyond your job description.",
                "Explain how you identified the gap.",
                "Quantify the business impact of your improvement."
            ],
            "answer": "I noticed our QA cycle took three days because testing was entirely manual. Without being assigned to it, I wrote a Selenium test suite covering our 40 most-used user flows. After merging it into the CI pipeline, the QA cycle dropped to four hours and we caught two regressions in the very first week."
        },
        {
            "question": "Tell me about a project you are most proud of and what made it successful.",
            "category": "behavioral",
            "tips": [
                "Choose a project that shows your strongest skill.",
                "Explain your specific role — don't just say 'we built it'.",
                "Mention concrete success metrics or user impact."
            ],
            "answer": "I led the rebuild of our search feature using Elasticsearch. I owned the index design, relevance tuning, and frontend integration. After launch, search-result click-through rate rose by 45% and customer support tickets about 'can't find product' dropped by 70% within a month."
        },
        {
            "question": "Describe a time you had to meet a very tight deadline. What was your approach?",
            "category": "behavioral",
            "tips": [
                "Show prioritisation skills — what did you cut vs keep?",
                "Mention how you communicated progress to stakeholders.",
                "Explain what you would do differently next time."
            ],
            "answer": "We had a regulatory compliance feature due in five days. I broke it into must-have vs nice-to-have items, got stakeholder sign-off on the scope cut, worked focused four-hour blocks with daily check-ins, and shipped the critical path on day four with full test coverage — leaving one day for UAT."
        }
    ]
    questions.extend(behavioral_pool[:3])

    # ── 2. Technical – matched to resume skills + target role ─────────────────
    tech_db = {
        "python": {
            "question": "Explain Python's GIL. When does it hurt performance, and how do you work around it?",
            "category": "technical",
            "tips": [
                "Define the GIL clearly — it is a mutex protecting the interpreter state.",
                "Explain why CPU-bound threads are affected but I/O-bound threads are not.",
                "Mention multiprocessing, asyncio, or C extensions as workarounds."
            ],
            "answer": "The Global Interpreter Lock prevents multiple native threads from executing Python bytecode simultaneously. It hurts CPU-bound parallelism but barely affects I/O-bound tasks because threads release the GIL while waiting on I/O. I work around it using the `multiprocessing` module for CPU-heavy tasks, or `asyncio` for high-concurrency I/O work."
        },
        "javascript": {
            "question": "What is the JavaScript event loop, and how does it handle asynchronous code?",
            "category": "technical",
            "tips": [
                "Explain the call stack, task queue, and microtask queue.",
                "Give a concrete example with setTimeout vs Promises.",
                "Clarify why JavaScript is single-threaded yet non-blocking."
            ],
            "answer": "JavaScript is single-threaded. The event loop continuously checks the call stack — if it is empty, it picks tasks from the microtask queue (Promises) first, then the macrotask queue (setTimeout, setInterval). This means a resolved Promise callback always runs before a setTimeout(fn, 0) callback, even if both are ready at the same time."
        },
        "react": {
            "question": "How does React's reconciliation algorithm decide what to re-render?",
            "category": "technical",
            "tips": [
                "Explain the virtual DOM diffing strategy.",
                "Discuss how `key` props help React identify list items.",
                "Mention React.memo and useMemo for preventing unnecessary re-renders."
            ],
            "answer": "React builds a virtual DOM tree on each render and diffs it against the previous snapshot using a heuristic O(n) algorithm: elements of different types are replaced entirely, and list items are matched by their `key` prop. I wrap pure components in `React.memo` and memoize expensive calculations with `useMemo` to prevent unnecessary re-renders."
        },
        "sql": {
            "question": "Explain your indexing strategy. How do you decide which columns to index?",
            "category": "technical",
            "tips": [
                "Discuss selectivity — high-cardinality columns benefit most from indexes.",
                "Explain composite index column order (most selective first).",
                "Mention write overhead trade-off: more indexes = slower writes."
            ],
            "answer": "I index columns that appear in WHERE, JOIN ON, and ORDER BY clauses and have high cardinality. For composite indexes I put the most selective column first. I use EXPLAIN ANALYZE to verify the planner uses the index. I also avoid over-indexing — every index slows down INSERT/UPDATE, so I only add indexes that address measured slow queries."
        },
        "docker": {
            "question": "How do you optimise a Dockerfile to minimise image size and build time?",
            "category": "technical",
            "tips": [
                "Discuss multi-stage builds to drop build-time tools from the final image.",
                "Explain layer caching — put infrequently changing layers first.",
                "Mention using a minimal base image like `python:3.12-slim`."
            ],
            "answer": "I use multi-stage builds: compile or install dependencies in a full builder image, then COPY only the final artifacts into a minimal base like `alpine` or `slim`. I order Dockerfile instructions so that dependency installation (slow, rarely changed) comes before copying application code (fast, frequently changed), maximising cache reuse."
        },
        "aws": {
            "question": "How would you architect a highly available, auto-scaling web application on AWS?",
            "category": "technical",
            "tips": [
                "Mention multiple AZs for fault tolerance.",
                "Discuss ALB + Auto Scaling Group or ECS/Fargate for containers.",
                "Add RDS Multi-AZ and ElastiCache for the data layer."
            ],
            "answer": "I'd deploy across at least two Availability Zones behind an Application Load Balancer. Compute would be an ECS Fargate service with target-tracking auto-scaling on CPU utilisation. The database would be RDS Aurora with a Multi-AZ read replica. Static assets go on S3 behind CloudFront, and secrets are stored in AWS Secrets Manager."
        },
        "git": {
            "question": "What is your team's Git branching strategy, and how do you handle hotfixes in production?",
            "category": "technical",
            "tips": [
                "Describe Gitflow, GitHub Flow, or trunk-based development.",
                "Explain how a hotfix branch is cut from the production tag.",
                "Mention cherry-pick or merge-back to keep the fix in the main branch."
            ],
            "answer": "We use GitHub Flow: all branches come from `main`, and merges happen via reviewed pull requests. For hotfixes, I cut a `hotfix/` branch directly from the production tag, apply a minimal fix with a regression test, merge it to `main` and the release branch, then tag a new patch release. CI/CD handles deployment automatically."
        },
        "machine learning": {
            "question": "Walk me through how you would build and evaluate a classification model end-to-end.",
            "category": "technical",
            "tips": [
                "Cover data exploration, feature engineering, model selection, and evaluation.",
                "Mention train/val/test split or cross-validation.",
                "Explain why accuracy alone is misleading for imbalanced classes."
            ],
            "answer": "I start with EDA to understand class balance and feature distributions, then clean and engineer features. I split data 70/15/15 for train/val/test. I baseline with Logistic Regression, then try XGBoost. I tune hyperparameters via Optuna on the validation set and evaluate the final model on the held-out test set using F1-score, AUC-ROC, and a confusion matrix — because accuracy is misleading when classes are imbalanced."
        },
        "node": {
            "question": "How does Node.js handle concurrent requests if it is single-threaded?",
            "category": "technical",
            "tips": [
                "Explain the event loop and non-blocking I/O.",
                "Contrast with thread-per-request models.",
                "Mention Worker Threads for CPU-heavy tasks."
            ],
            "answer": "Node.js uses libuv's event loop and non-blocking I/O. When a request triggers a DB query or file read, Node hands it to the OS, immediately moves to the next request, and runs the callback when the result is ready — all on one thread. This is very efficient for I/O-bound workloads. For CPU-intensive work I use Worker Threads or offload to a separate service."
        },
        "typescript": {
            "question": "What are TypeScript generics and how do they improve type safety?",
            "category": "technical",
            "tips": [
                "Show a concrete example like a typed API response wrapper.",
                "Explain generic constraints with `extends`.",
                "Mention how generics avoid `any` while keeping code reusable."
            ],
            "answer": "Generics let you write reusable, type-safe functions without sacrificing flexibility. For example, `function wrap<T>(value: T): { data: T }` works for any type and still gives full autocomplete. I use generic constraints — like `<T extends { id: number }>` — to require that type parameters have specific properties, keeping code both flexible and safe."
        },
        "css": {
            "question": "How does CSS specificity work, and how do you avoid specificity wars in large projects?",
            "category": "technical",
            "tips": [
                "Explain the 0,0,0,0 specificity calculation (inline, IDs, classes, elements).",
                "Mention BEM naming convention to keep specificity flat.",
                "Discuss avoiding !important."
            ],
            "answer": "CSS specificity is calculated as a four-part score: inline styles beat IDs beat class/pseudo-class selectors beat element selectors. In large projects I adopt BEM — every component gets one class like `.card__title--highlighted`, keeping specificity at 0,1,0,0 across the board and making !important unnecessary."
        },
        "data analysis": {
            "question": "Walk me through how you would clean a messy real-world dataset before analysis.",
            "category": "technical",
            "tips": [
                "Cover missing values, duplicates, outliers, and type mismatches.",
                "Mention pandas profiling or describe() for initial exploration.",
                "Explain imputation strategy choice — mean vs median vs forward-fill."
            ],
            "answer": "I start with `df.info()` and `df.describe()` to spot missing values and type issues. I remove exact duplicates, then decide per-column how to handle nulls: numerical columns get median imputation (robust to outliers), categorical columns get mode or a dedicated 'Unknown' category. I clip or log-transform outliers that skew distributions, then validate with domain knowledge."
        }
    }

    # Role-specific bonus technical questions
    role_tech_db = {
        "web developer": [
            {
                "question": "Explain the browser's critical rendering path and how you optimise it for performance.",
                "category": "technical",
                "tips": [
                    "Cover HTML parsing → DOM, CSS parsing → CSSOM, Layout, Paint, Composite.",
                    "Mention render-blocking scripts and how `defer`/`async` help.",
                    "Discuss lazy loading images and code splitting."
                ],
                "answer": "The browser parses HTML to build the DOM and CSS to build the CSSOM, merges them into a render tree, calculates layout, paints pixels, and composites layers. Render-blocking scripts delay this entire process. I optimise by adding `defer` to non-critical JS, inlining critical CSS above the fold, lazy-loading below-the-fold images with `loading='lazy'`, and code-splitting to ship only what the current page needs."
            }
        ],
        "data scientist": [
            {
                "question": "What is the bias-variance trade-off and how does it guide model selection?",
                "category": "technical",
                "tips": [
                    "Define bias (underfitting) and variance (overfitting).",
                    "Explain that increasing model complexity reduces bias but raises variance.",
                    "Mention regularisation and cross-validation as balancing tools."
                ],
                "answer": "Bias measures how far a model's average predictions are from the truth — high-bias models underfit. Variance measures sensitivity to training data — high-variance models overfit. As model complexity increases, bias decreases but variance increases. I navigate this trade-off using cross-validation to detect overfitting early and regularisation (L1/L2 or dropout) to penalise complexity without sacrificing accuracy."
            }
        ],
        "software engineer": [
            {
                "question": "How do you design a system to handle 1 million concurrent users?",
                "category": "technical",
                "tips": [
                    "Cover horizontal scaling, load balancing, caching, CDNs.",
                    "Discuss stateless services vs stateful sessions.",
                    "Mention database read replicas and eventual consistency."
                ],
                "answer": "I'd design stateless application servers behind a load balancer so any instance can serve any request. A CDN handles static assets globally. Frequently read data goes into distributed cache (Redis). The database uses read replicas to offload query load, with writes going to the primary. For extremely high write throughput I'd use an event queue (Kafka) to decouple producers from consumers and absorb spikes."
            }
        ],
        "devops": [
            {
                "question": "Explain how you would set up a zero-downtime deployment pipeline.",
                "category": "technical",
                "tips": [
                    "Discuss blue-green deployments or rolling deployments.",
                    "Mention health checks and automatic rollback on failure.",
                    "Explain feature flags as a decoupling strategy."
                ],
                "answer": "I implement blue-green deployments: two identical environments alternate as active. New code deploys to the idle environment, health checks run, and the load balancer shifts traffic in seconds. On failure the switch is instantly reversed. I also use feature flags so code can be shipped before a feature is exposed, decoupling deployment from release risk entirely."
            }
        ]
    }

    used_skills = [s.lower() for s in matched_skills] if matched_skills else []
    role_lower = (job_description or '').lower()

    # Collect skill-matched technical questions
    tech_questions = []
    used_keys = set()
    for skill in used_skills:
        if skill in tech_db and skill not in used_keys and len(tech_questions) < 5:
            tech_questions.append(tech_db[skill].copy())
            used_keys.add(skill)

    # Inject role-specific questions at the front
    for role_key, role_q_list in role_tech_db.items():
        if role_key in role_lower:
            for rq in role_q_list:
                if len(tech_questions) < 5:
                    tech_questions.insert(0, rq.copy())

    # Fallback general technical questions
    general_fallbacks = [
        {
            "question": "How do you write clean, maintainable code? Which principles do you follow?",
            "category": "technical",
            "tips": [
                "Name specific principles: SOLID, DRY, YAGNI.",
                "Mention code review practice and automated linting.",
                "Talk about how naming matters as much as logic."
            ],
            "answer": "I follow SOLID and DRY — every piece of knowledge should have one authoritative representation. Functions do one thing and are named to reveal intent. I enforce style via a linter in CI so style debates never reach code review. I also practise YAGNI — I don't add abstractions until a second use case proves them necessary."
        },
        {
            "question": "Explain the difference between REST and GraphQL and when you would choose each.",
            "category": "technical",
            "tips": [
                "REST has multiple resource-specific endpoints; GraphQL has one.",
                "Explain over-fetching and under-fetching.",
                "Mention GraphQL's cost for simple CRUD vs REST's cost for complex nested data."
            ],
            "answer": "REST exposes dedicated endpoints per resource — clean and cache-friendly, but clients often get too much or too little data. GraphQL exposes a single endpoint where the client declares exactly what fields it needs, eliminating over-fetching. I choose REST for simple public APIs where HTTP caching matters, and GraphQL when the front-end needs varied nested data in one round trip."
        },
        {
            "question": "How do you approach debugging a production issue you cannot reproduce locally?",
            "category": "technical",
            "tips": [
                "Discuss structured logging and correlation IDs.",
                "Mention feature flags to isolate the issue to a subset of users.",
                "Explain reproducing with anonymised production data snapshots."
            ],
            "answer": "I start with structured logs and distributed traces using correlation IDs to reconstruct the exact request path. If the bug is intermittent, I add targeted debug logging behind a feature flag for a small user cohort. If data is the culprit I create an anonymised snapshot of the production dataset and reproduce the issue in a safe local environment."
        },
        {
            "question": "What strategies do you use for securing a web application?",
            "category": "technical",
            "tips": [
                "Cover OWASP Top 10: XSS, SQL injection, CSRF.",
                "Mention authentication: OAuth2, JWT expiry, refresh tokens.",
                "Discuss HTTPS, HSTS, CSP headers."
            ],
            "answer": "I follow the OWASP Top 10 as a baseline. SQL injection is prevented with parameterised queries. XSS is mitigated with Content-Security-Policy headers and output escaping. CSRF is prevented with SameSite cookies and anti-CSRF tokens. Auth tokens are short-lived JWTs with refresh token rotation. All traffic is HTTPS-only enforced by HSTS headers."
        },
        {
            "question": "How do you ensure the quality of your code before it goes to production?",
            "category": "technical",
            "tips": [
                "Cover the testing pyramid: unit, integration, e2e.",
                "Mention automated CI gates: tests, lint, security scan.",
                "Discuss code review best practices."
            ],
            "answer": "I use the testing pyramid: many fast unit tests covering business logic, integration tests covering service boundaries, and a small e2e suite for critical user flows. Every pull request must pass lint, unit tests, and a security dependency scan before human review. Code reviews focus on logic correctness and edge cases — style is handled by the linter."
        }
    ]

    while len(tech_questions) < 5:
        for fb in general_fallbacks:
            if fb not in tech_questions:
                tech_questions.append(fb)
                break
        else:
            break

    questions.extend(tech_questions[:5])

    # ── 3. Situational / role-aware (4) ──────────────────────────────────────
    role_label = job_description.split()[0] if job_description and job_description.strip() else 'team member'
    situational_pool = [
        {
            "question": f"You are hired as a {role_label}. What would your plan be in the first 30 days to add value quickly?",
            "category": "situational",
            "tips": [
                "Show initiative: learn the codebase, talk to stakeholders, ask questions.",
                "Mention quick wins — small but visible contributions in week one.",
                "Explain how you balance learning with delivering."
            ],
            "answer": "Week one: read the codebase, run the product end-to-end, and ask teammates about the biggest pain points. Week two: pick a small but meaningful bug or improvement, deliver it fully with tests, and get it merged. Week three onward: propose an improvement to one process or document something undocumented. By day 30 I want to have shipped at least one thing and have a clear picture of where I can contribute most."
        },
        {
            "question": "How would you handle a situation where a key feature your team built suddenly underperforms in production?",
            "category": "situational",
            "tips": [
                "Prioritise user impact — communicate status before diving into code.",
                "Systematic diagnosis: logs → metrics → code.",
                "Discuss rollback vs hotfix decision-making."
            ],
            "answer": "First I'd check monitoring to scope the blast radius — how many users affected, which regions, since when. I'd post a status update to stakeholders within five minutes. Then I'd review recent deployments and check error logs. If a recent deploy correlates with the issue I'd initiate a rollback immediately. If the cause is unclear I'd gather more data with added logging and apply a targeted hotfix."
        },
        {
            "question": "If your manager gives you two equally urgent tasks but you can only complete one by end of day, how do you decide?",
            "category": "situational",
            "tips": [
                "Show structured prioritisation — not guessing.",
                "Communicate the trade-off to your manager proactively.",
                "Offer a partial delivery plan for the second task."
            ],
            "answer": "I'd quickly assess both tasks on two dimensions: business impact (revenue, user-facing, deadline-driven?) and effort (can task B be 80% done today and finished tomorrow?). I'd share my thinking with my manager in two sentences and get explicit alignment — they may have context I don't. I'd then time-box the chosen task and prepare a handoff plan for the second task."
        },
        {
            "question": "A junior teammate submits code that works but is poorly written and hard to maintain. How do you handle the code review?",
            "category": "situational",
            "tips": [
                "Balance honest feedback with encouragement.",
                "Use specific, actionable comments — not vague criticism.",
                "Offer to pair-program or point to a reference implementation."
            ],
            "answer": "I'd leave specific, kind review comments explaining *why* each change matters — e.g., 'This function does three things; splitting it makes unit testing each part much easier.' I'd avoid language like 'this is wrong' and use 'I'd suggest…' or 'here's a pattern that helps here.' If there are many comments I'd offer a 30-minute pair-programming session so they learn the patterns rather than just patching individual lines."
        }
    ]
    questions.extend(situational_pool[:4])

    return questions[:12]


def generate_cover_letter(resume_text, job_title, company_name, tone='professional'):
    """Generate a 3-4 paragraph cover letter using extracted resume skills."""
    skills = extract_skills(resume_text)
    top_skills = ', '.join(skills[:5]) if skills else 'a diverse technical skill set'
    secondary_skills = ', '.join(skills[5:10]) if len(skills) > 5 else 'strong problem-solving abilities'

    today_str = datetime.now().strftime('%B %d, %Y')

    # Tone adjustments
    if tone == 'enthusiastic':
        opening_adj = "thrilled"
        closing_adj = "I am genuinely excited about the possibility of contributing to"
        sign_off = "With enthusiasm,"
    elif tone == 'creative':
        opening_adj = "inspired"
        closing_adj = "I would love the chance to bring my creativity and skills to"
        sign_off = "Creatively yours,"
    else:  # professional
        opening_adj = "writing to express my strong interest in"
        closing_adj = "I am confident that my experience and skills would be a valuable addition to"
        sign_off = "Sincerely,"

    letter = f"""{today_str}

Dear Hiring Manager,

I am {opening_adj} the {job_title} position at {company_name}. With hands-on expertise in {top_skills}, I am confident I can contribute meaningfully to your team from day one. My background combines technical proficiency with a results-driven approach that aligns well with the demands of this role.

Throughout my career, I have developed strong competencies in {secondary_skills}. I have consistently delivered projects that improve efficiency, reduce costs, and drive measurable business outcomes. Whether building scalable systems, collaborating with cross-functional teams, or mentoring junior colleagues, I bring the same commitment to quality and continuous improvement.

{closing_adj} {company_name}. I am eager to discuss how my experience with {top_skills} can help your organization achieve its goals. I welcome the opportunity to speak with you further about how I can add value to the {job_title} role.

Thank you for considering my application. I look forward to the possibility of contributing to {company_name}'s continued success.

{sign_off}
[Your Name]
"""
    return letter.strip()


def generate_career_roadmap(current_skills, target_role):
    """Return a career-roadmap dict with milestones, level assessment, and resources."""
    current_set = {s.lower() for s in current_skills}

    # Determine target skills from JOB_DATABASE if possible
    target_skills = set()
    for job in JOB_DATABASE:
        if target_role.lower() in job['title'].lower():
            target_skills = set(job['required_skills'])
            break
    if not target_skills:
        # Fallback to general senior-dev skills
        target_skills = {'python', 'docker', 'aws', 'sql', 'rest api', 'git', 'leadership'}

    overlap = current_set & target_skills
    gap = target_skills - current_set

    # Level assessment
    ratio = len(overlap) / max(len(target_skills), 1)
    if ratio >= 0.8:
        level = 'Advanced – you already possess most required skills'
    elif ratio >= 0.5:
        level = 'Intermediate – solid foundation, some gaps to fill'
    elif ratio >= 0.2:
        level = 'Early-Intermediate – foundational skills present, significant growth needed'
    else:
        level = 'Beginner – substantial up-skilling required for this role'

    # Build milestones
    gap_list = list(gap)
    milestones = []

    if gap_list:
        chunk_size = max(1, len(gap_list) // 4)
        chunks = [gap_list[i:i + chunk_size] for i in range(0, len(gap_list), chunk_size)]
        milestone_titles = [
            ('Foundation Building', '0 – 2 months', 'Learn the foundational technologies required for the role.'),
            ('Core Skill Development', '2 – 4 months', 'Deepen expertise in the core tools and frameworks.'),
            ('Project Application', '4 – 6 months', 'Apply new skills in real or portfolio projects to build credibility.'),
            ('Advanced Mastery', '6 – 9 months', 'Master advanced concepts and best practices.'),
            ('Interview Readiness', '9 – 10 months', 'Practice coding challenges, system design, and behavioral interviews.'),
            ('Role Transition', '10 – 12 months', 'Start applying and networking for the target role.'),
        ]
        for idx, chunk in enumerate(chunks[:6]):
            title, timeframe, desc = milestone_titles[idx % len(milestone_titles)]
            milestones.append({
                'title': title,
                'description': desc,
                'skills_to_learn': chunk,
                'timeframe': timeframe,
            })
    else:
        milestones.append({
            'title': 'Portfolio & Visibility',
            'description': 'You have the skills — focus on showcasing them through projects and open-source contributions.',
            'skills_to_learn': [],
            'timeframe': '0 – 2 months',
        })
        milestones.append({
            'title': 'Interview Preparation',
            'description': 'Practice system design, coding challenges, and behavioral interview questions.',
            'skills_to_learn': [],
            'timeframe': '2 – 3 months',
        })

    encoded_role = target_role.replace(' ', '+')
    resources = [
        {
            'name': 'Coursera Courses',
            'url': f'https://www.coursera.org/search?query={encoded_role}'
        },
        {
            'name': 'Udemy Courses',
            'url': f'https://www.udemy.com/courses/search/?q={encoded_role}'
        },
        {
            'name': 'LeetCode Coding Practice',
            'url': 'https://leetcode.com/problemset/all/'
        },
        {
            'name': 'GitHub Open Source Projects',
            'url': f'https://github.com/search?q={encoded_role}&type=repositories'
        },
        {
            'name': 'Meetup Tech Events',
            'url': f'https://www.meetup.com/find/?keywords={encoded_role}'
        },
        {
            'name': 'Pramp Mock Interviews',
            'url': 'https://www.pramp.com/'
        }
    ]

    return {
        'current_level': level,
        'target_role': target_role,
        'matched_count': len(overlap),
        'gap_count': len(gap),
        'milestones': milestones,
        'recommended_resources': resources,
    }


def get_job_recommendations(skills):
    """Return 5-6 job recommendations with match percentages."""
    user_skills = {s.lower() for s in skills}
    scored_jobs = []

    for job in JOB_DATABASE:
        required = set(job['required_skills'])
        if not required:
            continue
        matched = user_skills & required
        pct = round(len(matched) / len(required) * 100, 1)
        scored_jobs.append({
            'title': job['title'],
            'match_percentage': pct,
            'required_skills': job['required_skills'],
            'description': job['description'],
        })

    scored_jobs.sort(key=lambda j: j['match_percentage'], reverse=True)
    return scored_jobs[:6]


def chatbot_response(message, user_context=None):
    """Simple intent-based chatbot for resume and career advice."""
    msg = message.lower().strip()

    # Greeting
    if any(w in msg for w in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
        return (
            "Hello! 👋 I'm your ResumeAI assistant. I can help with ATS scores, "
            "resume tips, interview prep, skill recommendations, and career advice. "
            "What would you like to know?"
        )

    # ATS score questions
    if 'ats' in msg or 'applicant tracking' in msg or 'score' in msg:
        return (
            "ATS (Applicant Tracking System) scores measure how well your resume "
            "matches a job description. Our analyzer uses TF-IDF and cosine similarity "
            "to compute the overlap between your resume and the job posting. A score "
            "above 70 % is generally considered strong. To improve your score:\n"
            "• Use keywords from the job description verbatim.\n"
            "• Stick to standard section headings (Experience, Education, Skills).\n"
            "• Avoid images, tables, and unusual formatting that ATS parsers may skip."
        )

    # Resume tips
    if any(w in msg for w in ['resume', 'cv', 'format', 'template', 'write']):
        return (
            "Here are some top resume tips:\n"
            "• Keep it to 1-2 pages — concise and relevant.\n"
            "• Use reverse-chronological order for experience.\n"
            "• Start each bullet with a strong action verb.\n"
            "• Quantify achievements (e.g., 'Increased revenue by 25 %').\n"
            "• Tailor your resume for every application.\n"
            "• Use a clean, ATS-friendly template with standard fonts."
        )

    # Skills advice
    if any(w in msg for w in ['skill', 'learn', 'trending', 'technology', 'tech stack']):
        return (
            "Trending skills employers are looking for in 2024–2025:\n"
            "• AI / ML: Python, TensorFlow, PyTorch, LLMs, prompt engineering\n"
            "• Cloud: AWS, Azure, GCP, Kubernetes, Terraform\n"
            "• Web: React, Next.js, TypeScript, Tailwind CSS\n"
            "• Data: SQL, Spark, dbt, data visualization\n"
            "• Soft: Communication, leadership, agile/scrum\n"
            "Focus on the intersection of your interests and market demand!"
        )

    # Interview tips
    if any(w in msg for w in ['interview', 'prepare', 'question', 'behavioral']):
        return (
            "Interview preparation tips:\n"
            "• Research the company's products, culture, and recent news.\n"
            "• Practice the STAR method (Situation, Task, Action, Result) for behavioral questions.\n"
            "• Review common data-structure and algorithm problems for coding rounds.\n"
            "• Prepare 3-5 thoughtful questions to ask the interviewer.\n"
            "• Do mock interviews with friends or platforms like Pramp.\n"
            "• Dress appropriately and test your tech setup for virtual interviews."
        )

    # Career advice
    if any(w in msg for w in ['career', 'path', 'growth', 'promotion', 'transition', 'switch']):
        return (
            "Career growth strategies:\n"
            "• Identify your target role and map the skills gap.\n"
            "• Build a portfolio of projects that demonstrate your abilities.\n"
            "• Contribute to open source to gain visibility.\n"
            "• Network at meetups, conferences, and on LinkedIn.\n"
            "• Seek mentors who have the role you aspire to.\n"
            "• Use our Career Roadmap feature to get a personalized plan!"
        )

    # Salary / negotiation
    if any(w in msg for w in ['salary', 'negotiat', 'pay', 'compensation']):
        return (
            "Salary negotiation tips:\n"
            "• Research market rates on Glassdoor, Levels.fyi, and Payscale.\n"
            "• Let the employer make the first offer when possible.\n"
            "• Negotiate total compensation — base, bonus, equity, benefits.\n"
            "• Be confident but collaborative in tone.\n"
            "• Practice your pitch so you can articulate your value clearly."
        )

    # Default
    return (
        "That's a great question! While I specialize in resume optimization, ATS "
        "scoring, interview prep, and career advice, I'm happy to help however I can. "
        "Try asking me about:\n"
        "• How to improve your ATS score\n"
        "• Resume formatting best practices\n"
        "• Trending skills to learn\n"
        "• Interview preparation strategies\n"
        "• Career growth and transitions"
    )


def generate_keyword_analysis(resume_text, job_description):
    """Analyze keyword density between resume and job description."""
    job_skills = extract_skills(job_description)
    resume_lower = resume_text.lower()

    keyword_matches = []
    matched_count = 0

    # Score importance based on frequency in JD
    jd_lower = job_description.lower()
    for skill in job_skills:
        in_resume = bool(re.search(r'\b' + re.escape(skill) + r'\b', resume_lower))
        freq = len(re.findall(r'\b' + re.escape(skill) + r'\b', jd_lower))
        if freq >= 3:
            importance = 'high'
        elif freq >= 2:
            importance = 'medium'
        else:
            importance = 'low'
        keyword_matches.append({
            'keyword': skill,
            'in_resume': in_resume,
            'importance': importance,
        })
        if in_resume:
            matched_count += 1

    density_score = round(matched_count / max(len(job_skills), 1) * 100, 1)

    tips = []
    high_missing = [k['keyword'] for k in keyword_matches if not k['in_resume'] and k['importance'] == 'high']
    if high_missing:
        tips.append(f"Add these HIGH-importance missing keywords: {', '.join(high_missing)}.")
    medium_missing = [k['keyword'] for k in keyword_matches if not k['in_resume'] and k['importance'] == 'medium']
    if medium_missing:
        tips.append(f"Consider adding these MEDIUM-importance keywords: {', '.join(medium_missing)}.")
    if density_score >= 80:
        tips.append("Excellent keyword coverage! Focus on contextualizing each keyword within achievements.")
    elif density_score >= 50:
        tips.append("Decent coverage, but adding more matched keywords could boost your ATS ranking.")
    else:
        tips.append("Low keyword density. Rewrite experience bullets to naturally incorporate job-description terms.")

    return {
        'keyword_matches': keyword_matches,
        'density_score': density_score,
        'optimization_tips': tips,
    }

def generate_detailed_analysis(resume_text, job_description, matched_skills, missing_skills, ats_score):
    """
    Generates a comprehensive JSON-serializable dictionary containing 
    advanced recruiter-style ATS analysis inspired by Cake.me.
    """
    import random
    
    # 1. Sub-Scores
    job_match_score = ats_score
    word_count = len(resume_text.split())
    quality_score = min(100, int(word_count / 5 + 40))
    completeness_score = min(100, int(len(matched_skills) * 2 + 50))
    
    # Recruiter Recommendation
    if ats_score >= 80:
        recommendation = "Strong Match"
    elif ats_score >= 60:
        recommendation = "Good Match"
    elif ats_score >= 40:
        recommendation = "Average Match"
    else:
        recommendation = "Needs Improvement"
        
    # 2. Categorized Skills
    categories = {
        'Technical Skills': ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 'php', 'sql', 'html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'next.js', 'tailwind'],
        'Data & AI': ['machine learning', 'deep learning', 'data science', 'data analysis', 'natural language processing', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn'],
        'Soft Skills': ['leadership', 'communication', 'teamwork', 'agile', 'scrum', 'problem solving', 'project management'],
        'Cloud & DevOps': ['aws', 'azure', 'google cloud', 'docker', 'kubernetes', 'ci/cd', 'linux', 'git', 'terraform']
    }
    
    categorized = {}
    for cat, pool in categories.items():
        cat_matched = [s for s in matched_skills if s in pool]
        cat_missing = [s for s in missing_skills if s in pool]
        if cat_matched or cat_missing:
            score = 0
            total = len(cat_matched) + len(cat_missing)
            if total > 0:
                score = int((len(cat_matched) / total) * 100)
            categorized[cat] = {
                'matched': cat_matched,
                'missing': cat_missing,
                'score': score
            }
            
    # 3. Section Analysis
    sections = [
        {'name': 'Professional Summary', 'required': True, 'keywords': ['summary', 'profile', 'about me', 'objective']},
        {'name': 'Work Experience', 'required': True, 'keywords': ['experience', 'employment', 'history', 'work']},
        {'name': 'Education', 'required': True, 'keywords': ['education', 'degree', 'university', 'college']},
        {'name': 'Skills', 'required': True, 'keywords': ['skills', 'technologies', 'core competencies']},
        {'name': 'Projects', 'required': False, 'keywords': ['projects', 'portfolio']}
    ]
    
    section_analysis = []
    resume_lower = resume_text.lower()
    for sec in sections:
        found = any(kw in resume_lower for kw in sec['keywords'])
        score = 100 if found else 0
        status = "Excellent" if found else ("Missing" if sec['required'] else "Optional")
        suggestions = ["Section looks complete and well-formatted."] if found else [f"Consider adding a {sec['name']} section to improve your score."]
        section_analysis.append({
            'section': sec['name'],
            'score': score,
            'status': status,
            'suggestions': suggestions
        })
        
    # 4. ATS Format Check
    format_issues = []
    if "table" in resume_lower or "grid" in resume_lower:
        format_issues.append({'issue': 'Tables Detected', 'type': 'high', 'desc': 'Tables can break traditional ATS parsers.'})
    if "column" in resume_lower:
        format_issues.append({'issue': 'Multi-column Layout', 'type': 'medium', 'desc': 'Two-column layouts may be read out of order by older systems.'})
    if not format_issues:
        format_issues.append({'issue': 'No major formatting issues detected', 'type': 'success', 'desc': 'Your resume appears to be ATS-friendly.'})
        
    # 5. AI Rewrite Suggestions
    improvements = []
    if "helped" in resume_lower or "assisted" in resume_lower:
        improvements.append({
            'original': 'Helped the team build the new product feature.',
            'improved': 'Collaborated with a cross-functional team to engineer a new product feature, increasing user engagement by 15%.'
        })
    if "managed" in resume_lower:
        improvements.append({
            'original': 'Managed a team of developers.',
            'improved': 'Spearheaded a team of 5 developers, orchestrating agile workflows that accelerated project delivery by 2 weeks.'
        })
    if not improvements:
        improvements.append({
            'original': 'Worked on various tasks to improve performance.',
            'improved': 'Optimized application performance through proactive troubleshooting, resulting in a 20% reduction in load times.'
        })

    return {
        'scores': {
            'ats': ats_score,
            'match': job_match_score,
            'quality': quality_score,
            'completeness': completeness_score,
            'recommendation': recommendation
        },
        'categorized_skills': categorized,
        'section_analysis': section_analysis,
        'format_issues': format_issues,
        'ai_improvements': improvements,
        'recruiter_insights': {
            'verdict': recommendation,
            'interview_probability': min(95, int(ats_score + 15)),
            'strengths': ['Strong alignment with core technologies'] if matched_skills else ['Clear section headings detected'],
            'concerns': [f'Missing critical skill: {missing_skills[0]}'] if missing_skills else ['Ensure metrics are quantified across all roles']
        }
    }


def generate_pdf_report(result_data, filepath):
    """Generate a professionally styled PDF report using ReportLab."""
    primary = HexColor('#6C63FF')
    secondary = HexColor('#00D2FF')
    dark = HexColor('#1a1a2e')
    white = HexColor('#FFFFFF')
    light_gray = HexColor('#F5F5F5')

    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=26,
        textColor=primary,
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=dark,
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=15,
        textColor=primary,
        spaceBefore=18,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        'BodyText2',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=dark,
        leading=14,
        alignment=TA_LEFT,
    )
    bullet_style = ParagraphStyle(
        'BulletItem',
        parent=body_style,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=4,
    )

    elements = []

    # --- Header ---
    elements.append(Paragraph('ResumeAI', title_style))
    elements.append(Paragraph('AI-Powered Resume Analysis Report', subtitle_style))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        ParagraphStyle('DateLine', parent=subtitle_style, fontSize=9, textColor=HexColor('#888888'))
    ))
    elements.append(HRFlowable(width='100%', thickness=2, color=primary, spaceAfter=16))

    # --- ATS Score ---
    elements.append(Paragraph('ATS Compatibility Score', section_style))
    score = result_data.get('ats_score', 0)
    if score >= 70:
        score_color = HexColor('#27ae60')
        verdict = 'Strong Match'
    elif score >= 40:
        score_color = HexColor('#f39c12')
        verdict = 'Moderate Match'
    else:
        score_color = HexColor('#e74c3c')
        verdict = 'Needs Improvement'

    score_table_data = [
        [
            Paragraph(f'<font size="36" color="{score_color.hexval()}">{score}%</font>', ParagraphStyle('ScoreBig', alignment=TA_CENTER)),
            Paragraph(f'<font size="14" color="{dark.hexval()}">{verdict}</font>', ParagraphStyle('Verdict', alignment=TA_CENTER, spaceBefore=12)),
        ]
    ]
    score_table = Table(score_table_data, colWidths=[3 * inch, 4 * inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_gray),
        ('BOX', (0, 0), (-1, -1), 1, primary),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 12))

    # --- Matched Skills ---
    matched = result_data.get('matched_skills', [])
    elements.append(Paragraph('Matched Skills', section_style))
    if matched:
        for skill in matched:
            elements.append(Paragraph(f'✓  {skill}', bullet_style))
    else:
        elements.append(Paragraph('No matching skills detected.', body_style))
    elements.append(Spacer(1, 8))

    # --- Missing Skills ---
    missing = result_data.get('missing_skills', [])
    elements.append(Paragraph('Missing Skills', section_style))
    if missing:
        for skill in missing:
            elements.append(Paragraph(f'✗  {skill}', bullet_style))
    else:
        elements.append(Paragraph('No critical skill gaps — great job!', body_style))
    elements.append(Spacer(1, 8))

    # --- AI Suggestions ---
    suggestions = result_data.get('suggestions', [])
    elements.append(Paragraph('AI Suggestions', section_style))
    for idx, suggestion in enumerate(suggestions, 1):
        elements.append(Paragraph(f'{idx}. {suggestion}', bullet_style))
    elements.append(Spacer(1, 8))

    # --- Interview Questions ---
    questions = result_data.get('interview_questions', [])
    elements.append(Paragraph('Recommended Interview Questions', section_style))
    for idx, question in enumerate(questions, 1):
        elements.append(Paragraph(f'{idx}. {question}', bullet_style))

    # --- Footer (via onPage callback is simplest but we add a final line) ---
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width='100%', thickness=1, color=HexColor('#cccccc'), spaceAfter=6))
    elements.append(Paragraph(
        'Generated by ResumeAI — AI-Powered Resume Analyzer',
        ParagraphStyle('Footer', parent=body_style, fontSize=8, textColor=HexColor('#aaaaaa'), alignment=TA_CENTER),
    ))

    doc.build(elements)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    full_name = request.form.get('full_name', '').strip()

    if not username or not email or not password:
        flash('All fields are required.', 'danger')
        return redirect(url_for('signup'))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, email, password_hash, full_name) VALUES (?, ?, ?, ?)",
            (username, email, generate_password_hash(password), full_name),
        )
        db.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    except sqlite3.IntegrityError:
        flash('Username or email already exists.', 'danger')
        return redirect(url_for('signup'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        flash(f"Welcome back, {user['username']}!", 'success')
        return redirect(url_for('dashboard'))

    flash('Invalid username or password.', 'danger')
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out. See you next time!', 'info')
    return redirect(url_for('index'))


@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/authorize/google')
def authorize_google():
    token = oauth.google.authorize_access_token()
    if not token:
        flash("Failed to authenticate with Google.", "danger")
        return redirect(url_for('login'))
        
    user_info = token.get('userinfo')
    if not user_info:
        flash("Failed to retrieve user info from Google.", "danger")
        return redirect(url_for('login'))
        
    google_id = user_info.get('sub')
    email = user_info.get('email')
    name = user_info.get('name')
    picture = user_info.get('picture')
    
    db = get_db()
    
    # Try to find user by google_id or email
    user = db.execute("SELECT * FROM users WHERE google_id = ? OR email = ?", (google_id, email)).fetchone()
    
    if user:
        # Update google_id and picture if they log in via email previously
        db.execute(
            "UPDATE users SET google_id = ?, profile_picture_url = ? WHERE id = ?",
            (google_id, picture, user['id'])
        )
        db.commit()
        
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        flash(f"Welcome back, {user['username']}!", 'success')
        return redirect(url_for('dashboard'))
    else:
        # Create new user
        username = email.split('@')[0]
        # Ensure unique username
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            username = f"{username}_{secrets.token_hex(2)}"
            
        dummy_password = generate_password_hash(secrets.token_urlsafe(16))
        
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash, full_name, google_id, profile_picture_url) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, dummy_password, name, google_id, picture)
        )
        db.commit()
        
        session['user_id'] = cursor.lastrowid
        session['username'] = username
        session['role'] = 'user'
        flash(f"Account created successfully! Welcome, {username}!", 'success')
        return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    resumes = db.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 10",
        (session['user_id'],),
    ).fetchall()

    stats_row = db.execute(
        "SELECT COUNT(*) as total_analyses, COALESCE(AVG(ats_score), 0) as average_score "
        "FROM resumes WHERE user_id = ?",
        (session['user_id'],),
    ).fetchone()

    total_reports = db.execute(
        "SELECT COUNT(*) as cnt FROM reports WHERE user_id = ?",
        (session['user_id'],),
    ).fetchone()['cnt']

    stats = {
        'total_analyses': stats_row['total_analyses'],
        'average_score': round(stats_row['average_score'], 1),
        'total_reports': total_reports,
    }

    return render_template('dashboard.html', user=user, resumes=resumes, stats=stats)


@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    if 'resume' not in request.files:
        flash('No file uploaded.', 'danger')
        return redirect(url_for('dashboard'))

    file = request.files['resume']
    job_description = request.form.get('job_description', '').strip()

    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('dashboard'))

    if not allowed_file(file.filename):
        flash('Only PDF files are allowed.', 'danger')
        return redirect(url_for('dashboard'))

    if not job_description:
        flash('Please provide a job description.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        safe_name = f"{session['user_id']}_{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        file.save(filepath)

        resume_text = extract_text_from_pdf(filepath)
        if not resume_text.strip():
            flash('Could not extract text from PDF. Please try a different file.', 'danger')
            return redirect(url_for('dashboard'))

        ats_score = calculate_ats_score(resume_text, job_description)
        resume_skills = extract_skills(resume_text)
        job_skills = extract_skills(job_description)
        matched_skills = [s for s in resume_skills if s in job_skills]
        missing_skills = get_missing_skills(resume_skills, job_skills)
        suggestions = generate_suggestions(ats_score, matched_skills, missing_skills, resume_text)
        interview_questions = generate_interview_questions(job_description, matched_skills)
        detailed_analysis = generate_detailed_analysis(resume_text, job_description, matched_skills, missing_skills, ats_score)

        db = get_db()
        cur = db.execute(
            """INSERT INTO resumes
               (user_id, filename, original_text, job_description, ats_score,
                matched_skills, missing_skills, suggestions, interview_questions, detailed_analysis)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session['user_id'], safe_name, resume_text, job_description,
                ats_score,
                json.dumps(matched_skills),
                json.dumps(missing_skills),
                json.dumps(suggestions),
                json.dumps(interview_questions),
                json.dumps(detailed_analysis),
            ),
        )
        db.commit()
        resume_id = cur.lastrowid

        # Generate PDF report
        report_name = f"report_{session['user_id']}_{resume_id}.pdf"
        report_path = os.path.join(app.config['REPORTS_FOLDER'], report_name)
        report_data = {
            'ats_score': ats_score,
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'suggestions': suggestions,
            'interview_questions': interview_questions,
        }
        generate_pdf_report(report_data, report_path)

        db.execute(
            "INSERT INTO reports (user_id, resume_id, report_data, pdf_path) VALUES (?, ?, ?, ?)",
            (session['user_id'], resume_id, json.dumps(report_data), report_path),
        )
        db.commit()

        flash('Resume analyzed successfully!', 'success')
        return redirect(url_for('result', resume_id=resume_id))

    except Exception as exc:
        flash(f'An error occurred during analysis: {str(exc)}', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/result/<int:resume_id>')
@login_required
def result(resume_id):
    db = get_db()
    resume = db.execute(
        "SELECT * FROM resumes WHERE id = ? AND user_id = ?",
        (resume_id, session['user_id']),
    ).fetchone()

    if not resume:
        flash('Resume not found.', 'danger')
        return redirect(url_for('dashboard'))

    matched_skills = json.loads(resume['matched_skills'] or '[]')
    missing_skills = json.loads(resume['missing_skills'] or '[]')
    suggestions = json.loads(resume['suggestions'] or '[]')
    interview_questions = json.loads(resume['interview_questions'] or '[]')
    detailed_analysis = json.loads(resume['detailed_analysis'] or '{}')

    keyword_analysis = generate_keyword_analysis(
        resume['original_text'] or '', resume['job_description'] or ''
    )
    job_recommendations = get_job_recommendations(matched_skills)

    return render_template(
        'result.html',
        resume=resume,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        suggestions=suggestions,
        interview_questions=interview_questions,
        keyword_analysis=keyword_analysis,
        job_recommendations=job_recommendations,
        detailed_analysis=detailed_analysis,
    )


@app.route('/download_report/<int:resume_id>')
@login_required
def download_report(resume_id):
    db = get_db()
    report = db.execute(
        "SELECT * FROM reports WHERE resume_id = ? AND user_id = ?",
        (resume_id, session['user_id']),
    ).fetchone()

    if not report or not report['pdf_path']:
        flash('Report not found.', 'danger')
        return redirect(url_for('dashboard'))

    if not os.path.exists(report['pdf_path']):
        flash('Report file is missing. Please re-analyze your resume.', 'danger')
        return redirect(url_for('dashboard'))

    return send_file(
        report['pdf_path'],
        as_attachment=True,
        download_name=f"ResumeAI_Report_{resume_id}.pdf",
    )


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        dark_mode = 1 if request.form.get('dark_mode') else 0
        db.execute(
            "UPDATE users SET full_name = ?, dark_mode = ? WHERE id = ?",
            (full_name, dark_mode, session['user_id']),
        )
        db.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


@app.route('/history')
@login_required
def history():
    db = get_db()
    resumes = db.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC",
        (session['user_id'],),
    ).fetchall()
    return render_template('history.html', resumes=resumes)


@app.route('/delete_resume/<int:resume_id>', methods=['POST'])
@login_required
def delete_resume(resume_id):
    db = get_db()
    resume = db.execute(
        "SELECT * FROM resumes WHERE id = ? AND user_id = ?",
        (resume_id, session['user_id']),
    ).fetchone()

    if not resume:
        flash('Resume not found.', 'danger')
        return redirect(url_for('history'))

    # Delete associated report file
    report = db.execute("SELECT * FROM reports WHERE resume_id = ?", (resume_id,)).fetchone()
    if report and report['pdf_path'] and os.path.exists(report['pdf_path']):
        try:
            os.remove(report['pdf_path'])
        except OSError:
            pass

    # Delete uploaded PDF
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], resume['filename'])
    if os.path.exists(upload_path):
        try:
            os.remove(upload_path)
        except OSError:
            pass

    db.execute("DELETE FROM reports WHERE resume_id = ?", (resume_id,))
    db.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
    db.commit()

    flash('Resume and associated report deleted.', 'success')
    return redirect(url_for('history'))


@app.route('/cover-letter', methods=['GET', 'POST'])
@login_required
def cover_letter():
    if request.method == 'GET':
        return render_template('cover_letter.html', letter_content=None)

    job_title = request.form.get('job_title', '').strip()
    company_name = request.form.get('company_name', '').strip()
    tone = request.form.get('tone', 'professional').strip()

    if not job_title or not company_name:
        flash('Job title and company name are required.', 'danger')
        return redirect(url_for('cover_letter'))

    db = get_db()
    latest_resume = db.execute(
        "SELECT original_text FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
        (session['user_id'],),
    ).fetchone()

    resume_text = latest_resume['original_text'] if latest_resume else ''
    if not resume_text:
        flash('Please upload and analyze a resume first so we can personalize your cover letter.', 'warning')
        return redirect(url_for('dashboard'))

    letter_content = generate_cover_letter(resume_text, job_title, company_name, tone)

    # Save to DB
    resume_id = None
    if latest_resume:
        rid = db.execute(
            "SELECT id FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
            (session['user_id'],),
        ).fetchone()
        resume_id = rid['id'] if rid else None

    db.execute(
        "INSERT INTO cover_letters (user_id, resume_id, job_title, company_name, content) VALUES (?, ?, ?, ?, ?)",
        (session['user_id'], resume_id, job_title, company_name, letter_content),
    )
    db.commit()

    flash('Cover letter generated!', 'success')
    return render_template(
        'cover_letter.html',
        letter_content=letter_content,
        job_title=job_title,
        company_name=company_name,
    )


@app.route('/career-roadmap', methods=['GET', 'POST'])
@login_required
def career_roadmap():
    if request.method == 'GET':
        return render_template('career_roadmap.html', roadmap=None)

    target_role = request.form.get('target_role', '').strip()
    if not target_role:
        flash('Please enter a target role.', 'danger')
        return redirect(url_for('career_roadmap'))

    db = get_db()
    latest = db.execute(
        "SELECT matched_skills FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
        (session['user_id'],),
    ).fetchone()

    current_skills = json.loads(latest['matched_skills'] or '[]') if latest else []
    # Also pull all extracted skills from latest resume text
    if not current_skills and latest:
        resume_row = db.execute(
            "SELECT original_text FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
            (session['user_id'],),
        ).fetchone()
        if resume_row and resume_row['original_text']:
            current_skills = extract_skills(resume_row['original_text'])

    roadmap = generate_career_roadmap(current_skills, target_role)

    return render_template('career_roadmap.html', roadmap=roadmap, target_role=target_role)


@app.route('/interview-prep')
@login_required
def interview_prep():
    db = get_db()
    latest = db.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
        (session['user_id'],),
    ).fetchone()

    target_role = request.args.get('role', '').strip()
    
    formatted_questions = []
    prep_tips = []

    if latest or target_role:
        if target_role:
            # Generate role-specific questions on the fly
            all_questions = generate_interview_questions(target_role, json.loads(latest['matched_skills'] or '[]') if latest else [])
            prep_tips = [
                f"Research the company's tech stack and recent products related to {target_role}.",
                f"Be prepared to discuss your past projects and how they relate to a {target_role} position.",
                f"Review common system design patterns and architectures used by {target_role}s.",
                f"Practice explaining complex technical concepts clearly to non-technical stakeholders."
            ]
        elif latest:
            all_questions = json.loads(latest['interview_questions'] or '[]')
            prep_tips = [
                "Review the core technologies listed on your resume.",
                "Prepare STAR method answers for behavioral questions.",
                "Practice coding problems on platforms like LeetCode."
            ]
        else:
            all_questions = []

        for idx, q in enumerate(all_questions):
            # Backward compatibility check
            if isinstance(q, str):
                q = {
                    "question": q,
                    "tips": ["Prepare real-world examples.", "Structure with STAR method."],
                    "answer": "Demonstrate your experience clearly with specific metrics.",
                    "category": "behavioral" if idx < 3 else ("technical" if idx < 7 else "situational")
                }
            formatted_questions.append(q)

    return render_template('interview_prep.html', questions=formatted_questions, resume=latest, target_role=target_role, prep_tips=prep_tips)


@app.route('/admin')
@login_required
@admin_required
def admin():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    total_users = db.execute("SELECT COUNT(*) as cnt FROM users").fetchone()['cnt']
    total_resumes = db.execute("SELECT COUNT(*) as cnt FROM resumes").fetchone()['cnt']
    total_reports = db.execute("SELECT COUNT(*) as cnt FROM reports").fetchone()['cnt']
    recent_resumes = db.execute(
        """SELECT r.*, u.username FROM resumes r
           JOIN users u ON r.user_id = u.id
           ORDER BY r.uploaded_at DESC LIMIT 20"""
    ).fetchall()

    stats = {
        'total_users': total_users,
        'total_resumes': total_resumes,
        'total_reports': total_reports,
    }

    return render_template('admin.html', users=users, stats=stats, recent_activity=recent_resumes)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash('You cannot delete your own admin account.', 'danger')
        return redirect(url_for('admin'))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin'))

    # Clean up user's report PDFs
    reports = db.execute("SELECT pdf_path FROM reports WHERE user_id = ?", (user_id,)).fetchall()
    for r in reports:
        if r['pdf_path'] and os.path.exists(r['pdf_path']):
            try:
                os.remove(r['pdf_path'])
            except OSError:
                pass

    # Clean up uploaded resume files
    resumes = db.execute("SELECT filename FROM resumes WHERE user_id = ?", (user_id,)).fetchall()
    for res in resumes:
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], res['filename'])
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except OSError:
                pass

    # Delete all related data
    db.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM cover_letters WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM reports WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM resumes WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    flash(f"User '{user['username']}' and all associated data deleted.", 'success')
    return redirect(url_for('admin'))


@app.route('/api/chatbot', methods=['POST'])
@login_required
def api_chatbot():
    data = request.get_json(silent=True)
    if not data or not data.get('message'):
        return jsonify({'error': 'Message is required.'}), 400

    message = data['message']
    response = chatbot_response(message)

    db = get_db()
    db.execute(
        "INSERT INTO chat_messages (user_id, message, response) VALUES (?, ?, ?)",
        (session['user_id'], message, response),
    )
    db.commit()

    return jsonify({'response': response})


@app.route('/api/score-history')
@login_required
def api_score_history():
    db = get_db()
    rows = db.execute(
        "SELECT uploaded_at as date, ats_score as score FROM resumes WHERE user_id = ? ORDER BY uploaded_at ASC",
        (session['user_id'],),
    ).fetchall()

    history = [{'date': row['date'], 'score': row['score']} for row in rows]
    return jsonify(history)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    init_db()
    app.run(debug=True)
