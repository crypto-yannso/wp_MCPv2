from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from api.auth import oauth2_scheme, get_current_user
from wordpress.content_manager import WordPressContentManager
from wordpress.connector import WordPressConnector
from api.events import send_sse_event
import asyncio
import logging
import time

router = APIRouter(prefix="/wordpress", tags=["wordpress"])
wp_manager = WordPressContentManager()
logger = logging.getLogger(__name__)

# Types d'événements WordPress
WP_EVENT_PAGE_CREATED = "wp_page_created"
WP_EVENT_PAGE_UPDATED = "wp_page_updated"
WP_EVENT_SECTION_ADDED = "wp_section_added"
WP_EVENT_SECTION_UPDATED = "wp_section_updated"
WP_EVENT_SECTION_DELETED = "wp_section_deleted"

async def send_wordpress_event(client_id: str, event_type: str, data: dict):
    """Envoyer un événement WordPress via SSE"""
    try:
        await send_sse_event(client_id, event_type, {
            "timestamp": time.time(),
            "type": event_type,
            **data
        })
    except Exception as e:
        logger.error(f"Error sending WordPress event: {str(e)}")

def get_wordpress_client() -> WordPressConnector:
    """
    Dépendance FastAPI pour obtenir une instance du client WordPress.
    Cette fonction sera utilisée par FastAPI pour l'injection de dépendances.
    """
    try:
        return WordPressConnector()
    except Exception as e:
        logger.error(f"Failed to initialize WordPress client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Could not initialize WordPress connection"
        )

class ContentCreate(BaseModel):
    title: str
    content: str
    status: str = "draft"

class ContentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None

class SectionCreate(BaseModel):
    title: str
    content: str
    position: Optional[int] = None

class SectionUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class PageList(BaseModel):
    limit: Optional[int] = 10
    offset: Optional[int] = 0
    status: Optional[str] = "publish"

class PageDetails(BaseModel):
    id: int
    title: str
    status: str
    content: Optional[str] = None
    url: Optional[str] = None
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    author: Optional[str] = None
    template: Optional[str] = None
    is_elementor: Optional[bool] = None
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None

class ElementorDetails(BaseModel):
    id: int
    title: str
    status: str
    url: Optional[str] = None
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    author: Optional[str] = None
    content: Optional[str] = None
    elementor_data: Optional[Dict[str, Any]] = None
    elementor_settings: Optional[Dict[str, Any]] = None
    template: Optional[str] = None
    featured_image: Optional[str] = None

class ElementorSectionUpdate(BaseModel):
    section_id: str
    title: Optional[str] = None
    content: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    columns: Optional[List[Dict[str, Any]]] = None

@router.post("/pages", response_model=Dict[str, Any])
async def create_page(
    content: ContentCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    client_id: str = Query(None)
):
    """Créer une nouvelle page WordPress avec notifications SSE"""
    try:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_PAGE_CREATED, {
                "status": "starting",
                "message": "Création de la page en cours..."
            })

        result = await wp_manager.add_content(
            title=content.title,
            content=content.content,
            status=content.status
        )

        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_PAGE_CREATED, {
                "status": "completed",
                "message": "Page créée avec succès",
                "data": result
            })

        return result
    except Exception as e:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_PAGE_CREATED, {
                "status": "error",
                "message": str(e)
            })
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/pages/{post_id}")
async def get_page(post_id: int, token: str = Depends(oauth2_scheme)):
    """Récupérer une page WordPress par son ID"""
    try:
        return await wp_manager.get_content(post_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/pages/{post_id}")
async def update_page(
    post_id: int,
    content: ContentUpdate,
    client_id: str = Query(None),
    token: str = Depends(oauth2_scheme)
):
    """Mettre à jour partiellement une page WordPress avec notifications SSE"""
    try:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_PAGE_UPDATED, {
                "status": "starting",
                "message": f"Mise à jour de la page {post_id}...",
                "post_id": post_id
            })

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            wp_manager.update_content,
            post_id,
            content.title,
            content.content,
            content.status
        )

        if not result:
            raise HTTPException(status_code=404, detail="Page not found")

        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_PAGE_UPDATED, {
                "status": "completed",
                "message": "Page mise à jour avec succès",
                "data": result
            })

        return result
    except Exception as e:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_PAGE_UPDATED, {
                "status": "error",
                "message": str(e)
            })
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/pages/{post_id}")
async def delete_page(post_id: int, token: str = Depends(oauth2_scheme)):
    """Supprimer une page WordPress"""
    try:
        return await wp_manager.delete_content(post_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/pages/{post_id}/sections")
async def add_section(
    post_id: int,
    section: SectionCreate,
    client_id: str = Query(None),
    token: str = Depends(oauth2_scheme)
):
    """Ajouter une section à une page WordPress avec notifications SSE"""
    try:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_SECTION_ADDED, {
                "status": "starting",
                "message": "Ajout d'une nouvelle section...",
                "post_id": post_id
            })

        result = await wp_manager.add_section(
            post_id=post_id,
            title=section.title,
            content=section.content,
            position=section.position
        )

        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_SECTION_ADDED, {
                "status": "completed",
                "message": "Section ajoutée avec succès",
                "data": result
            })

        return result
    except Exception as e:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_SECTION_ADDED, {
                "status": "error",
                "message": str(e)
            })
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/pages/{post_id}/sections/{section_id}")
async def update_section(
    post_id: int,
    section_id: str,
    section: SectionUpdate,
    client_id: str = Query(None),
    token: str = Depends(oauth2_scheme)
):
    """Mettre à jour une section avec notifications en temps réel"""
    try:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_SECTION_UPDATED, {
                "status": "starting",
                "message": f"Mise à jour de la section {section_id}...",
                "post_id": post_id,
                "section_id": section_id
            })

        result = await wp_manager.update_section(
            post_id=post_id,
            section_id=section_id,
            title=section.title,
            content=section.content
        )

        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_SECTION_UPDATED, {
                "status": "completed",
                "message": "Section mise à jour avec succès",
                "data": result
            })

        return result
    except Exception as e:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_SECTION_UPDATED, {
                "status": "error",
                "message": str(e)
            })
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/pages/{post_id}/sections/{section_id}")
async def delete_section(
    post_id: int,
    section_id: str,
    client_id: str = Query(None),
    token: str = Depends(oauth2_scheme)
):
    """Supprimer une section avec notifications en temps réel"""
    try:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_SECTION_DELETED, {
                "status": "starting",
                "message": f"Suppression de la section {section_id}...",
                "post_id": post_id,
                "section_id": section_id
            })

        result = await wp_manager.delete_section(post_id, section_id)

        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_SECTION_DELETED, {
                "status": "completed",
                "message": "Section supprimée avec succès",
                "data": result
            })

        return result
    except Exception as e:
        if client_id:
            await send_wordpress_event(client_id, WP_EVENT_SECTION_DELETED, {
                "status": "error",
                "message": str(e)
            })
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/pages/{post_id}/sections/reorder")
async def reorder_sections(
    post_id: int,
    section_order: List[str],
    client_id: str = Query(None),
    token: str = Depends(oauth2_scheme)
):
    """Réorganiser les sections avec notifications en temps réel"""
    try:
        if client_id:
            await send_wordpress_event(client_id, "wp_sections_reordered", {
                "status": "starting",
                "message": "Réorganisation des sections...",
                "post_id": post_id
            })

        result = await wp_manager.reorder_sections(post_id, section_order)

        if client_id:
            await send_wordpress_event(client_id, "wp_sections_reordered", {
                "status": "completed",
                "message": "Sections réorganisées avec succès",
                "data": result
            })

        return result
    except Exception as e:
        if client_id:
            await send_wordpress_event(client_id, "wp_sections_reordered", {
                "status": "error",
                "message": str(e)
            })
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/pages", response_model=List[PageDetails])
async def list_pages(
    limit: Optional[int] = Query(default=10, ge=1, le=100),
    offset: Optional[int] = Query(default=0, ge=0),
    status: Optional[str] = Query(default="publish", regex="^(publish|draft|private|pending|future|trash)$"),
    detailed: bool = Query(default=False, description="Inclure les détails complets des pages"),
    token: str = Depends(oauth2_scheme),
    wp: WordPressConnector = Depends(get_wordpress_client)
):
    """Récupérer la liste des pages WordPress avec leurs détails"""
    try:
        # Préparer la requête
        query = {
            'post_type': 'page',
            'number': limit,
            'offset': offset,
            'post_status': status
        }
        
        # Récupérer les pages
        pages = wp.get_posts(query)
        
        # Formater les résultats avec plus de détails
        formatted_pages = []
        for page in pages:
            # Conversion des dates en chaînes ISO
            date_created = getattr(page, 'date', None)
            if hasattr(date_created, 'isoformat'):
                date_created = date_created.isoformat()
                
            date_modified = getattr(page, 'modified', None)
            if hasattr(date_modified, 'isoformat'):
                date_modified = date_modified.isoformat()
                
            # Gestion de l'image mise en avant
            featured_image = None
            if hasattr(page, 'thumbnail') and page.thumbnail:
                if isinstance(page.thumbnail, list):
                    featured_image = page.thumbnail[0] if page.thumbnail else None
                else:
                    featured_image = str(page.thumbnail)
            
            page_data = {
                "id": page.id,
                "title": page.title,
                "status": page.post_status,
                "url": getattr(page, 'link', None),
                "date_created": date_created,
                "date_modified": date_modified,
                "author": str(getattr(page, 'author', None)),
                "excerpt": getattr(page, 'excerpt', None),
                "featured_image": featured_image
            }
            
            # Ajouter les détails supplémentaires si demandé
            if detailed:
                page_data.update({
                    "content": page.content,
                    "template": getattr(page, 'template', None),
                    "is_elementor": hasattr(page, 'custom_fields') and '_elementor_edit_mode' in page.custom_fields
                })
            else:
                # Ajouter un court extrait du contenu
                if hasattr(page, 'content'):
                    content = page.content[:200] + '...' if len(page.content) > 200 else page.content
                    page_data["excerpt"] = content
            
            formatted_pages.append(page_data)
            
        return formatted_pages
        
    except Exception as e:
        logger.error(f"Failed to get pages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/elementor-pages", response_model=List[ElementorDetails])
async def get_elementor_pages(
    current_user: dict = Depends(get_current_user),
    wp: WordPressConnector = Depends(get_wordpress_client),
    detailed: bool = Query(default=False, description="Inclure les données Elementor complètes")
):
    """
    Récupère la liste des pages créées avec Elementor avec leurs détails
    """
    try:
        # Récupérer les pages Elementor
        query = {
            'post_type': 'page',
            'meta_key': '_elementor_edit_mode',
            'meta_value': 'builder',
            'number': 100  # Limite maximale, ajustez selon vos besoins
        }
        
        pages = wp.get_posts(query)
        formatted_pages = []
        
        for page in pages:
            # Conversion des dates en chaînes ISO
            date_created = getattr(page, 'date', None)
            if hasattr(date_created, 'isoformat'):
                date_created = date_created.isoformat()
                
            date_modified = getattr(page, 'modified', None)
            if hasattr(date_modified, 'isoformat'):
                date_modified = date_modified.isoformat()
            
            # Gestion de l'image mise en avant
            featured_image = None
            if hasattr(page, 'thumbnail') and page.thumbnail:
                if isinstance(page.thumbnail, list):
                    featured_image = page.thumbnail[0] if page.thumbnail else None
                else:
                    featured_image = str(page.thumbnail)
            
            # Données de base
            page_data = {
                "id": page.id,
                "title": page.title,
                "status": page.post_status,
                "url": getattr(page, 'link', None),
                "date_created": date_created,
                "date_modified": date_modified,
                "author": str(getattr(page, 'author', None)),
                "featured_image": featured_image,
                "template": getattr(page, 'template', None)
            }
            
            # Ajouter les détails Elementor si demandé
            if detailed:
                elementor_data = {}
                elementor_settings = {}
                
                if hasattr(page, 'custom_fields'):
                    custom_fields = page.custom_fields
                    if isinstance(custom_fields, dict):
                        elementor_data = custom_fields.get('_elementor_data', {})
                        elementor_settings = custom_fields.get('_elementor_page_settings', {})
                    else:
                        # Si custom_fields est une liste de tuples (clé, valeur)
                        for field in custom_fields:
                            if isinstance(field, (list, tuple)) and len(field) == 2:
                                key, value = field
                                if key == '_elementor_data':
                                    elementor_data = value
                                elif key == '_elementor_page_settings':
                                    elementor_settings = value
                
                page_data.update({
                    "content": page.content,
                    "elementor_data": elementor_data,
                    "elementor_settings": elementor_settings
                })
            else:
                # Ajouter un court extrait du contenu
                if hasattr(page, 'content'):
                    content = page.content[:200] + '...' if len(page.content) > 200 else page.content
                    page_data["content"] = content
            
            formatted_pages.append(page_data)
        
        return formatted_pages
        
    except Exception as e:
        logger.error(f"Error getting Elementor pages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Elementor pages: {str(e)}"
        )

@router.patch("/elementor-pages/{page_id}/sections/{section_id}", response_model=Dict[str, Any])
async def update_elementor_section(
    page_id: int,
    section_id: str,
    section_data: ElementorSectionUpdate,
    current_user: dict = Depends(get_current_user),
    wp: WordPressConnector = Depends(get_wordpress_client)
):
    """
    Modifier une section spécifique d'une page Elementor sans affecter le reste
    """
    try:
        # Récupérer la page
        page = wp.get_post(page_id)
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")
            
        # Vérifier que c'est une page Elementor
        if not hasattr(page, 'custom_fields') or '_elementor_data' not in page.custom_fields:
            raise HTTPException(status_code=400, detail="This is not an Elementor page")
            
        # Récupérer les données Elementor
        elementor_data = page.custom_fields.get('_elementor_data', '[]')
        if isinstance(elementor_data, str):
            import json
            try:
                elementor_data = json.loads(elementor_data)
            except json.JSONDecodeError:
                elementor_data = []
                
        # Trouver et mettre à jour la section
        section_found = False
        for section in elementor_data:
            if section.get('id') == section_id:
                section_found = True
                # Mettre à jour les champs fournis
                if section_data.title is not None:
                    section['settings']['title'] = section_data.title
                if section_data.content is not None:
                    section['settings']['content'] = section_data.content
                if section_data.settings is not None:
                    section['settings'].update(section_data.settings)
                if section_data.columns is not None:
                    section['elements'] = section_data.columns
                break
                
        if not section_found:
            raise HTTPException(status_code=404, detail="Section not found in this page")
            
        # Mettre à jour la page avec les nouvelles données
        page.custom_fields['_elementor_data'] = json.dumps(elementor_data)
        success = wp.update_post(
            post_id=page_id,
            content=page.content,  # Garder le contenu existant
            title=page.title      # Garder le titre existant
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update the page")
            
        return {
            "message": "Section updated successfully",
            "page_id": page_id,
            "section_id": section_id,
            "updated_data": section_data.dict(exclude_unset=True)
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating Elementor section: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update Elementor section: {str(e)}"
        ) 