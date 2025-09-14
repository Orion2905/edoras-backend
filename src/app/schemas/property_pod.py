"""
Schemi Marshmallow per il modello PropertyPod
"""

from marshmallow import Schema, fields, validate, validates, ValidationError, validates_schema
from datetime import datetime

from ..models.property_pod import PropertyPod


class PropertyPodBaseSchema(Schema):
    """Schema base per PropertyPod con campi comuni"""
    
    property_unit_id = fields.Int(
        required=True,
        validate=validate.Range(min=1, error="ID PropertyUnit deve essere maggiore di 0"),
        error_messages={
            'required': 'ID PropertyUnit è obbligatorio',
            'invalid': 'ID PropertyUnit deve essere un numero intero'
        }
    )
    
    pod_id = fields.Int(
        required=True,
        validate=validate.Range(min=1, error="ID POD deve essere maggiore di 0"),
        error_messages={
            'required': 'ID POD è obbligatorio',
            'invalid': 'ID POD deve essere un numero intero'
        }
    )
    
    is_primary = fields.Bool(missing=True)
    
    is_active = fields.Bool(missing=True)
    
    notes = fields.Str(
        allow_none=True,
        validate=validate.Length(max=500, error="Le note non possono superare 500 caratteri"),
        missing=None
    )

    @validates_schema
    def validate_connection(self, data, **kwargs):
        """Validazioni a livello di schema"""
        # Qui possiamo aggiungere validazioni che richiedono accesso al database
        # Ad esempio, verificare che property_unit_id e pod_id esistano
        pass


class PropertyPodCreateSchema(PropertyPodBaseSchema):
    """Schema per la creazione di una nuova connessione PropertyPod"""
    pass


class PropertyPodUpdateSchema(PropertyPodBaseSchema):
    """Schema per l'aggiornamento di una connessione PropertyPod esistente"""
    
    property_unit_id = fields.Int(
        required=False,
        validate=validate.Range(min=1)
    )
    
    pod_id = fields.Int(
        required=False,
        validate=validate.Range(min=1)
    )


class PropertyPodResponseSchema(PropertyPodBaseSchema):
    """Schema per la risposta con i dati della connessione PropertyPod"""
    
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format='%Y-%m-%d %H:%M:%S')
    updated_at = fields.DateTime(dump_only=True, format='%Y-%m-%d %H:%M:%S')
    
    # Dati delle entità correlate
    property_unit = fields.Method('get_property_unit_info', dump_only=True)
    pod = fields.Method('get_pod_info', dump_only=True)
    
    def get_property_unit_info(self, obj):
        """Restituisce info base della PropertyUnit"""
        if hasattr(obj, 'property_unit') and obj.property_unit:
            return {
                'id': obj.property_unit.id,
                'name': obj.property_unit.name,
                'code': obj.property_unit.code,
                'address': obj.property_unit.address,
                'property_type': obj.property_unit.property_type.name if obj.property_unit.property_type else None
            }
        return None
    
    def get_pod_info(self, obj):
        """Restituisce info base del POD"""
        if hasattr(obj, 'pod') and obj.pod:
            return {
                'id': obj.pod.id,
                'pod_code': obj.pod.pod_code,
                'pod_type': obj.pod.pod_type.value if obj.pod.pod_type else None,
                'supplier': obj.pod.supplier
            }
        return None


class PropertyPodListSchema(Schema):
    """Schema per la lista paginata delle connessioni PropertyPod"""
    
    property_pods = fields.List(fields.Nested(PropertyPodResponseSchema))
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()
    pages = fields.Int()
    has_next = fields.Bool()
    has_prev = fields.Bool()


class PropertyPodSearchSchema(Schema):
    """Schema per i parametri di ricerca PropertyPod"""
    
    page = fields.Int(missing=1, validate=validate.Range(min=1))
    per_page = fields.Int(missing=20, validate=validate.Range(min=1, max=100))
    
    # Filtri di ricerca
    property_unit_id = fields.Int(missing=None, validate=validate.Range(min=1))
    pod_id = fields.Int(missing=None, validate=validate.Range(min=1))
    is_primary = fields.Bool(missing=None)
    is_active = fields.Bool(missing=None)
    
    # Filtri per tipo POD
    pod_type = fields.Str(missing=None, validate=validate.OneOf(['ELECTRICITY', 'GAS', 'WATER', 'HEATING']))
    
    # Ricerca testuale
    search = fields.Str(missing=None, validate=validate.Length(max=100))
    
    # Ordinamento
    sort_by = fields.Str(
        missing='created_at',
        validate=validate.OneOf([
            'created_at', 'updated_at', 'property_unit_id', 'pod_id', 'is_primary'
        ])
    )
    sort_order = fields.Str(
        missing='desc',
        validate=validate.OneOf(['asc', 'desc'])
    )


class PropertyPodStatsSchema(Schema):
    """Schema per le statistiche delle connessioni PropertyPod"""
    
    total_connections = fields.Int()
    active_connections = fields.Int()
    inactive_connections = fields.Int()
    primary_connections = fields.Int()
    
    # Statistiche per tipo POD
    connections_by_pod_type = fields.Dict()
    
    # Statistiche per PropertyUnit
    properties_with_pods = fields.Int()
    properties_without_pods = fields.Int()
    avg_pods_per_property = fields.Float()
    
    # Statistiche per POD
    pods_with_properties = fields.Int()
    pods_without_properties = fields.Int()
    avg_properties_per_pod = fields.Float()
    
    # Top connessioni
    top_properties_by_pods = fields.List(fields.Dict())
    top_pods_by_properties = fields.List(fields.Dict())


class PropertyPodBulkActionSchema(Schema):
    """Schema per le azioni bulk sulle connessioni PropertyPod"""
    
    action = fields.Str(
        required=True,
        validate=validate.OneOf([
            'activate', 'deactivate', 'delete', 'set_primary', 'unset_primary'
        ])
    )
    
    property_pod_ids = fields.List(
        fields.Int(),
        required=True,
        validate=validate.Length(min=1, max=100)
    )


class PropertyPodDuplicateCheckSchema(Schema):
    """Schema per il controllo duplicati connessione PropertyPod"""
    
    property_unit_id = fields.Int(required=True)
    pod_id = fields.Int(required=True)
    exclude_id = fields.Int(missing=None)  # ID da escludere dal controllo


class PropertyPodValidationSchema(Schema):
    """Schema per la validazione dati PropertyPod"""
    
    property_unit_id = fields.Int(required=True)
    pod_id = fields.Int(required=True)
    is_primary = fields.Bool(missing=False)


class PropertyPodByPropertySchema(Schema):
    """Schema per ottenere connessioni per PropertyUnit"""
    
    property_unit_id = fields.Int(required=True)
    include_inactive = fields.Bool(missing=False)


class PropertyPodByPodSchema(Schema):
    """Schema per ottenere connessioni per POD"""
    
    pod_id = fields.Int(required=True)
    include_inactive = fields.Bool(missing=False)


class PropertyPodPrimarySchema(Schema):
    """Schema per impostare connessione come primaria"""
    
    is_primary = fields.Bool(required=True)


# Export degli schemi
__all__ = [
    'PropertyPodBaseSchema',
    'PropertyPodCreateSchema', 
    'PropertyPodUpdateSchema',
    'PropertyPodResponseSchema',
    'PropertyPodListSchema',
    'PropertyPodSearchSchema',
    'PropertyPodStatsSchema',
    'PropertyPodBulkActionSchema',
    'PropertyPodDuplicateCheckSchema',
    'PropertyPodValidationSchema',
    'PropertyPodByPropertySchema',
    'PropertyPodByPodSchema',
    'PropertyPodPrimarySchema'
]

# Istanze degli schemi per l'uso nell'applicazione
property_pod_schema = PropertyPodResponseSchema()
property_pods_schema = PropertyPodResponseSchema(many=True)
property_pod_create_schema = PropertyPodCreateSchema()
property_pod_update_schema = PropertyPodUpdateSchema()
property_pod_list_schema = PropertyPodListSchema()
property_pod_stats_schema = PropertyPodStatsSchema()
property_pod_duplicate_check_schema = PropertyPodDuplicateCheckSchema()
property_pod_bulk_action_schema = PropertyPodBulkActionSchema()
property_pod_validation_schema = PropertyPodValidationSchema()
property_pod_by_property_schema = PropertyPodByPropertySchema()
property_pod_by_pod_schema = PropertyPodByPodSchema()
property_pod_primary_schema = PropertyPodPrimarySchema()
