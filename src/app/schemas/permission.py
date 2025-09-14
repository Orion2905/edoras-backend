# Permission Schemas

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models.permission import Permission
from ..models.role import Role


class PermissionSchema(SQLAlchemyAutoSchema):
    """Schema per la serializzazione completa dei permessi."""
    
    class Meta:
        model = Permission
        load_instance = True
        
    # Campi computati
    role_name = fields.Method("get_role_name")
    
    def get_role_name(self, obj):
        """Ritorna il nome del ruolo associato."""
        return obj.role.name if obj.role else None


class PermissionCreateSchema(Schema):
    """Schema per la creazione di nuovi permessi."""
    
    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=100),
            validate.Regexp(
                r'^[a-z][a-z0-9_.]*$',
                error='Il nome deve iniziare con una lettera minuscola e contenere solo lettere minuscole, numeri, punti e underscore'
            )
        ]
    )
    display_name = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=150)
    )
    description = fields.Str(
        missing=None,
        validate=validate.Length(max=500)
    )
    category = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=50),
            validate.OneOf([
                'system', 'company', 'user', 'property', 
                'invoice', 'booking', 'pod', 'report', 'other'
            ])
        ]
    )
    role_id = fields.Int(
        required=True,
        validate=validate.Range(min=1)
    )
    is_active = fields.Bool(missing=True)
    
    @validates('role_id')
    def validate_role_exists(self, value):
        """Verifica che il ruolo esista."""
        role = Role.query.get(value)
        if not role:
            raise ValidationError(f'Il ruolo con ID {value} non esiste')
    
    @validates('name')
    def validate_permission_unique_for_role(self, value):
        """Verifica che il permesso sia unico per il ruolo."""
        # Questo verrà validato durante il load completo con role_id
        pass


class PermissionUpdateSchema(Schema):
    """Schema per l'aggiornamento dei permessi esistenti."""
    
    display_name = fields.Str(
        validate=validate.Length(min=3, max=150)
    )
    description = fields.Str(
        validate=validate.Length(max=500),
        allow_none=True
    )
    category = fields.Str(
        validate=[
            validate.Length(min=2, max=50),
            validate.OneOf([
                'system', 'company', 'user', 'property',
                'invoice', 'booking', 'pod', 'report', 'other'
            ])
        ]
    )
    is_active = fields.Bool()


class PermissionListSchema(Schema):
    """Schema per la lista dei permessi con filtri."""
    
    page = fields.Int(missing=1, validate=validate.Range(min=1))
    per_page = fields.Int(missing=20, validate=validate.Range(min=1, max=100))
    search = fields.Str(missing=None, validate=validate.Length(max=100))
    category = fields.Str(
        missing=None,
        validate=validate.OneOf([
            'system', 'company', 'user', 'property',
            'invoice', 'booking', 'pod', 'report', 'other'
        ])
    )
    role_id = fields.Int(validate=validate.Range(min=1))
    is_active = fields.Bool(missing=None)
    include_role_info = fields.Bool(missing=False)


class PermissionBulkCreateSchema(Schema):
    """Schema per la creazione di permessi in batch."""
    
    permissions = fields.List(
        fields.Nested(PermissionCreateSchema),
        required=True,
        validate=validate.Length(min=1, max=50)
    )


class PermissionBulkUpdateSchema(Schema):
    """Schema per l'aggiornamento in batch dei permessi."""
    
    permission_ids = fields.List(
        fields.Int(validate=validate.Range(min=1)),
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    updates = fields.Nested(PermissionUpdateSchema, required=True)
    
    @validates('permission_ids')
    def validate_permission_ids_exist(self, value):
        """Verifica che tutti i permission_ids esistano."""
        existing_count = Permission.query.filter(Permission.id.in_(value)).count()
        if existing_count != len(value):
            raise ValidationError('Uno o più permission_id non esistono')


class PermissionCategoryStatsSchema(Schema):
    """Schema per le statistiche per categoria."""
    
    category = fields.Str()
    total_permissions = fields.Int()
    active_permissions = fields.Int()
    inactive_permissions = fields.Int()
    roles_with_permissions = fields.Int()


class PermissionStatsSchema(Schema):
    """Schema per le statistiche complete dei permessi."""
    
    total_permissions = fields.Int()
    active_permissions = fields.Int()
    inactive_permissions = fields.Int()
    categories_stats = fields.List(fields.Nested(PermissionCategoryStatsSchema))
    permissions_by_role = fields.Dict()
    most_used_permissions = fields.List(fields.Dict())


class PermissionImportSchema(Schema):
    """Schema per l'importazione di permessi da template."""
    
    template_name = fields.Str(
        required=True,
        validate=validate.OneOf([
            'basic_company', 'full_company', 'property_management',
            'invoice_management', 'booking_management', 'custom'
        ])
    )
    role_id = fields.Int(
        required=True,
        validate=validate.Range(min=1)
    )
    override_existing = fields.Bool(missing=False)
    
    @validates('role_id')
    def validate_role_exists_for_import(self, value):
        """Verifica che il ruolo esista per l'importazione."""
        role = Role.query.get(value)
        if not role:
            raise ValidationError(f'Il ruolo con ID {value} non esiste')


# Istanze degli schemi
permission_schema = PermissionSchema()
permissions_schema = PermissionSchema(many=True)
permission_create_schema = PermissionCreateSchema()
permission_update_schema = PermissionUpdateSchema()
permission_list_schema = PermissionListSchema()
permission_bulk_create_schema = PermissionBulkCreateSchema()
permission_bulk_update_schema = PermissionBulkUpdateSchema()
permission_stats_schema = PermissionStatsSchema()
permission_import_schema = PermissionImportSchema()
