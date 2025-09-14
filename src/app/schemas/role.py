# Role Schemas

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models.role import Role
from ..models.permission import Permission


class RoleSchema(SQLAlchemyAutoSchema):
    """Schema per la serializzazione completa dei ruoli."""
    
    class Meta:
        model = Role
        load_instance = True
        
    # Campi computati
    permissions_count = fields.Method("get_permissions_count")
    users_count = fields.Method("get_users_count")
    permissions_list = fields.Method("get_permissions_list")
    
    def get_permissions_count(self, obj):
        """Ritorna il numero di permessi attivi."""
        return obj.permissions.filter_by(is_active=True).count()
    
    def get_users_count(self, obj):
        """Ritorna il numero di utenti con questo ruolo."""
        return obj.users.filter_by(is_active=True).count()
    
    def get_permissions_list(self, obj):
        """Ritorna la lista dei permessi del ruolo."""
        return [perm.name for perm in obj.permissions.filter_by(is_active=True).all()]


class RoleCreateSchema(Schema):
    """Schema per la creazione di nuovi ruoli."""
    
    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=50),
            validate.Regexp(
                r'^[a-z][a-z0-9_]*$',
                error='Il nome deve iniziare con una lettera minuscola e contenere solo lettere minuscole, numeri e underscore'
            )
        ]
    )
    display_name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    description = fields.Str(
        missing=None,
        validate=validate.Length(max=500)
    )
    access_level = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=10)
    )
    is_active = fields.Bool(missing=True)
    is_default = fields.Bool(missing=False)
    
    @validates('name')
    def validate_name_unique(self, value):
        """Verifica che il nome del ruolo sia unico."""
        existing = Role.query.filter_by(name=value).first()
        if existing:
            raise ValidationError(f'Il ruolo "{value}" esiste già')
    
    @validates('access_level')
    def validate_access_level(self, value):
        """Validazioni per il livello di accesso."""
        if value <= 0:
            raise ValidationError('Il livello di accesso deve essere positivo')


class RoleUpdateSchema(Schema):
    """Schema per l'aggiornamento dei ruoli esistenti."""
    
    display_name = fields.Str(
        validate=validate.Length(min=2, max=100)
    )
    description = fields.Str(
        validate=validate.Length(max=500),
        allow_none=True
    )
    access_level = fields.Int(
        validate=validate.Range(min=1, max=10)
    )
    is_active = fields.Bool()
    is_default = fields.Bool()
    
    @validates('access_level')
    def validate_access_level_update(self, value):
        """Validazioni per l'aggiornamento del livello di accesso."""
        if value <= 0:
            raise ValidationError('Il livello di accesso deve essere positivo')


class RolePermissionAssignmentSchema(Schema):
    """Schema per l'assegnazione di permessi ai ruoli."""
    
    permission_ids = fields.List(
        fields.Int(validate=validate.Range(min=1)),
        required=True,
        validate=validate.Length(min=1)
    )
    
    @validates('permission_ids')
    def validate_permission_ids(self, value):
        """Verifica che tutti i permission_ids esistano."""
        existing_count = Permission.query.filter(Permission.id.in_(value)).count()
        if existing_count != len(value):
            raise ValidationError('Uno o più permission_id non esistono')


class RoleListSchema(Schema):
    """Schema per la lista dei ruoli con filtri."""
    
    page = fields.Int(missing=1, validate=validate.Range(min=1))
    per_page = fields.Int(missing=20, validate=validate.Range(min=1, max=100))
    search = fields.Str(missing=None, validate=validate.Length(max=100))
    access_level = fields.Int(validate=validate.Range(min=1, max=10))
    is_active = fields.Bool(missing=None)
    include_permissions = fields.Bool(missing=False)
    include_stats = fields.Bool(missing=False)


class RoleStatsSchema(Schema):
    """Schema per le statistiche dei ruoli."""
    
    total_roles = fields.Int()
    active_roles = fields.Int()
    inactive_roles = fields.Int()
    roles_by_level = fields.Dict()
    default_role = fields.Nested(RoleSchema, exclude=['permissions_list'])


# Istanze degli schemi
role_schema = RoleSchema()
roles_schema = RoleSchema(many=True)
role_create_schema = RoleCreateSchema()
role_update_schema = RoleUpdateSchema()
role_permission_assignment_schema = RolePermissionAssignmentSchema()
role_list_schema = RoleListSchema()
role_stats_schema = RoleStatsSchema()
