from db.mongo import mongo  # Import your MongoDB connection

class User:
    def __init__(self, username, password, email):
        self.username = username
        self.password = password
        self.email = email

    def save(self):
        users_collection = mongo.db.users  # Access the 'users' collection
        user_data = {
            'username': self.username,
            'password': self.password,  # Remember to hash the password!
            'email': self.email
        }
        users_collection.insert_one(user_data)

    @staticmethod
    def find_by_username(username):
        users_collection = mongo.db.users
        user = users_collection.find_one({'username': username})
        if user:
            return User(user['username'], user['password'], user['email'])
        return None