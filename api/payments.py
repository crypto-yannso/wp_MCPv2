from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import stripe
import os
from dotenv import load_dotenv
from .database import Database
from .auth import get_current_user

# Charger les variables d'environnement
load_dotenv()

# Configuration Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

router = APIRouter(prefix="/payments", tags=["payments"])

class PaymentIntent(BaseModel):
    amount: float
    currency: str = "eur"
    payment_method_types: list = ["card"]

class CreditPackage(BaseModel):
    id: str
    name: str
    credits: int
    price: float
    description: str

class CreatePaymentIntentRequest(BaseModel):
    package_id: str

# Packages de crédits disponibles
CREDIT_PACKAGES = [
    CreditPackage(
        id="basic",
        name="Pack Basic",
        credits=100,
        price=9.99,
        description="100 crédits pour commencer"
    ),
    CreditPackage(
        id="pro",
        name="Pack Pro",
        credits=500,
        price=39.99,
        description="500 crédits pour les utilisateurs réguliers"
    ),
    CreditPackage(
        id="enterprise",
        name="Pack Enterprise",
        credits=2000,
        price=149.99,
        description="2000 crédits pour les entreprises"
    )
]

async def get_credit_packages() -> List[CreditPackage]:
    """Récupérer la liste des packages de crédits disponibles"""
    return CREDIT_PACKAGES

@router.get("/packages")
async def get_credit_packages_endpoint() -> List[CreditPackage]:
    """Endpoint pour récupérer la liste des packages de crédits disponibles"""
    return await get_credit_packages()

async def create_payment_intent(request: CreatePaymentIntentRequest, current_user: Dict) -> Dict:
    """Créer une intention de paiement pour un package"""
    # Trouver le package demandé
    package = next((p for p in CREDIT_PACKAGES if p.id == request.package_id), None)
    if not package:
        raise HTTPException(status_code=404, detail="Package non trouvé")

    try:
        # Créer l'intention de paiement avec Stripe
        payment_intent = stripe.PaymentIntent.create(
            amount=int(package.price * 100),  # Convertir en centimes
            currency="eur",
            metadata={
                "user_id": current_user["id"],
                "package_id": package.id,
                "credits": str(package.credits)
            }
        )

        # Créer une transaction en attente
        transaction = await Database.create_transaction(
            user_id=current_user["id"],
            amount=package.price,
            type="credit_purchase",
            description=f"Achat de {package.credits} crédits",
            stripe_payment_id=payment_intent.id,
            status="pending"
        )

        return {
            "clientSecret": payment_intent.client_secret,
            "package": package,
            "transaction": transaction.get("transaction", {})
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create-payment-intent")
async def create_payment_intent_endpoint(request: CreatePaymentIntentRequest, current_user: Dict = Depends(lambda: {"id": "test"})) -> Dict:
    """Endpoint pour créer une intention de paiement"""
    return await create_payment_intent(request, current_user)

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Gérer les webhooks Stripe"""
    try:
        # Récupérer la signature du webhook
        signature = request.headers.get("stripe-signature")
        if not signature:
            raise HTTPException(status_code=400, detail="Signature manquante")

        # Récupérer le corps de la requête
        payload = await request.body()
        
        # Vérifier la signature
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Signature invalide")

        # Traiter l'événement
        if event.type == "payment_intent.succeeded":
            payment_intent = event.data.object
            await process_successful_payment(payment_intent)

        return {"status": "success"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def process_successful_payment(payment_intent) -> Dict:
    """Traiter un paiement réussi"""
    try:
        user_id = payment_intent.metadata["user_id"]
        credits = int(payment_intent.metadata["credits"])
        amount = payment_intent.amount / 100  # Convertir les centimes en euros

        # Mettre à jour la transaction
        transaction = await Database.create_transaction(
            user_id=user_id,
            amount=amount,
            type="credit_purchase",
            description=f"Achat de {credits} crédits",
            stripe_payment_id=payment_intent.id,
            status="completed"
        )

        if not transaction.get("success"):
            raise Exception(transaction.get("error", "Erreur lors de la création de la transaction"))

        # Ajouter les crédits à l'utilisateur
        credits_result = await Database.add_user_credits(user_id, credits)

        if not credits_result.get("success"):
            raise Exception(credits_result.get("error", "Erreur lors de l'ajout des crédits"))

        return {
            "success": True,
            "transaction": transaction.get("transaction", {}),
            "credits": credits_result.get("credits", {})
        }

    except Exception as e:
        print(f"Erreur lors du traitement du paiement: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/credits")
async def get_user_credits(current_user = Depends(get_current_user)):
    """Obtenir le solde de crédits de l'utilisateur"""
    try:
        credits = await Database.get_user_credits(current_user.id)
        return {
            "credits": credits,
            "user_id": current_user.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/transactions")
async def get_user_transactions(current_user = Depends(get_current_user)):
    """Obtenir l'historique des transactions de l'utilisateur"""
    try:
        transactions = await Database.get_user_transactions(current_user.id)
        return {
            "transactions": transactions,
            "user_id": current_user.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 