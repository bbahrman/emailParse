#!/usr/bin/env python3
"""
Helper script to update template.yml based on synced configuration.
This script provides guidance on common console changes that need to be synced.
"""

import json
import sys
import os
from pathlib import Path

def load_json_file(filepath):
    """Load and parse a JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON in {filepath}: {e}")
        return None

def compare_lambda_config(config_file, template_handler):
    """Compare Lambda configuration and suggest template updates."""
    config = load_json_file(config_file)
    if not config:
        return []
    
    suggestions = []
    
    # Check environment variables
    env_vars = config.get('Environment', {}).get('Variables', {})
    if env_vars:
        suggestions.append({
            'type': 'environment_variables',
            'message': f"Environment variables in deployed function: {list(env_vars.keys())}",
            'action': 'Ensure all variables are in template.yml under Environment.Variables'
        })
    
    # Check timeout
    timeout = config.get('Timeout', None)
    if timeout:
        suggestions.append({
            'type': 'timeout',
            'message': f"Deployed timeout: {timeout} seconds",
            'action': f"Ensure Timeout: {timeout} in template.yml"
        })
    
    # Check memory
    memory = config.get('MemorySize', None)
    if memory:
        suggestions.append({
            'type': 'memory',
            'message': f"Deployed memory: {memory} MB",
            'action': f"Ensure MemorySize: {memory} in template.yml"
        })
    
    return suggestions

def check_iam_policies(role_file, policy_files, attached_policies_file):
    """Check IAM role policies and suggest updates."""
    suggestions = []
    
    # Check attached managed policies
    attached = load_json_file(attached_policies_file)
    if attached and attached.get('AttachedPolicies'):
        policies = [p['PolicyArn'] for p in attached['AttachedPolicies']]
        suggestions.append({
            'type': 'managed_policies',
            'message': f"Managed policies attached: {policies}",
            'action': 'Add ManagedPolicyArns or ensure Policies section covers all permissions'
        })
    
    # Check inline policies
    for policy_file in policy_files:
        policy = load_json_file(policy_file)
        if policy:
            policy_name = policy.get('PolicyName', 'unknown')
            statements = policy.get('PolicyDocument', {}).get('Statement', [])
            suggestions.append({
                'type': 'inline_policy',
                'message': f"Inline policy '{policy_name}' with {len(statements)} statement(s)",
                'action': 'Ensure Policies section in template.yml matches these permissions'
            })
    
    return suggestions

def check_api_gateway(api_details_file, stages_file):
    """Check API Gateway configuration."""
    suggestions = []
    
    api_details = load_json_file(api_details_file)
    if api_details:
        # Check CORS
        cors_config = api_details.get('CorsConfiguration')
        if cors_config:
            suggestions.append({
                'type': 'cors',
                'message': "CORS configuration found in deployed API",
                'action': 'Add CorsConfiguration to ServerlessHttpApi in template.yml'
            })
        
        # Check API name
        api_name = api_details.get('Name')
        if api_name:
            suggestions.append({
                'type': 'api_name',
                'message': f"API name: {api_name}",
                'action': 'Consider adding Name property to ServerlessHttpApi'
            })
    
    stages = load_json_file(stages_file)
    if stages and stages.get('Items'):
        for stage in stages['Items']:
            stage_name = stage.get('StageName')
            auto_deploy = stage.get('AutoDeploy', False)
            default_route_settings = stage.get('DefaultRouteSettings', {})
            
            if default_route_settings:
                suggestions.append({
                    'type': 'stage_settings',
                    'message': f"Stage '{stage_name}' has route settings: {default_route_settings}",
                    'action': 'Add DefaultRouteSettings to ServerlessHttpApiStage in template.yml'
                })
    
    return suggestions

def main():
    """Main function to generate template update suggestions."""
    output_dir = Path("sync_output")
    
    if not output_dir.exists():
        print("❌ sync_output directory not found.")
        print("   Run ./sync_template_from_console.sh first to export configurations.")
        sys.exit(1)
    
    print("🔍 Analyzing synced configurations and generating suggestions...")
    print("")
    
    all_suggestions = []
    
    # Check Lambda functions
    print("📦 Checking Lambda functions...")
    bookings_config = output_dir / "bookings_api_lambda_config.json"
    if bookings_config.exists():
        suggestions = compare_lambda_config(bookings_config, "bookings-api-lambda")
        all_suggestions.extend(suggestions)
        for s in suggestions:
            print(f"   • {s['message']}")
    
    email_config = output_dir / "email_parse_lambda_config.json"
    if email_config.exists():
        suggestions = compare_lambda_config(email_config, "email-parse-lambda")
        all_suggestions.extend(suggestions)
        for s in suggestions:
            print(f"   • {s['message']}")
    
    print("")
    
    # Check IAM roles
    print("🔐 Checking IAM roles...")
    bookings_role = output_dir / "bookings_api_role.json"
    if bookings_role.exists():
        policy_files = list(output_dir.glob("bookings_api_role_*.json"))
        policy_files = [f for f in policy_files if 'attached_policies' not in str(f)]
        attached = output_dir / "bookings_api_role_attached_policies.json"
        
        suggestions = check_iam_policies(bookings_role, policy_files, attached)
        all_suggestions.extend(suggestions)
        for s in suggestions:
            print(f"   • {s['message']}")
    
    print("")
    
    # Check API Gateway
    print("🌐 Checking API Gateway...")
    api_files = list(output_dir.glob("http_api_*_details.json"))
    for api_file in api_files:
        api_id = api_file.stem.replace('http_api_', '').replace('_details', '')
        stages_file = output_dir / f"http_api_{api_id}_stages.json"
        
        suggestions = check_api_gateway(api_file, stages_file)
        all_suggestions.extend(suggestions)
        for s in suggestions:
            print(f"   • {s['message']}")
    
    print("")
    
    # Generate recommendations
    print("📋 Recommendations:")
    print("")
    
    for i, suggestion in enumerate(all_suggestions, 1):
        print(f"{i}. {suggestion['type'].upper()}: {suggestion['message']}")
        print(f"   Action: {suggestion['action']}")
        print("")
    
    # Save to file
    report_file = output_dir / "template_update_suggestions.json"
    with open(report_file, 'w') as f:
        json.dump(all_suggestions, f, indent=2)
    
    print(f"💾 Suggestions saved to: {report_file}")
    print("")
    print("📝 Next steps:")
    print("   1. Review the suggestions above")
    print("   2. Update template.yml accordingly")
    print("   3. Test with: sam build && sam deploy --no-execute-changeset")
    print("   4. Deploy with: ./deploy.sh")

if __name__ == "__main__":
    main()

