"""Configuration files and templates"""


from pathlib import Path


class SystemConfig:
    """System configuration wrapper"""
    
    def __init__(self):
        self.system = {
            "name": "Agentic AI System",
            "version": "2.0.0",
            "description": "Autonomous Multi-Agent Intelligence Platform",
        }
        self.core = {
            "prompt_master": {"enabled": True},
            "memory_bus": {"enabled": True},
            "sync_engine": {"enabled": True},
            "scheduler": {"enabled": True},
            "ai_selector": {"enabled": True},
        }
        self.agents = {
            "defaults": {
                "timeout": 300,
                "max_retries": 3,
            },
            "cybershell": {"enabled": True},
            "agent_maker": {"enabled": True},
            "ui_designer": {"enabled": True},
            "dev_engine": {"enabled": True},
            "data_sync": {"enabled": True},
            "fullstack_dev": {"enabled": True},
            "deploy_manager": {"enabled": True},
            "prompt_generator": {"enabled": True},
        }
        self.llm = {
            "primary_provider": "llm7",
        }
        self.database = {
            "primary": {
                "type": "sqlite",
                "url": "sqlite:///data/agentic.db",
            }
        }
        self.web_interface = {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 5000,
        }
        self.logging = {
            "level": "INFO",
        }
        self.monitoring = {
            "enabled": True,
        }
        self.security = {
            "api": {"authentication": {"enabled": True}},
        }
        
        # Try to load YAML config if available
        try:
            import yaml
            config_path = Path(__file__).parent / "system_config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    yaml_config = yaml.safe_load(f)
                if yaml_config:
                    for key, value in yaml_config.items():
                        if hasattr(self, key):
                            if isinstance(value, dict) and isinstance(getattr(self, key), dict):
                                getattr(self, key).update(value)
                            else:
                                setattr(self, key, value)
                        else:
                            setattr(self, key, value)
        except ImportError:
            pass  # YAML not available, use defaults
    
    def get(self, key, default=None):
        """Get a configuration value by key"""
        return getattr(self, key, default)
    
    def __repr__(self):
        return f"SystemConfig(version={self.system.get('version', 'unknown')})"


# Global instance
system_config = SystemConfig()
