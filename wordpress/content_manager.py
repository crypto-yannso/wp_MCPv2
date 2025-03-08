import logging
import os
import re
from bs4 import BeautifulSoup
from .connector import WordPressConnector
from utils.config import RESTRICTED_OPERATIONS

logger = logging.getLogger(__name__)

class WordPressContentManager:
    """
    Class to manage WordPress content, including adding, modifying, and deleting content
    """
    def __init__(self):
        """Initialize the content manager with a WordPress connector"""
        try:
            # Use demo mode if specified in environment
            demo_mode = os.getenv("MCP_DEMO_MODE", "false").lower() == "true"
            self.wp = WordPressConnector(demo_mode=demo_mode)
            logger.info(f"WordPress Content Manager initialized (Demo mode: {self.wp.demo_mode})")
        except Exception as e:
            logger.error(f"Failed to initialize WordPress connector: {str(e)}")
            # If we allow demo mode via environment variable, create a demo connector
            if os.getenv("MCP_ALLOW_DEMO_MODE", "false").lower() == "true":
                self.wp = WordPressConnector(demo_mode=True)
                logger.info("WordPress Content Manager initialized in DEMO mode due to error")
            else:
                # Re-raise the exception
                raise
    
    def extract_sections(self, content):
        """Extract sections from HTML content using BeautifulSoup"""
        soup = BeautifulSoup(content, 'html.parser')
        sections = []
        
        # Get all headings as potential section markers
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for i, heading in enumerate(headings):
            section = {"id": f"section-{i}", "title": heading.get_text(), "content": ""}
            content_elements = []
            
            # Get all elements until the next heading
            current = heading.next_sibling
            while current and current.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if current.name:  # Skip NavigableString objects
                    content_elements.append(str(current))
                current = current.next_sibling
                
            section["content"] = "".join(content_elements)
            sections.append(section)
            
        return sections
    
    def build_content_from_sections(self, sections):
        """Build complete HTML content from sections list"""
        content = ""
        for section in sections:
            # Using h2 as default heading, but could be determined by section level
            content += f"<h2>{section['title']}</h2>\n{section['content']}\n"
        return content
    
    def get_content(self, post_id):
        """Get a post and its parsed sections"""
        post = self.wp.get_post(post_id)
        sections = self.extract_sections(post.content)
        return {
            "id": post_id,
            "title": post.title,
            "content": post.content,
            "sections": sections
        }
    
    def add_content(self, title, content, status='draft'):
        """Add new content to WordPress"""
        post_id = self.wp.create_post(title, content, status)
        return {
            "id": post_id,
            "title": title,
            "status": status,
            "message": f"Content added successfully with ID: {post_id}"
        }
    
    def update_content(self, post_id, title=None, content=None, status=None):
        """Update existing content"""
        success = self.wp.update_post(post_id, title, content, status)
        return {
            "id": post_id,
            "success": success,
            "message": f"Content {'updated successfully' if success else 'update failed'}"
        }
    
    def delete_content(self, post_id, force=False):
        """Delete content if allowed"""
        if "delete_content" in RESTRICTED_OPERATIONS and not force:
            logger.warning(f"Attempted restricted operation: delete_content for post {post_id}")
            return {
                "success": False,
                "message": "Delete operation is restricted. Use force=True to override."
            }
            
        success = self.wp.delete_post(post_id)
        return {
            "success": success,
            "message": f"Content {'deleted successfully' if success else 'deletion failed'}"
        }
    
    def add_section(self, post_id, title, content, position=None):
        """Add a new section to an existing post"""
        post = self.wp.get_post(post_id)
        sections = self.extract_sections(post.content)
        
        new_section = {
            "id": f"section-{len(sections)}",
            "title": title,
            "content": content
        }
        
        if position is not None and 0 <= position <= len(sections):
            sections.insert(position, new_section)
        else:
            sections.append(new_section)
            
        updated_content = self.build_content_from_sections(sections)
        success = self.wp.update_post(post_id, content=updated_content)
        
        return {
            "success": success,
            "message": f"Section {'added successfully' if success else 'add failed'}",
            "sections": sections if success else None
        }
    
    def update_section(self, post_id, section_id, title=None, content=None):
        """Update a specific section in a post"""
        post = self.wp.get_post(post_id)
        sections = self.extract_sections(post.content)
        
        # Find the section by ID
        for section in sections:
            if section["id"] == section_id:
                if title is not None:
                    section["title"] = title
                if content is not None:
                    section["content"] = content
                break
        else:
            return {
                "success": False,
                "message": f"Section {section_id} not found"
            }
            
        updated_content = self.build_content_from_sections(sections)
        success = self.wp.update_post(post_id, content=updated_content)
        
        return {
            "success": success,
            "message": f"Section {section_id} {'updated successfully' if success else 'update failed'}",
            "sections": sections if success else None
        }
    
    def delete_section(self, post_id, section_id, force=False):
        """Delete a specific section if allowed"""
        if "delete_section" in RESTRICTED_OPERATIONS and not force:
            logger.warning(f"Attempted restricted operation: delete_section for section {section_id}")
            return {
                "success": False,
                "message": "Delete operation is restricted. Use force=True to override."
            }
            
        post = self.wp.get_post(post_id)
        sections = self.extract_sections(post.content)
        
        # Find and remove the section by ID
        for i, section in enumerate(sections):
            if section["id"] == section_id:
                del sections[i]
                break
        else:
            return {
                "success": False,
                "message": f"Section {section_id} not found"
            }
            
        updated_content = self.build_content_from_sections(sections)
        success = self.wp.update_post(post_id, content=updated_content)
        
        return {
            "success": success,
            "message": f"Section {section_id} {'deleted successfully' if success else 'delete failed'}",
            "sections": sections if success else None
        }
    
    def reorder_sections(self, post_id, section_order):
        """Reorder sections in a post"""
        post = self.wp.get_post(post_id)
        current_sections = self.extract_sections(post.content)
        
        # Create a map of section IDs to their objects
        section_map = {section["id"]: section for section in current_sections}
        
        # Create new ordered list based on provided IDs
        new_sections = []
        for section_id in section_order:
            if section_id in section_map:
                new_sections.append(section_map[section_id])
            else:
                return {
                    "success": False,
                    "message": f"Section {section_id} not found"
                }
                
        updated_content = self.build_content_from_sections(new_sections)
        success = self.wp.update_post(post_id, content=updated_content)
        
        return {
            "success": success,
            "message": f"Sections {'reordered successfully' if success else 'reorder failed'}",
            "sections": new_sections if success else None
        }