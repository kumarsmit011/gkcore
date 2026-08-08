import sys
import bcrypt
import getpass
from sqlalchemy.sql import select
from sqlalchemy.exc import SQLAlchemyError
from gkcore import eng
from gkcore.models.gkdb import gkusers

def main():
    """Reset user password.

    Usage: gkauth --reset-password
    """

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "--reset-password":
            reset_password()
        else:
            print("Unknown argument:", arg)
            print("Usage: gkauth --reset-password")
            sys.exit(1)
    else:
        print("No argument provided.")
        sys.exit(1)

def reset_password():
    username = input('Username: ')
    user = eng.execute(
        select([gkusers.c.userid])
        .where(gkusers.c.username==username)
    ).fetchone()
    user_id = user["userid"]

    if not user_id:
        print('User not found, please try again')
        sys.exit(1)
    password = getpass.getpass('Password: ')
    confirm_password = getpass.getpass('Confirm Password: ')

    if not password == confirm_password:
        print("Passwords don't match, please try again.")
        sys.exit(1)

    encoded_password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(encoded_password, salt)
    user_password = hashed_password.decode('utf-8')

    try:
        eng.execute(
            gkusers.update()
            .where(gkusers.c.userid==user_id)
            .values(userpassword=user_password)
        )
    except SQLAlchemyError:
        print("Error in updating password, please try again.")
        sys.exit(1)

    print("Password updated successfully.")


if __name__ == "__main__":
    main()
