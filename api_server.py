from flask import Flask, jsonify, request
from cnvsweb_scraper import CNVSWebScraper
import threading
import time
import os

app = Flask(__name__)

# Token de acesso (pode vir de variável de ambiente)
TOKEN = os.environ.get('TOKEN', '2G4B7UIZ')

# Inicializa o scraper globalmente
scraper = None
scraper_ready = False

def initialize_scraper():
    """Inicializa o scraper em background"""
    global scraper, scraper_ready
    try:
        print("🚀 Inicializando scraper...")
        scraper = CNVSWebScraper(TOKEN)
        if scraper.login():
            scraper_ready = True
            print("✓ Scraper inicializado com sucesso")
        else:
            print("✗ Erro ao fazer login")
    except Exception as e:
        print(f"✗ Erro ao inicializar scraper: {e}")
        import traceback
        traceback.print_exc()

# Thread para manter a sessão ativa
def keep_session_alive():
    """Mantém a sessão ativa a cada 3 minutos"""
    while True:
        time.sleep(180)  # 3 minutos
        try:
            if scraper and scraper_ready:
                scraper.keep_alive()
        except Exception as e:
            print(f"Erro no keep-alive: {e}")

# Inicia o scraper em background
init_thread = threading.Thread(target=initialize_scraper, daemon=True)
init_thread.start()

# Aguarda até 15 segundos para o scraper estar pronto
print("⏳ Aguardando scraper ficar pronto...")
for i in range(15):
    if scraper_ready:
        print(f"✓ Scraper pronto após {i+1} segundos")
        break
    time.sleep(1)

# Inicia thread de keep-alive
keep_alive_thread = threading.Thread(target=keep_session_alive, daemon=True)
keep_alive_thread.start()

@app.route('/')
def home():
    """Página inicial com informações da API"""
    return jsonify({
        'status': 'online',
        'scraper_ready': scraper_ready,
        'message': 'CNVSWeb Scraper API - Versão Corrigida',
        'version': '2.1.0',
        'endpoints': {
            'most_watched': {
                'url': '/api/most-watched',
                'method': 'GET',
                'description': 'Filmes mais assistidos do dia (com vídeos)',
                'params': {
                    'limit': 'Opcional - Número máximo de resultados (padrão: todos)'
                },
                'example': '/api/most-watched?limit=10'
            },
            'search': {
                'url': '/api/search?q=query',
                'method': 'GET',
                'description': 'Busca filmes com URLs de vídeo',
                'params': {
                    'q': 'Obrigatório - Termo de busca',
                    'limit': 'Opcional - Número máximo de resultados'
                },
                'example': '/api/search?q=avengers&limit=10'
            },
            'search_fast': {
                'url': '/api/search-fast?q=query',
                'method': 'GET',
                'description': 'Busca rápida sem URLs de vídeo',
                'params': {
                    'q': 'Obrigatório - Termo de busca',
                    'limit': 'Opcional - Número máximo de resultados'
                },
                'example': '/api/search-fast?q=batman&limit=5'
            }
        },
        'notes': [
            'A primeira requisição após inatividade pode demorar ~30s (Render free tier)',
            'URLs de vídeo são válidas por tempo limitado',
            'A sessão é mantida automaticamente a cada 3 minutos',
            'VERSÃO CORRIGIDA: melhor extração de dados e debugging'
        ]
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy' if scraper_ready else 'initializing',
        'scraper_ready': scraper_ready,
        'timestamp': time.time()
    })

@app.route('/api/most-watched')
def most_watched():
    """Retorna os filmes mais assistidos do dia COM URLs de vídeo"""
    if not scraper_ready:
        return jsonify({
            'success': False,
            'error': 'Scraper ainda está inicializando. Tente novamente em alguns segundos.'
        }), 503
    
    try:
        limit = request.args.get('limit', type=int)
        
        print("\n" + "="*50)
        print("Extraindo filmes mais assistidos do dia...")
        print("="*50 + "\n")
        
        movies = scraper.get_most_watched_today(get_video_urls=True)
        
        # Aplica limite se especificado
        if limit and limit > 0:
            movies = movies[:limit]
        
        return jsonify({
            'success': True,
            'count': len(movies),
            'total_found': len(movies),
            'data': movies
        })
    except Exception as e:
        print(f"Erro em /api/most-watched: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search')
def search():
    """Busca filmes por query COM URLs de vídeo"""
    if not scraper_ready:
        return jsonify({
            'success': False,
            'error': 'Scraper ainda está inicializando. Tente novamente em alguns segundos.'
        }), 503
    
    query = request.args.get('q', '')
    limit = request.args.get('limit', type=int)
    
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
        
        # Aplica limite se especificado
        if limit and limit > 0:
            results = results[:limit]
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(results),
            'data': results
        })
    except Exception as e:
        print(f"Erro em /api/search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search-fast')
def search_fast():
    """Busca filmes por query SEM URLs de vídeo (mais rápido)"""
    if not scraper_ready:
        return jsonify({
            'success': False,
            'error': 'Scraper ainda está inicializando. Tente novamente em alguns segundos.'
        }), 503
    
    query = request.args.get('q', '')
    limit = request.args.get('limit', type=int)
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter "q" is required',
            'example': '/api/search-fast?q=batman'
        }), 400
    
    try:
        print(f"\nBusca rápida: {query}")
        results = scraper.search_movies(query, get_video_urls=False)
        
        # Aplica limite se especificado
        if limit and limit > 0:
            results = results[:limit]
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(results),
            'data': results
        })
    except Exception as e:
        print(f"Erro em /api/search-fast: {e}")
        import traceback
        traceback.print_exc()
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
