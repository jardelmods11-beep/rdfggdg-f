import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs
import json

class CNVSWebScraper:
    def __init__(self, token):
        self.base_url = "https://cnvsweb.stream"
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://cnvsweb.stream/',
        })
        self.last_activity = time.time()
        self.logged_in = False
    
    def login(self):
        """Faz login no site usando o token"""
        try:
            login_url = f"{self.base_url}/login"
            
            # Primeiro GET para pegar cookies
            print("🔑 Acessando página de login...")
            self.session.get(login_url)
            time.sleep(1)
            
            # POST com o token
            payload = {
                'token': self.token
            }
            
            print(f"🔑 Fazendo login com token: {self.token}")
            response = self.session.post(login_url, data=payload, allow_redirects=True)
            
            # Verifica se foi redirecionado para a página principal
            if response.status_code == 200:
                # Verifica se está logado procurando elementos da página logada
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Verifica se existe o menu de perfil (indicador de login bem-sucedido)
                profile_menu = soup.find('ul', class_='profile')
                
                if profile_menu or '/logout' in response.text:
                    print("✓ Login realizado com sucesso")
                    self.last_activity = time.time()
                    self.logged_in = True
                    return True
                else:
                    print(f"⚠ Login pode ter falhado - mas continuando...")
                    # Mesmo assim, considera logado se redirecionou
                    self.logged_in = True
                    return True
            else:
                print(f"✗ Erro no login: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Erro no login: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def keep_alive(self):
        """Atualiza a sessão para não deslogar"""
        if not self.logged_in:
            return
            
        current_time = time.time()
        # Verifica se passaram 3 minutos desde a última atividade
        if current_time - self.last_activity > 180:  # 3 minutos
            print("⟳ Atualizando sessão...")
            try:
                response = self.session.get(self.base_url)
                self.last_activity = time.time()
                print("✓ Sessão atualizada")
            except Exception as e:
                print(f"Erro ao atualizar sessão: {e}")
    
    def get_most_watched_today(self, get_video_urls=True):
        """Pega os filmes mais assistidos do dia"""
        self.keep_alive()
        
        try:
            print("📡 Acessando página principal...")
            response = self.session.get(self.base_url)
            self.last_activity = time.time()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Procura pela seção "Mais Visto do Dia"
            most_watched_section = None
            
            # MÉTODO 1: Procura por h5 com texto exato
            all_h5 = soup.find_all('h5')
            for h5 in all_h5:
                if h5.text and 'Mais Visto' in h5.text:
                    most_watched_section = h5
                    print(f"✓ Seção encontrada: '{h5.text.strip()}'")
                    break
            
            if not most_watched_section:
                print("✗ Seção 'Mais Visto do Dia' não encontrada")
                print(f"🔍 Seções encontradas: {[h5.text.strip() for h5 in all_h5]}")
                return []
            
            # Pega o container pai
            container = most_watched_section.find_parent('div', class_='col-12')
            
            if not container:
                print("✗ Container pai não encontrado")
                return []
            
            print("✓ Container encontrado")
            
            movies = []
            # Procura por todos os slides
            items = container.find_all('div', class_='swiper-slide')
            
            if not items:
                # Método alternativo
                items = container.find_all('div', class_='item')
            
            print(f"📊 Encontrados {len(items)} itens na seção")
            
            for idx, item in enumerate(items, 1):
                try:
                    # Extrai informações do item
                    info_div = item.find('div', class_='info')
                    
                    if not info_div:
                        continue
                    
                    # Título
                    title_tag = info_div.find('h6')
                    title = title_tag.text.strip() if title_tag else "Sem título"
                    
                    # Link para assistir
                    watch_btn = info_div.find('a', href=True)
                    watch_link = watch_btn['href'] if watch_btn else ""
                    
                    # Tags (duração/temporadas, ano, IMDb)
                    tags = info_div.find('p', class_='tags')
                    duration_or_seasons = ""
                    year = ""
                    imdb = ""
                    
                    if tags:
                        spans = tags.find_all('span')
                        if len(spans) > 0:
                            duration_or_seasons = spans[0].text.strip()
                        if len(spans) > 1:
                            year = spans[1].text.strip()
                        if len(spans) > 2:
                            imdb_text = spans[2].text.strip()
                            # Remove "IMDb" do texto
                            imdb = imdb_text.replace('IMDb', '').strip()
                    
                    # Imagem de fundo
                    content_div = item.find('div', class_='content')
                    image_url = ""
                    if content_div:
                        bg_style = content_div.get('style', '')
                        image_match = re.search(r'url\((.*?)\)', bg_style)
                        if image_match:
                            image_url = image_match.group(1).strip('"\'')
                    
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
                    
                    print(f"  {idx}. {title}")
                    
                    # Se solicitado, extrai URLs do player e vídeo
                    if get_video_urls and watch_link:
                        print(f"     🎬 Extraindo vídeo...")
                        try:
                            player_url = self.get_player_url(watch_link)
                            movie_data['player_url'] = player_url
                            
                            if player_url:
                                print(f"     ✓ Player: {player_url[:60]}...")
                                video_url = self.get_video_mp4_url(player_url)
                                movie_data['video_url'] = video_url
                                if video_url:
                                    print(f"     ✓ Vídeo: {video_url[:80]}...")
                                else:
                                    print(f"     ⚠ URL do vídeo não encontrada")
                            else:
                                print(f"     ⚠ URL do player não encontrada")
                        except Exception as e:
                            print(f"     ✗ Erro ao extrair vídeo: {e}")
                    
                    movies.append(movie_data)
                    
                    # Delay para não sobrecarregar o servidor
                    if get_video_urls and idx < len(items):
                        time.sleep(0.3)
                    
                except Exception as e:
                    print(f"  ✗ Erro ao processar item {idx}: {e}")
                    continue
            
            print(f"\n✓ Total: {len(movies)} filmes extraídos")
            return movies
            
        except Exception as e:
            print(f"✗ Erro ao buscar filmes mais assistidos: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def search_movies(self, query, get_video_urls=True):
        """Busca filmes no site"""
        self.keep_alive()
        
        try:
            search_url = f"{self.base_url}/search.php"
            params = {'q': query}
            
            print(f"🔍 Buscando: {query}")
            response = self.session.get(search_url, params=params)
            self.last_activity = time.time()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            movies = []
            items = soup.find_all('div', class_='item poster')
            
            print(f"📊 Encontrados {len(items)} resultados")
            
            for idx, item in enumerate(items, 1):
                try:
                    info_div = item.find('div', class_='info')
                    if not info_div:
                        continue
                    
                    title_tag = info_div.find('h6')
                    title = title_tag.text.strip() if title_tag else "Sem título"
                    
                    watch_btn = info_div.find('a', href=True)
                    watch_link = watch_btn['href'] if watch_btn else ""
                    
                    tags = info_div.find('p', class_='tags')
                    duration_or_seasons = ""
                    year = ""
                    imdb = ""
                    
                    if tags:
                        spans = tags.find_all('span')
                        if len(spans) > 0:
                            duration_or_seasons = spans[0].text.strip()
                        if len(spans) > 1:
                            year = spans[1].text.strip()
                        if len(spans) > 2:
                            imdb_text = spans[2].text.strip()
                            imdb = imdb_text.replace('IMDb', '').strip()
                    
                    content_div = item.find('div', class_='content')
                    image_url = ""
                    if content_div:
                        bg_style = content_div.get('style', '')
                        image_match = re.search(r'url\((.*?)\)', bg_style)
                        if image_match:
                            image_url = image_match.group(1).strip('"\'')
                    
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
                    
                    print(f"  {idx}. {title}")
                    
                    if get_video_urls and watch_link:
                        print(f"     🎬 Extraindo vídeo...")
                        try:
                            player_url = self.get_player_url(watch_link)
                            movie_data['player_url'] = player_url
                            
                            if player_url:
                                video_url = self.get_video_mp4_url(player_url)
                                movie_data['video_url'] = video_url
                                if video_url:
                                    print(f"     ✓ Vídeo extraído")
                                else:
                                    print(f"     ⚠ Vídeo não encontrado")
                            else:
                                print(f"     ⚠ Player não encontrado")
                        except Exception as e:
                            print(f"     ✗ Erro: {e}")
                    
                    movies.append(movie_data)
                    
                    if get_video_urls and idx < len(items):
                        time.sleep(0.3)
                    
                except Exception as e:
                    print(f"  ✗ Erro ao processar item {idx}: {e}")
                    continue
            
            print(f"\n✓ Total: {len(movies)} resultados para '{query}'")
            return movies
            
        except Exception as e:
            print(f"✗ Erro na busca: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_movie_details(self, movie_url):
        """Extrai TODAS as informações detalhadas de um filme"""
        self.keep_alive()
        
        try:
            if not movie_url.startswith('http'):
                movie_url = urljoin(self.base_url, movie_url)
            
            print(f"📄 Acessando página do filme: {movie_url}")
            response = self.session.get(movie_url)
            self.last_activity = time.time()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            movie_info = {
                'title': '',
                'original_title': '',
                'year': '',
                'duration': '',
                'genres': [],
                'imdb_rating': '',
                'synopsis': '',
                'director': '',
                'cast': [],
                'trailer_url': '',
                'image_url': '',
                'backdrop_url': '',
                'watch_link': movie_url,
                'player_url': None,
                'video_url': None
            }
            
            # Título
            title_tag = soup.find('h1') or soup.find('h2', class_='title')
            if title_tag:
                movie_info['title'] = title_tag.text.strip()
            
            # Imagem principal
            poster_div = soup.find('div', class_='poster') or soup.find('img', class_='poster')
            if poster_div:
                if poster_div.name == 'img':
                    movie_info['image_url'] = poster_div.get('src', '')
                else:
                    bg_style = poster_div.get('style', '')
                    image_match = re.search(r'url\((.*?)\)', bg_style)
                    if image_match:
                        movie_info['image_url'] = image_match.group(1).strip('"\'')
            
            # Sinopse
            synopsis_div = soup.find('div', class_='synopsis') or soup.find('p', class_='overview')
            if synopsis_div:
                movie_info['synopsis'] = synopsis_div.text.strip()
            
            # Tags (ano, duração, IMDb)
            tags = soup.find('p', class_='tags') or soup.find('div', class_='tags')
            if tags:
                spans = tags.find_all('span')
                for span in spans:
                    text = span.text.strip()
                    if 'Min' in text or 'Temporadas' in text:
                        movie_info['duration'] = text
                    elif text.isdigit() and len(text) == 4:
                        movie_info['year'] = text
                    elif 'IMDb' in text:
                        movie_info['imdb_rating'] = text.replace('IMDb', '').strip()
            
            # Gêneros
            genres_div = soup.find('div', class_='genres')
            if genres_div:
                genre_links = genres_div.find_all('a')
                movie_info['genres'] = [g.text.strip() for g in genre_links]
            
            # Player e vídeo
            print("     🎬 Extraindo player e vídeo...")
            player_url = self.get_player_url(movie_url)
            movie_info['player_url'] = player_url
            
            if player_url:
                print(f"     ✓ Player: {player_url}")
                video_url = self.get_video_mp4_url(player_url)
                movie_info['video_url'] = video_url
                if video_url:
                    print(f"     ✓ Vídeo MP4 extraído")
            
            return movie_info
            
        except Exception as e:
            print(f"✗ Erro ao obter detalhes do filme: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_player_url(self, movie_url):
        """Extrai a URL do player do filme"""
        self.keep_alive()
        
        try:
            if not movie_url.startswith('http'):
                movie_url = urljoin(self.base_url, movie_url)
            
            response = self.session.get(movie_url)
            self.last_activity = time.time()
            soup = BeautifulSoup(response.content, 'html.parser')
            html = response.text
            
            # MÉTODO 1: Procura por iframe com src contendo "play"
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src', '')
                if src and 'play' in src.lower():
                    player_url = src if src.startswith('http') else urljoin(self.base_url, src)
                    return player_url
            
            # MÉTODO 2: Qualquer iframe
            if iframes and iframes[0].get('src'):
                player_url = iframes[0]['src']
                if not player_url.startswith('http'):
                    player_url = urljoin(self.base_url, player_url)
                return player_url
            
            # MÉTODO 3: Procura no JavaScript por URLs de player
            patterns = [
                r'https?://[^\s"\']*playcnvs[^\s"\']*',
                r'https?://[^\s"\']*player[^\s"\']*',
                r'"playerUrl"\s*:\s*"([^"]+)"',
                r"'playerUrl'\s*:\s*'([^']+)'",
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    url = matches[0].strip('";,\'')
                    if 'play' in url.lower() or 'stream' in url.lower():
                        return url
            
            return None
            
        except Exception as e:
            print(f"       ✗ Erro ao extrair player URL: {e}")
            return None
    
    def get_video_mp4_url(self, player_url):
        """Extrai a URL do vídeo .mp4 do player"""
        self.keep_alive()
        
        try:
            response = self.session.get(player_url)
            self.last_activity = time.time()
            html = response.text
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # MÉTODO 1: Procura tag <video> com src
            video_tag = soup.find('video')
            if video_tag:
                src = video_tag.get('src')
                if src and '.mp4' in src:
                    return src
                
                # Procura <source> dentro de <video>
                source_tag = video_tag.find('source')
                if source_tag:
                    src = source_tag.get('src')
                    if src:
                        return src
            
            # MÉTODO 2: Regex para URLs .mp4 no HTML/JS
            mp4_patterns = [
                r'https?://[^\s<>"\']+\.mp4[^\s<>"\']*',  # URL completa .mp4
                r'"file"\s*:\s*"([^"]+\.mp4[^"]*)"',      # file: "url.mp4"
                r'"src"\s*:\s*"([^"]+\.mp4[^"]*)"',       # src: "url.mp4"
                r'src\s*=\s*"([^"]+\.mp4[^"]*)"',         # src="url.mp4"
                r"src\s*=\s*'([^']+\.mp4[^']*)'",         # src='url.mp4'
                r'"video"\s*:\s*"([^"]+\.mp4[^"]*)"',     # video: "url.mp4"
            ]
            
            for pattern in mp4_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    video_url = matches[0].strip('"\'')
                    return video_url
            
            # MÉTODO 3: Procura por servidor de vídeo específico
            server_patterns = [
                r'https?://server[^\s<>"\']+\.mp4[^\s<>"\']*',
                r'https?://[^\s<>"\']*playmycnvs[^\s<>"\']+\.mp4[^\s<>"\']*',
            ]
            
            for pattern in server_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    video_url = matches[0].strip('"\'')
                    return video_url
            
            return None
            
        except Exception as e:
            print(f"       ✗ Erro ao extrair vídeo MP4: {e}")
            return None


def main():
    """Função de teste"""
    TOKEN = "2E9RCU0B"
    
    print("\n" + "="*70)
    print("CNVSWeb Scraper - Versão Corrigida Final")
    print("="*70)
    
    scraper = CNVSWebScraper(TOKEN)
    
    # Login
    print("\n" + "="*70)
    print("ETAPA 1: LOGIN")
    print("="*70 + "\n")
    
    if not scraper.login():
        print("\n✗ Falha no login. Verifique o token.")
        return
    
    # Filmes mais assistidos
    print("\n" + "="*70)
    print("ETAPA 2: FILMES MAIS ASSISTIDOS DO DIA")
    print("="*70 + "\n")
    
    most_watched = scraper.get_most_watched_today(get_video_urls=True)
    
    if most_watched:
        print("\n" + "="*70)
        print(f"RESULTADOS: {len(most_watched)} FILMES")
        print("="*70)
        
        for i, movie in enumerate(most_watched[:3], 1):
            print(f"\n🎬 {i}. {movie['title']}")
            print(f"   📅 Ano: {movie['year']}")
            print(f"   ⏱️  Duração: {movie['duration_or_seasons']}")
            print(f"   ⭐ IMDb: {movie['imdb']}")
            if movie['player_url']:
                print(f"   🎮 Player: {movie['player_url'][:60]}...")
            if movie['video_url']:
                print(f"   🎥 Vídeo: {movie['video_url'][:80]}...")
    
    # Salva resultados
    output = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total': len(most_watched),
        'movies': most_watched
    }
    
    with open('cnvsweb_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Resultados salvos em cnvsweb_results.json")


if __name__ == "__main__":
    main()
