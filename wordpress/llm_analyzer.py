import requests
import logging
import os
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from openai import OpenAI
from dotenv import load_dotenv
from urllib.parse import urlparse
import socket
from requests.exceptions import RequestException
import time

# Charger les variables d'environnement
load_dotenv()

logger = logging.getLogger(__name__)

class BaseLLMAnalyzer(ABC):
    """Classe de base pour l'analyse LLM"""
    
    def __init__(self, site_url: str):
        self.site_url = self._normalize_url(site_url)
        self.timeout = int(os.getenv("API_TIMEOUT", 30))
        self.max_retries = 3
        
    def _normalize_url(self, url: str) -> str:
        """Normalise l'URL en ajoutant le protocole si nécessaire"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
        
    def _is_valid_url(self, url: str) -> bool:
        """Vérifie si l'URL est valide et accessible"""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False
                
            # Vérifier si le domaine est résolvable
            socket.gethostbyname(result.netloc)
            return True
        except Exception:
            return False
            
    def get_site_content(self) -> str:
        """Récupère le contenu du site avec retry et timeout"""
        if not self._is_valid_url(self.site_url):
            logger.error(f"URL invalide ou inaccessible: {self.site_url}")
            return ""
            
        for attempt in range(self.max_retries):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(
                    self.site_url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=True
                )
                response.raise_for_status()
                return response.text
                
            except RequestException as e:
                logger.warning(f"Tentative {attempt + 1}/{self.max_retries} échouée: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # Attendre 1 seconde avant de réessayer
                continue
            except Exception as e:
                logger.error(f"Erreur lors de la récupération du contenu: {str(e)}")
                return ""
                
        logger.error(f"Impossible de récupérer le contenu après {self.max_retries} tentatives")
        return ""

class GPT4Analyzer(BaseLLMAnalyzer):
    """Analyseur utilisant GPT-4"""
    
    def __init__(self, site_url: str, api_key: Optional[str] = None):
        super().__init__(site_url)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.max_tokens = int(os.getenv("GPT4_MAX_TOKENS", 4000))
        self.client = OpenAI(api_key=self.api_key)
        
    def analyze_content(self, content: str) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en analyse de contenu web. Analysez le site web fourni et donnez des recommandations détaillées."},
                    {"role": "user", "content": f"Analysez ce contenu et donnez des recommandations: {content[:self.max_tokens]}"}
                ]
            )
            return {
                "model": "GPT-4",
                "recommendations": response.choices[0].message.content.split("\n"),
                "score": 0.95
            }
        except Exception as e:
            logger.error(f"Erreur GPT-4: {str(e)}")
            return {"error": str(e)}

class OpenAIMiniAnalyzer(BaseLLMAnalyzer):
    """Analyseur utilisant OpenAI o1-mini"""
    
    def __init__(self, site_url: str, api_key: Optional[str] = None):
        super().__init__(site_url)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.max_tokens = int(os.getenv("OPENAI_MINI_MAX_TOKENS", 2000))
        self.client = OpenAI(api_key=self.api_key)
        
    def analyze_content(self, content: str) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Analysez ce site web de manière concise."},
                    {"role": "user", "content": f"Analyse rapide du contenu: {content[:self.max_tokens]}"}
                ]
            )
            return {
                "model": "OpenAI-Mini",
                "recommendations": response.choices[0].message.content.split("\n"),
                "score": 0.85
            }
        except Exception as e:
            logger.error(f"Erreur OpenAI-Mini: {str(e)}")
            return {"error": str(e)}

class DeepSeekAnalyzer(BaseLLMAnalyzer):
    """Analyseur utilisant DeepSeek"""
    
    def __init__(self, site_url: str, api_key: Optional[str] = None):
        super().__init__(site_url)
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", 3000))
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
    def analyze_content(self, content: str) -> Dict:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Vous êtes un expert en analyse de contenu web. Analysez le site web fourni et donnez des recommandations détaillées."},
                    {"role": "user", "content": f"Analysez ce contenu et donnez des recommandations: {content[:self.max_tokens]}"}
                ]
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "model": "DeepSeek",
                "recommendations": result["choices"][0]["message"]["content"].split("\n"),
                "score": 0.88
            }
        except Exception as e:
            logger.error(f"Erreur DeepSeek: {str(e)}")
            return {"error": str(e)}

class LLMAnalyzer:
    """Classe principale pour l'analyse multi-LLM"""
    
    def __init__(self, site_url: str, api_keys: Optional[Dict[str, str]] = None):
        """
        Initialise l'analyseur LLM
        
        Args:
            site_url (str): URL du site à analyser
            api_keys (Dict[str, str], optional): Clés API pour chaque service
        """
        self.site_url = site_url
        self.api_keys = api_keys or {}
        
        # Initialiser les analyseurs
        self.analyzers = {
            "gpt4": GPT4Analyzer(site_url, self.api_keys.get("openai")),
            "openai_mini": OpenAIMiniAnalyzer(site_url, self.api_keys.get("openai")),
            "deepseek": DeepSeekAnalyzer(site_url, self.api_keys.get("deepseek"))
        }
        
    def analyze_site(self, models: Optional[List[str]] = None) -> Dict:
        """
        Analyse le site avec les modèles spécifiés
        
        Args:
            models (List[str], optional): Liste des modèles à utiliser
            
        Returns:
            Dict: Résultats de l'analyse
        """
        if not models:
            models = list(self.analyzers.keys())
            
        # Utiliser GPT4 pour récupérer le contenu une seule fois
        content = self.analyzers["gpt4"].get_site_content()
        if not content:
            logger.error(f"Impossible d'analyser le site {self.site_url}: contenu inaccessible")
            return {
                "error": "Site inaccessible",
                "details": "Impossible de récupérer le contenu du site. Vérifiez l'URL et l'accessibilité du site."
            }
            
        results = {}
        for model in models:
            if model in self.analyzers:
                model_result = self.analyzers[model].analyze_content(content)
                if "error" not in model_result:
                    results[model] = model_result
                else:
                    logger.warning(f"Erreur avec le modèle {model}: {model_result['error']}")
            
        if not results:
            return {
                "error": "Analyse échouée",
                "details": "Aucun modèle n'a pu analyser le contenu correctement."
            }
            
        return results
        
    def get_brand_ranking(self) -> List[Dict]:
        """
        Récupère le classement de la marque à travers différents LLMs
        
        Returns:
            List[Dict]: Liste des classements par LLM
        """
        try:
            results = self.analyze_site()
            if "error" in results:
                return []
                
            rankings = []
            for model, result in results.items():
                if "error" not in result:
                    rankings.append({
                        "model": result["model"],
                        "score": result["score"],
                        "recommendations": result["recommendations"][:3]  # Top 3 recommandations
                    })
                    
            return rankings
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du classement: {str(e)}")
            return []
            
    def get_recommendations(self) -> List[str]:
        """
        Récupère les recommandations d'amélioration
        
        Returns:
            List[str]: Liste des recommandations
        """
        try:
            results = self.analyze_site()
            if "error" in results:
                return []
                
            # Fusionner les recommandations de tous les modèles
            all_recommendations = []
            for result in results.values():
                if "error" not in result:
                    all_recommendations.extend(result["recommendations"])
                    
            # Supprimer les doublons et trier par pertinence
            return list(dict.fromkeys(all_recommendations))
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des recommandations: {str(e)}")
            return [] 