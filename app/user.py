from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_id, name, email, profile_pic):
        self.id = user_id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

    @staticmethod
    def get(user_id):
        # In a real app, this would fetch from DB
        # For this POC, we rely on the user object being stored in session
        # via the user_loader callback which we will implement to just return None
        # if not using a DB, OR we can store user dict in session.
        # However, Flask-Login expects a user_loader that takes an ID.
        # Without a DB, standard Flask-Login is tricky.
        # Strategy: We will store the user *data* in the session ourselves 
        # and reconstruct the User object in the user_loader if possible, 
        # or just fail if we can't look it up.
        # ACTUALLY: For a rigorous POC w/o DB, we can just refuse to load 
        # if not in a global cache (bad for Cloud Run multiple instances).
        # BEST APPROACH FOR POC: Just store minimal data in session and 
        # re-create user from session data? Flask-Login doesn't work that way easily.
        
        # Let's simplify: We won't use a DB lookup. We will assume the ID passed 
        # is valid and return a dummy user wrapper if we don't have a DB.
        # But to have data (name, pic), we need to store it.
        # Let's simple return a User object with just ID.
        # The view functions can pull simpler data from session if needed, 
        # OR we can stash attributes in the User object.
        return User(user_id, "User", user_id, "")
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "profile_pic": self.profile_pic
        }
