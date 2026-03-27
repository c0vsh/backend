import os

class Config:
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "e5a9e2b4c6e17c13d268b125db8e85d6d31ec64b3f0a1a1b9bfc491f94b501d6")

    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER', 'student')}:{os.getenv('DB_PASSWORD', '5432')}@{os.getenv('DB_HOST', '109.198.190.115')}:{os.getenv('DB_PORT', '32322')}/{os.getenv('DB_NAME', 'ChekalinI')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    @staticmethod
    def init_app(app):
        pass