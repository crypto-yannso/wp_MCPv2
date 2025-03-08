import logging
import os
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import GetPost, NewPost, EditPost, GetPosts, DeletePost
from wordpress_xmlrpc.methods.users import GetUserInfo
from wordpress_xmlrpc.methods.taxonomies import GetTerms
from wordpress_xmlrpc.methods import media
import base64
import requests
from utils.config import WP_URL, WP_USERNAME, WP_PASSWORD

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