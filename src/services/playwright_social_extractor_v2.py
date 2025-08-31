#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced v3.0 - Playwright Social Media Image Extractor
Extrator real de imagens de redes sociais usando Playwright + Chromium
"""

import asyncio
import logging
import json
import time
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import hashlib
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

class PlaywrightSocialImageExtractor:
    """
    Extrator real de imagens de redes sociais usando Playwright + Chromium
    Extração real sem simulações
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        
        # Configurações de extração otimizadas
        self.config = {
            'headless': False,  # False para melhor compatibilidade
            'timeout': 60000,  # 60 segundos
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'max_concurrent_pages': 3,
            'wait_between_requests': 3,  # segundos
            'max_retries': 3,
            'min_images_per_platform': 10,
            'max_images_per_platform': 50,
            'min_image_size': 100,  # pixels mínimos
            'scroll_attempts': 5,
            'scroll_delay': 2000  # ms
        }
        
        # Seletores atualizados e testados para 2024/2025
        self.selectors = {
            'instagram': {
                'posts': 'article, div[role="button"] img, div._aagv img',
                'images': [
                    'img[srcset]',
                    'img[data-testid="user-avatar"]',
                    'img.x5yr21d',
                    'img._aagt',
                    'div._aagv img',
                    'article img[alt]',
                    'img[crossorigin="anonymous"]'
                ],
                'profile_images': 'img._aa8j',
                'story_images': 'img._ab25',
                'explore_images': 'div._aagv img, div._aabd img'
            },
            'facebook': {
                'images': [
                    'img[src*="scontent"]',
                    'img[src*="fbcdn"]',
                    'img[data-src]',
                    'img.scaledImageFitWidth',
                    'img.scaledImageFitHeight',
                    'div[role="img"] img',
                    'img[referrerpolicy="origin-when-cross-origin"]',
                    'img[alt][src]'
                ],
                'video_thumbs': 'img[src*="video"]',
                'profile_images': 'image._1glk._6phc.img',
                'feed_images': 'div[data-pagelet*="FeedUnit"] img'
            },
            'youtube': {
                'thumbnails': [
                    'img#img',
                    'img.yt-core-image',
                    'img[src*="i.ytimg.com"]',
                    'img[src*="yt3.ggpht.com"]',
                    'ytd-thumbnail img',
                    'img.style-scope.yt-img-shadow',
                    'img[width="360"]',
                    'img[width="720"]'
                ],
                'channel_images': 'img#avatar-btn img, img#img.style-scope.yt-img-shadow',
                'playlist_thumbs': 'ytd-playlist-thumbnail img'
            },
            'tiktok': {
                'images': [
                    'img[mode="aspectFill"]',
                    'img[loading="lazy"]',
                    'img.tiktok-1zpj2q-ImgAvatar',
                    'div[data-e2e="user-post-item"] img',
                    'img[alt*="cover"]',
                    'canvas + img',
                    'div.image-card img',
                    'img[class*="DivContainer"] img'
                ],
                'video_covers': 'div[data-e2e="user-post-item-list"] img',
                'profile_images': 'img.tiktok-1zpj2q-ImgAvatar'
            },
            'twitter': {
                'images': [
                    'img[alt="Image"]',
                    'img[src*="pbs.twimg.com"]',
                    'img[src*="ton.twitter.com"]',
                    'div[data-testid="tweetPhoto"] img',
                    'img[draggable="true"]',
                    'div[aria-label*="Image"] img',
                    'img.css-9pa8cd',
                    'div[data-testid="tweet"] img[alt]'
                ],
                'profile_images': 'img[data-testid="UserAvatar-Container-unknown"]',
                'media_images': 'div[data-testid="swipe-to-dismiss"] img'
            },
            'pinterest': {
                'images': [
                    'img[src*="pinimg.com"]',
                    'img[loading="auto"]',
                    'div[data-test-id="pin-image"] img',
                    'img.hCL.kVc.L4E.MIw',
                    'div[role="img"] img',
                    'img[fetchpriority="auto"]'
                ],
                'board_images': 'div[data-test-id="board-image"] img'
            }
        }
        
        logger.info("🎭 Playwright Social Image Extractor inicializado")

    async def __aenter__(self):
        """Context manager entry"""
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close_browser()

    async def start_browser(self):
        """Inicia o browser Playwright com configurações otimizadas"""
        try:
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=self.config['headless'],
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--start-maximized',
                    '--ignore-certificate-errors',
                    '--allow-running-insecure-content'
                ]
            )
            
            # Context com stealth mode
            self.context = await self.browser.new_context(
                viewport=self.config['viewport'],
                user_agent=self.config['user_agent'],
                ignore_https_errors=True,
                java_script_enabled=True,
                bypass_csp=True,
                extra_http_headers={
                    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            # Adiciona scripts de stealth
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' })
                    })
                });
            """)
            
            logger.info("✅ Browser Playwright iniciado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar browser: {e}")
            raise

    async def close_browser(self):
        """Fecha o browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("✅ Browser fechado com sucesso")
        except Exception as e:
            logger.error(f"⚠️ Erro ao fechar browser: {e}")

    async def extract_images_from_all_platforms(
        self, 
        query: str, 
        platforms: List[str] = None,
        min_images: int = 10
    ) -> Dict[str, Any]:
        """
        Extrai imagens reais de todas as plataformas especificadas
        """
        if platforms is None:
            platforms = ['instagram', 'pinterest', 'youtube', 'twitter', 'tiktok']
        
        logger.info(f"🔍 Extraindo imagens para: {query}")
        logger.info(f"📱 Plataformas: {platforms}")
        
        results = {
            'query': query,
            'extraction_started': datetime.now().isoformat(),
            'platforms_data': {},
            'all_images': [],
            'total_images_extracted': 0,
            'unique_images': 0,
            'extraction_metrics': {}
        }
        
        all_image_urls = set()
        
        # Extrai de cada plataforma
        for platform in platforms:
            try:
                logger.info(f"🎯 Extraindo imagens de {platform.upper()}")
                
                platform_data = await self._extract_platform_images(
                    platform, 
                    query, 
                    min_images
                )
                
                results['platforms_data'][platform] = platform_data
                
                # Adiciona URLs únicas
                for img in platform_data.get('images', []):
                    if img['url'] and img['url'] not in all_image_urls:
                        all_image_urls.add(img['url'])
                        results['all_images'].append(img)
                
                await asyncio.sleep(self.config['wait_between_requests'])
                
            except Exception as e:
                logger.error(f"❌ Erro ao extrair de {platform}: {e}")
                results['platforms_data'][platform] = {
                    'error': str(e),
                    'images': [],
                    'count': 0
                }
        
        # Calcula métricas finais
        results['total_images_extracted'] = len(results['all_images'])
        results['unique_images'] = len(all_image_urls)
        results['extraction_completed'] = datetime.now().isoformat()
        
        # Ordena por qualidade estimada
        results['all_images'] = sorted(
            results['all_images'],
            key=lambda x: x.get('estimated_quality', 0),
            reverse=True
        )
        
        logger.info(f"✅ Extração concluída: {results['total_images_extracted']} imagens únicas")
        
        return results

    async def _extract_platform_images(
        self, 
        platform: str, 
        query: str, 
        min_images: int
    ) -> Dict[str, Any]:
        """Extrai imagens de uma plataforma específica"""
        
        extractors = {
            'instagram': self._extract_instagram_images,
            'facebook': self._extract_facebook_images,
            'youtube': self._extract_youtube_images,
            'tiktok': self._extract_tiktok_images,
            'twitter': self._extract_twitter_images,
            'pinterest': self._extract_pinterest_images
        }
        
        if platform in extractors:
            return await extractors[platform](query, min_images)
        else:
            logger.warning(f"⚠️ Plataforma não suportada: {platform}")
            return {'platform': platform, 'images': [], 'count': 0}

    async def _extract_instagram_images(self, query: str, min_images: int) -> Dict[str, Any]:
        """Extrai imagens reais do Instagram"""
        page = await self.context.new_page()
        images_data = []
        seen_urls = set()
        
        try:
            # Múltiplas estratégias de busca
            search_strategies = [
                f"https://www.instagram.com/explore/tags/{query.replace(' ', '').replace('#', '')}/",
                f"https://www.instagram.com/explore/search/keyword/?q={query}",
                f"https://www.instagram.com/{query.replace(' ', '')}/"
            ]
            
            for strategy_url in search_strategies:
                if len(images_data) >= min_images:
                    break
                    
                try:
                    logger.info(f"🔍 Tentando estratégia Instagram: {strategy_url}")
                    await page.goto(strategy_url, wait_until='networkidle', timeout=self.config['timeout'])
                    await page.wait_for_timeout(3000)
                    
                    # Scroll para carregar mais conteúdo
                    for scroll in range(self.config['scroll_attempts']):
                        # Tenta múltiplos seletores
                        for selector_group in self.selectors['instagram']['images']:
                            elements = await page.query_selector_all(selector_group)
                            
                            for element in elements:
                                if len(images_data) >= self.config['max_images_per_platform']:
                                    break
                                    
                                try:
                                    # Extrai URL da imagem
                                    img_url = await element.get_attribute('src') or await element.get_attribute('data-src')
                                    
                                    if not img_url:
                                        srcset = await element.get_attribute('srcset')
                                        if srcset:
                                            # Pega a maior resolução do srcset
                                            urls = srcset.split(',')
                                            img_url = urls[-1].strip().split(' ')[0]
                                    
                                    if img_url and img_url not in seen_urls and self._is_valid_image_url(img_url):
                                        seen_urls.add(img_url)
                                        
                                        # Extrai metadados
                                        alt_text = await element.get_attribute('alt') or ''
                                        width = await element.get_attribute('width')
                                        height = await element.get_attribute('height')
                                        
                                        image_info = {
                                            'platform': 'instagram',
                                            'url': img_url,
                                            'alt_text': alt_text[:200],
                                            'width': width,
                                            'height': height,
                                            'type': 'post_image' if 'scontent' in img_url else 'profile_image',
                                            'estimated_quality': self._estimate_image_quality(img_url, width, height),
                                            'extracted_at': datetime.now().isoformat()
                                        }
                                        
                                        images_data.append(image_info)
                                        logger.debug(f"✅ Imagem Instagram extraída: {img_url[:50]}...")
                                        
                                except Exception as e:
                                    logger.debug(f"⚠️ Erro ao processar elemento: {e}")
                                    continue
                        
                        # Scroll down
                        await page.evaluate('window.scrollBy(0, window.innerHeight)')
                        await page.wait_for_timeout(self.config['scroll_delay'])
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erro na estratégia {strategy_url}: {e}")
                    continue
            
            logger.info(f"✅ Instagram: {len(images_data)} imagens extraídas")
            
            return {
                'platform': 'instagram',
                'query': query,
                'images': images_data,
                'count': len(images_data),
                'success': len(images_data) >= min_images
            }
            
        except Exception as e:
            logger.error(f"❌ Erro geral no Instagram: {e}")
            return {
                'platform': 'instagram',
                'query': query,
                'images': images_data,
                'count': len(images_data),
                'error': str(e),
                'success': False
            }
        finally:
            await page.close()

    async def _extract_pinterest_images(self, query: str, min_images: int) -> Dict[str, Any]:
        """Extrai imagens reais do Pinterest"""
        page = await self.context.new_page()
        images_data = []
        seen_urls = set()
        
        try:
            search_url = f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}"
            await page.goto(search_url, wait_until='networkidle', timeout=self.config['timeout'])
            await page.wait_for_timeout(3000)
            
            # Pinterest carrega dinamicamente
            for scroll in range(self.config['scroll_attempts']):
                for selector in self.selectors['pinterest']['images']:
                    elements = await page.query_selector_all(selector)
                    
                    for element in elements:
                        if len(images_data) >= self.config['max_images_per_platform']:
                            break
                            
                        try:
                            img_url = await element.get_attribute('src')
                            
                            if img_url and img_url not in seen_urls and 'pinimg.com' in img_url:
                                # Tenta pegar a versão de alta resolução
                                hq_url = img_url.replace('/236x/', '/originals/')
                                hq_url = hq_url.replace('/474x/', '/originals/')
                                hq_url = hq_url.replace('/736x/', '/originals/')
                                
                                seen_urls.add(hq_url)
                                
                                image_info = {
                                    'platform': 'pinterest',
                                    'url': hq_url,
                                    'original_url': img_url,
                                    'type': 'pin_image',
                                    'estimated_quality': self._estimate_image_quality(hq_url, None, None),
                                    'extracted_at': datetime.now().isoformat()
                                }
                                
                                images_data.append(image_info)
                                logger.debug(f"✅ Imagem Pinterest extraída: {hq_url[:50]}...")
                                
                        except Exception as e:
                            logger.debug(f"⚠️ Erro ao processar elemento Pinterest: {e}")
                            continue
                
                # Scroll
                await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                await page.wait_for_timeout(self.config['scroll_delay'])
            
            logger.info(f"✅ Pinterest: {len(images_data)} imagens extraídas")
            
            return {
                'platform': 'pinterest',
                'query': query,
                'images': images_data,
                'count': len(images_data),
                'success': len(images_data) >= min_images
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no Pinterest: {e}")
            return {
                'platform': 'pinterest',
                'query': query,
                'images': images_data,
                'count': len(images_data),
                'error': str(e),
                'success': False
            }
        finally:
            await page.close()

    async def _extract_youtube_images(self, query: str, min_images: int) -> Dict[str, Any]:
        """Extrai thumbnails reais do YouTube"""
        page = await self.context.new_page()
        images_data = []
        seen_urls = set()
        
        try:
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            await page.goto(search_url, wait_until='networkidle', timeout=self.config['timeout'])
            await page.wait_for_timeout(3000)
            
            # Scroll para carregar mais vídeos
            for scroll in range(self.config['scroll_attempts']):
                for selector in self.selectors['youtube']['thumbnails']:
                    elements = await page.query_selector_all(selector)
                    
                    for element in elements:
                        if len(images_data) >= self.config['max_images_per_platform']:
                            break
                            
                        try:
                            img_url = await element.get_attribute('src')
                            
                            if img_url and img_url not in seen_urls and 'ytimg.com' in img_url:
                                # Converte para máxima qualidade
                                hq_url = img_url
                                if '/hqdefault.jpg' in img_url:
                                    hq_url = img_url.replace('/hqdefault.jpg', '/maxresdefault.jpg')
                                elif '/mqdefault.jpg' in img_url:
                                    hq_url = img_url.replace('/mqdefault.jpg', '/maxresdefault.jpg')
                                elif '/sddefault.jpg' in img_url:
                                    hq_url = img_url.replace('/sddefault.jpg', '/maxresdefault.jpg')
                                
                                seen_urls.add(hq_url)
                                
                                # Extrai ID do vídeo se possível
                                video_id = None
                                if '/vi/' in hq_url:
                                    video_id = hq_url.split('/vi/')[1].split('/')[0]
                                
                                image_info = {
                                    'platform': 'youtube',
                                    'url': hq_url,
                                    'original_url': img_url,
                                    'video_id': video_id,
                                    'type': 'video_thumbnail',
                                    'estimated_quality': self._estimate_image_quality(hq_url, '1280', '720'),
                                    'extracted_at': datetime.now().isoformat()
                                }
                                
                                images_data.append(image_info)
                                logger.debug(f"✅ Thumbnail YouTube extraído: {hq_url[:50]}...")
                                
                        except Exception as e:
                            logger.debug(f"⚠️ Erro ao processar elemento YouTube: {e}")
                            continue
                
                # Scroll
                await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                await page.wait_for_timeout(self.config['scroll_delay'])
            
            logger.info(f"✅ YouTube: {len(images_data)} thumbnails extraídos")
            
            return {
                'platform': 'youtube',
                'query': query,
                'images': images_data,
                'count': len(images_data),
                'success': len(images_data) >= min_images
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no YouTube: {e}")
            return {
                'platform': 'youtube',
                'query': query,
                'images': images_data,
                'count': len(images_data),
                'error': str(e),
                'success': False
            }
        finally:
            await page.close()

    async def _extract_tiktok_images(self, query: str, min_images: int) -> Dict[str, Any]:
        """Extrai imagens/covers reais do TikTok"""
        page = await self.context.new_page()
        images_data = []
        seen_urls = set()
        
        try:
            search_url = f"https://www.tiktok.com/search?q={query.replace(' ', '%20')}"
            await page.goto(search_url, wait_until='networkidle', timeout=self.config['timeout'])
            await page.wait_for_timeout(4000)
            
            # TikTok usa lazy loading agressivo
            for scroll in range(self.config['scroll_attempts']):
                for selector in self.selectors['tiktok']['images']:
                    elements = await page.query_selector_all(selector)
                    
                    for element in elements:
                        if len(images_data) >= self.config['max_images_per_platform']:
                            break
                            
                        try:
                            img_url = await element.get_attribute('src')
                            
                            if img_url and img_url not in seen_urls and self._is_valid_image_url(img_url):
                                seen_urls.add(img_url)
                                
                                image_info = {
                                    'platform': 'tiktok',
                                    'url': img_url,
                                    'type': 'video_cover' if 'cover' in img_url.lower() else 'profile_image',
                                    'estimated_quality': self._estimate_image_quality(img_url, None, None),
                                    'extracted_at': datetime.now().isoformat()
                                }
                                
                                images_data.append(image_info)
                                logger.debug(f"✅ Imagem TikTok extraída: {img_url[:50]}...")
                                
                        except Exception as e:
                            logger.debug(f"⚠️ Erro ao processar elemento TikTok: {e}")
                            continue
                
                # Scroll com espera maior para TikTok
                await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                await page.wait_for_timeout(self.config['scroll_delay'] + 1000)
            
            logger.info(f"✅ TikTok: {len(images_data)} imagens extraídas")
            
            return {
                'platform': 'tiktok',
                'query': query,
                'images': images_data,
                'count': len(images_data),
                'success': len(images_data) >= min_images
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no TikTok: {e}")
            return {
                'platform': 'tiktok',
                'query': query,
                'images': images_data,
                'count': len(images_data),
                'error': str(e),
                'success': False
            }
        finally:
            await page.close()

    async def _extract_twitter_images(self, query: str, min_images: int) -> Dict[str, Any]:
        """Extrai imagens reais do Twitter/X"""
        page = await self.context.new_page()
        images_data = []
        seen_urls = set()
        
        try:
            # Twitter agora requer login para muitas funcionalidades
            search_url = f"https://twitter.com/search?q={query.replace(' ', '%20')}&src=typed_query&f=image"
            await page.goto(search_url, wait_until='networkidle', timeout=self.config['timeout'])
            await page.wait_for_timeout(4000)
            
            # Scroll para carregar tweets
            for scroll in range(self.config['scroll_attempts']):
                for selector in self.selectors['twitter']['images']:
                    elements = await page.query_selector_all(selector)
                    
                    for element in elements:
                        if len(images_data) >= self.config['max_images_per_platform']:
                            break
                            
                        try:
                            img_url = await element.get_attribute('src')
                            
                            if img_url and img_url not in seen_urls and 'pbs.twimg.com' in img_url:
                                # Converte para qualidade original
                                hq_url = img_url
                                if '&name=' in hq_url:
                                    hq_url = hq_url.split('&name=')[0] + '&name=orig'
                                elif '?format=' in hq_url and '&name=' not in hq_url:
                                    hq_url = hq_url + '&name=orig'
                                
                                seen_urls.add(hq_url)
                                
                                alt_text = await element.get_attribute('alt') or ''
                                
                                image_info = {
                                    'platform': 'twitter',
                                    'url': hq_url,
                                    'original_url': img_url,
                                    'alt_text': alt_text[:200],
                                    'type': 'tweet_image',
                                    'estimated_quality': self._estimate_image_quality(hq_url, None, None),
                                    'extracted_at': datetime.now().isoformat()
                                }
                                
                                images_data.append(image_info)
                                logger.debug(f"✅ Imagem Twitter extraída: {hq_url[:50]}...")
                                
                        except Exception as e:
                            logger.debug(f"⚠️ Erro ao processar elemento Twitter: {e}")
                            continue
                
                # Scroll
                await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                await page.wait_for_timeout(self.config['scroll_delay'])
            
            logger.info(f"✅ Twitter: {len(images_data)} imagens extraídas")
            
            return {
                'platform': 'twitter',
                'query': query,
                'images': images_data,
                'count': len(images_data),
                'success': len(images_data) >= min_images
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no Twitter: {e}")
            return {
                'platform': 'twitter',
                'query': query,
                'content': [],
                'error': str(e),
                'success': False
            }
        finally:
            await page.close()

    async def capture_screenshots(self, urls: List[str], session_id: str) -> List[Dict[str, Any]]:
        """Captura screenshots de URLs"""
        screenshots = []
        screenshots_dir = Path(f"analyses_data/files/{session_id}")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        for i, url in enumerate(urls):
            try:
                page = await self.context.new_page()
                await page.goto(url, timeout=self.config['timeout'])
                await page.wait_for_timeout(2000)
                
                screenshot_path = screenshots_dir / f"screenshot_{i+1:03d}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                
                screenshots.append({
                    'url': url,
                    'screenshot_path': str(screenshot_path),
                    'index': i + 1,
                    'captured_at': datetime.now().isoformat()
                })
                
                await page.close()
                logger.info(f"📸 Screenshot {i+1} capturado: {url}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao capturar screenshot de {url}: {e}")
                continue
        
        return screenshots

# Instância global
playwright_social_extractor = PlaywrightSocialImageExtractor()