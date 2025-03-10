from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from supabase import create_client
import os
from dotenv import load_dotenv
from typing import Optional
from .database import Database
import jwt
from datetime import datetime, timedelta

# Charger les variables d'environnement
load_dotenv()

# Récupérer les variables d'environnement
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL et SUPABASE_KEY doivent être définis dans le fichier .env")

# Initialisation de Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter(prefix="/auth", tags=["auth"])

# Configuration des URLs de redirection
FRONTEND_URL = "http://localhost:3000"
VERIFICATION_SUCCESS_URL = f"{FRONTEND_URL}/auth/verification-success"
RESET_PASSWORD_URL = f"{FRONTEND_URL}/auth/reset-password"

# Modèles de données
class UserCreate(BaseModel):
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "user"

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

# OAuth2 scheme pour la vérification du token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Fonction pour vérifier le token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Vérifier le token avec Supabase
        user = supabase.auth.get_user(token)
        return user.user
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Modèles supplémentaires
class ResetPasswordRequest(BaseModel):
    email: str

class UpdatePasswordRequest(BaseModel):
    new_password: str
    token: str

# Routes d'authentification
@router.post("/register")
async def register(user_data: UserCreate):
    """Créer un nouvel utilisateur"""
    result = await Database.create_user(user_data.email, user_data.password)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    # Mettre à jour le profil avec les informations supplémentaires
    if user_data.first_name or user_data.last_name:
        profile_data = {
            "first_name": user_data.first_name,
            "last_name": user_data.last_name
        }
        await Database.update_user_profile(result["user"].id, profile_data)
    
    return {
        "message": "Utilisateur créé avec succès",
        "user": result["user"]
    }

@router.post("/login")
async def login(request: Request):
    """Connecter un utilisateur"""
    try:
        # Vérifier le type de contenu
        content_type = request.headers.get("content-type", "").lower()
        
        if "application/json" in content_type:
            # Pour les requêtes JSON
            body = await request.json()
            email = body.get("username") or body.get("email")
            password = body.get("password")
        else:
            # Pour les requêtes form-urlencoded
            form = await request.form()
            email = form.get("username") or form.get("email")
            password = form.get("password")
            
        if not email or not password:
            raise HTTPException(
                status_code=422,
                detail="Email et mot de passe requis"
            )
            
        result = await Database.login_user(email, password)
        
        if not result["success"]:
            raise HTTPException(
                status_code=401,
                detail="Email ou mot de passe incorrect"
            )
        
        return Token(
            access_token=result["access_token"],
            user=result["user"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la connexion: {str(e)}"
        )

@router.get("/profile")
async def get_profile(token: str = Depends(oauth2_scheme)):
    """Récupérer le profil de l'utilisateur connecté"""
    try:
        # Décoder le token pour obtenir l'ID utilisateur
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        result = await Database.get_user_profile(user_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail="Profil non trouvé")
        
        return result["profile"]
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

@router.put("/profile")
async def update_profile(
    profile_data: dict,
    token: str = Depends(oauth2_scheme)
):
    """Mettre à jour le profil de l'utilisateur"""
    try:
        # Décoder le token pour obtenir l'ID utilisateur
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        result = await Database.update_user_profile(user_id, profile_data)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result["profile"]
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

@router.delete("/profile")
async def delete_profile(token: str = Depends(oauth2_scheme)):
    """Supprimer le compte utilisateur"""
    try:
        # Décoder le token pour obtenir l'ID utilisateur
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        result = await Database.delete_user(user_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return {"message": "Compte supprimé avec succès"}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

@router.post("/auth/forgot-password")
async def forgot_password(request: ResetPasswordRequest):
    try:
        # Envoyer l'email de réinitialisation via Supabase
        response = supabase.auth.reset_password_email(
            email=request.email,
            options={
                "redirect_to": RESET_PASSWORD_URL
            }
        )
        return {
            "message": "Instructions de réinitialisation envoyées par email",
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auth/reset-password")
async def reset_password(request: UpdatePasswordRequest):
    try:
        # Mettre à jour le mot de passe avec le token
        response = supabase.auth.verify_and_change_password(
            token=request.token,
            new_password=request.new_password
        )
        return {
            "message": "Mot de passe mis à jour avec succès",
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/auth/verify")
async def verify_email(token: str):
    try:
        # Vérifier le token de vérification d'email
        response = supabase.auth.verify_otp({
            "token": token,
            "type": "email"
        })
        # Rediriger vers le front-end avec succès
        return RedirectResponse(url=VERIFICATION_SUCCESS_URL)
    except Exception as e:
        # Rediriger vers le front-end avec erreur
        error_url = f"{FRONTEND_URL}/auth/verification-error?error={str(e)}"
        return RedirectResponse(url=error_url) 

