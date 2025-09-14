# Company CRUD Endpoints - Implementazione Completa

## 📋 Riepilogo Implementazione

### ✅ Completato

1. **Schema Marshmallow** (`/src/app/schemas/company.py`)
   - `CompanySchema`: Per serializzazione/deserializzazione completa
   - `CompanyCreateSchema`: Per validazione creazione nuove aziende
   - `CompanyUpdateSchema`: Per validazione aggiornamenti
   - Validazione completa di tutti i campi (email, VAT number, etc.)

2. **Endpoint REST API** (`/src/app/api/v1/companies.py`)
   - `GET /api/v1/companies` - Lista aziende con paginazione e filtri
   - `GET /api/v1/companies/{id}` - Dettaglio azienda specifica
   - `POST /api/v1/companies` - Creazione nuova azienda
   - `PUT /api/v1/companies/{id}` - Aggiornamento azienda
   - `DELETE /api/v1/companies/{id}` - Eliminazione (soft delete)
   - `POST /api/v1/companies/{id}/activate` - Riattivazione azienda

3. **Controlli di Sicurezza**
   - Autenticazione JWT richiesta per tutti gli endpoint
   - Controllo ruoli: solo Rohirrim può creare/eliminare aziende
   - Autorizzazione: utenti possono vedere solo la propria azienda (eccetto Rohirrim)
   - Validazione dati di input completa

4. **Caratteristiche Avanzate**
   - Paginazione intelligente (max 100 elementi per pagina)
   - Ricerca per nome, ragione sociale, P.IVA, codice fiscale
   - Filtro per aziende attive/inattive
   - Inclusione opzionale di statistiche (contatori utenti, unità immobiliari, etc.)
   - Gestione errori di integrità database (P.IVA/CF duplicati)

### 🔧 Configurazione

1. **Schema aggiunto a** `/src/app/schemas/__init__.py`
2. **Endpoint registrato in** `/src/app/api/v1/__init__.py`

### 🧪 Test di Validazione

Gli schemi Marshmallow sono stati testati e funzionano correttamente:

```python
# Test validazione OK
test_data = {'name': 'Test Company'}
result = company_create_schema.load(test_data)
# Output: {'name': 'Test Company', 'country': 'IT'}
```

### 📡 Esempi di Utilizzo API

#### Ottenere lista aziende
```http
GET /api/v1/companies?page=1&per_page=20&search=acme&include_stats=true
Authorization: Bearer <jwt_token>
```

#### Creare nuova azienda
```http
POST /api/v1/companies
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "ACME Corp",
  "legal_name": "ACME Corporation S.r.l.",
  "vat_number": "IT12345678901",
  "tax_code": "ACMCORP123456",
  "email": "info@acme.com",
  "phone": "+39 02 1234567",
  "address": "Via Roma 123",
  "city": "Milano",
  "province": "MI",
  "postal_code": "20100",
  "country": "IT"
}
```

#### Aggiornare azienda
```http
PUT /api/v1/companies/123
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "email": "new-email@acme.com",
  "phone": "+39 02 7654321"
}
```

### 🔐 Controlli di Autorizzazione

- **Rohirrim**: Accesso completo (CRUD) a tutte le aziende
- **Lord**: Può vedere/modificare solo la propria azienda
- **Dunedain**: Può solo visualizzare la propria azienda

### 🚦 Codici di Risposta

- `200`: Operazione completata con successo
- `201`: Azienda creata con successo
- `400`: Errore di validazione dati
- `401`: Token JWT mancante o non valido
- `403`: Accesso negato (permessi insufficienti)
- `404`: Azienda non trovata
- `409`: Conflitto (P.IVA o Codice Fiscale già esistente)
- `500`: Errore interno del server

### 🚀 Prossimi Passi

Per testare completamente gli endpoint:

1. Configurare environment senza Azure Key Vault per test locali
2. Avviare server su porta alternativa (5001)
3. Creare token JWT per test autenticazione
4. Eseguire test completi con Postman o curl

## 📁 File Modificati

- ✅ `/src/app/schemas/company.py` - Nuovo file
- ✅ `/src/app/schemas/__init__.py` - Aggiornato
- ✅ `/src/app/api/v1/companies.py` - Nuovo file  
- ✅ `/src/app/api/v1/__init__.py` - Aggiornato

## 💡 Note Tecniche

- Tutti gli endpoint rispettano le convenzioni REST
- Validazione robusta con Marshmallow
- Gestione errori completa
- Documentazione inline per ogni endpoint
- Supporto per operazioni bulk future (paginazione pronta)
- Schema database già esistente e migrato
