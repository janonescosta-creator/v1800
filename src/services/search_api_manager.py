#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRT Busca - Search API Manager
Gerenciador de APIs de busca com rotação automática
"""

import os
import logging
import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SearchAPIManager:
    """Gerenciador de APIs de busca com rotação automática"""

    def __init__(self):
        """Inicializa o gerenciador"""
        self.api_keys = self._load_api_keys()
        self.key_indices = {provider: 0 for provider in self.api_keys.keys()}
        self.provider_stats = {}

        logger.info(f"🔍 Search API Manager inicializado com {sum(len(keys) for keys in self.api_keys.values())} chaves")

    def _load_api_keys(self) -> Dict[str, List[str]]:
        """Carrega chaves de API do ambiente"""
        api_keys = {}

        providers = ['SERPER', 'GOOGLE', 'EXA', 'FIRECRAWL', 'JINA']

        for provider in providers:
            keys = []

            # Chave principal
            main_key = os.getenv(f"{provider}_API_KEY")
            if main_key:
                keys.append(main_key)

            # Chaves numeradas
            counter = 1
            while True:
                numbered_key = os.getenv(f"{provider}_API_KEY_{counter}")
                if numbered_key:
                    keys.append(numbered_key)
                    counter += 1
                else:
                    break

            if keys:
                api_keys[provider] = keys
                logger.info(f"✅ {provider}: {len(keys)} chaves carregadas")

        return api_keys

    def get_next_api_key(self, provider: str) -> Optional[str]:
        """Obtém próxima chave com rotação"""
        if provider not in self.api_keys or not self.api_keys[provider]:
            return None

        keys = self.api_keys[provider]
        current_index = self.key_indices[provider]

        key = keys[current_index]
        self.key_indices[provider] = (current_index + 1) % len(keys)

        # Atualiza estatísticas
        if provider not in self.provider_stats:
            self.provider_stats[provider] = {'requests': 0, 'successes': 0, 'failures': 0}
        self.provider_stats[provider]['requests'] += 1

        return key

    async def interleaved_search(self, query: str) -> Dict[str, Any]:
        """Executa busca intercalada com múltiplos provedores"""
        logger.info(f"🔍 Iniciando busca intercalada para: {query}")

        search_results = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'all_results': [],
            'successful_searches': 0,
            'failed_searches': 0,
            'consolidated_urls': []
        }

        # Define provedores e suas funções
        search_tasks = []

        if 'SERPER' in self.api_keys:
            search_tasks.append(('SERPER', self._search_serper(query)))

        if 'GOOGLE' in self.api_keys:
            search_tasks.append(('GOOGLE', self._search_google(query)))

        if 'EXA' in self.api_keys:
            search_tasks.append(('EXA', self._search_exa(query)))

        if 'FIRECRAWL' in self.api_keys:
            search_tasks.append(('FIRECRAWL', self._search_firecrawl(query)))

        if 'JINA' in self.api_keys:
            search_tasks.append(('JINA', self._search_jina(query)))

        # Executa buscas em paralelo
        if search_tasks:
            tasks = [task[1] for task in search_tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                provider_name = search_tasks[i][0]

                if isinstance(result, Exception):
                    logger.error(f"❌ Erro em {provider_name}: {result}")
                    search_results['failed_searches'] += 1
                    self.provider_stats[provider_name]['failures'] += 1
                    continue

                if result.get('success'):
                    search_results['all_results'].append(result)
                    search_results['successful_searches'] += 1
                    self.provider_stats[provider_name]['successes'] += 1

                    # Coleta URLs
                    for item in result.get('results', []):
                        url = item.get('url') or item.get('link')
                        if url and url not in search_results['consolidated_urls']:
                            search_results['consolidated_urls'].append(url)
                else:
                    search_results['failed_searches'] += 1
                    self.provider_stats[provider_name]['failures'] += 1

        logger.info(f"✅ Busca intercalada concluída: {search_results['successful_searches']} sucessos")
        return search_results

    async def _search_serper(self, query: str) -> Dict[str, Any]:
        """Busca usando Serper API"""
        try:
            api_key = self.get_next_api_key('SERPER')
            if not api_key:
                return {'success': False, 'error': 'Serper API key não disponível'}

            async with aiohttp.ClientSession() as session:
                headers = {
                    'X-API-KEY': api_key,
                    'Content-Type': 'application/json'
                }

                payload = {
                    'q': f"{query} Brasil",
                    'gl': 'br',
                    'hl': 'pt',
                    'num': 15
                }

                async with session.post(
                    'https://google.serper.dev/search',
                    json=payload,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []

                        for item in data.get('organic', []):
                            results.append({
                                'title': item.get('title', ''),
                                'url': item.get('link', ''),
                                'snippet': item.get('snippet', ''),
                                'source': 'serper'
                            })

                        return {
                            'success': True,
                            'provider': 'SERPER',
                            'results': results
                        }
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}

        except Exception as e:
            logger.error(f"❌ Erro Serper: {e}")
            return {'success': False, 'error': str(e)}

    async def _search_google(self, query: str) -> Dict[str, Any]:
        """Busca usando Google Custom Search"""
        try:
            api_key = self.get_next_api_key('GOOGLE')
            cse_id = os.getenv('GOOGLE_CSE_ID')

            if not api_key or not cse_id:
                return {'success': False, 'error': 'Google API não configurado'}

            async with aiohttp.ClientSession() as session:
                params = {
                    'key': api_key,
                    'cx': cse_id,
                    'q': f"{query} Brasil",
                    'num': 10,
                    'gl': 'br',
                    'hl': 'pt'
                }

                async with session.get(
                    'https://www.googleapis.com/customsearch/v1',
                    params=params,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []

                        for item in data.get('items', []):
                            results.append({
                                'title': item.get('title', ''),
                                'url': item.get('link', ''),
                                'snippet': item.get('snippet', ''),
                                'source': 'google'
                            })

                        return {
                            'success': True,
                            'provider': 'GOOGLE',
                            'results': results
                        }
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}

        except Exception as e:
            logger.error(f"❌ Erro Google: {e}")
            return {'success': False, 'error': str(e)}

    async def _search_exa(self, query: str) -> Dict[str, Any]:
        """Busca usando Exa Neural Search"""
        try:
            api_key = self.get_next_api_key('EXA')
            if not api_key:
                return {'success': False, 'error': 'Exa API key não disponível'}

            async with aiohttp.ClientSession() as session:
                headers = {
                    'x-api-key': api_key,
                    'Content-Type': 'application/json'
                }

                payload = {
                    'query': f"{query} Brasil mercado",
                    'numResults': 10,
                    'useAutoprompt': True,
                    'type': 'neural'
                }

                async with session.post(
                    'https://api.exa.ai/search',
                    json=payload,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []

                        for item in data.get('results', []):
                            results.append({
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'snippet': item.get('text', '')[:300],
                                'source': 'exa'
                            })

                        return {
                            'success': True,
                            'provider': 'EXA',
                            'results': results
                        }
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}

        except Exception as e:
            logger.error(f"❌ Erro Exa: {e}")
            return {'success': False, 'error': str(e)}

    async def _search_firecrawl(self, query: str) -> Dict[str, Any]:
        """Busca usando Firecrawl"""
        try:
            api_key = self.get_next_api_key('FIRECRAWL')
            if not api_key:
                return {'success': False, 'error': 'Firecrawl API key não disponível'}

            # Firecrawl é usado para extrair conteúdo, não para busca direta
            # Retorna resultado vazio por enquanto
            return {
                'success': True,
                'provider': 'FIRECRAWL',
                'results': []
            }

        except Exception as e:
            logger.error(f"❌ Erro Firecrawl: {e}")
            return {'success': False, 'error': str(e)}

    async def _search_jina(self, query: str) -> Dict[str, Any]:
        """Busca usando Jina AI"""
        try:
            api_key = self.get_next_api_key('JINA')
            if not api_key:
                return {'success': False, 'error': 'Jina API key não disponível'}

            # Jina é usado para leitura de conteúdo, não busca direta
            # Retorna resultado vazio por enquanto
            return {
                'success': True,
                'provider': 'JINA',
                'results': []
            }

        except Exception as e:
            logger.error(f"❌ Erro Jina: {e}")
            return {'success': False, 'error': str(e)}

    def get_provider_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos provedores"""
        return self.provider_stats.copy()

    async def execute_massive_search_with_websailor(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Executa busca massiva combinando APIs + WebSailor + Social"""
        logger.info(f"🚀 Iniciando busca massiva com WebSailor para: {query}")

        massive_results = {
            'query': query,
            'session_id': session_id,
            'search_started': datetime.now().isoformat(),
            'api_results': {},
            'websailor_results': {},
            'social_results': {},
            'viral_content': [],
            'screenshots_captured': [],
            'images_extracted': [],
            'statistics': {
                'total_sources': 0,
                'api_sources': 0,
                'websailor_pages': 0,
                'social_posts': 0,
                'screenshots_count': 0,
                'images_count': 0,
                'search_duration': 0
            }
        }

        start_time = time.time()

        try:
            # 1. Executa busca com APIs tradicionais
            logger.info("🔍 Executando busca intercalada com APIs...")
            api_search_results = await self.interleaved_search(query)
            api_results_list = api_search_results.get('all_results', [])
            massive_results['api_results'] = api_results_list
            massive_results['statistics']['api_sources'] = len(api_results_list)

            # Converte resultados para formato compatível
            consolidated_urls = []
            for provider_result in api_results_list:
                if isinstance(provider_result, dict) and provider_result.get('results'):
                    for item in provider_result['results']:
                        url = item.get('url') or item.get('link')
                        if url and url not in consolidated_urls:
                            consolidated_urls.append(url)

            massive_results['consolidated_urls'] = consolidated_urls

            # 2. Executa WebSailor (navegação profunda)
            try:
                logger.info("🌐 Executando Alibaba WebSailor...")
                from .alibaba_websailor import alibaba_websailor

                websailor_result = alibaba_websailor.navigate_and_research_deep(
                    query=query,
                    context=context,
                    max_pages=25,
                    depth_levels=2,
                    session_id=session_id
                )

                massive_results['websailor_results'] = websailor_result
                navegacao_stats = websailor_result.get('navegacao_profunda', {})
                massive_results['statistics']['websailor_pages'] = navegacao_stats.get('total_paginas_analisadas', 0)

                logger.info(f"✅ WebSailor: {massive_results['statistics']['websailor_pages']} páginas analisadas")

            except Exception as e:
                logger.error(f"❌ Erro no WebSailor: {e}")
                massive_results['websailor_results'] = {'error': str(e)}

            # 3. Executa busca social com Playwright
            try:
                logger.info("📱 Executando busca social com Playwright...")
                from .playwright_social_extractor import playwright_social_extractor

                # Executa extração social com imagens
                social_result = await playwright_social_extractor.extract_social_content_with_images(
                    search_results={'all_results': massive_results.get('api_results', [])},
                    session_id=session_id,
                    max_pages=10
                )

                massive_results['social_results'] = social_result
                massive_results['viral_content'] = social_result.get('social_content', [])
                massive_results['screenshots_captured'] = social_result.get('screenshots', [])
                massive_results['images_extracted'] = social_result.get('images_extracted', [])

                massive_results['statistics']['social_posts'] = len(massive_results['viral_content'])
                massive_results['statistics']['screenshots_count'] = len(massive_results['screenshots_captured'])
                massive_results['statistics']['images_count'] = len(massive_results.get('images_extracted', []))

                logger.info(f"✅ Social: {massive_results['statistics']['social_posts']} posts, "
                           f"{massive_results['statistics']['screenshots_count']} screenshots, "
                           f"{massive_results['statistics']['images_count']} imagens")

            except Exception as e:
                logger.error(f"❌ Erro na busca social: {e}")
                massive_results['social_results'] = {'error': str(e)}

            # 4. Executa extração de leads
            try:
                logger.info("🎯 Executando extração de leads...")
                from services.leads import process_leads_from_massive_search, save_leads_locally, extract_lead_data_from_item

                # Monta contexto para extração de leads
                leads_context = {
                    'segmento': context.get('segmento', ''),
                    'produto': context.get('produto', ''),
                    'publico': context.get('publico', ''),
                    'session_id': session_id,
                    'search_results': massive_results
                }

                # Simula busca de leads baseada nos resultados coletados
                leads_extracted = []

                # Extrai leads dos resultados das APIs
                for provider_result in api_results_list:
                    if isinstance(provider_result, dict) and provider_result.get('results'):
                        for item in provider_result['results']:
                            url = item.get('url', item.get('link', 'N/A'))
                            item_leads = extract_lead_data_from_item(item, url)
                            leads_extracted.extend(item_leads)
                
                # Extrai leads dos resultados sociais (se aplicável)
                for social_post in massive_results.get('viral_content', []):
                    # Aqui você pode definir como extrair leads de posts sociais
                    # Por exemplo, se houver um campo de contato ou URL no post
                    pass # Implementar extração de leads de posts sociais se necessário

                # Salva leads encontrados
                if leads_extracted:
                    save_leads_locally(leads_extracted, session_id, query)
                    logger.info(f"🎯 {len(leads_extracted)} leads extraídos e salvos")

                massive_results['leads_extracted'] = leads_extracted
                massive_results['statistics']['leads_count'] = len(leads_extracted)

            except Exception as e:
                logger.error(f"❌ Erro na extração de leads: {e}")
                massive_results['leads_extracted'] = []
                massive_results['statistics']['leads_count'] = 0

            # Calcula estatísticas finais
            massive_results['statistics']['total_sources'] = (
                massive_results['statistics']['api_sources'] +
                massive_results['statistics']['websailor_pages'] +
                massive_results['statistics']['social_posts']
            )

            end_time = time.time()
            massive_results['statistics']['search_duration'] = end_time - start_time

            logger.info(f"✅ Busca massiva concluída: {massive_results['statistics']['total_sources']} fontes, {massive_results['statistics']['leads_count']} leads em {massive_results['statistics']['search_duration']:.2f}s")

            return massive_results

        except Exception as e:
            logger.error(f"❌ Erro crítico na busca massiva: {e}")
            massive_results['error'] = str(e)
            massive_results['statistics']['search_duration'] = time.time() - start_time
            return massive_results

# Instância global
search_api_manager = SearchAPIManager()