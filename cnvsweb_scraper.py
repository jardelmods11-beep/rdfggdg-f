import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
import json

class CNVSWebScraper:
    def __init__(self, token):
        self.base_url = "https://cnvsweb.stream"
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.last_activity = time.time()
    
    def login(self):
        """Faz login no site usando o token"""
        login_url = f"{self.base_url}/login"
        
        # Faz POST com o token
        payload = {
            'token': self.token
        }
        
        response = self.session.post(login_url, data=payload)
        
        if response.status_code == 200:
            print("✓ Login realizado com sucesso")
            self.last_activity = time.time()
            return True
        else:
            print(f"✗ Erro no login: {response.status_code}")
            return False
    
    def keep_alive(self):
        """Atualiza a sessão para não deslogar"""
        current_time = time.time()
        # Verifica se passaram 3 minutos desde a última atividade
        if current_time - self.last_activity > 180:  # 3 minutos
            print("⟳ Atualizando sessão...")
            response = self.session.get(self.base_url)
            self.last_activity = time.time()
            print("✓ Sessão atualizada")
    
    def get_most_watched_today(self, get_video_urls=True):
        """Pega os filmes mais assistidos do dia com todas as informações"""
        self.keep_alive()
        
        response = self.session.get(self.base_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Encontra a seção "Mais Visto do Dia"
        most_watched_section = soup.find('h5', text='Mais Visto do Dia')
        
        if not most_watched_section:
            print("✗ Seção 'Mais Visto do Dia' não encontrada")
            return []
        
        # Pega o container pai
        container = most_watched_section.find_parent('div', class_='col-12')
        
        movies = []
        items = container.find_all('div', class_='item poster')
        
        for item in items:
            try:
                info_div = item.find('div', class_='info movie')
                
                # Extrai informações
                title = info_div.find('h6').text.strip()
                watch_link = info_div.find('a', class_='btn')['href']
                
                tags = info_div.find('p', class_='tags')
                spans = tags.find_all('span')
                
                duration_or_seasons = spans[0].text.strip() if len(spans) > 0 else ""
                year = spans[1].text.strip() if len(spans) > 1 else ""
                imdb = spans[2].text.strip() if len(spans) > 2 else ""
                
                # Extrai imagem de fundo
                content_div = item.find('div', class_='content')
                bg_style = content_div.get('style', '')
                image_url = re.search(r'url\((.*?)\)', bg_style)
                image_url = image_url.group(1) if image_url else ""
                
                movie_data = {
                    'title': title,
                    'watch_link': watch_link,
                    'duration_or_seasons': duration_or_seasons,
                    'year': year,
                    'imdb': imdb,
                    'image_url': image_url,
                    'player_url': None,
                    'video_url': None
                }
                
                # Se solicitado, extrai URLs do player e vídeo
                if get_video_urls:
                    print(f"  Extraindo vídeo de: {title}")
                    try:
                        player_url = self.get_player_url(watch_link)
                        movie_data['player_url'] = player_url
                        
                        if player_url:
                            video_url = self.get_video_mp4_url(player_url)
                            movie_data['video_url'] = video_url
                    except Exception as e:
                        print(f"    ✗ Erro ao extrair vídeo: {e}")
                
                movies.append(movie_data)
                
            except Exception as e:
                print(f"Erro ao processar item: {e}")
                continue
        
        print(f"✓ Encontrados {len(movies)} filmes mais assistidos do dia")
        return movies
    
    def search_movies(self, query, get_video_urls=True):
        """Busca filmes no site e extrai todas as informações incluindo vídeo"""
        self.keep_alive()
        
        search_url = f"{self.base_url}/search.php"
        params = {'q': query}
        
        response = self.session.get(search_url, params=params)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        movies = []
        items = soup.find_all('div', class_='item poster')
        
        for item in items:
            try:
                info_div = item.find('div', class_='info movie')
                
                title = info_div.find('h6').text.strip()
                watch_link = info_div.find('a', class_='btn')['href']
                
                tags = info_div.find('p', class_='tags')
                spans = tags.find_all('span')
                
                duration_or_seasons = spans[0].text.strip() if len(spans) > 0 else ""
                year = spans[1].text.strip() if len(spans) > 1 else ""
                imdb = spans[2].text.strip() if len(spans) > 2 else ""
                
                content_div = item.find('div', class_='content')
                bg_style = content_div.get('style', '')
                image_url = re.search(r'url\((.*?)\)', bg_style)
                image_url = image_url.group(1) if image_url else ""
                
                movie_data = {
                    'title': title,
                    'watch_link': watch_link,
                    'duration_or_seasons': duration_or_seasons,
                    'year': year,
                    'imdb': imdb,
                    'image_url': image_url,
                    'player_url': None,
                    'video_url': None
                }
                
                # Se solicitado, extrai URLs do player e vídeo
                if get_video_urls:
                    print(f"  Extraindo vídeo de: {title}")
                    try:
                        player_url = self.get_player_url(watch_link)
                        movie_data['player_url'] = player_url
                        
                        if player_url:
                            video_url = self.get_video_mp4_url(player_url)
                            movie_data['video_url'] = video_url
                    except Exception as e:
                        print(f"    ✗ Erro ao extrair vídeo: {e}")
                
                movies.append(movie_data)
                
            except Exception as e:
                print(f"Erro ao processar item: {e}")
                continue
        
        print(f"✓ Encontrados {len(movies)} resultados para '{query}'")
        return movies
    
    def get_movie_details(self, movie_url):
        """Pega detalhes completos de um filme"""
        self.keep_alive()
        
        if not movie_url.startswith('http'):
            movie_url = urljoin(self.base_url, movie_url)
        
        response = self.session.get(movie_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extrai informações da página do filme
        title = soup.find('title').text.replace('VisionCine - Assistir ', '').replace(' Online Grátis', '')
        
        movie_details = {
            'title': title,
            'url': movie_url
        }
        
        print(f"✓ Detalhes obtidos para: {title}")
        return movie_details
    
    def get_player_url(self, movie_url):
        """Extrai a URL do player do filme"""
        self.keep_alive()
        
        if not movie_url.startswith('http'):
            movie_url = urljoin(self.base_url, movie_url)
        
        response = self.session.get(movie_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Procura por iframe ou link do player
        iframe = soup.find('iframe')
        if iframe:
            player_url = iframe.get('src', '')
            print(f"✓ Player URL encontrada: {player_url}")
            return player_url
        
        # Procura por links que contenham 'play'
        links = soup.find_all('a', href=True)
        for link in links:
            if 'play' in link['href'].lower():
                player_url = link['href']
                if not player_url.startswith('http'):
                    player_url = urljoin(self.base_url, player_url)
                print(f"✓ Player URL encontrada: {player_url}")
                return player_url
        
        print("✗ Player URL não encontrada")
        return None
    
    def get_video_mp4_url(self, player_url):
        """Extrai a URL do vídeo .mp4 do player"""
        self.keep_alive()
        
        response = self.session.get(player_url)
        
        # Procura por URL .mp4 no HTML
        mp4_pattern = r'https?://[^\s<>"]+?\.mp4[^\s<>"]*'
        matches = re.findall(mp4_pattern, response.text)
        
        if matches:
            video_url = matches[0]
            print(f"✓ Vídeo .mp4 encontrado: {video_url[:80]}...")
            return video_url
        
        # Tenta encontrar no atributo src de vídeo
        soup = BeautifulSoup(response.content, 'html.parser')
        video_tag = soup.find('video')
        
        if video_tag:
            src = video_tag.get('src', '')
            if src:
                print(f"✓ Vídeo encontrado na tag <video>: {src[:80]}...")
                return src
        
        print("✗ URL do vídeo .mp4 não encontrada")
        return None


def main():
    # Token de acesso
    TOKEN = "2E9RCU0B"
    
    # Inicializa o scraper
    scraper = CNVSWebScraper(TOKEN)
    
    # Faz login
    if not scraper.login():
        print("Falha no login. Encerrando...")
        return
    
    print("\n" + "="*50)
    print("FILMES MAIS ASSISTIDOS DO DIA (COM VÍDEOS)")
    print("="*50 + "\n")
    
    # Pega filmes mais assistidos do dia COM vídeos
    most_watched = scraper.get_most_watched_today(get_video_urls=True)
    
    for i, movie in enumerate(most_watched[:3], 1):  # Mostra apenas os 3 primeiros
        print(f"\n{i}. {movie['title']}")
        print(f"   Ano: {movie['year']}")
        print(f"   Duração/Temporadas: {movie['duration_or_seasons']}")
        print(f"   IMDb: {movie['imdb']}")
        print(f"   Link: {movie['watch_link']}")
        print(f"   Player: {movie['player_url']}")
        print(f"   Vídeo: {movie['video_url'][:80] if movie['video_url'] else 'N/A'}...")
    
    # Exemplo de busca COM vídeos
    print("\n" + "="*50)
    print("BUSCA: 'veloz' (COM VÍDEOS)")
    print("="*50 + "\n")
    
    search_results = scraper.search_movies("veloz", get_video_urls=True)
    
    for i, movie in enumerate(search_results[:3], 1):  # Mostra apenas os 3 primeiros
        print(f"\n{i}. {movie['title']}")
        print(f"   Ano: {movie['year']}")
        print(f"   Duração/Temporadas: {movie['duration_or_seasons']}")
        print(f"   IMDb: {movie['imdb']}")
        print(f"   Player: {movie['player_url']}")
        print(f"   Vídeo: {movie['video_url'][:80] if movie['video_url'] else 'N/A'}...")
    
    # Salva resultados em JSON
    output = {
        'most_watched_today': most_watched,
        'search_results': search_results
    }
    
    with open('/home/claude/cnvsweb_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n✓ Resultados salvos em cnvsweb_results.json")


if __name__ == "__main__":
    main()
