"""
Servicio de Firebase Admin SDK para verificar tokens de autenticación.
"""
import os
import json
from typing import Optional, Dict
from firebase_admin import credentials, initialize_app, auth
from fastapi import HTTPException, status


class FirebaseService:
    """Servicio para interactuar con Firebase Admin SDK"""
    
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """
        Inicializar Firebase Admin SDK.
        
        Soporta dos métodos de configuración:
        1. Archivo JSON (FIREBASE_CREDENTIALS_PATH)
        2. Variables de entorno individuales
        """
        if cls._initialized:
            return
        
        try:
            # Opción 1: Usar archivo serviceAccountKey.json
            credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            
            if credentials_path and os.path.exists(credentials_path):
                cred = credentials.Certificate(credentials_path)
                initialize_app(cred)
                print(f"✅ Firebase inicializado desde archivo: {credentials_path}")
            
            # Opción 2: Usar variables de entorno individuales (más seguro para producción)
            elif os.getenv("FIREBASE_PROJECT_ID"):
                cred_dict = {
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": os.getenv("FIREBASE_CERT_URL")
                }
                cred = credentials.Certificate(cred_dict)
                initialize_app(cred)
                print("✅ Firebase inicializado desde variables de entorno")
            
            else:
                print("⚠️ Firebase no configurado. Google Auth no estará disponible.")
                print("   Configura FIREBASE_CREDENTIALS_PATH o las variables individuales.")
                return
            
            cls._initialized = True
            
        except Exception as e:
            print(f"❌ Error al inicializar Firebase: {e}")
            print("   Google Auth no estará disponible.")
    
    @staticmethod
    def verify_token(firebase_token: str) -> Optional[Dict]:
        """
        Verificar token de Firebase y extraer información del usuario.
        
        Args:
            firebase_token: Token de ID de Firebase desde el frontend
            
        Returns:
            Dict con información del usuario:
            - uid: ID único de Firebase
            - email: Email del usuario
            - email_verified: Si el email está verificado
            - name: Nombre del usuario
            - picture: URL de la foto de perfil
            
        Raises:
            HTTPException: Si el token es inválido o expirado
        """
        if not FirebaseService._initialized:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "success": False,
                    "status_code": 503,
                    "message": "Autenticación con Google no disponible",
                    "error": "GOOGLE_AUTH_NOT_CONFIGURED"
                }
            )
        
        try:
            # Verificar el token con Firebase Admin SDK
            decoded_token = auth.verify_id_token(firebase_token)
            
            return {
                "uid": decoded_token.get("uid"),
                "email": decoded_token.get("email"),
                "email_verified": decoded_token.get("email_verified", False),
                "name": decoded_token.get("name", decoded_token.get("email", "").split("@")[0]),
                "picture": decoded_token.get("picture")
            }
            
        except auth.ExpiredIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "status_code": 401,
                    "message": "El token de Google ha expirado",
                    "error": "FIREBASE_TOKEN_EXPIRED"
                }
            )
        except auth.RevokedIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "status_code": 401,
                    "message": "El token de Google ha sido revocado",
                    "error": "FIREBASE_TOKEN_REVOKED"
                }
            )
        except auth.InvalidIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "status_code": 401,
                    "message": "Token de Google inválido",
                    "error": "FIREBASE_TOKEN_INVALID"
                }
            )
        except Exception as e:
            print(f"Error al verificar token de Firebase: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "status_code": 401,
                    "message": "No se pudo verificar el token de Google",
                    "error": "FIREBASE_VERIFICATION_FAILED"
                }
            )


# Instancia global del servicio
firebase_service = FirebaseService()
