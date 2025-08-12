""
FastSearch for VRChat MCP

Provides fast, flexible search capabilities for VRChat avatars, parameters,
and assets using efficient in-memory indexing and fuzzy matching.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from rapidfuzz import fuzz, process
from thefuzz import fuzz as thefuzz_fuzz

from ..models import SearchRequest, SearchResult

logger = logging.getLogger(__name__)

class SearchCategory(str, Enum):
    """Categories for searchable items."""
    PARAMETER = "parameter"
    ANIMATION = "animation"
    EXPRESSION = "expression"
    ASSET = "asset"
    NPC = "npc"
    CONVERSATION = "conversation"
    OSC_ENDPOINT = "osc_endpoint"
    DOCUMENTATION = "documentation"

@dataclass
class SearchIndex:
    """In-memory search index for fast lookups."""
    items: Dict[str, Dict[str, Any]]
    index: Dict[str, Set[str]]
    
    def __init__(self):
        self.items = {}
        self.index = {}
    
    def add(self, item_id: str, item: Dict[str, Any], terms: List[str]) -> None:
        """Add an item to the search index."""
        self.items[item_id] = item
        
        for term in terms:
            term_lower = term.lower()
            if term_lower not in self.index:
                self.index[term_lower] = set()
            self.index[term_lower].add(item_id)
    
    def search(
        self,
        query: str,
        category: Optional[SearchCategory] = None,
        limit: int = 10,
        threshold: int = 50
    ) -> List[SearchResult]:
        """Search the index with fuzzy matching."""
        query = query.lower().strip()
        if not query:
            return []
        
        # Exact match in index
        if query in self.index:
            items = [self.items[item_id] for item_id in self.index[query]]
            return self._filter_and_rank(items, query, category, limit, threshold)
        
        # Fuzzy search across all items
        all_items = list(self.items.values())
        return self._filter_and_rank(all_items, query, category, limit, threshold)
    
    def _filter_and_rank(
        self,
        items: List[Dict[str, Any]],
        query: str,
        category: Optional[SearchCategory],
        limit: int,
        threshold: int
    ) -> List[SearchResult]:
        """Filter and rank search results."""
        results = []
        
        for item in items:
            # Filter by category if specified
            if category and item.get('category') != category.value:
                continue
            
            # Calculate match score
            name = item.get('name', '').lower()
            description = item.get('description', '').lower()
            
            # Use rapidfuzz for fast fuzzy matching
            name_score = fuzz.ratio(query, name)
            desc_score = fuzz.ratio(query, description) * 0.5  # Weight description matches less
            
            # TheFuzz for partial ratio (better for substrings)
            partial_name_score = thefuzz_fuzz.partial_ratio(query, name) * 0.8
            
            # Take the best score
            score = max(name_score, desc_score, partial_name_score)
            
            if score >= threshold:
                results.append(SearchResult(
                    id=item['id'],
                    name=item['name'],
                    description=item.get('description'),
                    score=score / 100.0,  # Convert to 0.0-1.0 range
                    type=item.get('category', 'unknown'),
                    metadata=item.get('metadata', {})
                ))
        
        # Sort by score (descending) and limit results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

class FastSearch:
    """
    FastSearch provides efficient search capabilities for VRChat-related data.
    
    Features:
    - Fuzzy string matching for parameters, animations, and assets
    - Real-time indexing of OSC endpoints
    - Built-in documentation search
    - Extensible search categories
    """
    
    def __init__(self):
        self.index = SearchIndex()
        self._load_standard_parameters()
    
    async def search(self, request: SearchRequest) -> List[SearchResult]:
        """
        Perform a search across all indexed items.
        
        Args:
            request: Search request with query and filters
            
        Returns:
            List of search results sorted by relevance
        """
        try:
            # Convert category string to enum if provided
            category = (
                SearchCategory(request.filters['category'])
                if request.filters and 'category' in request.filters
                else None
            )
            
            # Perform the search
            results = self.index.search(
                query=request.query,
                category=category,
                limit=request.limit,
                threshold=50  # Default threshold (0-100)
            )
            
            # Apply offset
            return results[request.offset:request.offset + request.limit]
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            return []
    
    async def index_parameter(self, param_name: str, param_type: str, **metadata) -> None:
        """Index a VRChat avatar parameter."""
        param_id = f"param:{param_name}"
        
        # Generate search terms
        terms = self._generate_terms(param_name)
        terms.extend(metadata.get('aliases', []))
        
        # Add to index
        self.index.add(
            item_id=param_id,
            item={
                'id': param_id,
                'name': param_name,
                'description': f"{param_type} parameter",
                'category': SearchCategory.PARAMETER.value,
                'type': param_type,
                'metadata': metadata
            },
            terms=terms
        )
    
    async def index_osc_endpoint(self, endpoint: str, **metadata) -> None:
        """Index an OSC endpoint."""
        endpoint_id = f"osc:{endpoint}"
        
        self.index.add(
            item_id=endpoint_id,
            item={
                'id': endpoint_id,
                'name': endpoint,
                'description': "OSC endpoint",
                'category': SearchCategory.OSC_ENDPOINT.value,
                'metadata': metadata
            },
            terms=self._generate_terms(endpoint)
        )
    
    async def index_npc(self, npc_id: str, name: str, **metadata) -> None:
        """Index an NPC."""
        npc_id = f"npc:{npc_id}"
        
        self.index.add(
            item_id=npc_id,
            item={
                'id': npc_id,
                'name': name,
                'description': metadata.get('description', 'NPC character'),
                'category': SearchCategory.NPC.value,
                'metadata': metadata
            },
            terms=self._generate_terms(name) + [f"npc:{name}"]
        )
    
    def _load_standard_parameters(self) -> None:
        """Load standard VRChat parameters into the search index."""
        standard_params = [
            ("VRCEmote", "Int", "Current emote (0-15)"),
            ("VRCFaceBlendH", "Float", "Head horizontal movement (-1.0 to 1.0)"),
            ("VRCFaceBlendV", "Float", "Head vertical movement (-1.0 to 1.0)"),
            ("VRCFaceEyesClosed", "Float", "Eyes closed amount (0.0 to 1.0)"),
            ("VRCFaceEyeLeftY", "Float", "Left eye vertical position"),
            ("VRCFaceEyeLeftX", "Float", "Left eye horizontal position"),
            ("VRCFaceEyeRightX", "Float", "Right eye horizontal position"),
            ("VRCFaceBrow", "Float", "Brow movement (0.0 to 1.0)"),
            ("VRCFaceBrowLeft", "Float", "Left brow movement"),
            ("VRCFaceBrowRight", "Float", "Right brow movement"),
            ("VRCFaceLipSqueezeL", "Float", "Left lip squeeze"),
            ("VRCFaceLipSqueezeR", "Float", "Right lip squeeze"),
            ("VRCFaceMouthOpen", "Float", "Mouth open amount (0.0 to 1.0)"),
            ("VRCFaceMouthPucker", "Float", "Mouth pucker amount"),
            ("VRCFaceMouthSmileL", "Float", "Left side smile"),
            ("VRCFaceMouthSmileR", "Float", "Right side smile"),
            ("VRCFaceCheekSquintL", "Float", "Left cheek squint"),
            ("VRCFaceCheekSquintR", "Float", "Right cheek squint"),
            ("VRCFaceNoseSneerL", "Float", "Left nose sneer"),
            ("VRCFaceNoseSneerR", "Float", "Right nose sneer"),
            ("VRCFaceTongueOut", "Float", "Tongue out amount"),
            ("VRCFaceJawOpen", "Float", "Jaw open amount"),
            ("VRCFaceJawForward", "Float", "Jaw forward amount"),
            ("VRCFaceJawLeft", "Float", "Jaw left amount"),
            ("VRCFaceJawRight", "Float", "Jaw right amount"),
            ("VRCFaceJawChew", "Float", "Jaw chewing motion"),
            ("VRCFaceMouthLeft", "Float", "Mouth left"),
            ("VRCFaceMouthRight", "Float", "Mouth right"),
            ("VRCFaceMouthClose", "Float", "Mouth close"),
            ("VRCFaceMouthFunnel", "Float", "Mouth funnel"),
            ("VRCFaceMouthPucker", "Float", "Mouth pucker"),
            ("VRCFaceMouthSmileLeft", "Float", "Mouth smile left"),
            ("VRCFaceMouthSmileRight", "Float", "Mouth smile right"),
            ("VRCFaceMouthDimpleLeft", "Float", "Mouth dimple left"),
            ("VRCFaceMouthDimpleRight", "Float", "Mouth dimple right"),
            ("VRCFaceMouthStretchLeft", "Float", "Mouth stretch left"),
            ("VRCFaceMouthStretchRight", "Float", "Mouth stretch right"),
            ("VRCFaceMouthRollLower", "Float", "Mouth roll lower"),
            ("VRCFaceMouthRollUpper", "Float", "Mouth roll upper"),
            ("VRCFaceMouthShrugLower", "Float", "Mouth shrug lower"),
            ("VRCFaceMouthShrugUpper", "Float", "Mouth shrug upper"),
            ("VRCFaceMouthPressLeft", "Float", "Mouth press left"),
            ("VRCFaceMouthPressRight", "Float", "Mouth press right"),
            ("VRCFaceMouthLowerDownLeft", "Float", "Mouth lower down left"),
            ("VRCFaceMouthLowerDownRight", "Float", "Mouth lower down right"),
            ("VRCFaceMouthUpperUpLeft", "Float", "Mouth upper up left"),
            ("VRCFaceMouthUpperUpRight", "Float", "Mouth upper up right"),
            ("VRCFaceNoseSneerLeft", "Float", "Nose sneer left"),
            ("VRCFaceNoseSneerRight", "Float", "Nose sneer right"),
            ("VRCFaceCheekPuff", "Float", "Cheek puff"),
            ("VRCFaceCheekSquintLeft", "Float", "Cheek squint left"),
            ("VRCFaceCheekSquintRight", "Float", "Cheek squint right"),
            ("VRCFaceEyeLookUpLeft", "Float", "Eye look up left"),
            ("VRCFaceEyeLookUpRight", "Float", "Eye look up right"),
            ("VRCFaceEyeLookDownLeft", "Float", "Eye look down left"),
            ("VRCFaceEyeLookDownRight", "Float", "Eye look down right"),
            ("VRCFaceEyeLookInLeft", "Float", "Eye look in left"),
            ("VRCFaceEyeLookInRight", "Float", "Eye look in right"),
            ("VRCFaceEyeLookOutLeft", "Float", "Eye look out left"),
            ("VRCFaceEyeLookOutRight", "Float", "Eye look out right"),
            ("VRCFaceEyeBlinkLeft", "Float", "Eye blink left"),
            ("VRCFaceEyeBlinkRight", "Float", "Eye blink right"),
            ("VRCFaceEyeSquintLeft", "Float", "Eye squint left"),
            ("VRCFaceEyeSquintRight", "Float", "Eye squint right"),
            ("VRCFaceEyeWideLeft", "Float", "Eye wide left"),
            ("VRCFaceEyeWideRight", "Float", "Eye wide right"),
            ("VRCFaceBrowDownLeft", "Float", "Brow down left"),
            ("VRCFaceBrowDownRight", "Float", "Brow down right"),
            ("VRCFaceBrowInnerUp", "Float", "Brow inner up"),
            ("VRCFaceBrowOuterUpLeft", "Float", "Brow outer up left"),
            ("VRCFaceBrowOuterUpRight", "Float", "Brow outer up right"),
            ("VRCFaceTongueOut", "Float", "Tongue out"),
            ("VRCFaceJawOpen", "Float", "Jaw open"),
            ("VRCFaceJawForward", "Float", "Jaw forward"),
            ("VRCFaceJawLeft", "Float", "Jaw left"),
            ("VRCFaceJawRight", "Float", "Jaw right"),
            ("VRCFaceJawChew", "Float", "Jaw chew"),
            ("VRCFaceMouthClose", "Float", "Mouth close"),
            ("VRCFaceMouthFunnel", "Float", "Mouth funnel"),
            ("VRCFaceMouthPucker", "Float", "Mouth pucker"),
            ("VRCFaceMouthLeft", "Float", "Mouth left"),
            ("VRCFaceMouthRight", "Float", "Mouth right"),
            ("VRCFaceMouthSmileLeft", "Float", "Mouth smile left"),
            ("VRCFaceSmileRight", "Float", "Mouth smile right"),
            ("VRCFaceMouthFrownLeft", "Float", "Mouth frown left"),
            ("VRCFaceMouthFrownRight", "Float", "Mouth frown right"),
            ("VRCFaceMouthDimpleLeft", "Float", "Mouth dimple left"),
            ("VRCFaceMouthDimpleRight", "Float", "Mouth dimple right"),
            ("VRCFaceMouthStretchLeft", "Float", "Mouth stretch left"),
            ("VRCFaceMouthStretchRight", "Float", "Mouth stretch right"),
            ("VRCFaceMouthRollLower", "Float", "Mouth roll lower"),
            ("VRCFaceMouthRollUpper", "Float", "Mouth roll upper"),
            ("VRCFaceMouthShrugLower", "Float", "Mouth shrug lower"),
            ("VRCFaceMouthShrugUpper", "Float", "Mouth shrug upper"),
            ("VRCFaceMouthPressLeft", "Float", "Mouth press left"),
            ("VRCFaceMouthPressRight", "Float", "Mouth press right"),
            ("VRCFaceMouthLowerDownLeft", "Float", "Mouth lower down left"),
            ("VRCFaceMouthLowerDownRight", "Float", "Mouth lower down right"),
            ("VRCFaceMouthUpperUpLeft", "Float", "Mouth upper up left"),
            ("VRCFaceMouthUpperUpRight", "Float", "Mouth upper up right"),
            ("VRCFaceBrowDownLeft", "Float", "Brow down left"),
            ("VRCFaceBrowDownRight", "Float", "Brow down right"),
            ("VRCFaceBrowInnerUp", "Float", "Brow inner up"),
            ("VRCFaceBrowOuterUpLeft", "Float", "Brow outer up left"),
            ("VRCFaceBrowOuterUpRight", "Float", "Brow outer up right"),
            ("VRCFaceCheekPuff", "Float", "Cheek puff"),
            ("VRCFaceCheekSquintLeft", "Float", "Cheek squint left"),
            ("VRCFaceCheekSquintRight", "Float", "Cheek squint right"),
            ("VRCFaceNoseSneerLeft", "Float", "Nose sneer left"),
            ("VRCFaceNoseSneerRight", "Float", "Nose sneer right"),
            ("VRCFaceTongueOut", "Float", "Tongue out"),
            ("VRCFaceJawOpen", "Float", "Jaw open"),
            ("VRCFaceJawForward", "Float", "Jaw forward"),
            ("VRCFaceJawLeft", "Float", "Jaw left"),
            ("VRCFaceJawRight", "Float", "Jaw right"),
            ("VRCFaceJawChew", "Float", "Jaw chew"),
            ("VRCFaceEyeLookUpLeft", "Float", "Eye look up left"),
            ("VRCFaceEyeLookUpRight", "Float", "Eye look up right"),
            ("VRCFaceEyeLookDownLeft", "Float", "Eye look down left"),
            ("VRCFaceEyeLookDownRight", "Float", "Eye look down right"),
            ("VRCFaceEyeLookInLeft", "Float", "Eye look in left"),
            ("VRCFaceEyeLookInRight", "Float", "Eye look in right"),
            ("VRCFaceEyeLookOutLeft", "Float", "Eye look out left"),
            ("VRCFaceEyeLookOutRight", "Float", "Eye look out right"),
            ("VRCFaceEyeBlinkLeft", "Float", "Eye blink left"),
            ("VRCFaceEyeBlinkRight", "Float", "Eye blink right"),
            ("VRCFaceEyeSquintLeft", "Float", "Eye squint left"),
            ("VRCFaceEyeSquintRight", "Float", "Eye squint right"),
            ("VRCFaceEyeWideLeft", "Float", "Eye wide left"),
            ("VRCFaceEyeWideRight", "Float", "Eye wide right"),
            ("VRCFaceCheekSquintLeft", "Float", "Cheek squint left"),
            ("VRCFaceCheekSquintRight", "Float", "Cheek squint right"),
            ("VRCFaceNoseSneerLeft", "Float", "Nose sneer left"),
            ("VRCFaceNoseSneerRight", "Float", "Nose sneer right"),
            ("VRCFaceTongueOut", "Float", "Tongue out"),
            ("VRCFaceJawOpen", "Float", "Jaw open"),
            ("VRCFaceJawForward", "Float", "Jaw forward"),
            ("VRCFaceJawLeft", "Float", "Jaw left"),
            ("VRCFaceJawRight", "Float", "Jaw right"),
            ("VRCFaceJawChew", "Float", "Jaw chew"),
            ("VRCFaceMouthClose", "Float", "Mouth close"),
            ("VRCFaceMouthFunnel", "Float", "Mouth funnel"),
            ("VRCFaceMouthPucker", "Float", "Mouth pucker"),
            ("VRCFaceMouthLeft", "Float", "Mouth left"),
            ("VRCFaceMouthRight", "Float", "Mouth right"),
            ("VRCFaceMouthSmileLeft", "Float", "Mouth smile left"),
            ("VRCFaceSmileRight", "Float", "Mouth smile right"),
            ("VRCFaceMouthFrownLeft", "Float", "Mouth frown left"),
            ("VRCFaceMouthFrownRight", "Float", "Mouth frown right"),
            ("VRCFaceMouthDimpleLeft", "Float", "Mouth dimple left"),
            ("VRCFaceMouthDimpleRight", "Float", "Mouth dimple right"),
            ("VRCFaceMouthStretchLeft", "Float", "Mouth stretch left"),
            ("VRCFaceMouthStretchRight", "Float", "Mouth stretch right"),
            ("VRCFaceMouthRollLower", "Float", "Mouth roll lower"),
            ("VRCFaceMouthRollUpper", "Float", "Mouth roll upper"),
            ("VRCFaceMouthShrugLower", "Float", "Mouth shrug lower"),
            ("VRCFaceMouthShrugUpper", "Float", "Mouth shrug upper"),
            ("VRCFaceMouthPressLeft", "Float", "Mouth press left"),
            ("VRCFaceMouthPressRight", "Float", "Mouth press right"),
            ("VRCFaceMouthLowerDownLeft", "Float", "Mouth lower down left"),
            ("VRCFaceMouthLowerDownRight", "Float", "Mouth lower down right"),
            ("VRCFaceMouthUpperUpLeft", "Float", "Mouth upper up left"),
            ("VRCFaceMouthUpperUpRight", "Float", "Mouth upper up right"),
            ("VRCFaceBrowDownLeft", "Float", "Brow down left"),
            ("VRCFaceBrowDownRight", "Float", "Brow down right"),
            ("VRCFaceBrowInnerUp", "Float", "Brow inner up"),
            ("VRCFaceBrowOuterUpLeft", "Float", "Brow outer up left"),
            ("VRCFaceBrowOuterUpRight", "Float", "Brow outer up right"),
            ("VRCFaceCheekPuff", "Float", "Cheek puff"),
            ("VRCFaceCheekSquintLeft", "Float", "Cheek squint left"),
            ("VRCFaceCheekSquintRight", "Float", "Cheek squint right"),
            ("VRCFaceNoseSneerLeft", "Float", "Nose sneer left"),
            ("VRCFaceNoseSneerRight", "Float", "Nose sneer right"),
            ("VRCFaceTongueOut", "Float", "Tongue out"),
            ("VRCFaceJawOpen", "Float", "Jaw open"),
            ("VRCFaceJawForward", "Float", "Jaw forward"),
            ("VRCFaceJawLeft", "Float", "Jaw left"),
            ("VRCFaceJawRight", "Float", "Jaw right"),
            ("VRCFaceJawChew", "Float", "Jaw chew"),
            ("VRCFaceEyeLookUpLeft", "Float", "Eye look up left"),
            ("VRCFaceEyeLookUpRight", "Float", "Eye look up right"),
            ("VRCFaceEyeLookDownLeft", "Float", "Eye look down left"),
            ("VRCFaceEyeLookDownRight", "Float", "Eye look down right"),
            ("VRCFaceEyeLookInLeft", "Float", "Eye look in left"),
            ("VRCFaceEyeLookInRight", "Float", "Eye look in right"),
            ("VRCFaceEyeLookOutLeft", "Float", "Eye look out left"),
            ("VRCFaceEyeLookOutRight", "Float", "Eye look out right"),
            ("VRCFaceEyeBlinkLeft", "Float", "Eye blink left"),
            ("VRCFaceEyeBlinkRight", "Float", "Eye blink right"),
            ("VRCFaceEyeSquintLeft", "Float", "Eye squint left"),
            ("VRCFaceEyeSquintRight", "Float", "Eye squint right"),
            ("VRCFaceEyeWideLeft", "Float", "Eye wide left"),
            ("VRCFaceEyeWideRight", "Float", "Eye wide right")
        ]
        
        for param_name, param_type, description in standard_params:
            self.index.add(
                item_id=f"std:{param_name}",
                item={
                    'id': f"std:{param_name}",
                    'name': param_name,
                    'description': f"{param_type} - {description}",
                    'category': SearchCategory.PARAMETER.value,
                    'type': param_type,
                    'is_standard': True,
                    'metadata': {
                        'source': 'VRChat Standard Parameters',
                        'documentation': 'https://docs.vrchat.com/docs/osc-avatar-parameters'
                    }
                },
                terms=self._generate_terms(param_name) + [f"type:{param_type}", "standard"]
            )
    
    def _generate_terms(self, text: str) -> List[str]:
        """Generate search terms from a string."""
        if not text:
            return []
        
        # Split camelCase and snake_case
        terms = re.sub('([a-z0-9])([A-Z])', r'\1 \2', text).lower().split()
        
        # Add whole string as a term
        terms.append(text.lower())
        
        # Add partial terms (for autocomplete)
        for i in range(2, len(text)):
            terms.append(text[:i].lower())
        
        return list(set(terms))  # Remove duplicates

# Singleton instance
fast_search = FastSearch()
