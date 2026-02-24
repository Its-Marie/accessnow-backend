from extensions import ma
from models import User, Favorite

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_fk = True
        load_instance = True
        exclude = ("password_hash",)

user_schema = UserSchema()
users_schema = UserSchema(many=True)

class FavoriteSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Favorite
        load_instance = True
        include_fk = True
        exclude = ("user",)

favorite_schema = FavoriteSchema()
favorites_schema = FavoriteSchema(many=True)