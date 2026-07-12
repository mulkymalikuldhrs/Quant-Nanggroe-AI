"""
Knowledge Enrichment System for Agentic AI
Integrates multiple external knowledge sources and APIs

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import aiohttp
import requests
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
from dataclasses import dataclass

@dataclass
class KnowledgeSource:
    """Data structure for knowledge sources"""
    name: str
    url: str
    api_key_required: bool
    description: str
    rate_limit: int  # requests per hour
    
class FreeAPIConnector:
    """Connector for free public APIs"""
    
    def __init__(self):
        self.apis = {
            'wikipedia': KnowledgeSource(
                name='Wikipedia',
                url='https://en.wikipedia.org/api/rest_v1',
                api_key_required=False,
                description='Encyclopedia knowledge',
                rate_limit=5000
            ),
            'jsonplaceholder': KnowledgeSource(
                name='JSONPlaceholder',
                url='https://jsonplaceholder.typicode.com',
                api_key_required=False,
                description='Sample REST API data',
                rate_limit=1000
            ),
            'httpbin': KnowledgeSource(
                name='HTTPBin',
                url='https://httpbin.org',
                api_key_required=False,
                description='HTTP testing service',
                rate_limit=1000
            ),
            'quotable': KnowledgeSource(
                name='Quotable',
                url='https://api.quotable.io',
                api_key_required=False,
                description='Inspirational quotes',
                rate_limit=1000
            ),
            'catfacts': KnowledgeSource(
                name='Cat Facts',
                url='https://catfact.ninja',
                api_key_required=False,
                description='Random cat facts',
                rate_limit=1000
            ),
            'uselessfacts': KnowledgeSource(
                name='Useless Facts',
                url='https://uselessfacts.jsph.pl',
                api_key_required=False,
                description='Random interesting facts',
                rate_limit=1000
            ),
            'jokes': KnowledgeSource(
                name='JokeAPI',
                url='https://v2.jokeapi.dev',
                api_key_required=False,
                description='Programming and general jokes',
                rate_limit=1000
            ),
            'advice': KnowledgeSource(
                name='Advice Slip',
                url='https://api.adviceslip.com',
                api_key_required=False,
                description='Random advice',
                rate_limit=1000
            ),
            'numbers': KnowledgeSource(
                name='Numbers API',
                url='http://numbersapi.com',
                api_key_required=False,
                description='Interesting number facts',
                rate_limit=1000
            ),
            'kanye': KnowledgeSource(
                name='Kanye REST',
                url='https://api.kanye.rest',
                api_key_required=False,
                description='Kanye West quotes',
                rate_limit=1000
            )
        }
        
    async def fetch_wikipedia_summary(self, topic: str) -> Optional[Dict]:
        """Fetch Wikipedia summary for a topic"""
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'source': 'Wikipedia',
                            'topic': topic,
                            'title': data.get('title', ''),
                            'extract': data.get('extract', ''),
                            'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                            'thumbnail': data.get('thumbnail', {}).get('source', ''),
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            print(f"Error fetching Wikipedia data: {e}")
            
        return None
    
    async def fetch_quotes(self, tags: Optional[str] = None) -> Optional[Dict]:
        """Fetch inspirational quotes"""
        try:
            url = "https://api.quotable.io/random"
            params = {}
            if tags:
                params['tags'] = tags
                
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'source': 'Quotable',
                            'content': data.get('content', ''),
                            'author': data.get('author', ''),
                            'tags': data.get('tags', []),
                            'length': data.get('length', 0),
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            
        return None
    
    async def fetch_random_fact(self) -> Optional[Dict]:
        """Fetch random interesting fact"""
        try:
            url = "https://uselessfacts.jsph.pl/random.json?language=en"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'source': 'Useless Facts',
                            'fact': data.get('text', ''),
                            'permalink': data.get('permalink', ''),
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            print(f"Error fetching random fact: {e}")
            
        return None
    
    async def fetch_advice(self) -> Optional[Dict]:
        """Fetch random advice"""
        try:
            url = "https://api.adviceslip.com/advice"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        slip = data.get('slip', {})
                        return {
                            'source': 'Advice Slip',
                            'advice': slip.get('advice', ''),
                            'id': slip.get('id', ''),
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            print(f"Error fetching advice: {e}")
            
        return None
    
    async def fetch_joke(self, category: str = 'Programming') -> Optional[Dict]:
        """Fetch programming or general joke"""
        try:
            url = f"https://v2.jokeapi.dev/joke/{category}"
            params = {
                'blacklistFlags': 'nsfw,religious,political,racist,sexist,explicit'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('type') == 'single':
                            joke_text = data.get('joke', '')
                        else:
                            setup = data.get('setup', '')
                            delivery = data.get('delivery', '')
                            joke_text = f"{setup}\n{delivery}"
                        
                        return {
                            'source': 'JokeAPI',
                            'category': data.get('category', ''),
                            'type': data.get('type', ''),
                            'joke': joke_text,
                            'safe': data.get('safe', True),
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            print(f"Error fetching joke: {e}")
            
        return None
    
    async def fetch_number_fact(self, number: Optional[int] = None) -> Optional[Dict]:
        """Fetch interesting fact about a number"""
        try:
            if number is None:
                url = "http://numbersapi.com/random"
            else:
                url = f"http://numbersapi.com/{number}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        fact_text = await response.text()
                        return {
                            'source': 'Numbers API',
                            'number': number or 'random',
                            'fact': fact_text,
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            print(f"Error fetching number fact: {e}")
            
        return None
    
    async def fetch_cat_fact(self) -> Optional[Dict]:
        """Fetch random cat fact"""
        try:
            url = "https://catfact.ninja/fact"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'source': 'Cat Facts',
                            'fact': data.get('fact', ''),
                            'length': data.get('length', 0),
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            print(f"Error fetching cat fact: {e}")
            
        return None

class IntelligentKnowledgeOrchestrator:
    """Orchestrates knowledge gathering from multiple sources based on context"""
    
    def __init__(self, free_api_connector: FreeAPIConnector):
        self.connector = free_api_connector
        self.knowledge_cache = {}
        
    async def gather_contextual_knowledge(self, topic: str, context: str = 'general') -> Dict[str, Any]:
        """Gather knowledge based on topic and context"""
        knowledge_result = {
            'topic': topic,
            'context': context,
            'sources': {},
            'summary': '',
            'timestamp': datetime.now().isoformat()
        }
        
        # Always try to get Wikipedia summary first
        wikipedia_data = await self.connector.fetch_wikipedia_summary(topic)
        if wikipedia_data:
            knowledge_result['sources']['wikipedia'] = wikipedia_data
            
        # Add context-specific knowledge
        if context.lower() in ['motivation', 'inspiration', 'quotes']:
            quotes_data = await self.connector.fetch_quotes(topic)
            if quotes_data:
                knowledge_result['sources']['quotes'] = quotes_data
                
        elif context.lower() in ['fun', 'entertainment', 'jokes']:
            joke_data = await self.connector.fetch_joke()
            if joke_data:
                knowledge_result['sources']['jokes'] = joke_data
                
            fact_data = await self.connector.fetch_random_fact()
            if fact_data:
                knowledge_result['sources']['facts'] = fact_data
                
        elif context.lower() in ['advice', 'guidance', 'help']:
            advice_data = await self.connector.fetch_advice()
            if advice_data:
                knowledge_result['sources']['advice'] = advice_data
                
        elif context.lower() in ['numbers', 'math', 'statistics']:
            try:
                # Try to extract number from topic
                number = int(''.join(filter(str.isdigit, topic)))
                number_fact = await self.connector.fetch_number_fact(number)
                if number_fact:
                    knowledge_result['sources']['numbers'] = number_fact
            except:
                # Fallback to random number fact
                number_fact = await self.connector.fetch_number_fact()
                if number_fact:
                    knowledge_result['sources']['numbers'] = number_fact
        
        # Always add some general interesting content
        if len(knowledge_result['sources']) < 2:
            fact_data = await self.connector.fetch_random_fact()
            if fact_data:
                knowledge_result['sources']['general_facts'] = fact_data
        
        # Generate summary
        knowledge_result['summary'] = self._generate_knowledge_summary(knowledge_result['sources'])
        
        return knowledge_result
    
    def _generate_knowledge_summary(self, sources: Dict) -> str:
        """Generate a summary from gathered knowledge"""
        summary_parts = []
        
        if 'wikipedia' in sources:
            wiki_data = sources['wikipedia']
            summary_parts.append(f"Wikipedia: {wiki_data.get('extract', '')[:200]}...")
            
        if 'quotes' in sources:
            quote_data = sources['quotes']
            summary_parts.append(f"Quote: \"{quote_data.get('content', '')}\" - {quote_data.get('author', '')}")
            
        if 'facts' in sources:
            fact_data = sources['facts']
            summary_parts.append(f"Interesting fact: {fact_data.get('fact', '')}")
            
        if 'advice' in sources:
            advice_data = sources['advice']
            summary_parts.append(f"Advice: {advice_data.get('advice', '')}")
            
        if 'jokes' in sources:
            joke_data = sources['jokes']
            summary_parts.append(f"Joke: {joke_data.get('joke', '')}")
            
        return " | ".join(summary_parts) if summary_parts else "No additional knowledge found."
    
    async def get_enriched_context_for_agent(self, agent_request: str, agent_type: str) -> Dict:
        """Get enriched context specifically for an agent's request"""
        
        # Determine context based on agent type and request
        context_mapping = {
            'agent_03_planner': 'planning',
            'agent_04_executor': 'technical',
            'agent_05_designer': 'creative',
            'agent_06_specialist': 'expert'
        }
        
        context = context_mapping.get(agent_type, 'general')
        
        # Extract main topic from request
        topic = self._extract_main_topic(agent_request)
        
        # Gather knowledge
        knowledge = await self.gather_contextual_knowledge(topic, context)
        
        # Add agent-specific insights
        agent_insights = self._generate_agent_specific_insights(knowledge, agent_type)
        knowledge['agent_insights'] = agent_insights
        
        return knowledge
    
    def _extract_main_topic(self, request: str) -> str:
        """Extract main topic from agent request"""
        # Simple keyword extraction (can be enhanced with NLP)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'create', 'make', 'build', 'develop', 'design'}
        words = request.lower().split()
        
        # Filter out common words and get the most meaningful terms
        meaningful_words = [word for word in words if word not in common_words and len(word) > 3]
        
        # Return the first few meaningful words as topic
        return ' '.join(meaningful_words[:3]) if meaningful_words else 'general topic'
    
    def _generate_agent_specific_insights(self, knowledge: Dict, agent_type: str) -> str:
        """Generate insights specific to agent type"""
        insights = {
            'agent_03_planner': "Consider breaking down complex topics into manageable phases. Use external knowledge to identify potential challenges and opportunities.",
            'agent_04_executor': "Focus on practical implementation details. External APIs and data sources can provide real-world context for execution.",
            'agent_05_designer': "Use visual and creative elements from external sources. Consider user experience and aesthetic appeal in design decisions.",
            'agent_06_specialist': "Leverage domain expertise and current best practices. Ensure compliance and quality standards are met."
        }
        
        base_insight = insights.get(agent_type, "Use external knowledge to enhance decision-making and provide comprehensive solutions.")
        
        # Add knowledge-specific insights
        if 'wikipedia' in knowledge.get('sources', {}):
            base_insight += " Wikipedia provides foundational knowledge for informed decision-making."
            
        if 'quotes' in knowledge.get('sources', {}):
            base_insight += " Inspirational content can motivate and guide approach."
            
        return base_insight

# Global knowledge orchestrator instance
free_api_connector = FreeAPIConnector()
knowledge_orchestrator = IntelligentKnowledgeOrchestrator(free_api_connector)
