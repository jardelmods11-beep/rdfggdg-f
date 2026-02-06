from flask import Flask, jsonify, request
from cnvsweb_scraper import CNVSWebScraper
import threading
import time
import os

app = Flask(__name__)

# Token de acesso (pode vir de variável de ambiente)
TOKEN = os.environ.get('TOKEN', '2E9RCU0B')

# Inicializa o scraper globalmente
scraper = CNVSWebScraper(TOKEN)

# Thread para manter a sessão ativa
def keep_session_alive():
    while True:
        time.sleep(180)  # 3 minutos
        try:
            scraper.keep_alive()
        except Exception as e:
            print(f"Erro no keep-alive: {e}")

# Faz login ao iniciar
try:
    scraper.login()
    # Inicia thread de keep-alive
    keep_alive_thread = threading.Thread(target=keep_session_alive, daemon=True)
    keep_alive_thread.start()
    print("✓ Scraper inicializado e keep-alive ativo")
except Exception as e:
    print(f"✗ Erro ao inicializar scraper: {e}")

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'message': 'CNVSWeb Scraper API',
        'version': '1.0.0',
        'endpoints': {
            'most_watched': {
                'url': '/api/most-watched',
                'method': 'GET',
                'description': 'Filmes mais assistidos do dia (com vídeos)'
            },
            'search': {
                'url': '/api/search?q=query',
                'method': 'GET',
                'description': 'Busca filmes com URLs de vídeo',
                'example': '/api/search?q=avengers'
            },
            'search_fast': {
                'url': '/api/search-fast?q=query',
                'method': 'GET',
                'description': 'Busca rápida sem URLs de vídeo',
                'example': '/api/search-fast?q=batman'
            }
        }
    })

@app.route('/health')
def health():
    """Health check endpoint para monitoramento"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })

@app.route('/api/most-watched')
def most_watched():
    """Retorna os filmes mais assistidos do dia COM URLs de vídeo"""
    try:
        print("\n" + "="*50)
        print("Extraindo filmes mais assistidos do dia...")
        print("="*50 + "\n")
        
        movies = scraper.get_most_watched_today(get_video_urls=True)
        
        return jsonify({
            'success': True,
            'count': len(movies),
            'data': movies
        })
    except Exception as e:
        print(f"Erro em /api/most-watched: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search')
def search():
    """Busca filmes por query COM URLs de vídeo"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter "q" is required',
            'example': '/api/search?q=avengers'
        }), 400
    
    try:
        print("\n" + "="*50)
        print(f"Buscando: {query}")
        print("="*50 + "\n")
        
        results = scraper.search_movies(query, get_video_urls=True)
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(results),
            'data': results
        })
    except Exception as e:
        print(f"Erro em /api/search: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search-fast')
def search_fast():
    """Busca filmes por query SEM URLs de vídeo (mais rápido)"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter "q" is required',
            'example': '/api/search-fast?q=batman'
        }), 400
    
    try:
        print(f"\nBusca rápida: {query}")
        results = scraper.search_movies(query, get_video_urls=False)
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(results),
            'data': results
        })
    except Exception as e:
        print(f"Erro em /api/search-fast: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Tratamento de erros 404
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'available_endpoints': [
            '/',
            '/health',
            '/api/most-watched',
            '/api/search?q=query',
            '/api/search-fast?q=query'
        ]
    }), 404

if __name__ == '__main__':
    # Porta configurável para deploy
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
