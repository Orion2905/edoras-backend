# Invoices CRUD API - Sistema Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, extract
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from decimal import Decimal
from ...models.invoice import Invoice
from ...models.company import Company
from ...schemas import (
    invoice_schema, invoices_schema,
    invoice_create_schema, invoice_update_schema,
    invoice_list_schema, invoice_workflow_schema,
    invoice_duplicate_check_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def user_can_manage_invoices(user):
    """Verifica se l'utente può gestire tutte le fatture (solo Rohirrim)."""
    return user and user.is_active and user.role and user.role.is_rohirrim()


def user_can_view_company_invoices(user, company_id=None):
    """Verifica se l'utente può visualizzare fatture dell'azienda."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim può vedere tutte le fatture
    if user.role and user.role.is_rohirrim():
        return True
    
    # Lord può vedere solo fatture della propria azienda
    if user.role and user.role.is_lord() and user.company_id:
        return company_id is None or company_id == user.company_id
    
    # Dunedain può vedere solo fatture della propria azienda (read-only)
    if user.role and user.role.is_dunedain() and user.company_id:
        return company_id is None or company_id == user.company_id
    
    return False


def user_can_edit_invoice(user, invoice):
    """Verifica se l'utente può modificare una fattura specifica."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim può modificare tutte le fatture
    if user.role and user.role.is_rohirrim():
        return True
    
    # Lord può modificare solo fatture della propria azienda
    if user.role and user.role.is_lord() and user.company_id:
        return invoice.company_id == user.company_id
    
    # Dunedain non può modificare fatture
    return False


@api_v1_bp.route('/invoices', methods=['GET'])
@jwt_required()
def get_invoices():
    """
    Ottiene la lista delle fatture con filtri avanzati.
    Rohirrim: tutte le fatture
    Lord: solo fatture della propria azienda
    Dunedain: solo fatture della propria azienda (read-only)
    """
    try:
        current_user = get_current_user()
        
        # Validazione parametri query
        args = invoice_list_schema.load(request.args)
        
        # Query base
        query = Invoice.query.filter(Invoice.is_active == True)
        
        # Filtri di autorizzazione
        if current_user.role and current_user.role.is_rohirrim():
            # Rohirrim può vedere tutte le fatture
            pass
        elif current_user.role and (current_user.role.is_lord() or current_user.role.is_dunedain()):
            # Lord e Dunedain solo della propria azienda
            if current_user.company_id:
                query = query.filter(Invoice.company_id == current_user.company_id)
            else:
                return jsonify({
                    'error': 'Accesso negato',
                    'message': 'Utente non associato a nessuna azienda'
                }), 403
        else:
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti per visualizzare le fatture'
            }), 403
        
        # Applica filtri
        if args.get('search'):
            search_term = f"%{args['search']}%"
            query = query.filter(
                or_(
                    Invoice.supplier.ilike(search_term),
                    Invoice.invoice_number.ilike(search_term),
                    Invoice.article_description.ilike(search_term),
                    Invoice.supplier_vat.ilike(search_term),
                    Invoice.notes.ilike(search_term)
                )
            )
        
        if args.get('supplier'):
            query = query.filter(Invoice.supplier.ilike(f"%{args['supplier']}%"))
        
        # Ordinamento
        sort_by = args.get('sort_by', 'invoice_date')
        sort_order = args.get('sort_order', 'desc')
        
        if hasattr(Invoice, sort_by):
            order_column = getattr(Invoice, sort_by)
            if sort_order == 'desc':
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
        
        # Paginazione
        page = args.get('page', 1)
        per_page = args.get('per_page', 20)
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Serializzazione
        invoices_data = invoices_schema.dump(pagination.items)
        
        return jsonify({
            'invoices': invoices_data,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'user_permissions': {
                'can_edit': user_can_manage_invoices(current_user) or 
                           (current_user.role and current_user.role.is_lord()),
                'can_delete': user_can_manage_invoices(current_user),
                'can_view_all_companies': user_can_manage_invoices(current_user),
                'company_filter': None if user_can_manage_invoices(current_user) else current_user.company_id
            }
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Parametri non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Errore interno del server',
            'message': str(e)
        }), 500


@api_v1_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@jwt_required()
def get_invoice(invoice_id):
    """
    Ottiene i dettagli di una fattura specifica.
    """
    try:
        current_user = get_current_user()
        invoice = Invoice.query.filter_by(id=invoice_id, is_active=True).first_or_404()
        
        # Verifica autorizzazioni
        if not user_can_view_company_invoices(current_user, invoice.company_id):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Non autorizzato a visualizzare questa fattura'
            }), 403
        
        # Serializzazione completa
        invoice_data = invoice_schema.dump(invoice)
        
        return jsonify(invoice_data), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero della fattura',
            'message': str(e)
        }), 500


@api_v1_bp.route('/invoices', methods=['POST'])
@jwt_required()
def create_invoice():
    """
    Crea una nuova fattura.
    """
    try:
        current_user = get_current_user()
        
        # Validazione dati
        data = invoice_create_schema.load(request.get_json())
        
        # Verifica autorizzazioni per creazione
        if current_user.role and current_user.role.is_dunedain():
            return jsonify({
                'error': 'Accesso negato',
                'message': 'I Dunedain non possono creare fatture'
            }), 403
        
        # Verifica autorizzazione per azienda specifica
        if not user_can_view_company_invoices(current_user, data['company_id']):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Non autorizzato a creare fatture per questa azienda'
            }), 403
        
        # Verifica unicità numero fattura per azienda
        existing = Invoice.query.filter_by(
            company_id=data['company_id'],
            invoice_number=data['invoice_number'],
            is_active=True
        ).first()
        
        if existing:
            return jsonify({
                'error': 'Numero fattura già esistente',
                'message': f'Il numero fattura "{data["invoice_number"]}" esiste già per questa azienda',
                'existing_invoice_id': existing.id
            }), 409
        
        # Creazione fattura
        invoice = Invoice(**data)
        
        db.session.add(invoice)
        db.session.commit()
        
        return jsonify({
            'message': 'Fattura creata con successo',
            'invoice': invoice_schema.dump(invoice)
        }), 201
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({
            'error': 'Violazione vincolo di integrità',
            'message': 'Numero fattura già esistente per questa azienda'
        }), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nella creazione della fattura',
            'message': str(e)
        }), 500


@api_v1_bp.route('/invoices/<int:invoice_id>', methods=['PUT'])
@jwt_required()
def update_invoice(invoice_id):
    """
    Aggiorna una fattura esistente.
    """
    try:
        current_user = get_current_user()
        invoice = Invoice.query.filter_by(id=invoice_id, is_active=True).first_or_404()
        
        # Verifica autorizzazioni
        if not user_can_edit_invoice(current_user, invoice):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Non autorizzato a modificare questa fattura'
            }), 403
        
        # Validazione dati
        data = invoice_update_schema.load(request.get_json())
        
        # Aggiornamento
        for key, value in data.items():
            if hasattr(invoice, key):
                setattr(invoice, key, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Fattura aggiornata con successo',
            'invoice': invoice_schema.dump(invoice)
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'aggiornamento della fattura',
            'message': str(e)
        }), 500


@api_v1_bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@jwt_required()
def delete_invoice(invoice_id):
    """
    Elimina una fattura (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Solo Rohirrim può eliminare fatture
        if not user_can_manage_invoices(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono eliminare fatture'
            }), 403
        
        invoice = Invoice.query.filter_by(id=invoice_id, is_active=True).first_or_404()
        
        # Soft delete
        invoice.is_active = False
        invoice.deleted_at = func.now()
        db.session.commit()
        
        return jsonify({
            'message': 'Fattura eliminata con successo',
            'invoice_number': invoice.invoice_number,
            'supplier': invoice.supplier
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'eliminazione della fattura',
            'message': str(e)
        }), 500


@api_v1_bp.route('/invoices/<int:invoice_id>/workflow', methods=['POST'])
@jwt_required()
def invoice_workflow_action(invoice_id):
    """
    Esegue azioni di workflow su una fattura.
    """
    try:
        current_user = get_current_user()
        invoice = Invoice.query.filter_by(id=invoice_id, is_active=True).first_or_404()
        
        # Verifica autorizzazioni
        if not user_can_edit_invoice(current_user, invoice):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Non autorizzato a modificare questa fattura'
            }), 403
        
        # Validazione dati
        data = invoice_workflow_schema.load(request.get_json())
        action = data['action']
        
        # Esegui azione specifica
        if action == 'mark_as_receipt':
            invoice.document_status = 'receipt'
            invoice.is_final = False
            message = 'Documento marcato come scontrino'
            
        elif action == 'mark_as_delivery_note':
            invoice.document_status = 'delivery_note'
            invoice.is_final = False
            message = 'Documento marcato come bolla di consegna'
            
        elif action == 'convert_to_invoice':
            invoice.document_status = 'invoice'
            invoice.is_final = True
            message = 'Documento convertito in fattura definitiva'
            
        elif action == 'mark_as_processed':
            invoice.is_processed = True
            message = 'Fattura marcata come processata'
            
        elif action == 'mark_as_validated':
            invoice.is_validated = True
            message = 'Fattura marcata come validata'
        
        # Aggiungi note se fornite
        if data.get('notes'):
            invoice.notes = (invoice.notes or '') + f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {data['notes']}"
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'invoice': invoice_schema.dump(invoice)
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'esecuzione dell\'azione workflow',
            'message': str(e)
        }), 500


@api_v1_bp.route('/invoices/check-duplicates', methods=['POST'])
@jwt_required()
def check_invoice_duplicates():
    """
    Controlla potenziali duplicati per una fattura.
    """
    try:
        current_user = get_current_user()
        
        # Validazione dati
        data = invoice_duplicate_check_schema.load(request.get_json())
        
        # Query base per ricerca duplicati
        query = Invoice.query.filter(
            Invoice.is_active == True,
            Invoice.supplier_vat == data['supplier_vat']
        )
        
        # Filtro per importo con tolleranza
        tolerance_amount = data.get('tolerance_amount', Decimal('0.01'))
        min_amount = data['total_amount'] - tolerance_amount
        max_amount = data['total_amount'] + tolerance_amount
        
        query = query.filter(
            Invoice.total_price_with_vat >= min_amount,
            Invoice.total_price_with_vat <= max_amount
        )
        
        # Applica filtri di autorizzazione
        if not user_can_manage_invoices(current_user):
            if current_user.company_id:
                query = query.filter(Invoice.company_id == current_user.company_id)
            else:
                query = query.filter(Invoice.id == None)  # Nessun risultato
        
        duplicates = query.all()
        
        return jsonify({
            'potential_duplicates': len(duplicates),
            'duplicates': [
                {
                    'id': dup.id,
                    'invoice_number': dup.invoice_number,
                    'supplier': dup.supplier,
                    'invoice_date': dup.invoice_date.isoformat() if dup.invoice_date else None,
                    'total_amount': float(dup.total_price_with_vat) if dup.total_price_with_vat else 0,
                    'document_status': dup.document_status,
                    'is_final': dup.is_final,
                    'company_id': dup.company_id
                } for dup in duplicates
            ],
            'search_criteria': data
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Errore nella ricerca duplicati',
            'message': str(e)
        }), 500


@api_v1_bp.route('/invoices/stats', methods=['GET'])
@jwt_required()
def get_invoices_stats():
    """
    Ottiene statistiche delle fatture.
    """
    try:
        current_user = get_current_user()
        
        # Query base con filtri di autorizzazione
        base_query = Invoice.query.filter(Invoice.is_active == True)
        
        if current_user.role and current_user.role.is_rohirrim():
            # Rohirrim può vedere tutte le statistiche
            pass
        elif current_user.role and (current_user.role.is_lord() or current_user.role.is_dunedain()):
            # Lord e Dunedain solo della propria azienda
            if current_user.company_id:
                base_query = base_query.filter(Invoice.company_id == current_user.company_id)
            else:
                return jsonify({
                    'error': 'Accesso negato',
                    'message': 'Utente non associato a nessuna azienda'
                }), 403
        else:
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Statistiche base
        total_invoices = base_query.count()
        total_amount = base_query.with_entities(
            func.sum(Invoice.total_price_with_vat)
        ).scalar() or Decimal('0.00')
        
        average_amount = total_amount / total_invoices if total_invoices > 0 else Decimal('0.00')
        
        stats = {
            'total_invoices': total_invoices,
            'total_amount': float(total_amount),
            'average_amount': float(average_amount),
            'user_context': {
                'company_filter': None if user_can_manage_invoices(current_user) else current_user.company_id,
                'can_view_all': user_can_manage_invoices(current_user)
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero delle statistiche',
            'message': str(e)
        }), 500
