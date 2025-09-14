# User Schemas

from marshmallow import Schema, fields, validate, post_load
from ..models.user import User


class UserSchema(Schema):
    """Schema per la serializzazione degli utenti."""
    
    id = fields.Integer(dump_only=True)
    email = fields.Email(required=True, validate=validate.Length(max=120))
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    first_name = fields.String(validate=validate.Length(max=50), allow_none=True)
    last_name = fields.String(validate=validate.Length(max=50), allow_none=True)
    full_name = fields.String(dump_only=True)
    avatar_url = fields.Url(allow_none=True)
    
    # Status e permessi
    is_active = fields.Boolean(dump_only=True)
    is_admin = fields.Boolean(dump_only=True)  # Deprecated
    email_verified = fields.Boolean(dump_only=True)
    
    # Relazioni
    company_id = fields.Integer(allow_none=True)
    role_id = fields.Integer(allow_none=True)
    
    # Timestamps
    last_login = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Campi calcolati (solo in output)
    company_name = fields.String(dump_only=True)
    role_name = fields.String(dump_only=True)
    permissions = fields.List(fields.String(), dump_only=True)


class UserRegistrationSchema(Schema):
    """Schema per la registrazione degli utenti."""
    
    email = fields.Email(required=True, validate=validate.Length(max=120))
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))
    first_name = fields.String(validate=validate.Length(max=50), allow_none=True)
    last_name = fields.String(validate=validate.Length(max=50), allow_none=True)


class UserLoginSchema(Schema):
    """Schema per il login degli utenti."""
    
    email = fields.Email(required=True)
    password = fields.String(required=True)


class UserUpdateSchema(Schema):
    """Schema per l'aggiornamento del profilo utente."""
    
    first_name = fields.String(validate=validate.Length(max=50), allow_none=True)
    last_name = fields.String(validate=validate.Length(max=50), allow_none=True)
    avatar_url = fields.Url(allow_none=True)


class PasswordChangeSchema(Schema):
    """Schema per il cambio password."""
    
    current_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=validate.Length(min=8, max=128))


class UserCreateSchema(Schema):
    """Schema per la creazione di nuovi utenti (admin)."""
    
    email = fields.Email(required=True, validate=validate.Length(max=120))
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))
    first_name = fields.String(validate=validate.Length(max=50), allow_none=True)
    last_name = fields.String(validate=validate.Length(max=50), allow_none=True)
    avatar_url = fields.Url(allow_none=True)
    
    # Assegnazioni amministrative
    company_id = fields.Integer(allow_none=True)
    role_id = fields.Integer(allow_none=True)
    is_active = fields.Boolean(missing=True)
    email_verified = fields.Boolean(missing=False)


class UserAdminUpdateSchema(Schema):
    """Schema per l'aggiornamento amministrativo degli utenti."""
    
    email = fields.Email(validate=validate.Length(max=120), allow_none=True)
    username = fields.String(validate=validate.Length(min=3, max=80), allow_none=True)
    first_name = fields.String(validate=validate.Length(max=50), allow_none=True)
    last_name = fields.String(validate=validate.Length(max=50), allow_none=True)
    avatar_url = fields.Url(allow_none=True)
    
    # Controlli amministrativi
    company_id = fields.Integer(allow_none=True)
    role_id = fields.Integer(allow_none=True)
    is_active = fields.Boolean(allow_none=True)
    email_verified = fields.Boolean(allow_none=True)


class UserPasswordResetSchema(Schema):
    """Schema per il reset password amministrativo."""
    
    new_password = fields.String(required=True, validate=validate.Length(min=8, max=128))


class UserRoleAssignmentSchema(Schema):
    """Schema per l'assegnazione di ruolo e company."""
    
    company_id = fields.Integer(required=True)
    role_id = fields.Integer(allow_none=True)  # Se None, usa ruolo di default


# Istanze degli schema
user_schema = UserSchema()
users_schema = UserSchema(many=True)
user_registration_schema = UserRegistrationSchema()
user_login_schema = UserLoginSchema()
user_update_schema = UserUpdateSchema()
password_change_schema = PasswordChangeSchema()
user_create_schema = UserCreateSchema()
user_admin_update_schema = UserAdminUpdateSchema()
user_password_reset_schema = UserPasswordResetSchema()
user_role_assignment_schema = UserRoleAssignmentSchema()
