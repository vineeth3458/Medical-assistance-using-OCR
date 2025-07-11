# document_manager.py
import logging
import json
from datetime import datetime
from collections import Counter
from flask import current_app
from extensions import db
from models import Document

logger = logging.getLogger(__name__)

class DocumentManager:
    def __init__(self):
        self.documents = {}
        logger.debug("Document Manager initialized")

    def add_document(self, document):
        document_id = document.get('id')
        if not document_id:
            raise ValueError("Document must have an ID")

        self.documents[document_id] = document

        try:
            existing_doc = Document.query.get(document_id)
            if existing_doc:
                existing_doc.name = document.get('name')
                existing_doc.type = document.get('type')
                existing_doc.raw_text = document.get('raw_text')
                existing_doc.image_data = document.get('image_data')
                existing_doc.set_processed_data(document.get('processed_data', {}))
            else:
                db_document = Document(
                    id=document_id,
                    name=document.get('name'),
                    type=document.get('type'),
                    raw_text=document.get('raw_text'),
                    image_data=document.get('image_data')
                )
                db_document.set_processed_data(document.get('processed_data', {}))
                db.session.add(db_document)

            db.session.commit()
            logger.debug(f"Added document to database with ID: {document_id}")
        except Exception as e:
            logger.error(f"Error storing document in database: {str(e)}")
            db.session.rollback()

        return document_id

    def get_document(self, document_id):
        try:
            db_document = Document.query.get(document_id)
            if db_document:
                logger.debug(f"Retrieved document {document_id} from database")
                return {
                    'id': db_document.id,
                    'name': db_document.name,
                    'type': db_document.type,
                    'created_at': db_document.created_at.isoformat(),
                    'raw_text': db_document.raw_text,
                    'processed_data': db_document.get_processed_data(),
                    'image_data': db_document.image_data
                }
        except Exception as e:
            logger.error(f"Error retrieving document from database: {str(e)}")

        document = self.documents.get(document_id)
        if not document:
            logger.warning(f"Document with ID {document_id} not found")
        return document

    def update_document(self, document_id, updates):
        document = self.documents.get(document_id)
        if document:
            document.update(updates)

        try:
            db_document = Document.query.get(document_id)
            if not db_document:
                logger.warning(f"Cannot update document {document_id} in database: not found")
                return document

            if 'name' in updates:
                db_document.name = updates['name']
            if 'type' in updates:
                db_document.type = updates['type']
            if 'raw_text' in updates:
                db_document.raw_text = updates['raw_text']
            if 'processed_data' in updates:
                db_document.set_processed_data(updates['processed_data'])
            if 'image_data' in updates:
                db_document.image_data = updates['image_data']

            db.session.commit()
            logger.debug(f"Updated document in database with ID: {document_id}")
            return self.get_document(document_id)
        except Exception as e:
            logger.error(f"Error updating document in database: {str(e)}")
            db.session.rollback()
            return document

    def delete_document(self, document_id):
        in_memory_deleted = False
        if document_id in self.documents:
            del self.documents[document_id]
            in_memory_deleted = True

        try:
            db_document = Document.query.get(document_id)
            if db_document:
                db.session.delete(db_document)
                db.session.commit()
                logger.debug(f"Deleted document from database with ID: {document_id}")
                return True
            else:
                logger.warning(f"Document {document_id} not found in database for deletion")
                return in_memory_deleted
        except Exception as e:
            logger.error(f"Error deleting document from database: {str(e)}")
            db.session.rollback()
            return in_memory_deleted

    def get_all_documents(self):
        documents = []
        try:
            db_documents = Document.query.all()
            for doc in db_documents:
                documents.append({
                    'id': doc.id,
                    'name': doc.name,
                    'type': doc.type,
                    'created_at': doc.created_at.isoformat(),
                    'raw_text': doc.raw_text,
                    'processed_data': doc.get_processed_data(),
                    'image_data': doc.image_data
                })
            logger.debug(f"Retrieved {len(documents)} documents from database")
        except Exception as e:
            logger.error(f"Error retrieving documents from database: {str(e)}")
            documents = list(self.documents.values())
            logger.debug(f"Falling back to {len(documents)} in-memory documents")

        return documents

    def get_documents_by_type(self, document_type):
        try:
            db_documents = Document.query.filter_by(type=document_type).all()
            documents = []
            for doc in db_documents:
                documents.append({
                    'id': doc.id,
                    'name': doc.name,
                    'type': doc.type,
                    'created_at': doc.created_at.isoformat(),
                    'raw_text': doc.raw_text,
                    'processed_data': doc.get_processed_data(),
                    'image_data': doc.image_data
                })
            logger.debug(f"Retrieved {len(documents)} documents of type {document_type} from database")
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents by type from database: {str(e)}")
            return [doc for doc in self.documents.values() if doc.get('type') == document_type]

    def search_documents(self, query):
        query = query.lower()
        results = []

        try:
            db_documents = Document.query.filter(Document.raw_text.ilike(f'%{query}%')).all()

            for doc in db_documents:
                doc_dict = {
                    'id': doc.id,
                    'name': doc.name,
                    'type': doc.type,
                    'created_at': doc.created_at.isoformat(),
                    'raw_text': doc.raw_text,
                    'processed_data': doc.get_processed_data(),
                    'image_data': doc.image_data
                }
                if doc_dict['id'] not in [d['id'] for d in results]:
                    results.append(doc_dict)

            db_docs = Document.query.all()
            for doc in db_docs:
                if doc.id in [d['id'] for d in results]:
                    continue

                processed_data = doc.get_processed_data()
                found = False
                for key, value in processed_data.items():
                    if isinstance(value, str) and query in value.lower():
                        found = True
                        break
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and query in item.lower():
                                found = True
                                break
                        if found:
                            break

                if found:
                    results.append({
                        'id': doc.id,
                        'name': doc.name,
                        'type': doc.type,
                        'created_at': doc.created_at.isoformat(),
                        'raw_text': doc.raw_text,
                        'processed_data': processed_data,
                        'image_data': doc.image_data
                    })

            logger.debug(f"Found {len(results)} documents matching '{query}' in database")
        except Exception as e:
            logger.error(f"Error searching documents in database: {str(e)}")
            for doc in self.documents.values():
                if query in doc.get('raw_text', '').lower():
                    results.append(doc)
                    continue

                processed_data = doc.get('processed_data', {})
                for key, value in processed_data.items():
                    if isinstance(value, str) and query in value.lower():
                        results.append(doc)
                        break
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and query in item.lower():
                                results.append(doc)
                                break

        return results

    def get_document_type_counts(self):
        try:
            from sqlalchemy import func
            type_counts = db.session.query(Document.type, func.count(Document.id)).group_by(Document.type).all()
            return dict(type_counts)
        except Exception as e:
            logger.error(f"Error getting document type counts from database: {str(e)}")
            types = [doc.get('type') for doc in self.documents.values()]
            return dict(Counter(types))
