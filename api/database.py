from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Dict, Any, List

# Charger les variables d'environnement
load_dotenv()

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY doivent être définis dans le fichier .env")

# Initialisation du client Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class Database:
    @staticmethod
    async def create_user(email: str, password: str) -> Dict:
        """Créer un nouvel utilisateur"""
        try:
            # Créer l'utilisateur dans auth.users
            auth_user = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            return {
                "success": True,
                "user": auth_user.user,
                "message": "Utilisateur créé avec succès"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Erreur lors de la création de l'utilisateur"
            }

    @staticmethod
    async def login_user(email: str, password: str) -> Dict:
        """Connecter un utilisateur"""
        try:
            print(f"Tentative de connexion pour l'email: {email}")  # Debug log
            
            # Authentifier l'utilisateur
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            print(f"Authentification réussie pour l'utilisateur: {auth_response.user.id}")  # Debug log
            
            try:
                # Récupérer les informations du profil
                user_profile = supabase.table("users").select("*").eq("id", auth_response.user.id).single().execute()
                profile_data = user_profile.data
            except Exception as profile_error:
                print(f"Profil non trouvé, création d'un nouveau profil")
                # Si le profil n'existe pas, on le crée
                profile_data = {
                    "id": auth_response.user.id,
                    "email": email,
                    "created_at": datetime.utcnow().isoformat()
                }
                try:
                    result = supabase.table("users").insert(profile_data).execute()
                    profile_data = result.data[0] if result.data else profile_data
                except Exception as insert_error:
                    print(f"Erreur lors de la création du profil: {str(insert_error)}")
                    # Même si la création du profil échoue, on continue avec les données de base
            
            print(f"Profil utilisateur: {profile_data}")  # Debug log
            
            return {
                "success": True,
                "access_token": auth_response.session.access_token,
                "user": {
                    **auth_response.user.model_dump(),
                    "profile": profile_data
                }
            }
        except Exception as e:
            print(f"Erreur de connexion: {str(e)}")  # Debug log
            return {
                "success": False,
                "error": str(e),
                "message": "Erreur lors de la connexion"
            }

    @staticmethod
    async def get_user_profile(user_id: str) -> Dict:
        """Récupérer le profil d'un utilisateur"""
        try:
            profile = supabase.table("users").select("*").eq("id", user_id).single().execute()
            return {
                "success": True,
                "profile": profile.data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Erreur lors de la récupération du profil"
            }

    @staticmethod
    async def update_user_profile(user_id: str, data: Dict) -> Dict:
        """Mettre à jour le profil d'un utilisateur"""
        try:
            data["updated_at"] = datetime.utcnow().isoformat()
            profile = supabase.table("users").update(data).eq("id", user_id).execute()
            return {
                "success": True,
                "profile": profile.data[0]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Erreur lors de la mise à jour du profil"
            }

    @staticmethod
    async def delete_user(user_id: str) -> Dict:
        """Supprimer un utilisateur"""
        try:
            # Supprimer l'utilisateur de auth.users (cela déclenchera la suppression en cascade)
            supabase.auth.admin.delete_user(user_id)
            return {
                "success": True,
                "message": "Utilisateur supprimé avec succès"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Erreur lors de la suppression de l'utilisateur"
            }

    @staticmethod
    async def save_command(
        user_id: str,
        command: str,
        command_type: str,
        parameters: Optional[Dict] = None,
        status: str = "pending"
    ):
        """Sauvegarder une commande dans la base de données"""
        data = {
            "user_id": user_id,
            "command": command,
            "command_type": command_type,
            "parameters": parameters,
            "status": status,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("commands").insert(data).execute()
        return result.data[0]

    @staticmethod
    async def update_command_status(command_id: int, status: str, result: Optional[Dict] = None):
        """Mettre à jour le statut d'une commande"""
        data = {
            "status": status,
            "result": result,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("commands").update(data).eq("id", command_id).execute()
        return result.data[0]

    @staticmethod
    async def get_user_commands(user_id: str):
        """Récupérer toutes les commandes d'un utilisateur"""
        result = supabase.table("commands").select("*").eq("user_id", user_id).execute()
        return result.data

    @staticmethod
    async def save_wordpress_page(
        user_id: str,
        title: str,
        content: str,
        wp_page_id: int,
        status: str = "published"
    ):
        """Sauvegarder une page WordPress"""
        data = {
            "user_id": user_id,
            "title": title,
            "content": content,
            "wp_page_id": wp_page_id,
            "status": status,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("wordpress_pages").insert(data).execute()
        return result.data[0]

    @staticmethod
    async def get_wordpress_pages(user_id: str):
        """Récupérer toutes les pages WordPress d'un utilisateur"""
        result = supabase.table("wordpress_pages").select("*").eq("user_id", user_id).execute()
        return result.data

    @staticmethod
    async def get_user_credits(user_id: str) -> float:
        """Obtenir le solde de crédits d'un utilisateur"""
        try:
            result = supabase.table("credits").select("amount").eq("user_id", user_id).single().execute()
            return result.data["amount"] if result.data else 0
        except Exception as e:
            print(f"Erreur lors de la récupération des crédits: {str(e)}")
            return 0

    @staticmethod
    async def add_user_credits(user_id: str, amount: float) -> Dict:
        """Ajouter des crédits à un utilisateur"""
        try:
            # Vérifier si l'utilisateur a déjà des crédits
            try:
                result = supabase.table("credits").select("amount").eq("user_id", user_id).single().execute()
                current_credits = result.data.get("amount", 0) if result.data else 0
            except Exception:
                current_credits = 0
            
            if current_credits > 0:
                # Mettre à jour les crédits existants
                result = supabase.table("credits").update({
                    "amount": current_credits + amount,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("user_id", user_id).execute()
            else:
                # Créer une nouvelle entrée
                result = supabase.table("credits").insert({
                    "user_id": user_id,
                    "amount": amount,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }).execute()
            
            if not result.data:
                raise Exception("Erreur lors de la mise à jour des crédits")
            
            return {
                "success": True,
                "credits": result.data[0]
            }
        except Exception as e:
            print(f"Erreur lors de l'ajout des crédits: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def use_credits(user_id: str, amount: float) -> Dict:
        """Utiliser des crédits"""
        try:
            current_credits = await Database.get_user_credits(user_id)
            
            if current_credits < amount:
                return {
                    "success": False,
                    "error": "Crédits insuffisants"
                }
            
            result = supabase.table("credits").update({
                "amount": current_credits - amount,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
            
            return {
                "success": True,
                "credits": result.data[0]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def create_transaction(
        user_id: str,
        amount: float,
        type: str,
        description: str,
        stripe_payment_id: Optional[str] = None,
        status: str = "completed"
    ) -> Dict:
        """Créer une nouvelle transaction"""
        try:
            data = {
                "user_id": user_id,
                "amount": amount,
                "type": type,
                "description": description,
                "status": status,
                "created_at": datetime.utcnow().isoformat()
            }
            
            if stripe_payment_id:
                data["stripe_payment_id"] = stripe_payment_id
            
            result = supabase.table("transactions").insert(data).execute()
            
            if not result.data:
                raise Exception("Erreur lors de la création de la transaction")
            
            return {
                "success": True,
                "transaction": result.data[0]
            }
        except Exception as e:
            print(f"Erreur lors de la création de la transaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def get_user_transactions(user_id: str) -> List[Dict]:
        """Récupérer l'historique des transactions d'un utilisateur"""
        try:
            result = supabase.table("transactions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return result.data
        except Exception as e:
            print(f"Erreur lors de la récupération des transactions: {str(e)}")
            return [] 