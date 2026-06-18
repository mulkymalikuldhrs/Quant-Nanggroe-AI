#!/usr/bin/env python3
"""
Automated Deployment Script for Agentic AI System
Deploys to Netlify and sets up Supabase integration

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables only")

def print_banner():
    """Print deployment banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                 🚀 AGENTIC AI DEPLOYMENT 🚀                  ║
║                                                              ║
║           Automated Multi-Platform Deployment               ║
║                                                              ║
║        Made with ❤️ by Mulky Malikul Dhaher 🇮🇩             ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking environment variables...")
    
    required_vars = [
        'NETLIFY_ACCESS_TOKEN',
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY',
        'SUPABASE_ANON_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file or environment")
        return False
    
    print("✅ All required environment variables are set")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def test_integrations():
    """Test platform integrations"""
    print("🔗 Testing platform integrations...")
    
    try:
        # Import and test integrations
        from src.integrations.netlify_integration import netlify_integration
        from src.integrations.supabase_integration import supabase_integration
        
        # Test Netlify
        print("  Testing Netlify connection...")
        netlify_status = netlify_integration.test_connection()
        if netlify_status['connected']:
            print("  ✅ Netlify connection successful")
            sites = netlify_integration.get_sites()
            print(f"     Found {len(sites)} existing sites")
        else:
            print(f"  ❌ Netlify connection failed: {netlify_status.get('error')}")
            return False
        
        # Test Supabase
        print("  Testing Supabase connection...")
        supabase_status = supabase_integration.test_connection()
        if supabase_status['connected']:
            print("  ✅ Supabase connection successful")
        else:
            print(f"  ❌ Supabase connection failed: {supabase_status.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def build_static_site():
    """Build static site for deployment"""
    print("🔨 Building static site...")
    
    try:
        subprocess.check_call([sys.executable, 'build_static.py'])
        print("✅ Static site built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build static site: {e}")
        return False

def deploy_to_netlify():
    """Deploy to Netlify"""
    print("🌐 Deploying to Netlify...")
    
    try:
        from src.integrations.netlify_integration import netlify_integration
        
        site_name = "agentic-ai-system"
        build_dir = "build"
        
        # Check if site exists
        sites = netlify_integration.get_sites()
        site = None
        
        for s in sites:
            if s.get('name') == site_name:
                site = s
                break
        
        if not site:
            print(f"  Creating new site: {site_name}")
            site = netlify_integration.create_site(site_name)
            if not site:
                print("  ❌ Failed to create site")
                return False
            print(f"  ✅ Site created: {site['id']}")
        else:
            print(f"  ✅ Using existing site: {site['id']}")
        
        # Deploy the site
        print("  Uploading files...")
        deploy_result = netlify_integration.deploy_site(site['id'], build_dir)
        
        if deploy_result:
            site_url = site.get('ssl_url') or site.get('url')
            print(f"  ✅ Deployment successful!")
            print(f"     Site URL: {site_url}")
            print(f"     Deploy ID: {deploy_result['id']}")
            print(f"     Status: {deploy_result['state']}")
            
            return {
                'success': True,
                'site_url': site_url,
                'deploy_id': deploy_result['id'],
                'site_id': site['id']
            }
        else:
            print("  ❌ Deployment failed")
            return False
            
    except Exception as e:
        print(f"❌ Netlify deployment error: {e}")
        return False

def setup_supabase():
    """Setup Supabase database"""
    print("🗄️ Setting up Supabase database...")
    
    try:
        from src.integrations.supabase_integration import supabase_integration
        
        # Test connection
        print("  Testing database connection...")
        connection = supabase_integration.test_connection()
        if not connection['connected']:
            print(f"  ❌ Database connection failed: {connection.get('error')}")
            return False
        
        print("  ✅ Database connection successful")
        
        # Initialize tables (this would require manual setup in Supabase dashboard)
        print("  📋 Database schema initialization:")
        print("     Tables should be created manually in Supabase Dashboard:")
        print("     - agents (for agent management)")
        print("     - tasks (for task tracking)")
        print("     - workflows (for workflow management)")
        print("     - performance_metrics (for monitoring)")
        print("     - agent_activities (for logging)")
        
        return {
            'success': True,
            'url': supabase_integration.url,
            'status': 'connected'
        }
        
    except Exception as e:
        print(f"❌ Supabase setup error: {e}")
        return False

def generate_deployment_report(netlify_result, supabase_result):
    """Generate deployment report"""
    report = {
        'deployment_timestamp': datetime.now().isoformat(),
        'netlify': netlify_result,
        'supabase': supabase_result,
        'system_info': {
            'version': '1.0.0',
            'platform': 'multi-platform',
            'developer': 'Mulky Malikul Dhaher',
            'country': 'Indonesia'
        }
    }
    
    # Save report
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    report_file = reports_dir / f"deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report, report_file

def print_deployment_summary(report):
    """Print deployment summary"""
    print("\n" + "="*60)
    print("🎉 DEPLOYMENT SUMMARY")
    print("="*60)
    
    if report['netlify'] and report['netlify'].get('success'):
        print(f"🌐 Netlify Deployment: ✅ SUCCESS")
        print(f"   URL: {report['netlify']['site_url']}")
        print(f"   Site ID: {report['netlify']['site_id']}")
    else:
        print(f"🌐 Netlify Deployment: ❌ FAILED")
    
    if report['supabase'] and report['supabase'].get('success'):
        print(f"🗄️ Supabase Setup: ✅ SUCCESS")
        print(f"   URL: {report['supabase']['url']}")
    else:
        print(f"🗄️ Supabase Setup: ❌ FAILED")
    
    print(f"\n📊 System Version: {report['system_info']['version']}")
    print(f"🕒 Deployed: {report['deployment_timestamp']}")
    print(f"🇮🇩 Made with ❤️ by {report['system_info']['developer']} in {report['system_info']['country']}")
    print("\n" + "="*60)

def main():
    """Main deployment function"""
    print_banner()
    
    # Pre-deployment checks
    if not check_environment():
        sys.exit(1)
    
    if not install_dependencies():
        sys.exit(1)
    
    if not test_integrations():
        sys.exit(1)
    
    # Build and deploy
    if not build_static_site():
        sys.exit(1)
    
    # Deploy to platforms
    print("\n🚀 Starting multi-platform deployment...")
    
    netlify_result = deploy_to_netlify()
    supabase_result = setup_supabase()
    
    # Generate report
    report, report_file = generate_deployment_report(netlify_result, supabase_result)
    
    # Print summary
    print_deployment_summary(report)
    
    print(f"\n📋 Detailed report saved to: {report_file}")
    
    # Determine overall success
    success = (
        netlify_result and netlify_result.get('success', False) and
        supabase_result and supabase_result.get('success', False)
    )
    
    if success:
        print("\n🎉 Deployment completed successfully!")
        print("🌟 Your Agentic AI System is now live!")
        
        if netlify_result and netlify_result.get('site_url'):
            print(f"\n🔗 Access your system at: {netlify_result['site_url']}")
        
        sys.exit(0)
    else:
        print("\n❌ Deployment completed with errors")
        print("Please check the logs and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()
