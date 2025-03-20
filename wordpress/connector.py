import logging
import os
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import GetPost, NewPost, EditPost, GetPosts, DeletePost
from wordpress_xmlrpc.methods.users import GetUserInfo
from wordpress_xmlrpc.methods.taxonomies import GetTerms
from wordpress_xmlrpc.methods import media
import base64
import requests
from typing import Union, Dict, Any, Iterable
from utils.config import WP_URL, WP_USERNAME, WP_PASSWORD

# Patch pour wordpress-xmlrpc qui utilise l'ancien collections.Iterable
import sys
import collections
if not hasattr(collections, 'Iterable'):
    collections.Iterable = Iterable

logger = logging.getLogger(__name__)

class WordPressConnector:
    """
    Class to handle WordPress API interactions through XML-RPC
    """
    def __init__(self, demo_mode=False):
        """Initialize WordPress client with credentials from config"""
        # Check if we're in demo mode
        if demo_mode:
            self.client = None
            logger.info("WordPress connector initialized in DEMO mode")
            return
            
        # Check if required environment variables are set
        if not all([WP_URL, WP_USERNAME, WP_PASSWORD]):
            logger.error("Missing WordPress credentials. Check your .env file.")
            if os.getenv("MCP_ALLOW_DEMO_MODE", "false").lower() == "true":
                self.client = None
                logger.info("WordPress connector initialized in DEMO mode due to missing credentials")
                return
            else:
                raise ValueError("WordPress credentials not configured")
        
        # Try to connect to WordPress
        try:
            self.client = Client(WP_URL, WP_USERNAME, WP_PASSWORD)
            # Test connection
            self.client.call(GetUserInfo())
            logger.info("WordPress connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to WordPress: {str(e)}")
            if os.getenv("MCP_ALLOW_DEMO_MODE", "false").lower() == "true":
                self.client = None
                logger.info("WordPress connector initialized in DEMO mode due to connection error")
                return
            else:
                raise ConnectionError(f"WordPress connection failed: {str(e)}")
    
    @property
    def demo_mode(self):
        """Check if we're in demo mode"""
        return self.client is None

    def get_post(self, post_id):
        """Get a post by ID"""
        if self.demo_mode:
            # Return mock data in demo mode
            logger.info(f"DEMO MODE: Returning mock data for post {post_id}")
            mock_post = self._create_mock_post(post_id)
            return mock_post
            
        try:
            return self.client.call(GetPost(post_id))
        except Exception as e:
            logger.error(f"Failed to get post {post_id}: {str(e)}")
            raise

    def get_posts(self, query: Union[Dict[str, Any], int, None] = None) -> list:
        """Get a list of posts with query parameters"""
        if self.demo_mode:
            # Return mock data in demo mode
            number = query.get('number', 10) if isinstance(query, dict) else 10
            logger.info(f"DEMO MODE: Returning {number} mock posts")
            return [self._create_mock_post(i) for i in range(1, number+1)]
            
        try:
            # Vérifier la connexion
            if not self.client:
                raise ConnectionError("WordPress client not initialized")

            # Normaliser la requête
            if isinstance(query, dict):
                final_query = query
            elif isinstance(query, (int, float)):
                final_query = {'number': int(query)}
            else:
                final_query = {'number': 10}

            # Ajouter les paramètres par défaut si nécessaire
            if 'post_type' not in final_query:
                final_query['post_type'] = 'page'
            
            logger.debug(f"Sending query to WordPress: {final_query}")
            posts = self.client.call(GetPosts(final_query))
            logger.info(f"Retrieved {len(posts)} posts from WordPress")
            return posts

        except Exception as e:
            logger.error(f"Failed to get posts: {str(e)}")
            if "Iterable" in str(e):
                logger.warning("WordPress XML-RPC compatibility issue, returning empty list")
                return []
            raise

    def create_post(self, title, content, status='draft', categories=None, tags=None):
        """Create a new post"""
        if self.demo_mode:
            # Simulate post creation in demo mode
            logger.info(f"DEMO MODE: Simulating post creation: {title}")
            return 999  # Mock post ID
            
        post = WordPressPost()
        post.title = title
        post.content = content
        post.post_status = status
        
        if categories:
            post.terms_names = {'category': categories}
        if tags:
            if not post.terms_names:
                post.terms_names = {}
            post.terms_names['post_tag'] = tags
            
        try:
            post_id = self.client.call(NewPost(post))
            logger.info(f"Post created with ID: {post_id}")
            return post_id
        except Exception as e:
            logger.error(f"Failed to create post: {str(e)}")
            raise

    def update_post(self, post_id, title=None, content=None, status=None):
        """Update an existing post"""
        if self.demo_mode:
            # Simulate post update in demo mode
            logger.info(f"DEMO MODE: Simulating post update for ID: {post_id}")
            return True
            
        try:
            # Get existing post
            post = self.client.call(GetPost(post_id))
            
            # Update only provided fields
            if title is not None:
                post.title = title
            if content is not None:
                post.content = content
            if status is not None:
                post.post_status = status
            
            # Save changes
            result = self.client.call(EditPost(post_id, post))
            if result:
                logger.info(f"Post {post_id} updated successfully")
            else:
                logger.warning(f"Post {post_id} update returned false")
            return result
        except Exception as e:
            logger.error(f"Failed to update post {post_id}: {str(e)}")
            return False

    def delete_post(self, post_id):
        """Delete a post by ID"""
        if self.demo_mode:
            # Simulate post deletion in demo mode
            logger.info(f"DEMO MODE: Simulating post deletion for ID: {post_id}")
            return True
            
        try:
            success = self.client.call(DeletePost(post_id))
            if success:
                logger.info(f"Post {post_id} deleted successfully")
            else:
                logger.warning(f"Post {post_id} deletion returned false")
            return success
        except Exception as e:
            logger.error(f"Failed to delete post {post_id}: {str(e)}")
            raise

    def upload_media(self, image_path, image_name=None):
        """Upload media to WordPress"""
        if self.demo_mode:
            # Simulate media upload in demo mode
            logger.info(f"DEMO MODE: Simulating media upload for: {image_path}")
            return {"id": 888, "url": f"https://example.com/wp-content/uploads/{image_path.split('/')[-1]}"}
            
        try:
            with open(image_path, 'rb') as img:
                data = base64.b64encode(img.read()).decode('ascii')
                
            name = image_name or image_path.split('/')[-1]
            data = {
                'name': name,
                'type': f'image/{name.split(".")[-1]}',
                'bits': data
            }
            
            response = self.client.call(media.UploadFile(data))
            logger.info(f"Media uploaded with ID: {response['id']}")
            return response
        except Exception as e:
            logger.error(f"Failed to upload media: {str(e)}")
            raise
            
    def _create_mock_post(self, post_id):
        """Create a mock post for demo mode"""
        from types import SimpleNamespace
        
        post = SimpleNamespace()
        post.id = post_id
        post.title = f"Exemple de page {post_id}"
        
        # Create some example content with sections
        sections = [
            {"title": "Introduction", "content": "<p>Bienvenue sur notre page d'exemple. Cette page est générée en mode démonstration.</p>"},
            {"title": "Nos services", "content": "<p>Nous proposons une variété de services de qualité.</p><ul><li>Service 1</li><li>Service 2</li><li>Service 3</li></ul>"},
            {"title": "Notre équipe", "content": "<p>Notre équipe est composée de professionnels qualifiés.</p>"},
            {"title": "Contactez-nous", "content": "<p>N'hésitez pas à nous contacter pour plus d'informations.</p>"}
        ]
        
        # Build HTML content
        content = ""
        for section in sections:
            content += f"<h2>{section['title']}</h2>{section['content']}"
            
        post.content = content
        post.post_status = "publish"
        post.post_date = "2025-01-01 12:00:00"
        post.terms_names = {"category": ["Pages"], "post_tag": ["exemple", "demo"]}
        
        return post

    def get_elementor_pages(self):
        """Get a list of pages built with Elementor"""
        try:
            # Récupérer toutes les pages
            query = {
                'post_type': 'page',
                'number': 100,  # Augmentez si nécessaire
                'meta_key': '_elementor_edit_mode',  # Filtre pour les pages Elementor
                'meta_value': 'builder'
            }
            
            pages = self.get_posts(query)
            
            # Formater les résultats pour plus de clarté
            elementor_pages = []
            for page in pages:
                elementor_pages.append({
                    'id': page.id,
                    'title': page.title,
                    'status': page.post_status,
                    'url': page.link if hasattr(page, 'link') else None
                })
            
            logger.info(f"Found {len(elementor_pages)} Elementor pages")
            return elementor_pages
            
        except Exception as e:
            logger.error(f"Failed to get Elementor pages: {str(e)}")
            if self.demo_mode:
                # Retourner des données de démonstration
                return [
                    {'id': 1, 'title': 'Accueil', 'status': 'publish', 'url': '/'},
                    {'id': 2, 'title': 'À propos', 'status': 'publish', 'url': '/about'},
                ]
            raise