import logging
import os
from typing import Iterable
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import GetPost, NewPost, EditPost, GetPosts, DeletePost
from wordpress_xmlrpc.methods.users import GetUserInfo
from wordpress_xmlrpc.methods.taxonomies import GetTerms
from wordpress_xmlrpc.methods import media
import base64
import requests
from utils.config import WP_URL, WP_USERNAME, WP_PASSWORD
from types import SimpleNamespace

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

    def get_posts(self, number=10):
        """Get a list of posts"""
        if self.demo_mode:
            # Return mock data in demo mode
            logger.info(f"DEMO MODE: Returning {number} mock posts")
            return [self._create_mock_post(i) for i in range(1, number+1)]
            
        try:
            return self.client.call(GetPosts({'number': number}))
        except Exception as e:
            logger.error(f"Failed to get posts: {str(e)}")
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
            post = self.client.call(GetPost(post_id))
            
            if title is not None:
                post.title = title
            if content is not None:
                post.content = content
            if status is not None:
                post.post_status = status
                
            success = self.client.call(EditPost(post_id, post))
            if success:
                logger.info(f"Post {post_id} updated successfully")
            else:
                logger.warning(f"Post {post_id} update returned false")
            return success
        except Exception as e:
            logger.error(f"Failed to update post {post_id}: {str(e)}")
            raise

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

    def get_post_meta(self, post_id):
        """Get post metadata including meta description"""
        if self.demo_mode:
            logger.info(f"DEMO MODE: Returning mock metadata for post {post_id}")
            return {
                "meta_description": "Ceci est une meta description d'exemple pour le mode démo",
                "_yoast_wpseo_metadesc": "Ceci est une meta description d'exemple pour le mode démo"
            }
            
        try:
            # Try to get meta using custom fields
            post = self.client.call(GetPost(post_id, ['custom_fields']))
            meta = {}
            
            if hasattr(post, 'custom_fields'):
                for field in post.custom_fields:
                    if field['key'] in ['_yoast_wpseo_metadesc', 'meta_description']:
                        meta[field['key']] = field['value']
            
            return meta
        except Exception as e:
            logger.error(f"Failed to get post metadata for {post_id}: {str(e)}")
            raise

    def update_post_meta(self, post_id, meta_description):
        """Update post meta description using WordPress REST API"""
        if self.demo_mode:
            logger.info(f"DEMO MODE: Simulating metadata update for post {post_id}")
            return True
            
        try:
            # Construire l'URL de l'API REST WordPress
            wp_base_url = self.client.url.replace('xmlrpc.php', 'wp-json/wp/v2')
            page_url = f"{wp_base_url}/pages/{post_id}"
            
            # Préparer les données pour la mise à jour
            data = {
                'meta': {
                    '_yoast_wpseo_metadesc': meta_description
                }
            }
            
            # Effectuer la requête PUT pour mettre à jour la page
            response = requests.put(
                page_url,
                json=data,
                auth=(WP_USERNAME, WP_PASSWORD),
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                verify=False
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Metadata updated successfully for page {post_id}")
                
                # Mise à jour supplémentaire via l'API XML-RPC pour s'assurer que les métadonnées sont bien enregistrées
                try:
                    post = self.client.call(GetPost(post_id))
                    if not hasattr(post, 'custom_fields'):
                        post.custom_fields = []
                    
                    # Mettre à jour ou ajouter le champ personnalisé
                    field_updated = False
                    for field in post.custom_fields:
                        if field['key'] == '_yoast_wpseo_metadesc':
                            field['value'] = meta_description
                            field_updated = True
                            break
                    
                    if not field_updated:
                        post.custom_fields.append({
                            'key': '_yoast_wpseo_metadesc',
                            'value': meta_description
                        })
                    
                    self.client.call(EditPost(post_id, post))
                except Exception as e:
                    logger.warning(f"XML-RPC update failed but REST update succeeded: {str(e)}")
                
                return True
            else:
                error_msg = f"Failed to update metadata: {response.status_code} - {response.text}"
                logger.warning(error_msg)
                return False
                
        except Exception as e:
            logger.error(f"Failed to update page metadata for {post_id}: {str(e)}")
            raise

    def get_seo_info(self, post_id=None):
        """Get complete SEO information for a post or the entire site"""
        if self.demo_mode:
            logger.info(f"DEMO MODE: Returning mock SEO data")
            return {
                "site_seo": {
                    "title": "Mon Site WordPress",
                    "description": "Description du site en mode démo",
                    "robots": "index, follow"
                },
                "post_seo": {} if post_id is None else {
                    "id": post_id,
                    "meta_description": "Meta description d'exemple",
                    "title_tag": "Titre SEO d'exemple",
                    "canonical_url": f"https://example.com/?p={post_id}",
                    "robots": "index, follow",
                    "og_title": "Titre Open Graph",
                    "og_description": "Description Open Graph",
                    "twitter_title": "Titre Twitter",
                    "twitter_description": "Description Twitter"
                }
            }
            
        try:
            seo_data = {}
            
            # Get site-wide SEO settings
            wp_base_url = self.client.url.replace('xmlrpc.php', 'wp-json')
            
            # Try to get Yoast SEO site data
            try:
                yoast_site_url = f"{wp_base_url}/yoast/v1/get_head"
                site_response = requests.get(
                    yoast_site_url,
                    auth=(WP_USERNAME, WP_PASSWORD),
                    verify=False
                )
                if site_response.status_code == 200:
                    seo_data["site_seo"] = site_response.json()
            except Exception as e:
                logger.warning(f"Could not fetch Yoast site SEO data: {str(e)}")
                seo_data["site_seo"] = {}
            
            # If post_id is provided, get post-specific SEO data
            if post_id:
                post_seo = {}
                
                # Get standard post meta
                post = self.client.call(GetPost(post_id, ['custom_fields']))
                
                # Extract all SEO-related meta fields
                if hasattr(post, 'custom_fields'):
                    seo_keys = [
                        '_yoast_wpseo_metadesc',
                        '_yoast_wpseo_title',
                        '_yoast_wpseo_canonical',
                        '_yoast_wpseo_meta-robots-noindex',
                        '_yoast_wpseo_meta-robots-nofollow',
                        '_yoast_wpseo_opengraph-title',
                        '_yoast_wpseo_opengraph-description',
                        '_yoast_wpseo_twitter-title',
                        '_yoast_wpseo_twitter-description',
                        '_yoast_wpseo_focuskw',
                        'meta_description',
                        '_meta_title'
                    ]
                    
                    for field in post.custom_fields:
                        if field['key'] in seo_keys:
                            clean_key = field['key'].replace('_yoast_wpseo_', '')
                            post_seo[clean_key] = field['value']
                
                # Try to get Yoast SEO post data
                try:
                    yoast_post_url = f"{wp_base_url}/yoast/v1/get_head?id={post_id}"
                    post_response = requests.get(
                        yoast_post_url,
                        auth=(WP_USERNAME, WP_PASSWORD),
                        verify=False
                    )
                    if post_response.status_code == 200:
                        post_seo.update(post_response.json())
                except Exception as e:
                    logger.warning(f"Could not fetch Yoast post SEO data: {str(e)}")
                
                seo_data["post_seo"] = post_seo
            
            return seo_data
                
        except Exception as e:
            logger.error(f"Failed to get SEO information: {str(e)}")
            raise

    def get_all_pages(self, number=100, page=1, status='any'):
        """Get all WordPress pages with pagination using REST API"""
        if self.demo_mode:
            logger.info(f"DEMO MODE: Returning mock pages data")
            mock_pages = []
            for i in range(1, 6):
                mock_pages.append({
                    "id": i,
                    "title": f"Exemple de page {i}",
                    "content": "<h2>Introduction</h2><p>Page de démonstration</p>",
                    "status": "publish",
                    "date": "2025-01-01 12:00:00"
                })
            return {
                "pages": mock_pages,
                "total": len(mock_pages),
                "page": page,
                "per_page": number
            }
            
        try:
            # Construct the REST API URL for pages
            wp_base_url = self.client.url.replace('xmlrpc.php', 'wp-json/wp/v2')
            pages_url = f"{wp_base_url}/pages"
            
            # Prepare the parameters
            params = {
                'per_page': number,
                'page': page,
                'status': status if status != 'any' else ['publish', 'draft', 'private']
            }
            
            # Prepare the headers with basic auth
            auth = (WP_USERNAME, WP_PASSWORD)
            headers = {
                'Accept': 'application/json'
            }
            
            # Get pages from WordPress REST API
            response = requests.get(
                pages_url,
                params=params,
                headers=headers,
                auth=auth,
                verify=False  # Pour le développement local
            )
            
            if response.status_code == 200:
                pages = response.json()
                total_pages = int(response.headers.get('X-WP-Total', 0))
                total_pages_count = int(response.headers.get('X-WP-TotalPages', 0))
                
                # Convert REST API response to our format using dictionaries
                formatted_pages = []
                for page_data in pages:
                    formatted_page = {
                        "id": page_data['id'],
                        "title": page_data['title']['rendered'],
                        "content": page_data['content']['rendered'],
                        "status": page_data['status'],
                        "date": page_data['date'],
                        "link": page_data.get('link', ''),
                        "modified": page_data.get('modified', ''),
                        "slug": page_data.get('slug', '')
                    }
                    formatted_pages.append(formatted_page)
                
                return {
                    "pages": formatted_pages,
                    "total": total_pages,
                    "page": page,
                    "per_page": number,
                    "total_pages": total_pages_count
                }
            else:
                error_msg = f"Failed to get pages: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Failed to get pages: {str(e)}")
            raise