from pydantic import BaseModel, Field


# the user payload schema
class UserSchema(BaseModel):
    username: str = Field(min_length=5, max_length=50, pattern=r"^[a-zA-Z][a-zA-Z\d]*(?:_?[a-zA-Z\d]+)?$")
    userpassword: str = Field(min_length=3)
    userquestion: str = Field(min_length=3, max_length=2000)
    useranswer: str = Field(min_length=1, max_length=2000)
    # godown in-charge will have orgs
    orgs: dict = Field(default=dict())

# the username payload schema
class UserNameSchema(BaseModel):
    username: str = Field(min_length=5, max_length=50, pattern=r"^[a-zA-Z][a-zA-Z\d]*(?:_?[a-zA-Z\d]+)?$")

# uses password reset model
class ResetPassword(BaseModel):
    userid: int
    userpassword: str = Field(min_length=3)

class ChangePassword(BaseModel):
    userid: int
    userpassword: str = Field(min_length=3)
    useranswer: str = Field(min_length=1, max_length=2000)
