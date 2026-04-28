#!/usr/bin/env python3
"""
Script para verificar que la configuración de TikTok esté correcta
"""

import requests
import json

def check_endpoint(url, description):
    """Verifica que un endpoint esté funcionando"""
    try:
        response = requests.get(url, timeout=10)
        status = "✅" if response.status_code == 200 else "❌"
        print(f"{status} {description}: {url}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"   Response: {response.text[:200]}...")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"❌ {description}: {url}")
        print(f"   Error: {e}")
        print()
        return False

def main():
    print("Verificación de Configuración de TikTok for Developers")
    print("=" * 60)
    print()

    base_url = "https://bounceeditor.onrender.com"

    # Verificar endpoints principales
    endpoints = [
        (f"{base_url}/", "Sitio Web Principal"),
        (f"{base_url}/terms.html", "Terms of Service"),
        (f"{base_url}/privacy.html", "Privacy Policy"),
        (f"{base_url}/api/health", "Health Check"),
        (f"{base_url}/api/config", "Config API"),
        (f"{base_url}/api/tiktok/status", "TikTok Status API"),
    ]

    results = []
    for url, description in endpoints:
        results.append(check_endpoint(url, description))

    print("=" * 60)
    print("Resumen:")
    print(f"Endpoints funcionando: {sum(results)}/{len(results)}")

    if all(results):
        print("✅ Todos los endpoints están funcionando correctamente")
        print("✅ La aplicación está lista para el proceso de revisión de TikTok")
    else:
        print("❌ Algunos endpoints no están funcionando")
        print("❌ Revisa la configuración antes de enviar la aplicación")

    print()
    print("Información para el formulario de TikTok:")
    print(f"App Name: BounceClub")
    print(f"Category: Entertainment")
    print(f"Terms of Service: {base_url}/terms.html")
    print(f"Privacy Policy: {base_url}/privacy.html")
    print(f"Redirect URI: {base_url}/api/tiktok/callback")

if __name__ == "__main__":
    main()