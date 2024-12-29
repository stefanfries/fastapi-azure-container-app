from datetime import datetime
from enum import Enum
from typing import Optional

from bson.objectid import ObjectId
from pydantic import BaseModel, EmailStr  # , Field


class Roles(str, Enum):
    """
    Enum class representing different user roles.
    Attributes:
        TEST (str): Role for testing purposes.
        ADMIN (str): Role for administrative users.
        PAYING (str): Role for users with a paid subscription.
        REGULAR (str): Role for regular users.
    """

    TEST = "test"
    ADMIN = "admin"
    PAYING = "paying"
    REGULAR = "regular"


class UserBase(BaseModel):
    """
    UserBase is a Pydantic model that represents the base schema for a user.
    Attributes:
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.
        username (str): The username of the user.
        role (Roles): The role assigned to the user.
        email (EmailStr): The email address of the user.
        email_verified (bool): Indicates whether the user's email has been verified. Defaults to False.
        is_active (bool): Indicates whether the user is active. Defaults to False.
        created_at (datetime): The timestamp when the user was created. Defaults to the current datetime.
        changed_at (datetime): The timestamp when the user was last changed. Defaults to the created_at datetime.
    """

    first_name: str
    last_name: str
    username: str
    role: Roles
    email: EmailStr
    email_verified: bool = False
    is_active: bool = False
    created_at: datetime = datetime.now()
    changed_at: datetime = created_at


class UserStoreDB(UserBase):
    """
    UserStoreDB is a model that represents a user in the database.
    Attributes:
        _id (Optional[ObjectId]): The unique identifier for the user in the database.
        hashed_password (str): The hashed password of the user.
    """

    _id: Optional[ObjectId] = None
    hashed_password: str


class UserCreate(UserBase):
    """
    UserCreate is a data model for creating a new user.
    Attributes:
        password (str): The password for the new user.
    """

    password: str
