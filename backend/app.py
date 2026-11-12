"""
NutriScan Flask Application Factory
Builds the core web and API server, registers blueprints, configures CORS,
error handling, and static/template routing.
"""

import os
import sys
import logging
from flask import Flask, jsonify, render_template, send_from_directory, request
from flask_cors import CORS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import Config
from backend.db import get_db
from backend.routes.health import health_bp
from backend.routes.auth import auth_bp
from backend.routes.profile import profile_bp
from backend.routes.foods import foods_bp
from backend.routes.intake import intake_bp
from backend.routes.nutrition import nutrition_bp
from backend.routes.assessment import assessment_bp
from backend.routes.history import history_bp
from backend.routes.recommendations import recommendations_bp


def create_app(test_config=None):
    template_folder = os.path.join(PROJECT_ROOT, 'frontend', 'templates')
    static_folder = os.path.join(PROJECT_ROOT, 'frontend', 'static')

    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder
    )

    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # Enable CORS for API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Logging setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] in %(module)s: %(message)s'
    )

    # Initialize DB connection, ensure indexes, and auto-seed if empty
    with app.app_context():
        db = get_db()
        db.create_indexes()
        try:
            if db.foods.count_documents({}) == 0:
                from data_pipeline.seed_db import seed_database
                app.logger.info("Database empty on startup. Auto-seeding foods and RDA tables...")
                seed_database()
        except Exception as e:
            app.logger.warning(f"Auto-seed notice: {e}")

    # Register API Blueprints under /api
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    app.register_blueprint(foods_bp, url_prefix='/api/foods')
    app.register_blueprint(intake_bp, url_prefix='/api/intake')
    app.register_blueprint(nutrition_bp, url_prefix='/api/nutrition')
    app.register_blueprint(assessment_bp, url_prefix='/api/assessment')
    app.register_blueprint(history_bp, url_prefix='/api/history')
    app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')

    # Frontend Page Routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/register')
    def register_page():
        return render_template('register.html')

    @app.route('/dashboard')
    def dashboard_page():
        return render_template('dashboard.html')

    @app.route('/profile')
    def profile_page():
        return render_template('profile.html')

    @app.route('/intake')
    def intake_page():
        return render_template('intake.html')

    @app.route('/results')
    def results_page():
        return render_template('results.html')

    @app.route('/questionnaire')
    def questionnaire_page():
        return render_template('questionnaire.html')

    @app.route('/recommendations')
    def recommendations_page():
        return render_template('recommendations.html')

    @app.route('/history')
    def history_page():
        return render_template('history.html')

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    # Global Error Handlers for API
    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith('/api'):
            return jsonify({
                'success': False,
                'message': getattr(error, 'description', 'Bad Request.'),
                'data': None
            }), 400
        return "Bad Request", 400

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api'):
            return jsonify({
                'success': False,
                'message': 'Requested API endpoint does not exist.',
                'data': None
            }), 404
        return render_template('base.html', page_title="Page Not Found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        if request.path.startswith('/api'):
            return jsonify({
                'success': False,
                'message': 'An internal server error occurred.',
                'data': None
            }), 500
        return "Internal Server Error", 500

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
