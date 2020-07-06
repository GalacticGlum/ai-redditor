from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import ai_redditor_service.template_filters as template_filters

db = SQLAlchemy()
migrate = Migrate(db=db)

def init_app(app):
    '''
    Initializes extensions with a Flask app context.

    '''

    db.init_app(app)
    template_filters.init_app(app)
    
    _init_migrate(app)

def _init_migrate(app):
    is_sqlite = app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:')
    migrate.init_app(app, render_as_batch=is_sqlite)