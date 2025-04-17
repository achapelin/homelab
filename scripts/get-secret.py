#!/usr/bin/env python3
# filepath: /Users/mathislgs/homelab/homelab-proxmox/scripts/get-secret.py

import argparse
import base64
import os
import sys
from pathlib import Path
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from rich.console import Console
from rich.panel import Panel

console = Console()

def setup_kubeconfig():
    """Set up Kubernetes configuration from default or specified location."""
    # Define project kubeconfig location explicitly
    default_kubeconfig = Path(__file__).parent.parent / "metal" / "ansible" / "kubeconfig.yaml"
    default_kubeconfig_str = str(default_kubeconfig.absolute())
    
    console.print(f"Default kubeconfig path: {default_kubeconfig_str}")
    
    # Check if KUBECONFIG env var is already set
    if "KUBECONFIG" in os.environ and os.path.exists(os.environ["KUBECONFIG"]):
        kubeconfig_path = os.environ["KUBECONFIG"]
        console.print(f"Using KUBECONFIG from environment: {kubeconfig_path}")
        try:
            # Explicitly pass the path rather than relying on the env var
            config.load_kube_config(config_file=kubeconfig_path)
            return
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load from KUBECONFIG env var: {str(e)}[/yellow]")
    
    # Try to use our project's default kubeconfig with explicit path
    if default_kubeconfig.exists():
        try:
            console.print(f"[green]Trying to load project kubeconfig with explicit path[/green]")
            # Set the env var but also pass the path explicitly
            os.environ["KUBECONFIG"] = default_kubeconfig_str
            config.load_kube_config(config_file=default_kubeconfig_str)
            return
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load project kubeconfig: {str(e)}[/yellow]")
    else:
        console.print(f"[red]Project kubeconfig does not exist at {default_kubeconfig_str}[/red]")
    
    # Fall back to default ~/.kube/config with explicit path
    home_kubeconfig = os.path.expanduser("~/.kube/config")
    if os.path.exists(home_kubeconfig):
        try:
            console.print(f"[green]Trying to load home kubeconfig with explicit path[/green]")
            config.load_kube_config(config_file=home_kubeconfig)
            return
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load home kubeconfig: {str(e)}[/yellow]")
    
    console.print(f"[red]Error: Could not load any kubeconfig[/red]")
    sys.exit(1)

def get_secret(name, namespace, key=None):
    """Get a secret from Kubernetes."""
    try:
        v1 = client.CoreV1Api()
        secret = v1.read_namespaced_secret(name=name, namespace=namespace)
        
        # Handle all secret data or just a specific key
        if key:
            if key in secret.data:
                value = base64.b64decode(secret.data[key]).decode('utf-8')
                return {key: value}
            else:
                console.print(f"[red]Key '{key}' not found in secret '{name}'[/red]")
                return None
        else:
            # Return all keys
            result = {}
            for k, v in secret.data.items():
                result[k] = base64.b64decode(v).decode('utf-8')
            return result
            
    except ApiException as e:
        if e.status == 404:
            console.print(f"[red]Secret '{name}' not found in namespace '{namespace}'[/red]")
        else:
            console.print(f"[red]Error accessing secret: {str(e)}[/red]")
        return None

def main():
    parser = argparse.ArgumentParser(description="Get Kubernetes secret")
    parser.add_argument("name", help="Secret name")
    parser.add_argument("-n", "--namespace", default="global-secrets", 
                      help="Kubernetes namespace (default: global-secrets)")
    parser.add_argument("-k", "--key", 
                      help="Specific key to retrieve (optional)")
    parser.add_argument("--kubeconfig", 
                      help="Path to kubeconfig file")
    args = parser.parse_args()
    
    # Set kubeconfig if provided via command line
    if args.kubeconfig:
        if os.path.exists(args.kubeconfig):
            os.environ["KUBECONFIG"] = args.kubeconfig
        else:
            console.print(f"[red]Error: Specified kubeconfig file not found: {args.kubeconfig}[/red]")
            sys.exit(1)
    
    setup_kubeconfig()
    
    # Get and display the secret
    secret_data = get_secret(args.name, args.namespace, args.key)
    
    if secret_data:
        if len(secret_data) == 1:
            # Single key - output just the value for easy copying
            key = list(secret_data.keys())[0]
            value = secret_data[key]
            console.print(f"[cyan]Secret: {args.name}[/cyan] - [yellow]Key: {key}[/yellow]")
            console.print("\n" + value + "\n")
        else:
            # Multiple keys - output in a structured format
            console.print(Panel(f"[bold blue]Secret: {args.name}[/bold blue]"))
            for key, value in secret_data.items():
                console.print(f"[yellow]{key}:[/yellow]")
                console.print(value)
                console.print("")

if __name__ == "__main__":
    main()