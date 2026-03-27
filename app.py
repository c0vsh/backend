from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from models import db, User, Book
from config import Config
from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError
from jwt.exceptions import ExpiredSignatureError


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

jwt = JWTManager(app)

def create_error_response(message, code):
    error_response = {
        "error": {
            "code": code,
            "message": message
        }
    }
    return jsonify(error_response), code

# Обработчик для отсутствующего токена
@app.errorhandler(NoAuthorizationError)
def handle_no_token(error):
    return create_error_response("Токен не предоставлен. Пожалуйста, войдите в систему.", 401)

# Обработчик для истекшего токена
@app.errorhandler(ExpiredSignatureError)
def handle_expired_token(error):
    return create_error_response("Срок действия токена истек. Пожалуйста, войдите в систему снова.", 401)

# Обработчик для некорректного токена
@app.errorhandler(InvalidHeaderError)
def handle_invalid_token(error):
    return create_error_response("Неверный токен. Пожалуйста, войдите в систему.", 401)

# Обработчик ошибки 405 (Method Not Allowed)
@app.errorhandler(405)
def method_not_allowed_error(error):
    return create_error_response("Метод не разрешен для этого ресурса", 405)


# Регистрация пользователя
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return create_error_response("Имя пользователя и пароль обязательны", 400)

    if not username or len(username) < 3 or len(username) > 150:
        return create_error_response("Имя пользователя должно быть от 3 до 150 символов", 422)

    if not password or len(password) < 6:
        return create_error_response("Пароль должен быть не короче 6 символов", 422)

    hashed_password = generate_password_hash(password)

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return create_error_response("Пользователь с таким именем уже существует", 422)

    new_user = User(username=username, password=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"msg": "Пользователь зарегистрирован", "user_id": new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return create_error_response(f"Ошибка при регистрации: {str(e)}", 500)


# Логин пользователя
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return create_error_response("Имя пользователя и пароль обязательны", 400)

    user = User.query.filter_by(username=username).first()

    if user is None:
        return create_error_response("Неверные учетные данные", 422)

    if not check_password_hash(user.password, password):
        return create_error_response("Неверные учетные данные", 422)

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200


# Выход из аккаунта
@app.route("/auth/logout", methods=["POST"])
@jwt_required()
def logout():
    return jsonify({"msg": "Выход успешен"}), 200


# Получение списка книг
@app.route("/books", methods=["GET"])
@jwt_required()
def get_books():
    books = Book.query.all()
    result = []
    for book in books:
        result.append({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "genre": book.genre,
            "year": book.year,
            "available": book.available
        })
    return jsonify(result), 200


# Получение одной книги
@app.route("/books/<int:id>", methods=["GET"])
@jwt_required()
def get_book(id):
    book = Book.query.get(id)

    if book is None:
        return create_error_response("Книга не найдена", 404)

    return jsonify({
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "year": book.year,
        "available": book.available
    }), 200


# Создание книги
@app.route("/books", methods=["POST"])
@jwt_required()
def create_book():
    data = request.get_json()
    title = data.get("title")
    author = data.get("author")
    genre = data.get("genre")
    year = data.get("year")
    available = data.get("available")

    if not title or not author or not genre or not year or available is None:
        return create_error_response("Все поля (title, author, genre, year, available) обязательны", 400)

    if len(title) < 1 or len(title) > 200:
        return create_error_response("Название книги должно быть от 1 до 200 символов", 422)

    if len(author) < 1 or len(author) > 200:
        return create_error_response("Автор книги должен быть от 1 до 200 символов", 422)

    if len(genre) > 100:
        return create_error_response("Жанр книги не должен превышать 100 символов", 422)

    if not isinstance(year, int) or year < 1000 or year > 9999:
        return create_error_response("Год книги должен быть целым числом в диапазоне от 1000 до 9999", 422)


    new_book = Book(title=title, author=author, genre=genre, year=year, available=available)

    try:
        db.session.add(new_book)
        db.session.commit()

        return jsonify({
            "book": {
                "id": new_book.id,
                "title": new_book.title,
                "author": new_book.author,
                "genre": new_book.genre,
                "year": new_book.year,
                "available": new_book.available
            },
            "msg": "Книга создана"
        }), 201
    except Exception as e:
        db.session.rollback()
        return create_error_response(f"Ошибка при создании книги: {str(e)}", 500)


# Полное обновление книги
@app.route("/books/<int:id>", methods=["PUT"])
@jwt_required()
def update_book(id):
    data = request.get_json()

    if not data:
            return create_error_response("Тело запроса не может быть пустым", 400)

    title = data.get("title")
    author = data.get("author")
    genre = data.get("genre")
    year = data.get("year")
    available = data.get("available")

    if not title or not author or not genre or not year or available is None:
        return create_error_response("Все поля (title, author, genre, year, available) обязательны", 400)

    if len(title) < 1 or len(title) > 200:
        return create_error_response("Название книги должно быть от 1 до 200 символов", 422)

    if len(author) < 1 or len(author) > 200:
        return create_error_response("Автор книги должен быть от 1 до 200 символов", 422)

    if len(genre) > 100:
        return create_error_response("Жанр книги не должен превышать 100 символов", 422)

    if not isinstance(year, int) or year < 1000 or year > 9999:
        return create_error_response("Год книги должен быть целым числом в диапазоне от 1000 до 9999", 422)

    book = Book.query.get(id)

    if book is None:
        return create_error_response("Книга не найдена", 404)

    book.title = title
    book.author = author
    book.genre = genre
    book.year = year
    book.available = available

    try:
        db.session.commit()
        return jsonify({"msg": "Книга обновлена"}), 200
    except Exception as e:
        db.session.rollback()
        return create_error_response(f"Ошибка при обновлении книги: {str(e)}", 500)


# Удаление книги
@app.route("/books/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_book(id):
    book = Book.query.get(id)

    if book is None:
        return create_error_response("Книга не найдена", 404)

    try:
        db.session.delete(book)
        db.session.commit()
        return jsonify({"msg": "Книга удалена"}), 200
    except Exception as e:
        db.session.rollback()
        return create_error_response(f"Ошибка при удалении книги: {str(e)}", 500)


# Частичное обновление книги
@app.route("/books/<int:id>", methods=["PATCH"])
@jwt_required()
def patch_book(id):
    data = request.get_json()

    book = Book.query.get(id)

    if book is None:
        return create_error_response("Книга не найдена", 404)

    allowed_fields = {"title", "author", "genre", "year", "available"}
    invalid_fields = [key for key in data if key not in allowed_fields]

    if invalid_fields:
        return create_error_response(f"Недопустимые поля: {', '.join(invalid_fields)}", 400)

    if "year" in data and (not isinstance(data["year"], int) or data["year"] < 1000 or data["year"] > 9999):
        return create_error_response("Год книги должен быть целым числом в диапазоне от 1000 до 9999", 422)

    if "available" in data and not isinstance(data["available"], bool):
        return create_error_response("Поле 'available' должно быть boolean", 422)

    if "title" in data:
        if len(data["title"]) < 1 or len(data["title"]) > 200:
            return create_error_response("Название книги должно быть от 1 до 200 символов", 422)
        book.title = data["title"]

    if "author" in data:
        if len(data["author"]) < 1 or len(data["author"]) > 200:
            return create_error_response("Автор книги должен быть от 1 до 200 символов", 422)
        book.author = data["author"]

    if "genre" in data:
        if len(data["genre"]) > 100:
            return create_error_response("Жанр книги не должен превышать 100 символов", 422)
        book.genre = data["genre"]

    if "year" in data:
        book.year = data["year"]

    if "available" in data:
        book.available = data["available"]

    try:
        db.session.commit()
        return jsonify({"msg": "Книга частично обновлена"}), 200
    except Exception as e:
        db.session.rollback()
        return create_error_response(f"Ошибка при обновлении книги: {str(e)}", 500)


if __name__ == "__main__":
    app.run(debug=True)