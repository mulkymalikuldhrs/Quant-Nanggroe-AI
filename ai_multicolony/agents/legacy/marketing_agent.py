"""
📈 Marketing Agent - Automated Promotion and Outreach System
Advanced AI agent for comprehensive marketing automation and brand promotion

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import logging
import hashlib
import requests
import time
import random
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
import threading
import sqlite3
from collections import defaultdict, Counter
import base64
import io

@dataclass
class Campaign:
    """Marketing campaign data structure"""
    campaign_id: str
    name: str
    campaign_type: str  # social_media, email, content, influencer, seo, ppc
    status: str  # draft, active, paused, completed, cancelled
    target_audience: Dict[str, Any]
    platforms: List[str]
    content: Dict[str, Any]
    schedule: Dict[str, Any]
    budget: float
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    metrics: Dict[str, Any] = None

@dataclass
class MarketingContent:
    """Marketing content data structure"""
    content_id: str
    content_type: str  # post, article, video, image, story, ad
    title: str
    content: str
    platform: str
    campaign_id: Optional[str]
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    engagement_metrics: Dict[str, Any] = None
    created_at: datetime = None

@dataclass
class InfluencerProfile:
    """Influencer profile data structure"""
    influencer_id: str
    name: str
    platform: str
    follower_count: int
    engagement_rate: float
    niche: List[str]
    contact_info: Dict[str, Any]
    collaboration_history: List[Dict[str, Any]] = None
    rates: Dict[str, float] = None

class MarketingAgent:
    """
    Marketing Agent: Comprehensive automated marketing and promotion
    
    Capabilities:
    - 📱 Social media automation
    - ✍️ Content creation and scheduling
    - 🎯 Targeted advertising campaigns
    - 📧 Email marketing automation
    - 🤝 Influencer outreach and management
    - 📊 SEO optimization and monitoring
    - 📈 Analytics and performance tracking
    - 🌐 Multi-platform management
    - 🤖 AI-powered content generation
    - 💰 ROI optimization and budget management
    """
    
    def __init__(self):
        self.agent_id = "marketing_agent"
        self.name = "Marketing Agent"
        self.status = "initializing"
        self.version = "1.0.0"
        self.start_time = datetime.now()
        
        # Core capabilities
        self.capabilities = [
            "social_media_automation",
            "content_creation",
            "targeted_advertising",
            "email_marketing",
            "influencer_outreach",
            "seo_optimization",
            "analytics_tracking",
            "multi_platform_management",
            "ai_content_generation",
            "roi_optimization"
        ]
        
        # Marketing data
        self.campaigns = {}
        self.marketing_content = {}
        self.influencers = {}
        self.scheduled_posts = {}
        
        # Platform integrations
        self.platforms = {
            "social_media": {
                "twitter": {"api_key": None, "active": False},
                "instagram": {"api_key": None, "active": False},
                "facebook": {"api_key": None, "active": False},
                "linkedin": {"api_key": None, "active": False},
                "tiktok": {"api_key": None, "active": False},
                "youtube": {"api_key": None, "active": False}
            },
            "email": {
                "mailchimp": {"api_key": None, "active": False},
                "sendgrid": {"api_key": None, "active": False},
                "constant_contact": {"api_key": None, "active": False}
            },
            "advertising": {
                "google_ads": {"api_key": None, "active": False},
                "facebook_ads": {"api_key": None, "active": False},
                "linkedin_ads": {"api_key": None, "active": False}
            },
            "analytics": {
                "google_analytics": {"api_key": None, "active": False},
                "hotjar": {"api_key": None, "active": False},
                "mixpanel": {"api_key": None, "active": False}
            }
        }
        
        # Marketing configuration
        self.config = {
            "auto_posting": True,
            "content_approval_required": False,
            "max_posts_per_day": {
                "twitter": 5,
                "instagram": 2,
                "facebook": 3,
                "linkedin": 2
            },
            "optimal_posting_times": {
                "twitter": ["09:00", "15:00", "18:00"],
                "instagram": ["11:00", "14:00", "17:00"],
                "facebook": ["13:00", "15:00", "19:00"],
                "linkedin": ["08:00", "12:00", "17:00"]
            },
            "hashtag_strategies": {
                "ai": ["#AI", "#MachineLearning", "#TechInnovation", "#Automation"],
                "development": ["#Coding", "#Programming", "#SoftwareDev", "#TechStack"],
                "indonesia": ["#Indonesia", "#TechIndonesia", "#StartupIndonesia"],
                "business": ["#Business", "#Entrepreneurship", "#Innovation", "#Growth"]
            },
            "brand_voice": {
                "tone": "professional_friendly",
                "style": "informative_engaging",
                "persona": "AI_expert_from_indonesia"
            }
        }
        
        # Marketing metrics
        self.metrics = {
            "campaigns_created": 0,
            "content_pieces_created": 0,
            "posts_published": 0,
            "emails_sent": 0,
            "influencers_contacted": 0,
            "total_reach": 0,
            "total_engagement": 0,
            "conversion_rate": 0.0,
            "roi": 0.0
        }
        
        # Brand information
        self.brand_info = {
            "name": "Dhaher AI Ecosystem",
            "tagline": "Autonomous Multi-Agent Intelligence System",
            "description": "Advanced AI agent ecosystem for automation, development, and innovation",
            "founder": "Mulky Malikul Dhaher",
            "location": "Indonesia",
            "website": "https://dhaher.ai",
            "logo": None,
            "colors": ["#00A8E8", "#007EA7", "#003459"],
            "keywords": ["AI", "Automation", "Indonesia", "Innovation", "Technology"],
            "unique_selling_points": [
                "First Indonesian-native AI agent ecosystem",
                "Mobile-first architecture",
                "Ethical AI with local cultural understanding",
                "Open source and community-driven"
            ]
        }
        
        # Content templates
        self.content_templates = {
            "introduction": [
                "🇮🇩 Introducing Dhaher AI Ecosystem - the first Indonesian-native AI agent platform! Built with ❤️ by {founder} to revolutionize automation and AI in Indonesia. {hashtags}",
                "🤖 Meet the future of AI in Indonesia! Dhaher AI Ecosystem brings autonomous intelligence to your fingertips. Created by {founder} for the Indonesian tech community. {hashtags}",
                "🚀 Breaking: New AI ecosystem launches in Indonesia! Dhaher AI features multi-agent automation, mobile-first design, and cultural understanding. By {founder}. {hashtags}"
            ],
            "feature_highlight": [
                "🔥 Feature Spotlight: {feature_name} - {feature_description}. This is what makes Dhaher AI special! {hashtags}",
                "💡 Did you know? Dhaher AI's {feature_name} can {capability}. Perfect for Indonesian businesses and developers! {hashtags}",
                "✨ New Feature Alert: {feature_name} is now live! {feature_description} {hashtags}"
            ],
            "educational": [
                "📚 AI Education: {topic} - {explanation}. Learn how Dhaher AI implements this for Indonesian users. {hashtags}",
                "🧠 Tech Tip: {tip_title} - {tip_content}. This is how we build better AI for Indonesia. {hashtags}",
                "🎓 AI Masterclass: Understanding {concept} in the context of Indonesian technology landscape. {hashtags}"
            ],
            "community": [
                "🤝 Community Spotlight: Meet {community_member} who's using Dhaher AI to {achievement}. Indonesia's AI community is growing! {hashtags}",
                "🌟 Success Story: {success_description} - another win for Indonesian AI innovation! {hashtags}",
                "👥 Join the Indonesian AI revolution! Share your Dhaher AI projects and let's build the future together. {hashtags}"
            ]
        }
        
        # Initialize logging
        self.setup_logging()
        
        # Initialize marketing infrastructure
        self.initialize_marketing_infrastructure()
        
        # Load existing data
        self.load_marketing_data()
        
        self.logger.info("Marketing Agent initialized successfully")
        self.status = "ready"
    
    def setup_logging(self):
        """Setup logging for Marketing Agent"""
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "marketing.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("MarketingAgent")
    
    def initialize_marketing_infrastructure(self):
        """Initialize marketing infrastructure"""
        # Create marketing directories
        marketing_dirs = [
            "data/marketing",
            "data/marketing/campaigns",
            "data/marketing/content",
            "data/marketing/analytics",
            "data/marketing/influencers",
            "data/marketing/templates",
            "data/marketing/assets"
        ]
        
        for directory in marketing_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.initialize_marketing_database()
    
    def initialize_marketing_database(self):
        """Initialize SQLite database for marketing data"""
        db_dir = Path("data/marketing")
        self.db_path = db_dir / "marketing.db"
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    campaign_type TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    target_audience TEXT,
                    platforms TEXT,
                    content TEXT,
                    schedule TEXT,
                    budget REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    metrics TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS marketing_content (
                    content_id TEXT PRIMARY KEY,
                    content_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    platform TEXT,
                    campaign_id TEXT,
                    scheduled_at TIMESTAMP,
                    published_at TIMESTAMP,
                    engagement_metrics TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (campaign_id) REFERENCES campaigns (campaign_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS influencers (
                    influencer_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    follower_count INTEGER DEFAULT 0,
                    engagement_rate REAL DEFAULT 0.0,
                    niche TEXT,
                    contact_info TEXT,
                    collaboration_history TEXT,
                    rates TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS marketing_metrics (
                    metric_id TEXT PRIMARY KEY,
                    metric_type TEXT NOT NULL,
                    metric_value REAL,
                    campaign_id TEXT,
                    content_id TEXT,
                    platform TEXT,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    schedule_id TEXT PRIMARY KEY,
                    content_id TEXT,
                    platform TEXT,
                    scheduled_at TIMESTAMP,
                    status TEXT DEFAULT 'scheduled',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (content_id) REFERENCES marketing_content (content_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("Marketing database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize marketing database: {e}")
    
    def load_marketing_data(self):
        """Load existing marketing data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load campaigns
            cursor.execute('SELECT * FROM campaigns')
            for row in cursor.fetchall():
                campaign = Campaign(
                    campaign_id=row[0],
                    name=row[1],
                    campaign_type=row[2],
                    status=row[3],
                    target_audience=json.loads(row[4]) if row[4] else {},
                    platforms=json.loads(row[5]) if row[5] else [],
                    content=json.loads(row[6]) if row[6] else {},
                    schedule=json.loads(row[7]) if row[7] else {},
                    budget=row[8] or 0.0,
                    created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
                    started_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    ended_at=datetime.fromisoformat(row[11]) if row[11] else None,
                    metrics=json.loads(row[12]) if row[12] else {}
                )
                self.campaigns[row[0]] = campaign
            
            # Load marketing content
            cursor.execute('SELECT * FROM marketing_content')
            for row in cursor.fetchall():
                content = MarketingContent(
                    content_id=row[0],
                    content_type=row[1],
                    title=row[2],
                    content=row[3],
                    platform=row[4],
                    campaign_id=row[5],
                    scheduled_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    published_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    engagement_metrics=json.loads(row[8]) if row[8] else {},
                    created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now()
                )
                self.marketing_content[row[0]] = content
            
            conn.close()
            
            self.logger.info(f"Loaded {len(self.campaigns)} campaigns and {len(self.marketing_content)} content pieces")
            
        except Exception as e:
            self.logger.error(f"Failed to load marketing data: {e}")
    
    async def create_campaign(self, name: str, campaign_type: str, target_audience: Dict[str, Any],
                            platforms: List[str], budget: float = 0.0, 
                            schedule: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new marketing campaign"""
        self.logger.info(f"Creating new marketing campaign: {name}")
        
        try:
            campaign_id = hashlib.md5(f"{name}_{campaign_type}_{datetime.now()}".encode()).hexdigest()[:12]
            
            campaign = Campaign(
                campaign_id=campaign_id,
                name=name,
                campaign_type=campaign_type,
                status="draft",
                target_audience=target_audience,
                platforms=platforms,
                content={},
                schedule=schedule or {},
                budget=budget,
                created_at=datetime.now(),
                metrics={}
            )
            
            self.campaigns[campaign_id] = campaign
            
            # Save to database
            await self._save_campaign_to_database(campaign)
            
            # Auto-generate initial content if it's a brand awareness campaign
            if campaign_type == "brand_awareness":
                await self._generate_brand_awareness_content(campaign_id)
            
            self.metrics["campaigns_created"] += 1
            
            self.logger.info(f"Campaign created successfully: {campaign_id}")
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "campaign_name": name,
                "platforms": platforms,
                "message": "Marketing campaign created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create campaign: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_content(self, content_type: str, platform: str, topic: str = None,
                             campaign_id: str = None, template_type: str = None) -> Dict[str, Any]:
        """Generate marketing content using AI"""
        self.logger.info(f"Generating {content_type} content for {platform}")
        
        try:
            content_id = hashlib.md5(f"{content_type}_{platform}_{datetime.now()}".encode()).hexdigest()[:12]
            
            # Generate content based on type and platform
            generated_content = await self._generate_ai_content(content_type, platform, topic, template_type)
            
            # Create content object
            content = MarketingContent(
                content_id=content_id,
                content_type=content_type,
                title=generated_content.get("title", ""),
                content=generated_content.get("content", ""),
                platform=platform,
                campaign_id=campaign_id,
                created_at=datetime.now(),
                engagement_metrics={}
            )
            
            self.marketing_content[content_id] = content
            
            # Save to database
            await self._save_content_to_database(content)
            
            self.metrics["content_pieces_created"] += 1
            
            self.logger.info(f"Content generated successfully: {content_id}")
            
            return {
                "success": True,
                "content_id": content_id,
                "content": generated_content,
                "platform": platform,
                "message": "Marketing content generated successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate content: {e}")
            return {"success": False, "error": str(e)}
    
    async def schedule_post(self, content_id: str, platform: str, scheduled_time: datetime) -> Dict[str, Any]:
        """Schedule a post for future publication"""
        self.logger.info(f"Scheduling post {content_id} for {platform} at {scheduled_time}")
        
        try:
            if content_id not in self.marketing_content:
                return {"success": False, "error": "Content not found"}
            
            # Update content with schedule
            content = self.marketing_content[content_id]
            content.scheduled_at = scheduled_time
            content.platform = platform
            
            # Create schedule entry
            schedule_id = hashlib.md5(f"{content_id}_{platform}_{scheduled_time}".encode()).hexdigest()[:8]
            
            self.scheduled_posts[schedule_id] = {
                "schedule_id": schedule_id,
                "content_id": content_id,
                "platform": platform,
                "scheduled_at": scheduled_time,
                "status": "scheduled",
                "created_at": datetime.now()
            }
            
            # Save to database
            await self._save_schedule_to_database(schedule_id)
            await self._update_content_in_database(content)
            
            self.logger.info(f"Post scheduled successfully: {schedule_id}")
            
            return {
                "success": True,
                "schedule_id": schedule_id,
                "content_id": content_id,
                "platform": platform,
                "scheduled_at": scheduled_time.isoformat(),
                "message": "Post scheduled successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to schedule post: {e}")
            return {"success": False, "error": str(e)}
    
    async def publish_content(self, content_id: str, platform: str) -> Dict[str, Any]:
        """Publish content immediately to specified platform"""
        self.logger.info(f"Publishing content {content_id} to {platform}")
        
        try:
            if content_id not in self.marketing_content:
                return {"success": False, "error": "Content not found"}
            
            content = self.marketing_content[content_id]
            
            # Simulate publishing to platform (in real implementation, this would use platform APIs)
            publish_result = await self._publish_to_platform(content, platform)
            
            if publish_result["success"]:
                # Update content status
                content.published_at = datetime.now()
                content.platform = platform
                
                # Save to database
                await self._update_content_in_database(content)
                
                self.metrics["posts_published"] += 1
                
                self.logger.info(f"Content published successfully to {platform}")
                
                return {
                    "success": True,
                    "content_id": content_id,
                    "platform": platform,
                    "published_at": content.published_at.isoformat(),
                    "message": f"Content published successfully to {platform}",
                    "post_url": publish_result.get("post_url")
                }
            else:
                return {"success": False, "error": publish_result.get("error", "Publishing failed")}
            
        except Exception as e:
            self.logger.error(f"Failed to publish content: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_influencer_outreach(self, campaign_id: str, influencer_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Start automated influencer outreach for campaign"""
        self.logger.info(f"Starting influencer outreach for campaign: {campaign_id}")
        
        try:
            if campaign_id not in self.campaigns:
                return {"success": False, "error": "Campaign not found"}
            
            # Find suitable influencers
            suitable_influencers = await self._find_suitable_influencers(influencer_criteria)
            
            outreach_results = []
            
            for influencer in suitable_influencers:
                # Generate personalized outreach message
                outreach_message = await self._generate_outreach_message(influencer, campaign_id)
                
                # Send outreach (simulated)
                outreach_result = await self._send_influencer_outreach(influencer, outreach_message)
                
                outreach_results.append({
                    "influencer_id": influencer["influencer_id"],
                    "name": influencer["name"],
                    "platform": influencer["platform"],
                    "outreach_sent": outreach_result["success"],
                    "message": outreach_result.get("message", "")
                })
                
                self.metrics["influencers_contacted"] += 1
            
            self.logger.info(f"Influencer outreach completed: {len(outreach_results)} influencers contacted")
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "influencers_contacted": len(outreach_results),
                "outreach_results": outreach_results,
                "message": "Influencer outreach campaign started successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start influencer outreach: {e}")
            return {"success": False, "error": str(e)}
    
    async def launch_brand_awareness_campaign(self) -> Dict[str, Any]:
        """Launch comprehensive brand awareness campaign for Dhaher AI Ecosystem"""
        self.logger.info("Launching brand awareness campaign for Dhaher AI Ecosystem")
        
        try:
            # Create main brand awareness campaign
            campaign_result = await self.create_campaign(
                name="Dhaher AI Ecosystem - Indonesian AI Revolution",
                campaign_type="brand_awareness",
                target_audience={
                    "demographics": ["tech_enthusiasts", "developers", "entrepreneurs"],
                    "locations": ["Indonesia", "Southeast Asia"],
                    "interests": ["AI", "automation", "programming", "innovation"],
                    "languages": ["Indonesian", "English"]
                },
                platforms=["twitter", "linkedin", "instagram", "facebook"],
                budget=1000.0,
                schedule={
                    "duration_days": 30,
                    "posts_per_week": 14,
                    "optimal_times": True
                }
            )
            
            if not campaign_result["success"]:
                return campaign_result
            
            campaign_id = campaign_result["campaign_id"]
            
            # Generate and schedule content for the next 7 days
            content_pieces = []
            
            # Introduction posts
            for i, template in enumerate(self.content_templates["introduction"][:2]):
                content_result = await self.generate_content(
                    content_type="post",
                    platform="twitter",
                    template_type="introduction",
                    campaign_id=campaign_id
                )
                if content_result["success"]:
                    content_pieces.append(content_result)
                    
                    # Schedule for the next few days
                    schedule_time = datetime.now() + timedelta(days=i+1, hours=9)
                    await self.schedule_post(content_result["content_id"], "twitter", schedule_time)
            
            # Feature highlight posts
            features = [
                {"name": "Commander AGI", "description": "Security monitoring and robotics coordination"},
                {"name": "Bug Hunter Bot", "description": "Automated ethical hacking and vulnerability discovery"},
                {"name": "Money Making Agent", "description": "Autonomous revenue generation system"},
                {"name": "Indonesian Voice Interface", "description": "Native Bahasa Indonesia voice commands"}
            ]
            
            for i, feature in enumerate(features):
                content_result = await self.generate_content(
                    content_type="post",
                    platform="linkedin",
                    topic=f"Feature: {feature['name']} - {feature['description']}",
                    campaign_id=campaign_id
                )
                if content_result["success"]:
                    content_pieces.append(content_result)
                    
                    # Schedule for LinkedIn
                    schedule_time = datetime.now() + timedelta(days=i+3, hours=12)
                    await self.schedule_post(content_result["content_id"], "linkedin", schedule_time)
            
            # Start automated posting
            asyncio.create_task(self._automated_posting_loop())
            
            self.logger.info(f"Brand awareness campaign launched with {len(content_pieces)} content pieces")
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "content_pieces_created": len(content_pieces),
                "platforms": ["twitter", "linkedin", "instagram", "facebook"],
                "duration_days": 30,
                "message": "Brand awareness campaign launched successfully for Dhaher AI Ecosystem"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to launch brand awareness campaign: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_marketing_analytics(self) -> Dict[str, Any]:
        """Get comprehensive marketing analytics"""
        try:
            # Campaign analytics
            active_campaigns = len([c for c in self.campaigns.values() if c.status == "active"])
            total_budget = sum(c.budget for c in self.campaigns.values())
            
            # Content analytics
            content_by_type = defaultdict(int)
            content_by_platform = defaultdict(int)
            
            for content in self.marketing_content.values():
                content_by_type[content.content_type] += 1
                if content.platform:
                    content_by_platform[content.platform] += 1
            
            # Engagement analytics (simulated)
            total_engagement = sum(
                content.engagement_metrics.get("total_engagement", 0)
                for content in self.marketing_content.values()
                if content.engagement_metrics
            )
            
            # Recent activity
            recent_content = [
                {
                    "content_id": content.content_id,
                    "title": content.title,
                    "platform": content.platform,
                    "created_at": content.created_at.isoformat()
                }
                for content in sorted(
                    self.marketing_content.values(),
                    key=lambda x: x.created_at,
                    reverse=True
                )[:10]
            ]
            
            return {
                "success": True,
                "overview": {
                    "total_campaigns": len(self.campaigns),
                    "active_campaigns": active_campaigns,
                    "total_content_pieces": len(self.marketing_content),
                    "total_budget": total_budget,
                    "total_reach": self.metrics["total_reach"],
                    "total_engagement": total_engagement
                },
                "metrics": self.metrics,
                "distributions": {
                    "content_by_type": dict(content_by_type),
                    "content_by_platform": dict(content_by_platform)
                },
                "recent_content": recent_content,
                "brand_info": self.brand_info,
                "agent_status": self.status,
                "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get marketing analytics: {e}")
            return {"success": False, "error": str(e)}
    
    # Private helper methods
    
    async def _generate_ai_content(self, content_type: str, platform: str, topic: str = None,
                                 template_type: str = None) -> Dict[str, Any]:
        """Generate AI-powered marketing content"""
        try:
            # Select appropriate template
            if template_type and template_type in self.content_templates:
                templates = self.content_templates[template_type]
                base_template = random.choice(templates)
            else:
                # Default to introduction template
                templates = self.content_templates["introduction"]
                base_template = random.choice(templates)
            
            # Generate hashtags based on platform and content
            hashtags = self._generate_hashtags(platform, topic)
            
            # Replace template variables
            content_text = base_template.format(
                founder=self.brand_info["founder"],
                hashtags=" ".join(hashtags),
                feature_name=topic.split(":")[0] if topic and ":" in topic else "AI Innovation",
                feature_description=topic.split(":")[1] if topic and ":" in topic else "Advanced automation capabilities"
            )
            
            # Generate title
            title = self._generate_title(content_type, platform, topic)
            
            # Platform-specific optimizations
            if platform == "twitter":
                content_text = content_text[:280]  # Twitter character limit
            elif platform == "linkedin":
                content_text += "\n\n#OpenToWork #TechInnovation #Indonesia"
            
            return {
                "title": title,
                "content": content_text,
                "hashtags": hashtags,
                "platform_optimized": True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI content: {e}")
            return {
                "title": "Dhaher AI Ecosystem",
                "content": "Introducing the future of AI in Indonesia! 🇮🇩",
                "hashtags": ["#AI", "#Indonesia"]
            }
    
    def _generate_hashtags(self, platform: str, topic: str = None) -> List[str]:
        """Generate relevant hashtags for content"""
        base_hashtags = ["#DhaherAI", "#IndonesiaAI", "#TechInnovation"]
        
        # Add topic-specific hashtags
        if topic:
            topic_lower = topic.lower()
            if "security" in topic_lower:
                base_hashtags.extend(self.config["hashtag_strategies"]["ai"][:2])
            elif "code" in topic_lower or "development" in topic_lower:
                base_hashtags.extend(self.config["hashtag_strategies"]["development"][:2])
            elif "business" in topic_lower:
                base_hashtags.extend(self.config["hashtag_strategies"]["business"][:2])
        
        # Add Indonesia-specific hashtags
        base_hashtags.extend(self.config["hashtag_strategies"]["indonesia"][:2])
        
        # Platform-specific hashtags
        if platform == "linkedin":
            base_hashtags.append("#Professional")
        elif platform == "instagram":
            base_hashtags.append("#TechLife")
        
        return base_hashtags[:10]  # Limit to 10 hashtags
    
    def _generate_title(self, content_type: str, platform: str, topic: str = None) -> str:
        """Generate appropriate title for content"""
        if topic:
            return f"Dhaher AI: {topic}"
        else:
            titles = [
                "Dhaher AI Ecosystem - The Future of Indonesian AI",
                "Revolutionary AI Platform Built in Indonesia",
                "Meet Your New AI Assistant from Indonesia",
                "Autonomous Intelligence for Indonesian Innovation"
            ]
            return random.choice(titles)
    
    async def _automated_posting_loop(self):
        """Background loop for automated posting"""
        while True:
            try:
                current_time = datetime.now()
                
                # Check for scheduled posts
                for schedule_id, schedule_data in self.scheduled_posts.items():
                    if (schedule_data["status"] == "scheduled" and 
                        schedule_data["scheduled_at"] <= current_time):
                        
                        # Publish the post
                        result = await self.publish_content(
                            schedule_data["content_id"],
                            schedule_data["platform"]
                        )
                        
                        if result["success"]:
                            schedule_data["status"] = "published"
                            self.logger.info(f"Auto-published: {schedule_id}")
                        else:
                            schedule_data["status"] = "failed"
                            self.logger.error(f"Auto-publish failed: {schedule_id}")
                
                # Wait 5 minutes before next check
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Automated posting loop error: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error

# Global instance
marketing_agent = MarketingAgent()

# Export for use by other modules
__all__ = ['MarketingAgent', 'marketing_agent', 'Campaign', 'MarketingContent', 'InfluencerProfile']
