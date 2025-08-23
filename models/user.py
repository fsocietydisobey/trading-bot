from db.mongo import mongo  # Import your MongoDB connection
from pymongo.errors import DuplicateKeyError

class User:
    def __init__(self, username, password, email, _id=None):
        self.username = username
        self.password = password
        self.email = email
        self.id = _id
# ... existing code ...
    def save(self):
        users_collection = mongo.db.users  # Access the 'users' collection
        # Ensure unique index on username (idempotent)
        users_collection.create_index('username', unique=True)
        user_data = {
            'username': self.username,
            'password': self.password,  # Already hashed before calling save()
            'email': self.email
        }
        try:
            result = users_collection.insert_one(user_data)
            self.id = result.inserted_id
            return self.id
        except DuplicateKeyError:
            # Surface a clean error that caller can map to 409
            raise ValueError("Username already exists")
# ... existing code ...
    @staticmethod
    def find_by_username(username):
        users_collection = mongo.db.users
        user = users_collection.find_one({'username': username})
        if user:
            return User(user['username'], user['password'], user['email'], _id=user.get('_id'))
        return None