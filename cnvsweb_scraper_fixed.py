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
                    print(f"✗ Login pode ter fallhado - verificando cookies...")
                    # Mostra os cookies para debug
                    print(f"Cookies: {self.session.cookies.get_dict()}")
                    # Mesmo assim, considera logado se redirecionou
                    self.logged_in = True
                    return True
            else:
                print(f"✗ Erro no login: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Erro no login: {e}")
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
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # MÉTODO 1: Procura pela seção "Mais Visto do Dia" - busca exata
            most_watched_section = soup.find('h5', string=lambda text: text and 'Mais Visto do Dia' in text)
            
            if not most_watched_section:
                # MÉTODO 2: Busca case-insensitive
                most_watched_section = soup.find('h5', string=re.compile(r'mais\s+visto\s+do\s+dia', re.IGNORECASE))
            
            if not most_watched_section:
                # MÉTODO 3: Busca por qualquer h5 com "Mais Visto"
                all_h5 = soup.find_all('h5')
                for h5 in all_h5:
                    if h5.text and 'Mais Visto' in h5.text:
                        most_watched_section = h5
                        break
            
            if not most_watched_section:
                print("✗ Seção 'Mais Visto do Dia' não encontrada")
                print(f"🔍 Debug: Procurando todas as seções h5...")
                all_h5 = soup.find_all('h5')
                print(f"Seções h5 encontradas: {[h5.text.strip() for h5 in all_h5]}")
                return []
            
            print(f"✓ Seção encontrada: '{most_watched_section.text.strip()}'")
            
            # Pega o container pai (div.col-12)
            container = most_watched_section.find_parent('div', class_='col-12')
            
            if not container:
                print("✗ Container pai não encontrado")
                return []
            
            print("✓ Container encontrado")
            
            movies = []
            items = container.find_all('div', class_='swiper-slide')
            
            if not items:
                # Tenta método alternativo
                items = container.find_all('div', class_='item poster')
            
            print(f"📊 Encontrados {len(items)} itens na seção")
            
            for idx, item in enumerate(items, 1):
                try:
                    # Extrai informações do item
                    info_div = item.find('div', class_='info')
                    
                    if not info_div:
                        print(f"  ⚠ Item {idx}: div.info não encontrada")
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
                                print(f"     ✓ Player encontrado: {player_url[:60]}...")
                                video_url = self.get_video_mp4_url(player_url)
                                movie_data['video_url'] = video_url
                                if video_url:
                                    print(f"     ✓ Vídeo extraído: {video_url[:80]}...")
                                else:
                                    print(f"     ⚠ URL do vídeo não encontrada")
                            else:
                                print(f"     ⚠ URL do player não encontrada")
                        except Exception as e:
                            print(f"     ✗ Erro ao extrair vídeo: {e}")
                    
                    movies.append(movie_data)
                    
                    # Delay para não sobrecarregar o servidor
                    if get_video_urls:
                        time.sleep(0.5)
                    
                except Exception as e:
                    print(f"  ✗ Erro ao processar item {idx}: {e}")
                    continue
            
            print(f"\n✓ Encontrados {len(movies)} filmes mais assistidos do dia")
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
                        print(f"     🎬 Extraindo vídeo de: {title}")
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
                    
                    if get_video_urls:
                        time.sleep(0.5)
                    
                except Exception as e:
                    print(f"  ✗ Erro ao processar item {idx}: {e}")
                    continue
            
            print(f"\n✓ Encontrados {len(movies)} resultados para '{query}'")
            return movies
            
        except Exception as e:
            print(f"✗ Erro na busca: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_player_url(self, movie_url):
        """Extrai a URL do player do filme"""
        self.keep_alive()
        
        try:
            if not movie_url.startswith('http'):
                movie_url = urljoin(self.base_url, movie_url)
            
            print(f"       🔗 Acessando: {movie_url}")
            response = self.session.get(movie_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # MÉTODO 1: Procura por iframe com src contendo "play"
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src', '')
                if src and 'play' in src.lower():
                    player_url = src if src.startswith('http') else urljoin(self.base_url, src)
                    print(f"       ✓ Player encontrado via iframe: {player_url}")
                    return player_url
            
            # MÉTODO 2: Procura por qualquer iframe
            if iframes and iframes[0].get('src'):
                player_url = iframes[0]['src']
                if not player_url.startswith('http'):
                    player_url = urljoin(self.base_url, player_url)
                print(f"       ✓ Player encontrado (iframe): {player_url}")
                return player_url
            
            # MÉTODO 3: Procura por botão com link de player
            watch_buttons = soup.find_all('a', class_='btn')
            for btn in watch_buttons:
                href = btn.get('href', '')
                if href and ('player' in href.lower() or 'play' in href.lower()):
                    player_url = href if href.startswith('http') else urljoin(self.base_url, href)
                    print(f"       ✓ Player encontrado (botão): {player_url}")
                    return player_url
            
            # MÉTODO 4: Procura no JavaScript
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Padrões de URL do player
                    patterns = [
                        r'https?://[^\s"\']*playcnvs[^\s"\']*',
                        r'https?://[^\s"\']*player[^\s"\']*',
                        r'"url"\s*:\s*"([^"]+)"',
                        r"'url'\s*:\s*'([^']+)'",
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, script.string, re.IGNORECASE)
                        if matches:
                            url = matches[0]
                            if 'play' in url.lower() or 'stream' in url.lower():
                                player_url = url.strip('";,\'')
                                print(f"       ✓ Player encontrado (JavaScript): {player_url}")
                                return player_url
            
            print(f"       ✗ URL do player não encontrado")
            return None
            
        except Exception as e:
            print(f"       ✗ Erro ao extrair player URL: {e}")
            return None
    
    def get_video_mp4_url(self, player_url):
        """Extrai a URL do vídeo .mp4 do player"""
        self.keep_alive()
        
        try:
            print(f"       🎥 Acessando player: {player_url}")
            response = self.session.get(player_url)
            html = response.text
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # MÉTODO 1: Procura tag <video> com src
            video_tag = soup.find('video')
            if video_tag:
                src = video_tag.get('src')
                if src and src.endswith('.mp4'):
                    print(f"       ✓ Vídeo encontrado em <video>")
                    return src
                
                # Procura <source> dentro de <video>
                source_tag = video_tag.find('source')
                if source_tag:
                    src = source_tag.get('src')
                    if src:
                        print(f"       ✓ Vídeo encontrado em <source>")
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
                    video_url = matches[0]
                    # Remove caracteres extras
                    video_url = video_url.strip('"\'')
                    print(f"       ✓ Vídeo encontrado (regex): {video_url[:80]}...")
                    return video_url
            
            # MÉTODO 3: Procura por servidor de vídeo comum
            server_patterns = [
                r'https?://server[^\s<>"\']+\.mp4[^\s<>"\']*',
                r'https?://[^\s<>"\']*playmycnvs[^\s<>"\']+\.mp4[^\s<>"\']*',
            ]
            
            for pattern in server_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    video_url = matches[0].strip('"\'')
                    print(f"       ✓ Vídeo encontrado (servidor): {video_url[:80]}...")
                    return video_url
            
            print(f"       ✗ URL do vídeo MP4 não encontrada")
            # Debug: mostra um trecho do HTML
            print(f"       🔍 Debug HTML (primeiros 500 chars): {html[:500]}")
            return None
            
        except Exception as e:
            print(f"       ✗ Erro ao extrair vídeo MP4: {e}")
            return None


def main():
    """Função de teste"""
    TOKEN = "2E9RCU0B"
    
    print("\n" + "="*70)
    print("CNVSWeb Scraper - Versão Corrigida")
    print("="*70)
    
    # Inicializa o scraper
    scraper = CNVSWebScraper(TOKEN)
    
    # Faz login
    print("\n" + "="*70)
    print("ETAPA 1: LOGIN")
    print("="*70 + "\n")
    
    if not scraper.login():
        print("\n✗ Falha no login. Verifique o token.")
        return
    
    # Pega filmes mais assistidos
    print("\n" + "="*70)
    print("ETAPA 2: FILMES MAIS ASSISTIDOS")
    print("="*70 + "\n")
    
    most_watched = scraper.get_most_watched_today(get_video_urls=True)
    
    # Mostra resultados
    if most_watched:
        print("\n" + "="*70)
        print(f"RESULTADOS: {len(most_watched)} FILMES ENCONTRADOS")
        print("="*70)
        
        # Mostra os 3 primeiros com detalhes
        for i, movie in enumerate(most_watched[:3], 1):
            print(f"\n🎬 {i}. {movie['title']}")
            print(f"   📅 Ano: {movie['year']}")
            print(f"   ⏱️  Duração: {movie['duration_or_seasons']}")
            print(f"   ⭐ IMDb: {movie['imdb']}")
            if movie['player_url']:
                print(f"   🎮 Player: {movie['player_url'][:60]}...")
            if movie['video_url']:
                print(f"   🎥 Vídeo: {movie['video_url'][:80]}...")
    else:
        print("\n⚠️ Nenhum filme encontrado")
    
    # Salva resultados
    output = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total': len(most_watched),
        'movies': most_watched
    }
    
    filename = 'cnvsweb_results.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Resultados salvos em {filename}")


if __name__ == "__main__":
    main()
