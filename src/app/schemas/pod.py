"""
Schemi Marshmallow per il modello POD
"""

from marshmallow import Schema, fields, validate, post_load, validates, ValidationError
from marshmallow_enum import EnumField

from ..models.pod import POD, PodType


class PODBaseSchema(Schema):
    """Schema base per POD con campi comuni"""
    
    pod_code = fields.Str(
        required=True,
        validate=[
            validate.Length(min=5, max=50, error="Il codice POD deve essere tra 5 e 50 caratteri"),
            validate.Regexp(
                r'^[A-Z0-9]+$',
                error="Il codice POD deve contenere solo lettere maiuscole e numeri"
            )
        ],
        error_messages={
            'required': 'Il codice POD è obbligatorio',
            'invalid': 'Formato codice POD non valido'
        }
    )
    
    pod_type = EnumField(
        PodType,
        required=True,
        error_messages={
            'required': 'Il tipo POD è obbligatorio',
            'invalid': 'Tipo POD non valido'
        }
    )
    
    supplier = fields.Str(
        allow_none=True,
        validate=validate.Length(max=100, error="Il fornitore non può superare 100 caratteri"),
        missing=None
    )
    
    supplier_contract = fields.Str(
        allow_none=True,
        validate=validate.Length(max=50, error="Il numero contratto non può superare 50 caratteri"),
        missing=None
    )
    
    description = fields.Str(
        allow_none=True,
        validate=validate.Length(max=500, error="La descrizione non può superare 500 caratteri"),
        missing=None
    )
    
    is_active = fields.Bool(missing=True)
    
    power_capacity = fields.Str(
        allow_none=True,
        validate=validate.Length(max=20, error="La potenza non può superare 20 caratteri"),
        missing=None
    )
    
    voltage = fields.Str(
        allow_none=True,
        validate=validate.Length(max=20, error="La tensione non può superare 20 caratteri"),
        missing=None
    )
    
    meter_serial = fields.Str(
        allow_none=True,
        validate=validate.Length(max=50, error="Il numero contatore non può superare 50 caratteri"),
        missing=None
    )

    @validates('pod_code')
    def validate_pod_code_format(self, value):
        """Validazione specifica per formato codice POD"""
        if not value:
            return
            
        # Validazione formato POD ENEL (IT001E...)
        if value.startswith('IT001E') and len(value) == 14:
            if not value[6:].isdigit():
                raise ValidationError("POD elettrico deve avere formato IT001E + 8 cifre")
            return
            
        # Validazione formato POD GAS (IT...)
        if value.startswith('IT') and len(value) >= 12:
            return
            
        # Altri formati validi possono essere aggiunti qui
        if len(value) >= 5:
            return
            
        raise ValidationError("Formato codice POD non riconosciuto")


class PODCreateSchema(PODBaseSchema):
    """Schema per la creazione di un nuovo POD"""
    pass


class PODUpdateSchema(PODBaseSchema):
    """Schema per l'aggiornamento di un POD esistente"""
    
    pod_code = fields.Str(
        required=False,
        validate=[
            validate.Length(min=5, max=50),
            validate.Regexp(r'^[A-Z0-9]+$')
        ]
    )
    
    pod_type = EnumField(PodType, required=False)


class PODResponseSchema(PODBaseSchema):
    """Schema per la risposta con i dati del POD"""
    
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format='%Y-%m-%d %H:%M:%S')
    updated_at = fields.DateTime(dump_only=True, format='%Y-%m-%d %H:%M:%S')
    
    # Dati aggiuntivi calcolati
    connected_properties_count = fields.Method('get_connected_properties_count', dump_only=True)
    is_electricity = fields.Method('get_is_electricity', dump_only=True)
    is_gas = fields.Method('get_is_gas', dump_only=True)
    
    def get_connected_properties_count(self, obj):
        """Calcola il numero di proprietà connesse"""
        if hasattr(obj, 'get_connected_properties_count'):
            return obj.get_connected_properties_count()
        return 0
    
    def get_is_electricity(self, obj):
        """Verifica se è un POD elettrico"""
        return obj.pod_type == PodType.ELECTRICITY
    
    def get_is_gas(self, obj):
        """Verifica se è un POD gas"""
        return obj.pod_type == PodType.GAS


class PODListSchema(Schema):
    """Schema per la lista paginata dei POD"""
    
    pods = fields.List(fields.Nested(PODResponseSchema))
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()
    pages = fields.Int()
    has_next = fields.Bool()
    has_prev = fields.Bool()


class PODSearchSchema(Schema):
    """Schema per i parametri di ricerca POD"""
    
    page = fields.Int(missing=1, validate=validate.Range(min=1))
    per_page = fields.Int(missing=20, validate=validate.Range(min=1, max=100))
    
    # Filtri di ricerca
    pod_code = fields.Str(missing=None, validate=validate.Length(max=50))
    pod_type = EnumField(PodType, missing=None)
    supplier = fields.Str(missing=None, validate=validate.Length(max=100))
    is_active = fields.Bool(missing=None)
    
    # Ricerca testuale
    search = fields.Str(missing=None, validate=validate.Length(max=100))
    
    # Ordinamento
    sort_by = fields.Str(
        missing='pod_code',
        validate=validate.OneOf([
            'pod_code', 'pod_type', 'supplier', 'created_at', 'updated_at'
        ])
    )
    sort_order = fields.Str(
        missing='asc',
        validate=validate.OneOf(['asc', 'desc'])
    )


class PODStatsSchema(Schema):
    """Schema per le statistiche dei POD"""
    
    total_pods = fields.Int()
    active_pods = fields.Int()
    inactive_pods = fields.Int()
    
    # Statistiche per tipo
    electricity_pods = fields.Int()
    gas_pods = fields.Int()
    water_pods = fields.Int()
    heating_pods = fields.Int()
    
    # Statistiche fornitori
    top_suppliers = fields.List(fields.Dict())
    
    # Statistiche connessioni
    pods_with_properties = fields.Int()
    pods_without_properties = fields.Int()
    avg_properties_per_pod = fields.Float()


class PODBulkActionSchema(Schema):
    """Schema per le azioni bulk sui POD"""
    
    action = fields.Str(
        required=True,
        validate=validate.OneOf([
            'activate', 'deactivate', 'delete', 'update_supplier'
        ])
    )
    
    pod_ids = fields.List(
        fields.Int(),
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    
    # Parametri opzionali per alcune azioni
    supplier = fields.Str(
        missing=None,
        validate=validate.Length(max=100)
    )


class PODDuplicateCheckSchema(Schema):
    """Schema per il controllo duplicati POD"""
    
    pod_code = fields.Str(required=True)
    exclude_id = fields.Int(missing=None)  # ID da escludere dal controllo


class PODValidationSchema(Schema):
    """Schema per la validazione dati POD"""
    
    pod_code = fields.Str(required=True)
    pod_type = EnumField(PodType, required=True)
    supplier = fields.Str(missing=None)


# Export degli schemi
__all__ = [
    'PODBaseSchema',
    'PODCreateSchema', 
    'PODUpdateSchema',
    'PODResponseSchema',
    'PODListSchema',
    'PODSearchSchema',
    'PODStatsSchema',
    'PODBulkActionSchema',
    'PODDuplicateCheckSchema',
    'PODValidationSchema'
]

# Istanze degli schemi per l'uso nell'applicazione
pod_schema = PODResponseSchema()
pods_schema = PODResponseSchema(many=True)
pod_create_schema = PODCreateSchema()
pod_update_schema = PODUpdateSchema()
pod_list_schema = PODListSchema()
pod_stats_schema = PODStatsSchema()
pod_duplicate_check_schema = PODDuplicateCheckSchema()
pod_bulk_action_schema = PODBulkActionSchema()
pod_validation_schema = PODValidationSchema()
pod_types_schema = PODResponseSchema(many=True)
