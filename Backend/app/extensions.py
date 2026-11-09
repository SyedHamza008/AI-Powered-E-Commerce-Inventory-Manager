from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize SQLAlchemy and Migrate without attaching them to an app yet
db = SQLAlchemy()
migrate = Migrate()