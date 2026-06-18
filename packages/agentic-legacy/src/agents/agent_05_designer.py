"""
Agent 05 (Designer) - Visual Asset Creation - UI, Diagrams, Infographics
"""

from typing import Dict, List, Any, Optional
import json
from datetime import datetime
import base64
import os

from ..core.base_agent import BaseAgent

class Agent05Designer(BaseAgent):
    """Specialized design agent for visual assets creation"""
    
    def __init__(self, config_path: str = "config/prompts.yaml"):
        super().__init__("agent_05_designer", config_path)
        self.created_assets = {}
        self.design_templates = self._load_design_templates()
        
    def _load_design_templates(self) -> Dict[str, Any]:
        """Load design templates and guidelines"""
        return {
            'ui_components': {
                'button': {'padding': '12px 24px', 'border_radius': '6px', 'font_weight': '600'},
                'card': {'padding': '20px', 'border_radius': '8px', 'box_shadow': '0 2px 4px rgba(0,0,0,0.1)'},
                'form': {'max_width': '400px', 'spacing': '16px'}
            },
            'color_palettes': {
                'professional': ['#2563eb', '#1f2937', '#6b7280', '#f3f4f6'],
                'modern': ['#06b6d4', '#0891b2', '#0e7490', '#164e63'],
                'warm': ['#f59e0b', '#d97706', '#b45309', '#92400e']
            },
            'typography': {
                'headings': {'font_family': 'Inter', 'font_weight': '700'},
                'body': {'font_family': 'Inter', 'font_weight': '400'},
                'code': {'font_family': 'JetBrains Mono', 'font_weight': '400'}
            }
        }
    
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process design creation requests"""
        
        if not self.validate_input(task):
            return self.handle_error(Exception("Invalid task format"), task)
        
        try:
            self.update_status("analyzing", task)
            
            # Analyze design requirements
            design_brief = self._analyze_design_requirements(task)
            
            # Generate concepts
            concepts = self._develop_design_concepts(design_brief)
            
            # Create design assets
            self.update_status("creating")
            assets = self._create_design_assets(concepts, design_brief)
            
            # Generate specifications
            specifications = self._generate_design_specifications(assets, design_brief)
            
            self.update_status("ready")
            
            # Prepare response
            response_content = f"""
🎨 DESIGN BRIEF: {design_brief['summary']}

💡 CONCEPT: {design_brief['design_approach']}

🖼️ DELIVERABLES:
{self._format_deliverables(assets)}

📋 SPECIFICATIONS:
{self._format_specifications(specifications)}

🔄 ITERATIONS: Ready for feedback and revisions

✨ FINAL ASSETS:
{self._format_final_assets(assets)}
            """
            
            # Store design project
            project_id = f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._store_design_project(project_id, task, design_brief, concepts, assets, specifications)
            
            return self.format_response(response_content.strip(), "design_deliverable")
            
        except Exception as e:
            return self.handle_error(e, task)
    
    def _analyze_design_requirements(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze design requirements from the task"""
        request = task.get('request', '')
        context = task.get('context', {})
        
        # Determine design type
        design_type = self._classify_design_type(request)
        
        # Extract design elements
        target_audience = self._identify_target_audience(request, context)
        style_preferences = self._extract_style_preferences(request)
        content_requirements = self._extract_content_requirements(request)
        technical_specs = self._extract_technical_specs(request, context)
        
        brief = {
            'summary': self._create_design_summary(request),
            'design_type': design_type,
            'target_audience': target_audience,
            'style_preferences': style_preferences,
            'content_requirements': content_requirements,
            'technical_specs': technical_specs,
            'design_approach': self._determine_design_approach(design_type, style_preferences),
            'deliverables': self._identify_deliverables(design_type, request)
        }
        
        return brief
    
    def _classify_design_type(self, request: str) -> str:
        """Classify the type of design needed"""
        request_lower = request.lower()
        
        design_types = {
            'ui_design': ['ui', 'interface', 'app design', 'website', 'dashboard'],
            'infographic': ['infographic', 'data visualization', 'chart', 'graph'],
            'diagram': ['diagram', 'flowchart', 'architecture', 'system design'],
            'logo': ['logo', 'branding', 'brand identity'],
            'presentation': ['presentation', 'slides', 'deck'],
            'print_design': ['flyer', 'poster', 'brochure', 'print'],
            'web_design': ['web design', 'landing page', 'website']
        }
        
        for design_type, keywords in design_types.items():
            if any(keyword in request_lower for keyword in keywords):
                return design_type
        
        return 'general_graphic'
    
    def _identify_target_audience(self, request: str, context: Dict[str, Any]) -> str:
        """Identify target audience for the design"""
        request_lower = request.lower()
        
        audiences = {
            'business_professional': ['business', 'corporate', 'professional', 'enterprise'],
            'developer': ['developer', 'technical', 'programmer', 'engineer'],
            'general_public': ['public', 'general', 'everyone', 'users'],
            'students': ['student', 'educational', 'academic'],
            'creative': ['creative', 'artist', 'designer']
        }
        
        for audience, keywords in audiences.items():
            if any(keyword in request_lower for keyword in keywords):
                return audience
        
        return context.get('target_audience', 'general_public')
    
    def _extract_style_preferences(self, request: str) -> Dict[str, Any]:
        """Extract style preferences from request"""
        request_lower = request.lower()
        
        styles = {
            'color_scheme': 'professional',  # default
            'typography': 'modern',
            'layout': 'clean',
            'aesthetic': 'minimalist'
        }
        
        # Color preferences
        if any(word in request_lower for word in ['colorful', 'vibrant', 'bright']):
            styles['color_scheme'] = 'vibrant'
        elif any(word in request_lower for word in ['dark', 'black']):
            styles['color_scheme'] = 'dark'
        elif any(word in request_lower for word in ['warm', 'orange', 'red']):
            styles['color_scheme'] = 'warm'
        
        # Aesthetic preferences
        if any(word in request_lower for word in ['modern', 'contemporary']):
            styles['aesthetic'] = 'modern'
        elif any(word in request_lower for word in ['classic', 'traditional']):
            styles['aesthetic'] = 'classic'
        elif any(word in request_lower for word in ['playful', 'fun']):
            styles['aesthetic'] = 'playful'
        
        return styles
    
    def _extract_content_requirements(self, request: str) -> Dict[str, Any]:
        """Extract content requirements"""
        return {
            'text_content': self._extract_text_content(request),
            'image_requirements': self._extract_image_requirements(request),
            'data_elements': self._extract_data_elements(request),
            'interactive_elements': self._extract_interactive_elements(request)
        }
    
    def _extract_technical_specs(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract technical specifications"""
        specs = {
            'dimensions': self._extract_dimensions(request),
            'format': self._extract_format(request),
            'resolution': self._extract_resolution(request),
            'platform': self._extract_platform(request, context)
        }
        
        return specs
    
    def _develop_design_concepts(self, design_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Develop design concepts based on the brief"""
        design_type = design_brief['design_type']
        
        concepts = []
        
        if design_type == 'ui_design':
            concepts = self._generate_ui_concepts(design_brief)
        elif design_type == 'infographic':
            concepts = self._generate_infographic_concepts(design_brief)
        elif design_type == 'diagram':
            concepts = self._generate_diagram_concepts(design_brief)
        else:
            concepts = self._generate_general_concepts(design_brief)
        
        return concepts
    
    def _generate_ui_concepts(self, design_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate UI design concepts"""
        return [
            {
                'concept_id': 'ui_concept_1',
                'name': 'Clean Dashboard',
                'description': 'Minimalist dashboard with clear navigation and data visualization',
                'layout': 'sidebar_navigation',
                'components': ['header', 'sidebar', 'main_content', 'footer'],
                'color_palette': self.design_templates['color_palettes']['professional']
            },
            {
                'concept_id': 'ui_concept_2', 
                'name': 'Modern Interface',
                'description': 'Contemporary design with card-based layout',
                'layout': 'card_grid',
                'components': ['navigation_bar', 'hero_section', 'content_cards'],
                'color_palette': self.design_templates['color_palettes']['modern']
            }
        ]
    
    def _generate_infographic_concepts(self, design_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate infographic concepts"""
        return [
            {
                'concept_id': 'infographic_1',
                'name': 'Data Story',
                'description': 'Visual narrative with charts and statistics',
                'layout': 'vertical_flow',
                'elements': ['title', 'key_stats', 'charts', 'conclusion']
            }
        ]
    
    def _generate_diagram_concepts(self, design_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate diagram concepts"""
        return [
            {
                'concept_id': 'diagram_1',
                'name': 'System Architecture',
                'description': 'Clear system component relationships',
                'layout': 'hierarchical',
                'elements': ['components', 'connections', 'data_flow']
            }
        ]
    
    def _generate_general_concepts(self, design_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate general design concepts"""
        return [
            {
                'concept_id': 'general_1',
                'name': 'Balanced Layout',
                'description': 'Well-proportioned design with clear hierarchy',
                'layout': 'grid_based',
                'elements': ['header', 'content', 'visual_elements']
            }
        ]
    
    def _create_design_assets(self, concepts: List[Dict[str, Any]], design_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create actual design assets"""
        assets = []
        
        for concept in concepts:
            if design_brief['design_type'] == 'ui_design':
                asset = self._create_ui_asset(concept, design_brief)
            elif design_brief['design_type'] == 'diagram':
                asset = self._create_diagram_asset(concept, design_brief)
            else:
                asset = self._create_general_asset(concept, design_brief)
            
            assets.append(asset)
        
        return assets
    
    def _create_ui_asset(self, concept: Dict[str, Any], design_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Create UI design asset"""
        return {
            'asset_id': f"ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'type': 'ui_design',
            'concept': concept['name'],
            'files': {
                'html': self._generate_html_mockup(concept, design_brief),
                'css': self._generate_css_styles(concept, design_brief),
                'wireframe': 'wireframe.svg (generated)',
                'mockup': 'mockup.png (generated)'
            },
            'components': concept.get('components', []),
            'responsive_breakpoints': ['mobile', 'tablet', 'desktop'],
            'accessibility_features': ['alt_text', 'keyboard_navigation', 'color_contrast']
        }
    
    def _create_diagram_asset(self, concept: Dict[str, Any], design_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Create diagram asset"""
        return {
            'asset_id': f"diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'type': 'diagram',
            'concept': concept['name'],
            'files': {
                'svg': self._generate_svg_diagram(concept, design_brief),
                'png': 'diagram.png (generated)',
                'pdf': 'diagram.pdf (generated)'
            },
            'elements': concept.get('elements', []),
            'format': design_brief['technical_specs']['format']
        }
    
    def _create_general_asset(self, concept: Dict[str, Any], design_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Create general design asset"""
        return {
            'asset_id': f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'type': design_brief['design_type'],
            'concept': concept['name'],
            'files': {
                'design': 'design.svg (generated)',
                'preview': 'preview.png (generated)'
            },
            'specifications': design_brief['technical_specs']
        }
    
    def _generate_html_mockup(self, concept: Dict[str, Any], design_brief: Dict[str, Any]) -> str:
        """Generate HTML mockup code"""
        components = concept.get('components', [])
        
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UI Mockup</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
"""
        
        # Add components based on concept
        if 'header' in components:
            html += """    <header class="main-header">
        <nav class="navigation">
            <div class="logo">Brand</div>
            <ul class="nav-links">
                <li><a href="#">Home</a></li>
                <li><a href="#">About</a></li>
                <li><a href="#">Contact</a></li>
            </ul>
        </nav>
    </header>
"""
        
        if 'sidebar' in components:
            html += """    <aside class="sidebar">
        <ul class="sidebar-menu">
            <li><a href="#">Dashboard</a></li>
            <li><a href="#">Analytics</a></li>
            <li><a href="#">Settings</a></li>
        </ul>
    </aside>
"""
        
        if 'main_content' in components:
            html += """    <main class="main-content">
        <section class="content-section">
            <h1>Welcome to Your Dashboard</h1>
            <div class="card-grid">
                <div class="card">
                    <h3>Statistics</h3>
                    <p>Key metrics and data</p>
                </div>
                <div class="card">
                    <h3>Recent Activity</h3>
                    <p>Latest updates</p>
                </div>
            </div>
        </section>
    </main>
"""
        
        html += """</body>
</html>"""
        
        return html
    
    def _generate_css_styles(self, concept: Dict[str, Any], design_brief: Dict[str, Any]) -> str:
        """Generate CSS styles"""
        color_palette = concept.get('color_palette', self.design_templates['color_palettes']['professional'])
        
        css = f"""/* Generated CSS Styles */
:root {{
    --primary-color: {color_palette[0]};
    --secondary-color: {color_palette[1]};
    --accent-color: {color_palette[2]};
    --background-color: {color_palette[3]};
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: {self.design_templates['typography']['body']['font_family']}, sans-serif;
    background-color: var(--background-color);
    color: var(--secondary-color);
    line-height: 1.6;
}}

.main-header {{
    background-color: var(--primary-color);
    padding: 1rem 2rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}

.navigation {{
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.logo {{
    font-size: 1.5rem;
    font-weight: {self.design_templates['typography']['headings']['font_weight']};
    color: white;
}}

.nav-links {{
    display: flex;
    list-style: none;
    gap: 2rem;
}}

.nav-links a {{
    color: white;
    text-decoration: none;
    transition: opacity 0.3s;
}}

.nav-links a:hover {{
    opacity: 0.8;
}}

.sidebar {{
    width: 250px;
    background-color: white;
    padding: 2rem 1rem;
    box-shadow: 2px 0 4px rgba(0,0,0,0.1);
}}

.main-content {{
    flex: 1;
    padding: 2rem;
}}

.card {{
    background: white;
    padding: {self.design_templates['ui_components']['card']['padding']};
    border-radius: {self.design_templates['ui_components']['card']['border_radius']};
    box-shadow: {self.design_templates['ui_components']['card']['box_shadow']};
    margin-bottom: 1rem;
}}

.card-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
    margin-top: 2rem;
}}

@media (max-width: 768px) {{
    .navigation {{
        flex-direction: column;
        gap: 1rem;
    }}
    
    .sidebar {{
        width: 100%;
    }}
    
    .card-grid {{
        grid-template-columns: 1fr;
    }}
}}
"""
        
        return css
    
    def _generate_svg_diagram(self, concept: Dict[str, Any], design_brief: Dict[str, Any]) -> str:
        """Generate SVG diagram"""
        return f"""<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
    <!-- {concept['name']} Diagram -->
    <defs>
        <style>
            .box {{ fill: #3b82f6; stroke: #1e40af; stroke-width: 2; }}
            .text {{ font-family: Arial, sans-serif; font-size: 14px; fill: white; text-anchor: middle; }}
            .connection {{ stroke: #6b7280; stroke-width: 2; marker-end: url(#arrowhead); }}
        </style>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
        </marker>
    </defs>
    
    <!-- Main components -->
    <rect x="100" y="100" width="120" height="60" class="box" rx="5"/>
    <text x="160" y="135" class="text">Component A</text>
    
    <rect x="300" y="100" width="120" height="60" class="box" rx="5"/>
    <text x="360" y="135" class="text">Component B</text>
    
    <rect x="500" y="100" width="120" height="60" class="box" rx="5"/>
    <text x="560" y="135" class="text">Component C</text>
    
    <!-- Connections -->
    <line x1="220" y1="130" x2="300" y2="130" class="connection"/>
    <line x1="420" y1="130" x2="500" y2="130" class="connection"/>
    
    <!-- Title -->
    <text x="400" y="40" style="font-size: 18px; font-weight: bold; text-anchor: middle; fill: #1f2937;">
        {concept['name']}
    </text>
</svg>"""
    
    def _generate_design_specifications(self, assets: List[Dict[str, Any]], design_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Generate design specifications"""
        return {
            'design_system': {
                'colors': self._get_color_specifications(design_brief),
                'typography': self._get_typography_specifications(),
                'spacing': self._get_spacing_specifications(),
                'components': self._get_component_specifications(assets)
            },
            'implementation_notes': self._get_implementation_notes(assets, design_brief),
            'responsive_guidelines': self._get_responsive_guidelines(),
            'accessibility_requirements': self._get_accessibility_requirements()
        }
    
    def _get_color_specifications(self, design_brief: Dict[str, Any]) -> Dict[str, str]:
        """Get color specifications"""
        style = design_brief['style_preferences']['color_scheme']
        palette = self.design_templates['color_palettes'].get(style, self.design_templates['color_palettes']['professional'])
        
        return {
            'primary': palette[0],
            'secondary': palette[1], 
            'accent': palette[2],
            'background': palette[3]
        }
    
    def _get_typography_specifications(self) -> Dict[str, Any]:
        """Get typography specifications"""
        return self.design_templates['typography']
    
    def _get_spacing_specifications(self) -> Dict[str, str]:
        """Get spacing specifications"""
        return {
            'small': '8px',
            'medium': '16px',
            'large': '24px',
            'xlarge': '32px'
        }
    
    def _get_component_specifications(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get component specifications"""
        return self.design_templates['ui_components']
    
    def _get_implementation_notes(self, assets: List[Dict[str, Any]], design_brief: Dict[str, Any]) -> List[str]:
        """Get implementation notes"""
        notes = [
            "Use semantic HTML for better accessibility",
            "Implement responsive design for all screen sizes",
            "Ensure color contrast meets WCAG 2.1 AA standards",
            "Test with keyboard navigation",
            "Optimize images for web performance"
        ]
        
        if design_brief['design_type'] == 'ui_design':
            notes.extend([
                "Use CSS Grid or Flexbox for layouts",
                "Implement proper focus states for interactive elements",
                "Consider dark mode compatibility"
            ])
        
        return notes
    
    def _get_responsive_guidelines(self) -> Dict[str, str]:
        """Get responsive design guidelines"""
        return {
            'mobile': '320px - 768px',
            'tablet': '768px - 1024px', 
            'desktop': '1024px+',
            'approach': 'Mobile-first responsive design'
        }
    
    def _get_accessibility_requirements(self) -> List[str]:
        """Get accessibility requirements"""
        return [
            "WCAG 2.1 AA compliance",
            "Keyboard navigation support",
            "Screen reader compatibility",
            "Color contrast ratio > 4.5:1",
            "Alt text for all images",
            "Focus indicators for interactive elements"
        ]
    
    # Helper methods for content extraction
    def _extract_text_content(self, request: str) -> List[str]:
        """Extract text content requirements"""
        # Simple text extraction - in production, use NLP
        return ["Main heading", "Body content", "Call to action"]
    
    def _extract_image_requirements(self, request: str) -> List[str]:
        """Extract image requirements"""
        if any(word in request.lower() for word in ['image', 'photo', 'picture']):
            return ["Hero image", "Supporting visuals"]
        return []
    
    def _extract_data_elements(self, request: str) -> List[str]:
        """Extract data visualization elements"""
        if any(word in request.lower() for word in ['chart', 'graph', 'data']):
            return ["Charts", "Statistics", "Metrics"]
        return []
    
    def _extract_interactive_elements(self, request: str) -> List[str]:
        """Extract interactive element requirements"""
        elements = []
        request_lower = request.lower()
        
        if 'button' in request_lower:
            elements.append('buttons')
        if 'form' in request_lower:
            elements.append('forms')
        if 'menu' in request_lower:
            elements.append('navigation')
        
        return elements
    
    def _extract_dimensions(self, request: str) -> str:
        """Extract dimension requirements"""
        # Look for dimension patterns
        import re
        dimension_pattern = r'(\d+)\s*x\s*(\d+)'
        matches = re.findall(dimension_pattern, request)
        
        if matches:
            return f"{matches[0][0]}x{matches[0][1]}"
        
        return "1920x1080"  # Default
    
    def _extract_format(self, request: str) -> str:
        """Extract format requirements"""
        formats = ['svg', 'png', 'jpg', 'pdf', 'html']
        request_lower = request.lower()
        
        for fmt in formats:
            if fmt in request_lower:
                return fmt
        
        return 'png'  # Default
    
    def _extract_resolution(self, request: str) -> str:
        """Extract resolution requirements"""
        if any(word in request.lower() for word in ['high', 'hd', 'retina']):
            return 'high'
        return 'standard'
    
    def _extract_platform(self, request: str, context: Dict[str, Any]) -> str:
        """Extract target platform"""
        platforms = ['web', 'mobile', 'desktop', 'print']
        request_lower = request.lower()
        
        for platform in platforms:
            if platform in request_lower:
                return platform
        
        return context.get('platform', 'web')
    
    def _create_design_summary(self, request: str) -> str:
        """Create design summary"""
        if len(request) <= 100:
            return request
        return request[:100] + "..."
    
    def _determine_design_approach(self, design_type: str, style_preferences: Dict[str, Any]) -> str:
        """Determine design approach"""
        approaches = {
            'ui_design': 'User-centered design with modern interface patterns',
            'infographic': 'Data-driven visual storytelling approach',
            'diagram': 'Clear hierarchical information architecture',
            'logo': 'Brand identity focused on memorability and scalability'
        }
        
        base_approach = approaches.get(design_type, 'Balanced visual design approach')
        aesthetic = style_preferences.get('aesthetic', 'minimalist')
        
        return f"{base_approach} with {aesthetic} aesthetic"
    
    def _identify_deliverables(self, design_type: str, request: str) -> List[str]:
        """Identify design deliverables"""
        deliverables = {
            'ui_design': ['Wireframes', 'High-fidelity mockups', 'Interactive prototype', 'Design system'],
            'infographic': ['Data visualization', 'Print-ready files', 'Web-optimized versions'],
            'diagram': ['Vector diagrams', 'Multiple format exports', 'Documentation'],
            'logo': ['Logo variations', 'Brand guidelines', 'File formats']
        }
        
        return deliverables.get(design_type, ['Design files', 'Documentation'])
    
    def _format_deliverables(self, assets: List[Dict[str, Any]]) -> str:
        """Format deliverables for display"""
        formatted = ""
        
        for asset in assets:
            formatted += f"• {asset['type']}: {asset['concept']}\n"
            
            files = asset.get('files', {})
            for file_type, file_name in files.items():
                formatted += f"  - {file_type}: {file_name}\n"
        
        return formatted
    
    def _format_specifications(self, specifications: Dict[str, Any]) -> str:
        """Format specifications for display"""
        design_system = specifications['design_system']
        
        formatted = "Design System:\n"
        formatted += f"Colors: {', '.join(design_system['colors'].values())}\n"
        formatted += f"Typography: {design_system['typography']['body']['font_family']}\n"
        formatted += f"Spacing: {', '.join(design_system['spacing'].values())}\n\n"
        
        formatted += "Implementation Notes:\n"
        for note in specifications['implementation_notes'][:3]:
            formatted += f"• {note}\n"
        
        return formatted
    
    def _format_final_assets(self, assets: List[Dict[str, Any]]) -> str:
        """Format final assets list"""
        formatted = ""
        
        for asset in assets:
            formatted += f"✅ {asset['concept']} - Ready for implementation\n"
            
            if 'components' in asset:
                formatted += f"   Components: {', '.join(asset['components'])}\n"
        
        return formatted
    
    def _store_design_project(self, project_id: str, task: Dict[str, Any], 
                             design_brief: Dict[str, Any], concepts: List[Dict[str, Any]], 
                             assets: List[Dict[str, Any]], specifications: Dict[str, Any]):
        """Store design project for future reference"""
        project = {
            'project_id': project_id,
            'created_at': datetime.now().isoformat(),
            'original_task': task,
            'design_brief': design_brief,
            'concepts': concepts,
            'assets': assets,
            'specifications': specifications,
            'status': 'completed'
        }
        
        self.created_assets[project_id] = project
        
        # Keep only recent projects
        if len(self.created_assets) > 30:
            oldest_projects = sorted(self.created_assets.keys())[:10]
            for old_project_id in oldest_projects:
                del self.created_assets[old_project_id]
