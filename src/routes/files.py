#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced v2.0 - Routes para gerenciamento de arquivos
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from services.local_file_manager import local_file_manager

logger = logging.getLogger(__name__)

files_bp = Blueprint('files', __name__)

@files_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload de arquivo"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nome de arquivo vazio'}), 400

        filename = secure_filename(file.filename)
        file_path = local_file_manager.save_file(file, filename)

        return jsonify({
            'success': True,
            'file_path': file_path,
            'filename': filename
        })

    except Exception as e:
        logger.error(f"Erro no upload: {str(e)}")
        return jsonify({'error': str(e)}), 500

@files_bp.route('/list', methods=['GET'])
def list_files():
    """Lista arquivos disponíveis"""
    try:
        files = local_file_manager.list_files()
        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@files_bp.route('/cleanup_old_files', methods=['POST'])
def cleanup_old_files():
    """Remove arquivos antigos (mais de 30 dias)"""

    try:
        data = request.get_json() or {}
        days_old = int(data.get('days_old', 30))
        dry_run = data.get('dry_run', True)  # Por padrão, apenas simula

        cutoff_date = datetime.now() - timedelta(days=days_old)

        files_to_remove = []
        total_size_to_remove = 0

        # Busca arquivos antigos
        for root, dirs, files in os.walk(local_file_manager.base_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

                    if file_mtime < cutoff_date:
                        file_size = os.path.getsize(file_path)
                        files_to_remove.append({
                            'path': file_path,
                            'name': file,
                            'size': file_size,
                            'modified': file_mtime.isoformat()
                        })
                        total_size_to_remove += file_size

                        # Remove arquivo se não for dry run
                        if not dry_run:
                            os.remove(file_path)
                            logger.info(f"🗑️ Arquivo removido: {file}")

                except Exception as e:
                    logger.error(f"Erro ao processar arquivo {file}: {str(e)}")
                    continue

        action = "Simulação de limpeza" if dry_run else "Limpeza executada"

        return jsonify({
            'success': True,
            'action': action,
            'files_found': len(files_to_remove),
            'total_size_mb': round(total_size_to_remove / (1024 * 1024), 2),
            'cutoff_date': cutoff_date.isoformat(),
            'files': files_to_remove if dry_run else [],
            'dry_run': dry_run
        })

    except Exception as e:
        logger.error(f"Erro na limpeza de arquivos: {str(e)}")
        return jsonify({
            'error': 'Erro na limpeza de arquivos',
            'message': str(e)
        }), 500

@files_bp.route('/download/<path:file_path>')
def download_file(file_path):
    """Download de arquivo"""
    try:
        full_path = os.path.join(local_file_manager.base_dir, file_path)
        if os.path.exists(full_path):
            return send_file(full_path, as_attachment=True)
        else:
            return jsonify({'error': 'Arquivo não encontrado'}), 404
    except Exception as e:
        logger.error(f"Erro no download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@files_bp.route('/delete', methods=['POST'])
def delete_file():
    """Deleta arquivo específico"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')

        if not file_path:
            return jsonify({'error': 'Caminho do arquivo não fornecido'}), 400

        success = local_file_manager.delete_file(file_path)

        if success:
            return jsonify({'success': True, 'message': 'Arquivo removido com sucesso'})
        else:
            return jsonify({'error': 'Falha ao remover arquivo'}), 500

    except Exception as e:
        logger.error(f"Erro ao deletar arquivo: {str(e)}")
        return jsonify({'error': str(e)}), 500